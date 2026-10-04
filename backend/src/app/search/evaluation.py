"""Avaliação da busca com consultas anotadas: posição dos relevantes, MRR, acerto @k, MAP e precisão @k.

Roda sobre cada representação no pipeline de `app.representations`; a seção do relatório fica aqui.
"""

from statistics import mean
from typing import Any

from app.representations.analyses import Analysis
from app.representations.context import AnalysisContext
from app.representations.metrics import average_precision, precision_at_k, reciprocal_rank, rounded
from app.representations.report import number
from app.representations.space import Representation
from app.search.retrieval import search


class Retrieval(Analysis):
    """Busca (recuperação de informação): posição dos filmes relevantes, MRR e acerto @k das consultas anotadas."""

    name = "retrieval"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return retrieval_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        k, corpus = context.config.neighbors_k, context.corpus
        items: list[dict[str, Any]] = []
        for query in context.queries:
            result = search(representation, corpus, query.text)
            relevant: list[dict[str, Any]] = [
                {
                    "id": movie_id,
                    "title": corpus.by_id[movie_id].title,
                    "rank": result.rank_of(movie_id),
                    "explanation": representation.explain(result.query, representation.document(corpus.ids.index(movie_id)), 5),
                }
                for movie_id in query.relevant_ids
            ]
            ranks = [item["rank"] for item in relevant]
            first = min((rank for rank in ranks if rank is not None), default=None)
            items.append(
                {
                    "id": query.id,
                    "text": query.text,
                    "note": query.note,
                    "tokens": list(result.query.tokens),
                    "out_of_vocabulary": list(result.query.out_of_vocabulary),
                    "null_vector": result.query.null,
                    "retrieved": len(result.ranked),
                    "relevant": relevant,
                    "reciprocal_rank": rounded(reciprocal_rank(first)),
                    "hit_at_k": first is not None and first <= k,
                    "average_precision": rounded(average_precision(ranks)),
                    "precision_at_k": rounded(precision_at_k(ranks, k)),
                    "top": result.top(corpus, k),
                }
            )
        return {
            "k": k,
            "mean_reciprocal_rank": rounded(mean(item["reciprocal_rank"] for item in items)) if items else None,
            "hit_rate_at_k": rounded(mean(item["hit_at_k"] for item in items)) if items else None,
            "mean_average_precision": rounded(mean(item["average_precision"] for item in items)) if items else None,
            "mean_precision_at_k": rounded(mean(item["precision_at_k"] for item in items)) if items else None,
            "queries": items,
        }


def retrieval_section(results: dict, context: AnalysisContext) -> list[str]:
    names = context.representation_names
    if not context.queries:
        return []
    k = context.config.neighbors_k
    lines = [
        "## Busca: consultas anotadas",
        "",
        "Busca é recuperação de informação: um texto de consulta vira um vetor no mesmo espaço das sinopses, que são ordenadas pelo cosseno. "
        "A consulta passa pelas mesmas regras de preparação da entrada de cada representação. "
        "A posição é a do primeiro filme anotado como relevante entre os filmes com cosseno positivo. "
        "MRR e acerto só olham o primeiro relevante; a precisão média (MAP) considera a posição de todos, "
        f"e a precisão @{k} é a fração relevante dos {k} primeiros resultados.",
        "",
        f"| Representação | MRR | Acerto @{k} | MAP | Precisão @{k} |",
        "|---|---:|---:|---:|---:|",
    ]
    lines += [
        f"| {name} | {number(results[name]['mean_reciprocal_rank'])} | {number(results[name]['hit_rate_at_k'])} | "
        f"{number(results[name]['mean_average_precision'])} | {number(results[name]['mean_precision_at_k'])} |"
        for name in names
    ]
    for index, query in enumerate(context.queries):
        lines += ["", f"### {query.id}: “{query.text}”", ""]
        if query.note:
            lines += [query.note, ""]
        total = len(query.relevant_ids)
        lines += [
            f"{total} filme(s) relevante(s).",
            "",
            f"| Representação | Primeiro relevante | Relevantes no top {k} | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |",
            "|---|---:|---:|---:|---|---|---|",
        ]
        for name in names:
            item = results[name]["queries"][index]
            found = sorted((r for r in item["relevant"] if r["rank"] is not None), key=lambda r: r["rank"])
            rank = found[0]["rank"] if found else None
            in_top = sum(1 for r in found if r["rank"] <= k)
            oov = ", ".join(item["out_of_vocabulary"]) or "—"
            explanation = ", ".join(found[0]["explanation"]) if found and found[0]["explanation"] else "—"
            top = "; ".join(f"{result['title']} ({result['score']:.3f})" for result in item["top"][:3])
            top = top or ("vetor nulo" if item["null_vector"] else "nenhum filme com cosseno positivo")
            lines.append(
                f"| {name} | {rank if rank is not None else 'não recuperado'} | {in_top} de {total} | {number(item['average_precision'], 3)} | "
                f"{oov} | {explanation} | {top} |"
            )
    return [*lines, ""]
