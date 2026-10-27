"""Métricas do sentimento com LLM, calculadas da mesma forma para o LLM e para as predições gravadas.

- **Polaridade:** acurácia, F1 macro e matriz de confusão, só sobre as críticas respondidas; as falhas são
  contadas à parte. Com a amostra equilibrada, o F1 do TF-IDF e do BERTimbau é recalculado nela: o 0,856 e o
  0,867 da Aula 9 valem para o conjunto completo, com 71% de positivas.
- **Nota:** erro absoluto médio e fração a até 1 ponto. A referência ingênua é a média das notas das
  críticas fora da amostra.
- **Estratos:** com e sem negação, do autor principal e dos demais.
- **Mesmas críticas:** quando alguma variante falhou (por cota), todos os sistemas também são medidos só nas
  críticas que todas as variantes responderam, para comparar coisas iguais.
- **Concordância:** em quais críticas a variante escolhida acerta e os dois modelos treinados erram, e o contrário.
- **Estabilidade:** a mesma crítica pedida duas vezes à variante escolhida.
"""

from collections.abc import Sequence
from statistics import mean

from app.representations.metrics import rounded
from app.sentiment.config import LABEL_NAMES

STRATA = (("com_negacao", True), ("com_negacao", False), ("autor_principal", True), ("autor_principal", False))
RATING_TOLERANCE = 1.0


def polarity_scores(pairs: Sequence[tuple[str, str | None]]) -> dict:
    """Acurácia, F1 macro e matriz de confusão das previsões respondidas; `None` é falha."""
    answered = [(real, guess) for real, guess in pairs if guess is not None]
    confusion = {real: {guess: 0 for guess in LABEL_NAMES} for real in LABEL_NAMES}
    for real, guess in answered:
        confusion[real][guess] += 1
    f1s = []
    for label in LABEL_NAMES:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in LABEL_NAMES if other != label)
        fn = sum(confusion[label][other] for other in LABEL_NAMES if other != label)
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0)
    return {
        "respondidas": len(answered),
        "falhas": len(pairs) - len(answered),
        "acuracia": rounded(sum(real == guess for real, guess in answered) / len(answered), 4) if answered else None,
        "f1_macro": rounded(mean(f1s), 4) if answered else None,
        "confusao": confusion,
    }


def rating_scores(pairs: Sequence[tuple[float, float | None]]) -> dict:
    """Erro absoluto médio e fração a até um ponto, sobre as notas respondidas."""
    errors = [abs(real - guess) for real, guess in pairs if guess is not None]
    return {
        "respondidas": len(errors),
        "erro_absoluto_medio": rounded(mean(errors), 3) if errors else None,
        "ate_1_ponto": rounded(sum(error <= RATING_TOLERANCE for error in errors) / len(errors), 4) if errors else None,
    }


def evaluate(rows: Sequence[dict], systems: Sequence[str], mean_rating: float, llm_systems: Sequence[str] = ()) -> dict:
    """Polaridade e nota de cada sistema no total e por estrato; `rows` são as linhas de `predictions.jsonl`."""

    def polarity(subset: Sequence[dict], system: str) -> dict:
        return polarity_scores([(row["polaridade_real"], row[system]["polaridade"]) for row in subset])

    def rating(subset: Sequence[dict], system: str) -> dict:
        return rating_scores([(row["nota_real"], row[system]["nota"]) for row in subset])

    strata = {}
    for field, value in STRATA:
        subset = [row for row in rows if row[field] is value]
        strata[f"{field}={str(value).lower()}"] = {"criticas": len(subset), **{system: polarity(subset, system) for system in systems}}
    common = [row for row in rows if all(row[system]["polaridade"] is not None for system in llm_systems)]
    return {
        "criticas": len(rows),
        "sistemas": list(systems),
        "mesmas_criticas": {
            "criticas": len(common),
            "polaridade": {system: polarity(common, system) for system in systems},
            "nota": {system: rating(common, system) for system in systems},
        },
        "polaridade": {system: polarity(rows, system) for system in systems},
        "nota": {
            "media_fora_da_amostra": {"valor": rounded(mean_rating, 3), **rating_scores([(row["nota_real"], mean_rating) for row in rows])},
            **{system: rating(rows, system) for system in systems},
        },
        "por_estrato": strata,
    }


def agreement(rows: Sequence[dict], variant: str, references: Sequence[str]) -> dict:
    """Críticas em que a variante acerta e todas as referências erram, e o contrário, pelos IDs do TMDB."""

    def correct(row: dict, system: str) -> bool:
        return row[system]["polaridade"] == row["polaridade_real"]

    answered = [row for row in rows if row[variant]["polaridade"] is not None]
    llm_only = [row["review_id"] for row in answered if correct(row, variant) and not any(correct(row, ref) for ref in references)]
    references_only = [row["review_id"] for row in answered if not correct(row, variant) and all(correct(row, ref) for ref in references)]
    return {"variante": variant, "so_o_llm_acerta": llm_only, "so_os_modelos_treinados_acertam": references_only}


def stability(pairs: Sequence[tuple[dict, dict]]) -> dict:
    """Respostas iguais entre o primeiro e o segundo pedido da mesma crítica (as duas precisam ter respondido)."""
    answered = [(first, second) for first, second in pairs if first["polaridade"] is not None and second["polaridade"] is not None]
    if not answered:
        return {"repetidas": len(pairs), "respondidas": 0, "polaridade_igual": None, "nota_igual": None, "diferenca_media_da_nota": None}
    return {
        "repetidas": len(pairs),
        "respondidas": len(answered),
        "polaridade_igual": rounded(mean(first["polaridade"] == second["polaridade"] for first, second in answered), 4),
        "nota_igual": rounded(mean(first["nota"] == second["nota"] for first, second in answered), 4),
        "diferenca_media_da_nota": rounded(mean(abs(first["nota"] - second["nota"]) for first, second in answered), 3),
    }


def usage(rows: Sequence[dict], system: str) -> dict:
    """Tokens médios, provedores que responderam e falhas por motivo de uma variante."""
    answered = [row[system] for row in rows if row[system]["polaridade"] is not None]
    providers: dict[str, int] = {}
    for item in answered:
        providers[item["provedor"]] = providers.get(item["provedor"], 0) + 1
    failures: dict[str, int] = {}
    for row in rows:
        if (reason := row[system]["motivo_da_falha"]) is not None:
            failures[reason] = failures.get(reason, 0) + 1
    return {
        "respostas": len(answered),
        "tokens_entrada_medio": rounded(mean(item["tokens_entrada"] for item in answered), 1) if answered else None,
        "tokens_saida_medio": rounded(mean(item["tokens_saida"] for item in answered), 1) if answered else None,
        "provedores": dict(sorted(providers.items())),
        "falhas_por_motivo": dict(sorted(failures.items())),
    }
