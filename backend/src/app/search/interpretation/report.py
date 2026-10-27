"""Relatório Markdown da avaliação da interpretação: regras × LLM zero-shot × LLM few-shot × reserva.

Só usa dados determinísticos (gabarito, respostas gravadas e métricas). A latência fica no manifesto,
porque muda a cada execução (ADR 0009).
"""

from collections.abc import Sequence

from app.representations.report import number
from app.search.interpretation.dataset import CATEGORIES, Judgement
from app.search.interpretation.evaluation import exact_match, invented

SYSTEM_LABELS = {
    "regras": "Regras (ADR 0005)",
    "zero_shot": "LLM zero-shot",
    "few_shot": "LLM few-shot",
    "reserva": "Site: LLM com reserva nas regras",
}
CATEGORY_LABELS = {
    "explicita": "Explícita",
    "parafrase": "Paráfrase",
    "negacao": "Negação",
    "periodo": "Período",
    "armadilha_lexica": "Armadilha léxica",
    "sem_filtro": "Sem filtro",
}
RANKING_LABELS = {
    "frase": "Frase preparada (busca atual)",
    "tema": "Tema separado pelo LLM",
    "frase_com_filtros_das_regras": "Frase + filtros das regras",
    "frase_com_filtros_do_llm": "Frase + filtros do LLM",
    "tema_com_filtros_do_llm": "Tema + filtros do LLM",
}
MAX_EXAMPLES = 8


def make_report(
    metrics: dict, predictions: Sequence[dict], site_variant: str, reference_date: str, models: Sequence[str], effect: dict | None
) -> str:
    systems = metrics["avaliacao"]["sistemas"]
    lines = [
        "# Interpretação da consulta: regras × LLM",
        "",
        f"{len(predictions)} frases anotadas antes da execução (`config/busca/interpretacao.json`), com data de referência {reference_date}. "
        f"Modelos que responderam: {', '.join(f'`{model}`' for model in models) or 'nenhum'}. "
        f"A variante usada no site é **{site_variant}**; a linha “Site” é essa variante com queda para as regras quando o LLM falha.",
        "",
        "## Resultado geral",
        "",
        "| Sistema | Acerto exato | F1 gêneros | F1 excluídos | Período | Qualidade | Filtro inventado | Falhas |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system in systems:
        item = metrics["avaliacao"]["total"][system]
        lines.append(
            f"| {SYSTEM_LABELS[system]} | {number(item['acerto_exato'], 2)} | {number(item['f1_generos'], 2)} | "
            f"{number(item['f1_excluidos'], 2)} | {number(item['acerto_periodo'], 2)} | {number(item['acerto_qualidade'], 2)} | "
            f"{item['filtro_inventado']} de {item['frases']} | {item['falhas']} |"
        )
    lines += [
        "",
        "Período: os anos de cada limite podem diferir em um. Filtro inventado: frases em que o sistema pôs um filtro que o gabarito não tem.",
        "",
        "## Por categoria",
        "",
        "Acerto exato e, entre parênteses, frases com filtro inventado.",
        "",
        "| Categoria | Frases | " + " | ".join(SYSTEM_LABELS[system] for system in systems) + " |",
        "|---|---:|" + "---:|" * len(systems),
    ]
    for category in CATEGORIES:
        by_system = metrics["avaliacao"]["por_categoria"].get(category)
        if not by_system:
            continue
        cells = [f"{number(by_system[system]['acerto_exato'], 2)} ({by_system[system]['filtro_inventado']})" for system in systems]
        lines.append(f"| {CATEGORY_LABELS[category]} | {by_system[systems[0]]['frases']} | " + " | ".join(cells) + " |")
    lines += ["", "## Custo", "", "| Variante | Respostas | Tokens de entrada (média) | Tokens de saída (média) | Provedores | Falhas |"]
    lines.append("|---|---:|---:|---:|---|---|")
    for variant, item in metrics["uso"].items():
        providers = ", ".join(f"{name}: {count}" for name, count in item["provedores"].items()) or "—"
        failures = ", ".join(f"{name}: {count}" for name, count in item["falhas_por_motivo"].items()) or "nenhuma"
        lines.append(
            f"| {SYSTEM_LABELS[variant]} | {item['respostas']} | {number(item['tokens_entrada_medio'], 1)} | "
            f"{number(item['tokens_saida_medio'], 1)} | {providers} | {failures} |"
        )
    lines += [
        "",
        f"No site, a reserva caiu para as regras em {metrics['reserva']['quedas_para_regras']} frase(s). "
        "A latência de cada variante está em `manifest.json`: ela muda a cada execução e não entra nos arquivos de conteúdo.",
        "",
    ]
    lines += _examples(predictions, site_variant)
    if effect is not None:
        lines += _effect(effect)
    return "\n".join(lines) + "\n"


def describe(value: Judgement | None) -> str:
    """Filtros em texto curto."""
    if value is None:
        return "falhou"
    parts = [", ".join(value["generos"])] if value["generos"] else []
    parts += [f"sem {name}" for name in value["generos_excluidos"]]
    if value["lancado_depois"] or value["lancado_antes"]:
        parts.append(f"{(value['lancado_depois'] or '')[:4]}–{(value['lancado_antes'] or '')[:4]}")
    if value["bem_avaliado"]:
        parts.append("bem avaliado")
    return "; ".join(parts) or "nenhum filtro"


def _examples(predictions: Sequence[dict], variant: str) -> list[str]:
    groups: dict[str, list[dict]] = {
        "LLM acerta e regras erram": [],
        "Regras acertam e LLM erra": [],
        "Os dois erram": [],
    }
    for row in predictions:
        rules_ok = exact_match(row["esperado"], row["regras"]["filtros"])
        llm_ok = exact_match(row["esperado"], row[variant]["filtros"])
        if llm_ok and not rules_ok:
            groups["LLM acerta e regras erram"].append(row)
        elif rules_ok and not llm_ok:
            groups["Regras acertam e LLM erra"].append(row)
        elif not rules_ok and not llm_ok:
            groups["Os dois erram"].append(row)
    lines = ["## Exemplos", "", f"Comparação entre as regras e a variante do site ({variant}); no máximo {MAX_EXAMPLES} por grupo.", ""]
    for title, rows in groups.items():
        lines += [f"### {title} ({len(rows)})", ""]
        if not rows:
            lines += ["Nenhuma frase.", ""]
            continue
        lines += ["| Frase | Categoria | Gabarito | Regras | LLM | Inventado pelo LLM |", "|---|---|---|---|---|---|"]
        for row in rows[:MAX_EXAMPLES]:
            extra = ", ".join(invented(row["esperado"], row[variant]["filtros"])) or "—"
            lines.append(
                f"| “{row['texto']}” | {CATEGORY_LABELS[row['categoria']]} | {describe(row['esperado'])} | "
                f"{describe(row['regras']['filtros'])} | {describe(row[variant]['filtros'])} | {extra} |"
            )
        lines.append("")
    return lines


def _effect(effect: dict) -> list[str]:
    k = effect["k"]
    lines = [
        "## Efeito na busca por tema",
        "",
        f"{effect['consultas']} consultas anotadas (`config/busca/consultas.json`) na amostra de 428 filmes, com a busca híbrida do site. "
        "Com filtros, um filme relevante recusado pelo filtro some da lista.",
        "",
        f"| Ordenação | MAP | Precisão @{k} | MRR | Acerto @{k} |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, item in effect["metricas"].items():
        lines.append(
            f"| {RANKING_LABELS[name]} | {number(item['map'], 3)} | {number(item['precisao_at_k'], 2)} | "
            f"{number(item['mrr'], 3)} | {number(item['acerto_at_k'], 2)} |"
        )
    lines += ["", "| Consulta | Tema do LLM | Relevantes recusados (regras) | Relevantes recusados (LLM) | AP frase | AP tema |"]
    lines.append("|---|---|---:|---:|---:|---:|")
    for item in effect["por_consulta"]:
        theme = "falhou" if item["llm_falhou"] else (f"“{item['tema']}”" if item["tema"] else "—")
        lines.append(
            f"| “{item['texto']}” | {theme} | {len(item['relevantes_recusados_pelas_regras'])} | "
            f"{len(item['relevantes_recusados_pelo_llm'])} | {number(item['precisao_media']['frase'], 3)} | "
            f"{number(item['precisao_media']['tema'], 3)} |"
        )
    return [*lines, ""]
