"""Serviço de pesquisa com uma estratégia por modo (Strategy).

- `titulo`: busca direta por título.
- `descoberta`: preferências extraídas por regras viram consulta de descoberta.
- `auto`: prioriza correspondência exata com título localizado ou original na primeira página; sem
  correspondência, usa preferências quando existem e volta à busca por título quando não existem.

A verificação de título exato sempre usa a primeira página, para que o modo escolhido não mude ao
paginar (ADR 0006).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from app.domain.search.extractor import ExtractedFilters, FilterExtractor
from app.domain.search.normalization import normalize
from app.domain.search.ports import MovieCatalog

NO_PREFERENCES_NOTICE = "Nenhuma preferência reconhecida"
EMPTY_PERIOD_NOTICE = "Período sem interseção"


class SearchMode(StrEnum):
    """Modo pedido pelo cliente."""

    AUTO = "auto"
    TITLE = "titulo"
    DISCOVERY = "descoberta"


@dataclass(frozen=True)
class SearchRequest:
    """Texto livre, página e ano opcional informado separadamente."""

    text: str
    page: int = 1
    year: int | None = None


@dataclass(frozen=True)
class FilterInterpretation:
    """Preferências reconhecidas, com gêneros por nome, para depuração e relatório."""

    included_genres: list[str]
    excluded_genres: list[str]
    min_rating: float | None
    min_votes: int | None
    released_after: str | None
    released_before: str | None


@dataclass(frozen=True)
class Notice:
    """Motivo pelo qual a descoberta não produziu consulta."""

    message: str


Interpretation = FilterInterpretation | Notice | None


@dataclass(frozen=True)
class SearchResult:
    """Modo efetivamente usado (`titulo` ou `descoberta`), filmes e interpretação."""

    mode: SearchMode
    results: list[dict] = field(default_factory=list)
    interpretation: Interpretation = None


class SearchStrategy(Protocol):
    """Uma forma de atender a pesquisa."""

    def search(self, request: SearchRequest) -> SearchResult: ...


class TitleSearch:
    """Busca direta por título."""

    def __init__(self, catalog: MovieCatalog) -> None:
        self._catalog = catalog

    def search(self, request: SearchRequest) -> SearchResult:
        return SearchResult(SearchMode.TITLE, self._catalog.search_movies(request.text, page=request.page, year=request.year))

    def has_exact_title(self, request: SearchRequest, current: SearchResult) -> bool:
        """Verdadeiro quando algum filme da primeira página tem título localizado ou original igual ao texto.

        Na primeira página reaproveita `current`; nas demais, consulta a primeira página.
        """
        expected = normalize(request.text)
        first_page = current.results if request.page == 1 else self._catalog.search_movies(request.text, page=1, year=request.year)
        return any(expected in {normalize(movie.get("title") or ""), normalize(movie.get("original_title") or "")} for movie in first_page)


class DiscoverySearch:
    """Descoberta a partir das preferências reconhecidas no texto."""

    def __init__(self, catalog: MovieCatalog, extractor: FilterExtractor) -> None:
        self._catalog = catalog
        self._extractor = extractor

    def search(self, request: SearchRequest) -> SearchResult:
        filters = self._extractor.extract(request.text)
        if not filters.has_filters():
            return SearchResult(SearchMode.DISCOVERY, interpretation=Notice(NO_PREFERENCES_NOTICE))
        return self.search_with(request, filters)

    def search_with(self, request: SearchRequest, filters: ExtractedFilters) -> SearchResult:
        """Descoberta com filtros já extraídos, respeitando o ano informado separadamente."""
        if request.year is not None:
            filters = filters.restricted_to_year(request.year)
        if filters.has_empty_period():
            return SearchResult(SearchMode.DISCOVERY, interpretation=Notice(EMPTY_PERIOD_NOTICE))
        results = self._catalog.discover_movies(filters.to_discover_query(), page=request.page)
        return SearchResult(SearchMode.DISCOVERY, results, interpret(filters, self._catalog.genres))


class AutomaticSearch:
    """Título exato primeiro; depois preferências; por fim, título."""

    def __init__(self, title: TitleSearch, discovery: DiscoverySearch, extractor: FilterExtractor) -> None:
        self._title = title
        self._discovery = discovery
        self._extractor = extractor

    def search(self, request: SearchRequest) -> SearchResult:
        by_title = self._title.search(request)
        if self._title.has_exact_title(request, by_title):
            return by_title
        filters = self._extractor.extract(request.text)
        if not filters.has_filters():
            return SearchResult(SearchMode.TITLE, by_title.results, interpret(filters, lambda: {}))
        return self._discovery.search_with(request, filters)


class SearchService:
    """Ponto de entrada da pesquisa: escolhe a estratégia pelo modo pedido."""

    def __init__(self, catalog: MovieCatalog) -> None:
        extractor = FilterExtractor(catalog)
        title = TitleSearch(catalog)
        discovery = DiscoverySearch(catalog, extractor)
        self._strategies: dict[SearchMode, SearchStrategy] = {
            SearchMode.TITLE: title,
            SearchMode.DISCOVERY: discovery,
            SearchMode.AUTO: AutomaticSearch(title, discovery, extractor),
        }

    def search(self, text: str, page: int = 1, year: int | None = None, mode: SearchMode = SearchMode.AUTO) -> SearchResult:
        """Atende a pesquisa com a estratégia do modo pedido."""
        return self._strategies[SearchMode(mode)].search(SearchRequest(text, page, year))


def interpret(filters: ExtractedFilters, genre_names: Callable[[], Mapping[int, str]]) -> FilterInterpretation:
    """Interpretação legível dos filtros; o mapa de gêneros só é consultado quando há gêneros."""
    names = genre_names() if filters.genres or filters.excluded_genres else {}
    return FilterInterpretation(
        included_genres=[names.get(genre, str(genre)) for genre in filters.genres],
        excluded_genres=[names.get(genre, str(genre)) for genre in filters.excluded_genres],
        min_rating=filters.min_rating,
        min_votes=filters.min_votes,
        released_after=filters.released_after,
        released_before=filters.released_before,
    )
