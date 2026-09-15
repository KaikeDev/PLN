"""Catálogo falso em memória: filmes e gêneros escritos para os testes, sem rede."""

from collections.abc import Mapping

from app.domain.search.ports import CatalogError, DiscoverQuery

TEST_GENRES = {
    28: "Ação",
    12: "Aventura",
    16: "Animação",
    35: "Comédia",
    80: "Crime",
    99: "Documentário",
    18: "Drama",
    10751: "Família",
    14: "Fantasia",
    36: "História",
    27: "Terror",
    10402: "Música",
    9648: "Mistério",
    10749: "Romance",
    878: "Ficção científica",
    53: "Thriller",
    10752: "Guerra",
}


class FakeCatalog:
    """Registra as chamadas e devolve respostas configuradas."""

    def __init__(self, titles: list[dict] | None = None, discovered: list[dict] | None = None, error: CatalogError | None = None) -> None:
        self.titles = titles or []
        self.discovered = discovered or []
        self.error = error
        self.search_calls: list[tuple[str, int, int | None]] = []
        self.discover_calls: list[tuple[DiscoverQuery, int]] = []
        self.genre_calls = 0

    def search_movies(self, query: str, page: int = 1, year: int | None = None) -> list[dict]:
        self._raise()
        self.search_calls.append((query, page, year))
        return self.titles

    def discover_movies(self, query: DiscoverQuery, page: int = 1) -> list[dict]:
        self._raise()
        self.discover_calls.append((query, page))
        return self.discovered

    def genres(self) -> Mapping[int, str]:
        self._raise()
        self.genre_calls += 1
        return TEST_GENRES

    def movie_details(self, movie_id: int) -> dict:
        self._raise()
        return {"id": movie_id, "title": "Matrix", "genres": [{"id": 878, "name": "Ficção científica"}], "credits": {"cast": []}}

    def _raise(self) -> None:
        if self.error is not None:
            raise self.error
