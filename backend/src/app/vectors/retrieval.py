"""Consultas em linguagem natural projetadas no mesmo espaço vetorial das sinopses."""

from dataclasses import dataclass

from app.vectors.corpus import ProcessedCorpus
from app.vectors.metrics import rounded
from app.vectors.space import Encoded, Representation


@dataclass(frozen=True)
class SearchResult:
    """Consulta codificada e pares (id, cosseno) com similaridade positiva, em ordem decrescente."""

    query: Encoded
    ranked: tuple[tuple[int, float], ...]

    def rank_of(self, movie_id: int) -> int | None:
        """Posição (a partir de 1) entre os filmes com cosseno positivo; None caso contrário."""
        return next((position for position, (ranked_id, _) in enumerate(self.ranked, 1) if ranked_id == movie_id), None)

    def top(self, corpus: ProcessedCorpus, k: int) -> list[dict]:
        return [
            {"rank": position, "id": movie_id, "title": corpus.by_id[movie_id].title, "score": rounded(score)}
            for position, (movie_id, score) in enumerate(self.ranked[:k], 1)
        ]


def search(representation: Representation, corpus: ProcessedCorpus, text: str) -> SearchResult:
    """Codifica `text` no espaço da representação e ordena as sinopses por cosseno."""
    query = representation.encode(text, corpus)
    scores = representation.cosine(query.vector)[0]
    ranked = tuple((representation.ids[row], float(scores[row])) for row in representation.ranking(scores) if scores[row] > 0)
    return SearchResult(query, ranked)
