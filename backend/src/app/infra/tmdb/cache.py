"""Cache em memória com expiração para o catálogo (Decorator de `MovieCatalog`).

O mapa de gêneros muda raramente e expira em um dia. As buscas por título expiram em minutos e têm
limite de entradas; isso evita repetir a consulta da primeira página quando o modo automático pagina
(ADR 0007). O cache é por processo, protegido por lock, e não é compartilhado entre réplicas.
"""

import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping

from app.domain.search.ports import DiscoverQuery, MovieCatalog

GENRES_TTL_SECONDS = 24 * 60 * 60
SEARCH_TTL_SECONDS = 5 * 60
MAX_SEARCH_ENTRIES = 256


class CachedMovieCatalog:
    """Envolve um catálogo e reaproveita gêneros e buscas por título enquanto não expiram."""

    def __init__(
        self,
        inner: MovieCatalog,
        clock: Callable[[], float] = time.monotonic,
        genres_ttl: float = GENRES_TTL_SECONDS,
        search_ttl: float = SEARCH_TTL_SECONDS,
        max_search_entries: int = MAX_SEARCH_ENTRIES,
    ) -> None:
        self._inner = inner
        self._clock = clock
        self._genres_ttl = genres_ttl
        self._search_ttl = search_ttl
        self._max_search_entries = max_search_entries
        self._lock = threading.Lock()
        self._genres: tuple[float, Mapping[int, str]] | None = None
        self._searches: OrderedDict[tuple[str, int, int | None], tuple[float, list[dict]]] = OrderedDict()

    def genres(self) -> Mapping[int, str]:
        """Mapa de gêneros, recarregado após `genres_ttl` segundos."""
        with self._lock:
            if self._genres is not None and self._clock() < self._genres[0]:
                return self._genres[1]
        genres = dict(self._inner.genres())
        with self._lock:
            self._genres = (self._clock() + self._genres_ttl, genres)
        return genres

    def search_movies(self, query: str, page: int = 1, year: int | None = None) -> list[dict]:
        """Busca por título, reaproveitada por `search_ttl` segundos."""
        key = (query, page, year)
        with self._lock:
            cached = self._searches.get(key)
            if cached is not None and self._clock() < cached[0]:
                self._searches.move_to_end(key)
                return cached[1]
        results = self._inner.search_movies(query, page=page, year=year)
        with self._lock:
            self._searches[key] = (self._clock() + self._search_ttl, results)
            self._searches.move_to_end(key)
            while len(self._searches) > self._max_search_entries:
                self._searches.popitem(last=False)
        return results

    def discover_movies(self, query: DiscoverQuery, page: int = 1) -> list[dict]:
        """Descoberta sem cache: os filtros variam muito entre pesquisas."""
        return self._inner.discover_movies(query, page=page)
