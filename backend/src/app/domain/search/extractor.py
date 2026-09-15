"""Extração de preferências: normalização → léxico → negação → qualidade → período → IDs de gênero.

O catálogo só é consultado quando o texto contém algum gatilho de gênero, para que uma busca por
título comum ("matrix") não exija o mapa de gêneros.
"""

from dataclasses import dataclass, field, replace

from app.domain.search import lexicon, negation
from app.domain.search.normalization import normalize, tokenize
from app.domain.search.period import extract_period
from app.domain.search.ports import POPULARITY_DESC, RATING_DESC, DiscoverQuery, MovieCatalog


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

    def to_discover_query(self) -> DiscoverQuery:
        """Consulta de descoberta equivalente."""
        return DiscoverQuery(
            self.genres, self.excluded_genres, self.min_rating, self.min_votes, self.released_after, self.released_before, self.sort_by
        )


class FilterExtractor:
    """Transforma texto livre em `ExtractedFilters`, usando o catálogo para resolver nomes de gênero."""

    def __init__(self, catalog: MovieCatalog) -> None:
        self._catalog = catalog

    def extract(self, text: str) -> ExtractedFilters:
        """Preferências reconhecidas em `text`."""
        normalized = normalize(text)
        tokens = tokenize(normalized)
        included_names, excluded_names = negation.split_negated_genres(tokens, lexicon.find_genres(tokens))
        quality = lexicon.find_quality(normalized)
        period = extract_period(normalized)
        included: tuple[int, ...] = ()
        excluded: tuple[int, ...] = ()
        if included_names or excluded_names:
            ids_by_name = {normalize(name): genre_id for genre_id, name in self._catalog.genres().items()}
            included = _resolve(included_names, ids_by_name)
            excluded = _resolve(excluded_names, ids_by_name)
        return ExtractedFilters(
            genres=included,
            excluded_genres=excluded,
            min_rating=quality.min_rating if quality else None,
            min_votes=quality.min_votes if quality else None,
            released_after=period.released_after,
            released_before=period.released_before,
            sort_by=RATING_DESC if quality else POPULARITY_DESC,
        )


def _resolve(names: list[str], ids_by_name: dict[str, int]) -> tuple[int, ...]:
    ids = (ids_by_name.get(normalize(name)) for name in names)
    return tuple(dict.fromkeys(genre_id for genre_id in ids if genre_id is not None))
