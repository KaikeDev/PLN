"""Relatório Markdown do sentimento com LLM: as três variantes e a reserva × TF-IDF × BERTimbau nas mesmas críticas.

Só usa dados determinísticos; a latência fica no manifesto (ADR 0009).
"""

from collections.abc import Mapping, Sequence

from app.representations.report import number
from app.sentiment.llm.prompt import SentimentLLMConfig
from app.sentiment.llm.sample import Review

SYSTEM_LABELS = {
    "tfidf": "TF-IDF (fora da dobra)",
    "bertimbau": "BERTimbau (fora da dobra)",
    "zero_shot": "LLM zero-shot",
    "few_shot": "LLM few-shot",
    "zero_shot_sem_justificativa": "LLM zero-shot sem justificativa",
    "reserva": "LLM reserva",
}
STRATUM_LABELS = {
    "com_negacao=true": "Com negação",
    "com_negacao=false": "Sem negação",
    "autor_principal=true": "Autor principal",
    "autor_principal=false": "Demais autores",
}
EXAMPLES = 3
EXCERPT_CHARS = 300


def make_report(
    metrics: dict,
    rows: Sequence[dict],
    cases: Sequence[dict],
    config: SentimentLLMConfig,
    models: Sequence[str],
    reviews: Mapping[str, Review],
) -> str:
    evaluation = metrics["avaliacao"]
    systems = evaluation["sistemas"]
    chosen = config.chosen_variant
    labels = {**SYSTEM_LABELS, "reserva": f"LLM reserva ({config.reserve_provider}, {chosen})"}
    lines = [
        "# Sentimento com LLM × modelos treinados",
        "",
        f"{evaluation['criticas']} críticas do TMDB sorteadas antes das chamadas (`config/sentimento/sentimento_llm_amostra.json`), metade negativas e "
        f"metade positivas, metade do autor principal. {metrics['criticas_cortadas']} críticas passaram de {config.sample.max_chars} caracteres e "
        f"foram cortadas no meio, igual para todas as variantes. Modelos que responderam: {', '.join(f'`{model}`' for model in models) or 'nenhum'}. "
        f"As variantes de prompt rodam em `{config.main_provider}`, e a reserva repete a variante escolhida (**{chosen}**) em `{config.reserve_provider}`. "
        "O TF-IDF e o BERTimbau são as predições fora da dobra da Aula 9: nenhum dos sistemas viu essas críticas antes.",
        "",
        "## Polaridade",
        "",
        "| Sistema | F1 macro | Acurácia | Negativas lidas como positivas | Positivas lidas como negativas | Falhas |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for system in systems:
        item = evaluation["polaridade"][system]
        confusion = item["confusao"]
        lines.append(
            f"| {labels[system]} | {number(item['f1_macro'], 3)} | {number(item['acuracia'], 3)} | "
            f"{confusion['negativo']['positivo']} | {confusion['positivo']['negativo']} | {item['falhas']} |"
        )
    lines += [
        "",
        "Na Aula 9, o F1 macro de 0,856 (TF-IDF) e 0,867 (BERTimbau) foi medido no conjunto completo, com 71% de positivas; "
        "aqui ele é recalculado na amostra equilibrada. As métricas do LLM contam só as críticas respondidas.",
        "",
        "### Por estrato (F1 macro)",
        "",
        "| Sistema | "
        + " | ".join(f"{STRATUM_LABELS[name]} ({stratum['criticas']})" for name, stratum in evaluation["por_estrato"].items())
        + " |",
        "|---|" + "---:|" * len(evaluation["por_estrato"]),
    ]
    for system in systems:
        cells = [number(stratum[system]["f1_macro"], 3) for stratum in evaluation["por_estrato"].values()]
        lines.append(f"| {labels[system]} | " + " | ".join(cells) + " |")
    lines += ["", "## Nota", "", "| Sistema | Erro absoluto médio | Até 1 ponto | Respondidas |", "|---|---:|---:|---:|"]
    baseline = evaluation["nota"]["media_fora_da_amostra"]
    lines.append(
        f"| Média das notas fora da amostra ({number(baseline['valor'], 2)}) | {number(baseline['erro_absoluto_medio'], 2)} | "
        f"{number(baseline['ate_1_ponto'], 2)} | {baseline['respondidas']} |"
    )
    for system in systems:
        item = evaluation["nota"][system]
        lines.append(
            f"| {labels[system]} | {number(item['erro_absoluto_medio'], 2)} | {number(item['ate_1_ponto'], 2)} | {item['respondidas']} |"
        )
    common = evaluation["mesmas_criticas"]
    if common["criticas"] < evaluation["criticas"]:
        lines += [
            "",
            f"## Nas mesmas críticas ({common['criticas']} de {evaluation['criticas']})",
            "",
            "Alguma variante falhou em parte das críticas; aqui todos os sistemas são medidos só nas que todas as variantes responderam.",
            "",
            "| Sistema | F1 macro | Acurácia | Erro absoluto médio da nota |",
            "|---|---:|---:|---:|",
        ]
        lines += [
            f"| {labels[system]} | {number(common['polaridade'][system]['f1_macro'], 3)} | {number(common['polaridade'][system]['acuracia'], 3)} | "
            f"{number(common['nota'][system]['erro_absoluto_medio'], 2)} |"
            for system in systems
        ]
    lines += _agreement(metrics["concordancia"], rows, reviews, labels)
    lines += _cases(cases, chosen)
    lines += _stability(metrics["estabilidade"], chosen)
    lines += ["## Custo", "", "| Variante | Respostas | Tokens de entrada (média) | Tokens de saída (média) | Provedores | Falhas |"]
    lines.append("|---|---:|---:|---:|---|---|")
    for variant, item in metrics["uso"].items():
        providers = ", ".join(f"{name}: {count}" for name, count in item["provedores"].items()) or "—"
        failures = ", ".join(f"{name}: {count}" for name, count in item["falhas_por_motivo"].items()) or "nenhuma"
        lines.append(
            f"| {labels[variant]} | {item['respostas']} | {number(item['tokens_entrada_medio'], 1)} | "
            f"{number(item['tokens_saida_medio'], 1)} | {providers} | {failures} |"
        )
    lines += ["", "A latência de cada variante está em `manifest.json`: ela muda a cada execução e não entra nos arquivos de conteúdo.", ""]
    return "\n".join(lines)


def _agreement(agreement: dict, rows: Sequence[dict], reviews: Mapping[str, Review], labels: Mapping[str, str]) -> list[str]:
    variant = agreement["variante"]
    by_id = {row["review_id"]: row for row in rows}
    groups = {
        f"Só o LLM ({variant}) acerta: os dois modelos treinados erram": agreement["so_o_llm_acerta"],
        "Só os modelos treinados acertam: o LLM erra": agreement["so_os_modelos_treinados_acertam"],
    }
    lines = ["", "## Onde os sistemas discordam", ""]
    for title, ids in groups.items():
        lines += [f"### {title} ({len(ids)})", ""]
        if not ids:
            lines += ["Nenhuma crítica.", ""]
            continue
        lines += ["| Filme | Nota do autor | Trecho | LLM | TF-IDF | BERTimbau |", "|---|---:|---|---|---|---|"]
        for review_id in ids[:EXAMPLES]:
            row = by_id[review_id]
            llm = row[variant]
            reason = f" — {_cell(llm['justificativa'])}" if llm["justificativa"] else ""
            lines.append(
                f"| {_cell(row['titulo'])} | {row['nota_real']:g} | {_cell(_excerpt(reviews[review_id].text))} | "
                f"{llm['polaridade']}, {llm['nota']:g}{reason} | {_reference(row['tfidf'])} | {_reference(row['bertimbau'])} |"
            )
        lines.append("")
    return lines


def _cases(cases: Sequence[dict], chosen: str) -> list[str]:
    lines = [
        "## Casos da equipe",
        "",
        f"Críticas escritas pela equipe (as da aba do site), fora das métricas. TF-IDF da tela e LLM ({chosen}). "
        "O BERTimbau não entra aqui: o experimento não guarda um modelo treinado com ele.",
        "",
        "| Tipo | Crítica | TF-IDF da tela | LLM |",
        "|---|---|---|---|",
    ]
    for case in cases:
        screen = case["tfidf_da_tela"]
        screen_text = (
            f"{screen['polaridade']} ({screen['probabilidade_positiva']:.0%} positiva), nota {screen['nota']:g}" if screen else "—"
        )
        llm = case["llm"]
        llm_text = (
            f"{llm['polaridade']}, nota {llm['nota']:g}" + (f" — {_cell(llm['justificativa'])}" if llm["justificativa"] else "")
            if llm["polaridade"]
            else f"falhou ({llm['motivo_da_falha']})"
        )
        lines.append(f"| {case['tipo']} | {_cell(case['texto'])} | {screen_text} | {llm_text} |")
    return [*lines, ""]


def _stability(result: dict, chosen: str) -> list[str]:
    if not result["repetidas"]:
        return []
    return [
        "## Estabilidade",
        "",
        f"{result['repetidas']} críticas pedidas duas vezes ao LLM ({chosen}), com temperatura 0; {result['respondidas']} responderam nas duas.",
        "",
        "| Polaridade igual | Nota igual | Diferença média da nota |",
        "|---:|---:|---:|",
        f"| {number(result['polaridade_igual'], 2)} | {number(result['nota_igual'], 2)} | {number(result['diferenca_media_da_nota'], 2)} |",
        "",
    ]


def _reference(item: dict) -> str:
    return f"{item['polaridade']} ({item['probabilidade_positiva']:.0%}), nota {item['nota']:.1f}"


def _excerpt(text: str) -> str:
    return text if len(text) <= EXCERPT_CHARS else text[:EXCERPT_CHARS].rsplit(" ", 1)[0] + "…"


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "/")
