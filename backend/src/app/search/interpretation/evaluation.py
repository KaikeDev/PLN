"""Métricas da interpretação: cada sistema contra o gabarito, no total e por categoria.

- **Acerto exato:** todos os campos iguais ao gabarito (o período com a tolerância abaixo).
- **F1 de gêneros incluídos e de excluídos:** micro, somando acertos e erros de todas as frases. Fica None
  quando nem o gabarito nem o sistema têm gênero.
- **Período:** os dois limites batem; um limite bate quando os dois são nulos ou quando os anos diferem
  em no máximo um ("depois de Matrix" pode começar em 1999 ou em 2000).
- **Qualidade:** `bem_avaliado` igual.
- **Filtro inventado:** o sistema pôs um gênero, uma exclusão, um limite de data ou a qualidade que o
  gabarito não tem. É o erro mais caro, porque esconde filmes certos.

Uma resposta que falhou (`None`) conta como errada em tudo e não inventa filtro.
"""

from collections.abc import Sequence

from app.representations.metrics import rounded
from app.search.interpretation.dataset import CATEGORIES, Judgement

YEAR_TOLERANCE = 1


def bound_matches(expected: str | None, predicted: str | None) -> bool:
    """Limites nulos nos dois, ou anos a no máximo `YEAR_TOLERANCE` de distância."""
    if expected is None or predicted is None:
        return expected is predicted
    return abs(int(expected[:4]) - int(predicted[:4])) <= YEAR_TOLERANCE


def period_matches(expected: Judgement, predicted: Judgement) -> bool:
    return bound_matches(expected["lancado_depois"], predicted["lancado_depois"]) and bound_matches(
        expected["lancado_antes"], predicted["lancado_antes"]
    )


def exact_match(expected: Judgement, predicted: Judgement | None) -> bool:
    return (
        predicted is not None
        and set(expected["generos"]) == set(predicted["generos"])
        and set(expected["generos_excluidos"]) == set(predicted["generos_excluidos"])
        and period_matches(expected, predicted)
        and expected["bem_avaliado"] == predicted["bem_avaliado"]
    )


def invented(expected: Judgement, predicted: Judgement | None) -> list[str]:
    """Filtros que o sistema pôs e o gabarito não tem, em texto curto."""
    if predicted is None:
        return []
    extra = [f"gênero {name}" for name in sorted(set(predicted["generos"]) - set(expected["generos"]))]
    extra += [f"sem {name}" for name in sorted(set(predicted["generos_excluidos"]) - set(expected["generos_excluidos"]))]
    for field, label in (("lancado_depois", "lançado depois"), ("lancado_antes", "lançado antes")):
        if predicted[field] is not None and expected[field] is None:
            extra.append(f"{label} de {predicted[field]}")
    if predicted["bem_avaliado"] and not expected["bem_avaliado"]:
        extra.append("bem avaliado")
    return extra


def scores(pairs: Sequence[tuple[Judgement, Judgement | None]]) -> dict:
    """Métricas de um sistema sobre pares (gabarito, previsão)."""
    counts = {field: [0, 0, 0] for field in ("generos", "generos_excluidos")}
    for expected, predicted in pairs:
        for field, tally in counts.items():
            gold, guess = set(expected[field]), set(predicted[field]) if predicted else set()
            tally[0] += len(gold & guess)
            tally[1] += len(guess - gold)
            tally[2] += len(gold - guess)
    total = len(pairs)
    return {
        "frases": total,
        "acerto_exato": _rate(sum(exact_match(e, p) for e, p in pairs), total),
        "f1_generos": _f1(*counts["generos"]),
        "f1_excluidos": _f1(*counts["generos_excluidos"]),
        "acerto_periodo": _rate(sum(p is not None and period_matches(e, p) for e, p in pairs), total),
        "acerto_qualidade": _rate(sum(p is not None and e["bem_avaliado"] == p["bem_avaliado"] for e, p in pairs), total),
        "filtro_inventado": sum(bool(invented(e, p)) for e, p in pairs),
        "falhas": sum(p is None for _, p in pairs),
    }


def evaluate(predictions: Sequence[dict], systems: Sequence[str]) -> dict:
    """Métricas de cada sistema no total e por categoria; `predictions` traz `esperado` e `<sistema>.filtros`."""
    result: dict = {"sistemas": list(systems), "total": {}, "por_categoria": {}}
    for system in systems:
        result["total"][system] = scores([(row["esperado"], row[system]["filtros"]) for row in predictions])
    for category in CATEGORIES:
        rows = [row for row in predictions if row["categoria"] == category]
        if rows:
            result["por_categoria"][category] = {
                system: scores([(row["esperado"], row[system]["filtros"]) for row in rows]) for system in systems
            }
    return result


def usage(predictions: Sequence[dict], system: str) -> dict:
    """Tokens médios, provedores que responderam e falhas de um sistema com LLM."""
    answered = [row[system] for row in predictions if row[system]["filtros"] is not None]
    providers: dict[str, int] = {}
    for item in answered:
        providers[item["provedor"]] = providers.get(item["provedor"], 0) + 1
    errors: dict[str, int] = {}
    for row in predictions:
        if (reason := row[system].get("motivo_da_falha")) is not None:
            errors[reason] = errors.get(reason, 0) + 1
    return {
        "respostas": len(answered),
        "tokens_entrada_medio": rounded(sum(item["tokens_entrada"] for item in answered) / len(answered), 1) if answered else None,
        "tokens_saida_medio": rounded(sum(item["tokens_saida"] for item in answered) / len(answered), 1) if answered else None,
        "provedores": dict(sorted(providers.items())),
        "falhas_por_motivo": dict(sorted(errors.items())),
    }


def _rate(hits: int, total: int) -> float | None:
    return rounded(hits / total, 4) if total else None


def _f1(tp: int, fp: int, fn: int) -> float | None:
    return rounded(2 * tp / (2 * tp + fp + fn), 4) if tp + fp + fn else None
