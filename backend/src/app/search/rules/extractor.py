"""Extração de preferências: normalização → léxico → negação → qualidade → período → IDs de gênero.

O catálogo só é consultado quando o texto contém algum gatilho de gênero, para que uma busca por
título comum ("matrix") não exija o mapa de gêneros. `current_year` fixa o ano dos termos relativos
("recente", "antigo"); a avaliação usa a data de referência das frases anotadas.
"""

from collections.abc import Mapping

from app.search.filters import ExtractedFilters
from app.search.ports import POPULARITY_DESC, RATING_DESC, GenreSource
from app.search.rules import lexicon, negation
from app.search.rules.normalization import normalize, tokenize
from app.search.rules.period import extract_period


class FilterExtractor:
    """Transforma texto livre em `ExtractedFilters`, usando o catálogo para resolver nomes de gênero."""

    def __init__(self, catalog: GenreSource, current_year: int | None = None) -> None:
        self._catalog = catalog
        self._current_year = current_year

    def extract(self, text: str) -> ExtractedFilters:
        """Preferências reconhecidas em `text`."""
        normalized = normalize(text)
        tokens = tokenize(normalized)
        included_names, excluded_names = negation.split_negated_genres(tokens, lexicon.find_genres(tokens))
        quality = lexicon.find_quality(normalized)
        period = extract_period(normalized, self._current_year)
        included: tuple[int, ...] = ()
        excluded: tuple[int, ...] = ()
        if included_names or excluded_names:
            ids_by_name = genre_ids_by_name(self._catalog.genres())
            included = resolve_genres(included_names, ids_by_name)
            excluded = resolve_genres(excluded_names, ids_by_name)
        return ExtractedFilters(
            genres=included,
            excluded_genres=excluded,
            min_rating=quality.min_rating if quality else None,
            min_votes=quality.min_votes if quality else None,
            released_after=period.released_after,
            released_before=period.released_before,
            sort_by=RATING_DESC if quality else POPULARITY_DESC,
        )


def genre_ids_by_name(genres: Mapping[int, str]) -> dict[str, int]:
    """Mapa do nome normalizado (sem acento, minúsculo) para o ID do gênero."""
    return {normalize(name): genre_id for genre_id, name in genres.items()}


def resolve_genres(names: list[str], ids_by_name: Mapping[str, int]) -> tuple[int, ...]:
    """IDs dos nomes conhecidos, sem repetição e na ordem dada; nomes desconhecidos são ignorados."""
    ids = (ids_by_name.get(normalize(name)) for name in names)
    return tuple(dict.fromkeys(genre_id for genre_id in ids if genre_id is not None))
