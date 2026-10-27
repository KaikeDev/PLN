"""Relatório Markdown da avaliação do RAG: ordenação × busca híbrida, métricas automáticas e as respostas para os juízes.

A fidelidade e a utilidade dependem do julgamento humano (`config/rag/rubrica.md`), feito depois e fora desta
pasta, que é imutável; a concordância entre os juízes sai de `python -m app.rag agreement`.
"""

from collections.abc import Sequence

from app.rag.config import RagConfig
from app.representations.report import number

CATEGORY_LABELS = {"tema": "Tema", "opiniao": "Opinião", "sem_resposta": "Sem resposta", "injecao": "Injeção"}


def make_report(
    metrics: dict, predictions: Sequence[dict], without_reviews: Sequence[dict], models: Sequence[str], config: RagConfig
) -> str:
    ranking = metrics["ordenacao"]
    lines = [
        "# RAG: perguntas sobre os filmes da amostra",
        "",
        f"Contexto do site: {config.k} filmes, até {config.excerpts_per_movie} trechos de crítica de cerca de {config.excerpt_chars} caracteres "
        f"por filme e até {config.max_cited} filmes citados. Modelos que responderam: {', '.join(f'`{model}`' for model in models) or 'nenhum'}. "
        f"Filtros da pergunta: {metrics['interpretacao']['llm']} frases interpretadas pelo LLM e {metrics['interpretacao']['regras']} pelas regras.",
        "",
        "## A. Ordenação: os filmes citados são melhores que os 5 primeiros da busca?",
        "",
        "Nas 20 consultas anotadas (`config/busca/consultas.json`). A precisão dos citados é a fração dos filmes citados que são relevantes; "
        "a revocação no contexto é a fração dos relevantes trazidos pela busca que o LLM citou (ele não alcança o que a busca não trouxe).",
        "",
        "| Sistema | Precisão | Revocação no contexto | Filmes por resposta | Tokens de entrada (média) | Falhas |",
        "|---|---:|---:|---:|---:|---:|",
        f"| Busca híbrida, 5 primeiros | {number(ranking['busca_hibrida_sozinha']['precisao_at_5'], 3)} | — | 5 | — | — |",
    ]
    for key, item in ranking.items():
        if key.startswith("k_"):
            lines.append(
                f"| RAG, {key[2:]} filmes no contexto | {number(item['precisao_dos_citados'], 3)} | {number(item['revocacao_no_contexto'], 3)} | "
                f"{number(item['citados_por_resposta'], 2)} | {number(item['tokens_entrada_medio'], 0)} | {item['falhas']} |"
            )
    lines += ["", "## B e C. Perguntas: métricas automáticas", ""]
    lines += _question_table(metrics["perguntas"])
    lines += [
        "",
        "Recusou: `contexto_suficiente` falso, o certo nas perguntas sem resposta. Citação inventada: filme fora do contexto, removido pela "
        "conferência antes de mostrar. Injeção obedecida: sinal automático na resposta bruta (palavras do pedido), a confirmar pelos juízes.",
        "",
    ]
    if metrics["sem_criticas"] is not None:
        lines += ["## D. Sem trechos de crítica no contexto", ""]
        lines += _question_table(metrics["sem_criticas"])
        lines.append("")
    usage = metrics["uso"]
    providers = ", ".join(f"{name}: {count}" for name, count in usage["provedores"].items()) or "—"
    failures = ", ".join(f"{name}: {count}" for name, count in usage["falhas_por_motivo"].items()) or "nenhuma"
    lines += [
        "## Custo",
        "",
        f"{usage['respostas']} respostas; tokens de entrada {number(usage['tokens_entrada_medio'], 0)} e de saída {number(usage['tokens_saida_medio'], 0)} "
        f"em média; provedores: {providers}; falhas: {failures}. A latência está em `manifest.json`.",
        "",
        "## Respostas para o julgamento",
        "",
        "O contexto completo de cada resposta (filmes, pontuação e trechos) está em `predictions.jsonl`.",
        "",
    ]
    for row in predictions:
        lines += [f"### {row['id']} ({CATEGORY_LABELS[row['categoria']]}): “{row['pergunta']}”", ""]
        if row["falha"]:
            lines += [f"Falhou: {row['falha']}", ""]
            continue
        cited = "; ".join(f"[F{item['id']}] {item['titulo']}" for item in row["citados"]) or "nenhum"
        notes = []
        if row["inventadas"]:
            notes.append(f"citações inventadas removidas: {row['inventadas']}")
        if row["trocada"]:
            notes.append("resposta trocada por “não encontrei”")
        lines += [f"> {_quote(row['resposta'])}", "", f"Citados: {cited}." + (f" Conferência: {'; '.join(notes)}." if notes else ""), ""]
    return "\n".join(lines) + "\n"


def _question_table(scores: dict) -> list[str]:
    lines = [
        "| Categoria | Perguntas | Respondidas | Recusou | Citações inventadas | Trocadas por “não encontrei” | Filmes por resposta | Injeção obedecida |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for category, label in CATEGORY_LABELS.items():
        item = scores.get(category)
        if item is None:
            continue
        obeyed = "—" if item["injecao_obedecida"] is None else str(item["injecao_obedecida"])
        lines.append(
            f"| {label} | {item['perguntas']} | {item['respondidas']} | {item['recusou']} | {item['citacoes_inventadas']} | "
            f"{item['trocadas_por_nao_encontrei']} | {number(item['citados_por_resposta'], 2)} | {obeyed} |"
        )
    return lines


def _quote(text: str) -> str:
    return " ".join(str(text).split())
