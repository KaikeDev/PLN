"""Cliente, catálogo e cache do TMDB com sessões e relógios falsos, sem rede."""

import threading
import unittest

import requests

from app.domain.search.ports import DiscoverQuery
from app.infra.tmdb.cache import CachedMovieCatalog
from app.infra.tmdb.catalog import TMDBMovieCatalog
from app.infra.tmdb.client import RETRY_STATUSES, TMDBClient, TMDBError, create_session
from app.settings import Settings
from tests.fakes import FakeCatalog

TOKEN = "token-de-teste-nao-real"


class FakeResponse:
    def __init__(self, status: int = 200, payload: object = None, invalid_json: bool = False) -> None:
        self.status_code = status
        self.payload = {"ok": True} if payload is None else payload
        self.invalid_json = invalid_json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self) -> object:
        if self.invalid_json:
            raise ValueError("not json")
        return self.payload


class FakeSession:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self.response = response
        self.calls: list[dict] = []
        self.closed = False

    def get(self, url: str, params: dict, timeout: float) -> FakeResponse:
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def close(self) -> None:
        self.closed = True


def client_with(response: FakeResponse | Exception, sessions: list[FakeSession] | None = None) -> TMDBClient:
    created = sessions if sessions is not None else []

    def factory(token: str) -> FakeSession:
        session = FakeSession(response)
        created.append(session)
        return session

    return TMDBClient(TOKEN, "https://api.example.test/3/", "pt-BR", 7.0, session_factory=factory)


class TMDBClientTests(unittest.TestCase):
    def test_get_applies_language_drops_none_and_keeps_token_out_of_url(self) -> None:
        sessions: list[FakeSession] = []
        client = client_with(FakeResponse(payload={"results": []}), sessions)
        self.assertEqual(client.get("/search/movie", query="matrix", year=None), {"results": []})
        call = sessions[0].calls[0]
        self.assertEqual(call["url"], "https://api.example.test/3/search/movie")
        self.assertEqual(call["params"], {"query": "matrix", "language": "pt-BR"})
        self.assertEqual(call["timeout"], 7.0)
        self.assertNotIn(TOKEN, repr(call))

    def test_errors_are_translated_without_leaking_details(self) -> None:
        cases = [
            (FakeResponse(status=404), 404, "HTTP 404"),
            (requests.ConnectionError(f"https://x?api_key={TOKEN}"), None, "ConnectionError"),
            (FakeResponse(invalid_json=True), None, "não é JSON"),
            (FakeResponse(payload=[1, 2]), None, "inesperada"),
        ]
        for response, status, message in cases:
            with self.subTest(message=message), self.assertRaises(TMDBError) as raised:
                client_with(response).get("/movie/1")
            self.assertEqual(raised.exception.status, status)
            self.assertIn(message, str(raised.exception))
            self.assertNotIn(TOKEN, str(raised.exception))

    def test_each_thread_gets_its_own_session_and_close_releases_all(self) -> None:
        sessions: list[FakeSession] = []
        client = client_with(FakeResponse(), sessions)
        client.get("/a")
        worker = threading.Thread(target=client.get, args=("/b",))
        worker.start()
        worker.join()
        client.get("/c")
        self.assertEqual(len(sessions), 2)
        client.close()
        self.assertTrue(all(session.closed for session in sessions))

    def test_session_authenticates_by_header_and_retries_transient_errors(self) -> None:
        session = create_session(TOKEN)
        self.assertEqual(session.headers["Authorization"], f"Bearer {TOKEN}")
        retry = session.get_adapter("https://api.themoviedb.org").max_retries
        self.assertEqual(retry.total, 3)
        self.assertEqual(tuple(retry.status_forcelist), RETRY_STATUSES)
        self.assertIn(429, retry.status_forcelist)

    def test_missing_token_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "TMDB_BEARER_TOKEN"):
            TMDBClient.from_settings(Settings(_env_file=None, tmdb_bearer_token=None))

    def test_settings_hide_token_and_validate_values(self) -> None:
        settings = Settings(_env_file=None, tmdb_bearer_token=TOKEN)
        self.assertNotIn(TOKEN, repr(settings))
        with self.assertRaises(ValueError):
            Settings(_env_file=None, tmdb_timeout=0)


class TMDBCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def get(self, path: str, **params: object) -> dict:
        self.calls.append((path, params))
        return {"results": [{"id": 1}], "genres": [{"id": 18, "name": "Drama"}]}

    def test_discover_uses_or_for_included_and_and_for_excluded_genres(self) -> None:
        catalog = TMDBMovieCatalog(self.get)
        catalog.discover_movies(DiscoverQuery((18, 35), (27, 10749), 7.0, 100, "2015-01-01", None, "vote_average.desc"), page=2)
        path, params = self.calls[0]
        self.assertEqual(path, "/discover/movie")
        self.assertEqual(params["with_genres"], "18|35")
        self.assertEqual(params["without_genres"], "27,10749")
        self.assertEqual(params["vote_average.gte"], 7.0)
        self.assertEqual(params["include_adult"], "false")
        self.assertEqual(params["page"], 2)

    def test_details_and_genres(self) -> None:
        catalog = TMDBMovieCatalog(self.get)
        catalog.movie_details(603)
        self.assertEqual(self.calls[0], ("/movie/603", {"append_to_response": "credits,videos"}))
        self.assertEqual(catalog.genres(), {18: "Drama"})


class CachedCatalogTests(unittest.TestCase):
    def test_genres_and_searches_expire(self) -> None:
        now = [0.0]
        inner = FakeCatalog(titles=[{"id": 1}])
        cached = CachedMovieCatalog(inner, clock=lambda: now[0], genres_ttl=100, search_ttl=10)
        cached.genres()
        cached.genres()
        cached.search_movies("matrix")
        cached.search_movies("matrix")
        self.assertEqual((inner.genre_calls, len(inner.search_calls)), (1, 1))
        now[0] = 11
        cached.search_movies("matrix")
        cached.genres()
        self.assertEqual((inner.genre_calls, len(inner.search_calls)), (1, 2))
        now[0] = 101
        cached.genres()
        self.assertEqual(inner.genre_calls, 2)

    def test_search_cache_is_bounded(self) -> None:
        inner = FakeCatalog()
        cached = CachedMovieCatalog(inner, max_search_entries=2)
        for text in ["a", "b", "c", "a"]:
            cached.search_movies(text)
        self.assertEqual([call[0] for call in inner.search_calls], ["a", "b", "c", "a"])


if __name__ == "__main__":
    unittest.main()
