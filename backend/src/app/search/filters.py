"""Filtros da pesquisa: o que as regras (ADR 0005) e o LLM (ADR 0030) extraem do texto livre.

Os dois extratores devolvem o mesmo `ExtractedFilters`, o que permite compará-los nas mesmas frases
anotadas e trocar um pelo outro no site. `origin` diz quem interpretou; `theme` é o assunto da frase
sem os filtros, que só o LLM preenche.
"""

from dataclasses import dataclass, field, replace
from typing import Literal

from app.search.ports import POPULARITY_DESC, DiscoverQuery

Origin = Literal["regras", "llm"]


@dataclass(frozen=True)
class ExtractedFilters:
    """Preferências reconhecidas; gêneros já resolvidos para IDs do catálogo."""

    genres: tuple[int, ...] = field(default_factory=tuple)
    excluded_genres: tuple[int, ...] = field(default_factory=tuple)
    min_rating: float | None = None
    min_votes: int | None = None
    released_after: str | None = None
    released_before: str | None = None
    sort_by: str = POPULARITY_DESC
    origin: Origin = "regras"
    theme: str | None = None

    def has_filters(self) -> bool:
        """Verdadeiro quando algum sinal descritivo (gênero, qualidade ou período) foi detectado."""
        return bool(
            self.genres
            or self.excluded_genres
            or self.min_rating is not None
            or self.released_after is not None
            or self.released_before is not None
        )

    def restricted_to_year(self, year: int) -> ExtractedFilters:
        """Interseção do período extraído com o ano informado separadamente."""
        first, last = f"{year}-01-01", f"{year}-12-31"
        return replace(
            self,
            released_after=max(self.released_after or first, first),
            released_before=min(self.released_before or last, last),
        )

    def has_empty_period(self) -> bool:
        """Verdadeiro quando o limite inicial é posterior ao final."""
        return bool(self.released_after and self.released_before and self.released_after > self.released_before)

    def accepts(self, movie: dict) -> bool:
        """Verdadeiro quando o filme (campos do TMDB) satisfaz as mesmas preferências da descoberta.

        Gêneros incluídos valem com qualquer um (OU); datas e nota sem valor no filme não passam num filtro.
        """
        genres = set(movie.get("genre_ids") or ())
        date = movie.get("release_date") or ""
        rating, votes = movie.get("vote_average"), movie.get("vote_count")
        return (
            (not self.genres or bool(genres & set(self.genres)))
            and not genres & set(self.excluded_genres)
            and (self.released_after is None or (bool(date) and date >= self.released_after))
            and (self.released_before is None or (bool(date) and date <= self.released_before))
            and (self.min_rating is None or (rating is not None and rating >= self.min_rating))
            and (self.min_votes is None or (votes is not None and votes >= self.min_votes))
        )

    def to_discover_query(self) -> DiscoverQuery:
        """Consulta de descoberta equivalente."""
        return DiscoverQuery(
            self.genres, self.excluded_genres, self.min_rating, self.min_votes, self.released_after, self.released_before, self.sort_by
        )
