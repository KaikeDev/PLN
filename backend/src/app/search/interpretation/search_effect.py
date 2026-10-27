"""Efeito da interpretação na busca por tema, nas consultas anotadas da amostra (`config/busca/consultas.json`).

Cinco formas de ordenar, com as mesmas métricas da busca híbrida (ADR 0020):

- `frase`: a frase preparada por `strip_request`, como o site faz hoje (é o MAP de referência, 0,627);
- `tema`: o tema que o LLM separou, ou a frase quando ele não separou nada;
- `frase_com_filtros_das_regras`: a frase, sem os filmes que os filtros das regras recusam;
- `frase_com_filtros_do_llm`: a frase, sem os filmes que os filtros do LLM recusam;
- `tema_com_filtros_do_llm`: o tema, sem os filmes que os filtros do LLM recusam.

As três últimas mostram o custo de um filtro errado: um relevante recusado some da lista. A diferença entre as
duas últimas é o efeito de trocar a frase pelo tema no site.
"""

from collections.abc import Callable, Sequence
from statistics import mean

from app.representations.config import QuerySpec
from app.representations.metrics import average_precision, precision_at_k, reciprocal_rank, rounded
from app.search.filters import ExtractedFilters
from app.search.ports import PreferenceExtractor, SynopsisIndex

RANKINGS = ("frase", "tema", "frase_com_filtros_das_regras", "frase_com_filtros_do_llm", "tema_com_filtros_do_llm")
K = 5


def search_effect(
    index: SynopsisIndex,
    queries: Sequence[QuerySpec],
    rules: PreferenceExtractor,
    interpret: Callable[[str], ExtractedFilters | None],
) -> dict:
    """Métricas de cada forma de ordenar e o que cada intérprete extraiu de cada consulta.

    `interpret` devolve os filtros do LLM com o tema, ou None quando ele falhou; nesse caso o tema é a frase e não há filtro.
    """
    per_query = []
    rankings: dict[str, list[list[int]]] = {name: [] for name in RANKINGS}
    for query in queries:
        by_rules = rules.extract(query.text)
        by_llm = interpret(query.text)
        theme = by_llm.theme if by_llm is not None and by_llm.theme else query.text
        phrase_ids = [movie_id for movie_id, _ in index.rank(query.text)]
        theme_ids = [movie_id for movie_id, _ in index.rank(theme)]
        lists = {
            "frase": phrase_ids,
            "tema": theme_ids,
            "frase_com_filtros_das_regras": [movie_id for movie_id in phrase_ids if by_rules.accepts(index.movie(movie_id))],
            "frase_com_filtros_do_llm": [movie_id for movie_id in phrase_ids if by_llm is None or by_llm.accepts(index.movie(movie_id))],
            "tema_com_filtros_do_llm": [movie_id for movie_id in theme_ids if by_llm is None or by_llm.accepts(index.movie(movie_id))],
        }
        for name, ids in lists.items():
            rankings[name].append(ids)
        per_query.append(
            {
                "id": query.id,
                "texto": query.text,
                "tema": theme if by_llm is not None and by_llm.theme else None,
                "llm_falhou": by_llm is None,
                "relevantes_recusados_pelas_regras": _refused(index, query, by_rules),
                "relevantes_recusados_pelo_llm": _refused(index, query, by_llm) if by_llm is not None else [],
                "precisao_media": {name: rounded(average_precision(_ranks(lists[name], query))) for name in RANKINGS},
            }
        )
    return {
        "k": K,
        "consultas": len(queries),
        "metricas": {name: _metrics(rankings[name], queries) for name in RANKINGS},
        "por_consulta": per_query,
    }


def _ranks(ids: list[int], query: QuerySpec) -> list[int | None]:
    positions = {movie_id: position for position, movie_id in enumerate(ids, 1)}
    return [positions.get(movie_id) for movie_id in query.relevant_ids]


def _metrics(lists: list[list[int]], queries: Sequence[QuerySpec]) -> dict:
    rows = []
    for ids, query in zip(lists, queries, strict=True):
        ranks = _ranks(ids, query)
        first = min((rank for rank in ranks if rank is not None), default=None)
        rows.append((reciprocal_rank(first), first is not None and first <= K, average_precision(ranks), precision_at_k(ranks, K)))
    return {
        "mrr": rounded(mean(row[0] for row in rows)),
        "acerto_at_k": rounded(mean(row[1] for row in rows)),
        "map": rounded(mean(row[2] for row in rows)),
        "precisao_at_k": rounded(mean(row[3] for row in rows)),
    }


def _refused(index: SynopsisIndex, query: QuerySpec, filters: ExtractedFilters) -> list[int]:
    return [movie_id for movie_id in query.relevant_ids if not filters.accepts(index.movie(movie_id))]
