"""Recomendação filme → filmes para o site (ADR 0023).

É a mesma conta da análise `Recommendation`: os k filmes de maior cosseno com o filme escolhido, sem
contar o próprio filme, com empates resolvidos pelo ID. Usa uma representação já construída, para que
o site não carregue outro modelo.
"""

import numpy as np

from app.representations.space import Representation


class SimilarMovies:
    """Filmes mais parecidos com um filme da amostra, por cosseno numa representação."""

    def __init__(self, representation: Representation) -> None:
        self._representation = representation
        self._rows = {movie_id: row for row, movie_id in enumerate(representation.ids)}
        self.representation_name = representation.spec.name

    def similar(self, movie_id: int, k: int) -> list[tuple[int, float]] | None:
        """Pares (id, cosseno) dos k filmes mais parecidos; None quando o filme não está na amostra."""
        row = self._rows.get(movie_id)
        if row is None:
            return None
        representation = self._representation
        scores = representation.cosine(representation.unit[row : row + 1])[0].astype(np.float64)
        scores[row] = -np.inf
        return [(representation.ids[other], float(scores[other])) for other in representation.ranking(scores)[:k]]
