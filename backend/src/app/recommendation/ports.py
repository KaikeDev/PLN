"""Porta da recomendação no site: o que a API precisa para sugerir filmes parecidos."""

from typing import Protocol


class SimilarMoviesProvider(Protocol):
    """Filmes mais parecidos com um filme, por uma representação das sinopses."""

    representation_name: str

    def similar(self, movie_id: int, k: int) -> list[tuple[int, float]] | None:
        """Pares (id, similaridade) dos k filmes mais parecidos; None quando o filme não está na amostra."""
        ...
