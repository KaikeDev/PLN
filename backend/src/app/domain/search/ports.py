"""Portas do domínio de pesquisa: o que ele precisa de um catálogo de filmes."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

POPULARITY_DESC = "popularity.desc"
RATING_DESC = "vote_average.desc"


class CatalogError(RuntimeError):
    """Falha do catálogo externo; `status` é o código HTTP da fonte, ou None quando não houve resposta."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class DiscoverQuery:
    """Preferências estruturadas para descoberta.

    `genres` aceita qualquer um dos gêneros (OU); `excluded_genres` exclui todos. Datas usam AAAA-MM-DD.
    """

    genres: tuple[int, ...] = field(default_factory=tuple)
    excluded_genres: tuple[int, ...] = field(default_factory=tuple)
    min_rating: float | None = None
    min_votes: int | None = None
    released_after: str | None = None
    released_before: str | None = None
    sort_by: str = POPULARITY_DESC


class MovieCatalog(Protocol):
    """Operações de consulta de filmes usadas pela pesquisa."""

    def search_movies(self, query: str, page: int = 1, year: int | None = None) -> list[dict]:
        """Filmes cujo título corresponde a `query`."""
        ...

    def discover_movies(self, query: DiscoverQuery, page: int = 1) -> list[dict]:
        """Filmes que satisfazem as preferências estruturadas."""
        ...

    def genres(self) -> Mapping[int, str]:
        """Mapa de ID de gênero para nome localizado."""
        ...


class MovieDetailsProvider(Protocol):
    """Ficha completa de um filme."""

    def movie_details(self, movie_id: int) -> dict:
        """Detalhes do filme, incluindo elenco e vídeos."""
        ...


class MovieSource(MovieCatalog, MovieDetailsProvider, Protocol):
    """Catálogo completo: pesquisa e fichas de filmes."""
