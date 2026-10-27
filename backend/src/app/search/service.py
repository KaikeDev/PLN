"""Serviço de pesquisa com uma estratégia por modo (Strategy).

- `titulo`: busca direta por título.
- `descoberta`: preferências extraídas da frase viram consulta de descoberta.
- `sinopse`: busca por tema nas sinopses do corpus, com a combinação TF-IDF + embedding de sentença
  (ADR 0020); as preferências reconhecidas filtram os filmes.
- `auto`: prioriza correspondência exata com título localizado ou original na primeira página; sem
  correspondência, usa a busca por sinopse quando ela está disponível e encontra filmes, depois as
  preferências quando existem e, por fim, a busca por título.

A verificação de título exato sempre usa a primeira página, para que o modo escolhido não mude ao
paginar (ADR 0006), e acontece antes da interpretação: um título não gasta cota do LLM.

Quem interpreta a frase depende de `interpretacao` (ADR 0030): `regras` usa as regras léxicas (ADR 0005);
`llm` usa só o LLM e falha com `LLMUnavailable` quando ele não responde; `auto` tenta o LLM e recorre às
regras. Sem LLM configurado, `auto` usa as regras. A frase é interpretada uma vez por pesquisa.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from app.llm.ports import LLMUnavailable
from app.search.filters import ExtractedFilters, Origin
from app.search.interpretation.hybrid_extractor import FallbackExtractor
from app.search.ports import MovieCatalog, PreferenceExtractor, SynopsisIndex
from app.search.rules.extractor import FilterExtractor
from app.search.rules.normalization import normalize

NO_PREFERENCES_NOTICE = "Nenhuma preferência reconhecida"
EMPTY_PERIOD_NOTICE = "Período sem interseção"
SYNOPSIS_UNAVAILABLE_NOTICE = "Busca por sinopse indisponível"
LLM_UNAVAILABLE_MESSAGE = "Interpretação por LLM indisponível: nenhum provedor configurado"
PAGE_SIZE = 20


class SearchMode(StrEnum):
    """Modo pedido pelo cliente."""

    AUTO = "auto"
    TITLE = "titulo"
    DISCOVERY = "descoberta"
    SYNOPSIS = "sinopse"


class InterpretationMode(StrEnum):
    """Quem interpreta a frase: regras, LLM, ou LLM com reserva nas regras."""

    AUTO = "auto"
    RULES = "regras"
    LLM = "llm"


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
    origin: Origin = "regras"
    theme: str | None = None


@dataclass(frozen=True)
class Notice:
    """Motivo pelo qual a descoberta não produziu consulta."""

    message: str


Interpretation = FilterInterpretation | Notice | None


@dataclass(frozen=True)
class SearchResult:
    """Modo efetivamente usado (`titulo`, `descoberta` ou `sinopse`), filmes e interpretação."""

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

    def __init__(self, catalog: MovieCatalog, extractor: PreferenceExtractor) -> None:
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


class SynopsisSearch:
    """Filmes do corpus ordenados pela similaridade da sinopse com o texto, filtrados pelas preferências.

    Quando o LLM devolve o tema (o assunto sem os filtros) e o prompt pede para usá-lo, ele substitui a frase na ordenação.
    """

    def __init__(self, index: SynopsisIndex | None, catalog: MovieCatalog, extractor: PreferenceExtractor) -> None:
        self._index = index
        self._catalog = catalog
        self._extractor = extractor

    @property
    def available(self) -> bool:
        return self._index is not None

    def search(self, request: SearchRequest) -> SearchResult:
        if self._index is None:
            return SearchResult(SearchMode.SYNOPSIS, interpretation=Notice(SYNOPSIS_UNAVAILABLE_NOTICE))
        return self.search_with(request, self._extractor.extract(request.text))

    def search_with(self, request: SearchRequest, filters: ExtractedFilters) -> SearchResult:
        """Busca por tema com filtros já extraídos."""
        if self._index is None:
            return SearchResult(SearchMode.SYNOPSIS, interpretation=Notice(SYNOPSIS_UNAVAILABLE_NOTICE))
        if request.year is not None:
            filters = filters.restricted_to_year(request.year)
        if filters.has_empty_period():
            return SearchResult(SearchMode.SYNOPSIS, interpretation=Notice(EMPTY_PERIOD_NOTICE))
        index = self._index
        ranked = index.rank(filters.theme or request.text)
        matches = [(movie_id, score) for movie_id, score in ranked if filters.accepts(index.movie(movie_id))]
        start = (request.page - 1) * PAGE_SIZE
        results = [{**index.movie(movie_id), "pontuacao": round(score, 4)} for movie_id, score in matches[start : start + PAGE_SIZE]]
        return SearchResult(SearchMode.SYNOPSIS, results, interpret(filters, self._catalog.genres))


class AutomaticSearch:
    """Título exato primeiro; depois sinopses; depois preferências; por fim, título."""

    def __init__(self, title: TitleSearch, discovery: DiscoverySearch, synopsis: SynopsisSearch, extractor: PreferenceExtractor) -> None:
        self._title = title
        self._discovery = discovery
        self._synopsis = synopsis
        self._extractor = extractor

    def search(self, request: SearchRequest) -> SearchResult:
        by_title = self._title.search(request)
        if self._title.has_exact_title(request, by_title):
            return by_title
        filters = self._extractor.extract(request.text)
        if self._synopsis.available:
            by_synopsis = self._synopsis.search_with(request, filters)
            if by_synopsis.results:
                return by_synopsis
        if not filters.has_filters():
            return SearchResult(SearchMode.TITLE, by_title.results, interpret(filters, lambda: {}))
        return self._discovery.search_with(request, filters)


class SearchService:
    """Ponto de entrada da pesquisa: escolhe a estratégia pelo modo pedido e o intérprete pela `interpretacao`."""

    def __init__(
        self, catalog: MovieCatalog, synopsis_index: SynopsisIndex | None = None, llm_extractor: PreferenceExtractor | None = None
    ) -> None:
        rules = FilterExtractor(catalog)
        extractors: dict[InterpretationMode, PreferenceExtractor] = {InterpretationMode.RULES: rules, InterpretationMode.AUTO: rules}
        if llm_extractor is not None:
            extractors[InterpretationMode.LLM] = llm_extractor
            extractors[InterpretationMode.AUTO] = FallbackExtractor(llm_extractor, rules)
        self._extractors = extractors
        self._strategies = {
            interpretation: _strategies(catalog, synopsis_index, extractor) for interpretation, extractor in extractors.items()
        }

    def interpreter(self, interpretation: InterpretationMode = InterpretationMode.AUTO) -> PreferenceExtractor:
        """Intérprete da frase usado pela pesquisa; o RAG usa o mesmo (ADR 0032)."""
        return self._extractors.get(InterpretationMode(interpretation), self._extractors[InterpretationMode.AUTO])

    def search(
        self,
        text: str,
        page: int = 1,
        year: int | None = None,
        mode: SearchMode = SearchMode.AUTO,
        interpretation: InterpretationMode = InterpretationMode.AUTO,
    ) -> SearchResult:
        """Atende a pesquisa com a estratégia do modo pedido; `interpretacao=llm` sem LLM levanta `LLMUnavailable`."""
        strategies = self._strategies.get(InterpretationMode(interpretation))
        if strategies is None:
            raise LLMUnavailable("sem_chave", LLM_UNAVAILABLE_MESSAGE)
        return strategies[SearchMode(mode)].search(SearchRequest(text, page, year))


def _strategies(catalog: MovieCatalog, index: SynopsisIndex | None, extractor: PreferenceExtractor) -> dict[SearchMode, SearchStrategy]:
    title = TitleSearch(catalog)
    discovery = DiscoverySearch(catalog, extractor)
    synopsis = SynopsisSearch(index, catalog, extractor)
    return {
        SearchMode.TITLE: title,
        SearchMode.DISCOVERY: discovery,
        SearchMode.SYNOPSIS: synopsis,
        SearchMode.AUTO: AutomaticSearch(title, discovery, synopsis, extractor),
    }


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
        origin=filters.origin,
        theme=filters.theme,
    )
