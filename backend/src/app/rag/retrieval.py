"""Recuperação do RAG: a mesma busca do site, mais os títulos citados na pergunta e os trechos das críticas.

1. O intérprete da busca (LLM com reserva nas regras, ADR 0030) extrai os filtros da pergunta.
2. Filmes cujo título aparece na pergunta ("o que acharam de Oppenheimer?") entram primeiro: a sinopse de um
   filme raramente traz o próprio título, e a busca por tema não os acharia. Valem títulos com pelo menos
   `MIN_TITLE_CHARS` caracteres, inteiros ou até os dois-pontos ("Top Gun" em "Top Gun: Maverick"), como
   palavras inteiras, e no máximo metade do contexto: "Homem-Aranha" casa com a franquia inteira.
3. O restante vem da busca híbrida (ADR 0020), pela pergunta inteira, sem os filmes que os filtros recusam.
4. Os `k` primeiros recebem até `excerpts_per_movie` trechos de crítica cada.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from app.rag.config import RagConfig
from app.rag.reviews import Excerpt, ReviewStore
from app.search.filters import ExtractedFilters
from app.search.ports import PreferenceExtractor, SynopsisIndex
from app.search.rules.normalization import normalize

MIN_TITLE_CHARS = 5


@dataclass(frozen=True)
class RetrievedMovie:
    """Filme do contexto: dados de exibição, pontuação da busca (None quando veio do título) e trechos de crítica."""

    id: int
    score: float | None
    movie: dict
    excerpts: tuple[Excerpt, ...]
    reviews: int


@dataclass(frozen=True)
class Retrieval:
    filters: ExtractedFilters
    movies: tuple[RetrievedMovie, ...]


class TitleMatcher:
    """Encontra na pergunta os títulos do catálogo, como palavras inteiras e sem diferença de acento ou caixa."""

    def __init__(self, titles: Mapping[int, str]) -> None:
        keys: dict[str, set[int]] = {}
        for movie_id, title in titles.items():
            for variant in {title, title.split(":")[0]}:
                key = normalize(variant).strip(" .")
                if len(key) >= MIN_TITLE_CHARS:
                    keys.setdefault(key, set()).add(movie_id)
        self._keys = sorted(keys.items(), key=lambda item: (-len(item[0]), item[0]))

    def find(self, question: str) -> list[int]:
        """IDs dos títulos encontrados, dos títulos mais longos para os mais curtos."""
        text = normalize(question)
        found: list[int] = []
        for key, ids in self._keys:
            if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", text):
                found += sorted(movie_id for movie_id in ids if movie_id not in found)
        return found


class Retriever:
    """Monta o contexto de uma pergunta."""

    def __init__(
        self, index: SynopsisIndex, reviews: ReviewStore, extractor: PreferenceExtractor, titles: TitleMatcher, config: RagConfig
    ) -> None:
        self._index = index
        self._reviews = reviews
        self._extractor = extractor
        self._titles = titles
        self._config = config

    def retrieve(self, question: str, config: RagConfig | None = None) -> Retrieval:
        config = config or self._config
        filters = self._extractor.extract(question)
        by_title = self._titles.find(question)[: max(1, config.k // 2)]
        chosen: list[tuple[int, float | None]] = [(movie_id, None) for movie_id in by_title]
        seen = {movie_id for movie_id, _ in chosen}
        for movie_id, score in self._index.rank(question):
            if len(chosen) >= config.k:
                break
            if movie_id not in seen and filters.accepts(self._index.movie(movie_id)):
                chosen.append((movie_id, score))
                seen.add(movie_id)
        movies = tuple(
            RetrievedMovie(
                movie_id,
                None if score is None else round(score, 4),
                self._index.movie(movie_id),
                tuple(self._reviews.excerpts(movie_id, question, config.excerpts_per_movie, config.excerpt_chars)),
                self._reviews.count(movie_id),
            )
            for movie_id, score in chosen[: config.k]
        )
        return Retrieval(filters, movies)
