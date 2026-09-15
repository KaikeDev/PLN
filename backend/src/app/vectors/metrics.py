"""Métricas puras, sem estado e testáveis isoladamente."""

from collections import Counter
from collections.abc import Sequence


def rounded(value: float, digits: int = 6) -> float:
    """Arredonda para saídas JSON estáveis entre execuções."""
    return round(float(value), digits)


def purity(genres: Sequence[int], clusters: Sequence[int]) -> float:
    """Fração de filmes que pertencem ao gênero majoritário do próprio cluster."""
    if len(genres) != len(clusters):
        raise ValueError("Rótulos e clusters desalinhados")
    if not genres:
        return 0.0
    by_cluster: dict[int, Counter] = {}
    for genre, cluster in zip(genres, clusters, strict=True):
        by_cluster.setdefault(cluster, Counter())[genre] += 1
    return sum(counts.most_common(1)[0][1] for counts in by_cluster.values()) / len(genres)


def genre_agreement(genres: frozenset[int], others: Sequence[frozenset[int]]) -> float:
    """Fração de `others` que compartilha ao menos um gênero com `genres`."""
    return sum(bool(genres & other) for other in others) / len(others) if others else 0.0


def reciprocal_rank(rank: int | None) -> float:
    return 1 / rank if rank else 0.0
