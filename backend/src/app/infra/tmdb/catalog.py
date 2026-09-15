"""Catálogo de filmes sobre o TMDB (Adapter das portas `MovieCatalog` e `MovieDetailsProvider`).

Na descoberta, gêneros incluídos são unidos por `|` (qualquer um serve) e excluídos por `,` (nenhum
pode aparecer), conforme a semântica de `/discover/movie`. Conteúdo adulto nunca é incluído.
"""

from collections.abc import Callable, Mapping
from typing import Any

from app.domain.search.ports import DiscoverQuery

Get = Callable[..., dict[str, Any]]
DETAILS_EXTRAS = "credits,videos"


class TMDBMovieCatalog:
    """Traduz as operações do domínio para endpoints do TMDB."""

    def __init__(self, get: Get) -> None:
        self._get = get

    def search_movies(self, query: str, page: int = 1, year: int | None = None) -> list[dict]:
        """`/search/movie`: filmes cujo título corresponde a `query`."""
        return self._get("/search/movie", query=query, page=page, include_adult="false", year=year).get("results", [])

    def movie_details(self, movie_id: int) -> dict:
        """`/movie/{id}` com elenco e vídeos na mesma requisição."""
        return self._get(f"/movie/{int(movie_id)}", append_to_response=DETAILS_EXTRAS)

    def genres(self) -> Mapping[int, str]:
        """`/genre/movie/list`: mapa de ID para nome localizado."""
        return {genre["id"]: genre["name"] for genre in self._get("/genre/movie/list").get("genres", [])}

    def discover_movies(self, query: DiscoverQuery, page: int = 1) -> list[dict]:
        """`/discover/movie` com as preferências estruturadas."""
        params = {
            "with_genres": "|".join(str(genre) for genre in query.genres) or None,
            "without_genres": ",".join(str(genre) for genre in query.excluded_genres) or None,
            "vote_average.gte": query.min_rating,
            "vote_count.gte": query.min_votes,
            "primary_release_date.gte": query.released_after,
            "primary_release_date.lte": query.released_before,
            "sort_by": query.sort_by,
            "page": page,
            "include_adult": "false",
        }
        return self._get("/discover/movie", **params).get("results", [])
