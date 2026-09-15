"""Rotas HTTP com catálogo falso injetado: contrato JSON, validação, erros, CORS e limite."""

import unittest

from fastapi.testclient import TestClient

from app.api.rate_limit import RateLimiter
from app.domain.search.ports import CatalogError
from app.main import create_app
from app.settings import Settings
from tests.fakes import FakeCatalog

ORIGIN = "http://127.0.0.1:5500"


def client_for(catalog: FakeCatalog, rate_limit: int = 100) -> TestClient:
    settings = Settings(_env_file=None, cors_origins=[ORIGIN], rate_limit_per_minute=rate_limit)
    return TestClient(create_app(settings, catalog))


class ApiTests(unittest.TestCase):
    def test_health(self) -> None:
        with client_for(FakeCatalog()) as client:
            self.assertEqual(client.get("/saude").json(), {"status": "ok"})

    def test_title_search_contract(self) -> None:
        catalog = FakeCatalog(titles=[{"id": 603, "title": "Matrix", "original_title": "The Matrix", "popularity": 9.5}])
        with client_for(catalog) as client:
            body = client.get("/pesquisa", params={"q": "Matrix"}).json()
        self.assertEqual(body["modo"], "titulo")
        self.assertEqual(body["interpretacao"], {})
        self.assertEqual(body["resultados"][0]["id"], 603)
        self.assertEqual(body["resultados"][0]["popularity"], 9.5)

    def test_discovery_contract(self) -> None:
        with client_for(FakeCatalog(discovered=[{"id": 1}])) as client:
            body = client.get("/pesquisa", params={"q": "drama sem terror", "modo": "descoberta"}).json()
        self.assertEqual(body["modo"], "descoberta")
        self.assertEqual(body["interpretacao"]["generos_incluidos"], ["Drama"])
        self.assertEqual(body["interpretacao"]["generos_excluidos"], ["Terror"])
        self.assertIn("nota_minima", body["interpretacao"])
        with client_for(FakeCatalog()) as client:
            notice = client.get("/pesquisa", params={"q": "xyz", "modo": "descoberta"}).json()
        self.assertEqual(notice["interpretacao"], {"aviso": "Nenhuma preferência reconhecida"})

    def test_invalid_parameters_are_rejected(self) -> None:
        with client_for(FakeCatalog()) as client:
            for params in [{"q": ""}, {"q": "x" * 201}, {"q": "a", "modo": "outro"}, {"q": "a", "ano": 1800}, {"q": "a", "pagina": 0}]:
                with self.subTest(params=params):
                    self.assertEqual(client.get("/pesquisa", params=params).status_code, 422)
            self.assertEqual(client.get("/filmes/0").status_code, 422)

    def test_catalog_errors_map_to_404_and_502(self) -> None:
        with client_for(FakeCatalog(error=CatalogError("TMDB respondeu HTTP 404", status=404))) as client:
            self.assertEqual(client.get("/filmes/999").status_code, 404)
        with client_for(FakeCatalog(error=CatalogError("TMDB respondeu HTTP 503", status=503))) as client:
            response = client.get("/pesquisa", params={"q": "matrix"})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "TMDB respondeu HTTP 503")

    def test_movie_details(self) -> None:
        with client_for(FakeCatalog()) as client:
            body = client.get("/filmes/603").json()
        self.assertEqual(body["genres"], [{"id": 878, "name": "Ficção científica"}])

    def test_cors_allows_only_configured_origin(self) -> None:
        with client_for(FakeCatalog()) as client:
            allowed = client.get("/saude", headers={"Origin": ORIGIN})
            denied = client.get("/saude", headers={"Origin": "https://malicioso.example"})
        self.assertEqual(allowed.headers.get("access-control-allow-origin"), ORIGIN)
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_rate_limit_returns_429_with_retry_after(self) -> None:
        with client_for(FakeCatalog(), rate_limit=2) as client:
            statuses = [client.get("/pesquisa", params={"q": "a"}).status_code for _ in range(3)]
            last = client.get("/pesquisa", params={"q": "a"})
            self.assertEqual(client.get("/saude").status_code, 200)
        self.assertEqual(statuses, [200, 200, 429])
        self.assertIn("retry-after", last.headers)

    def test_rate_limiter_window_slides(self) -> None:
        now = [0.0]
        limiter = RateLimiter(1, window=10, clock=lambda: now[0])
        request = type("Request", (), {"client": type("Client", (), {"host": "127.0.0.1"})()})()
        limiter(request)
        now[0] = 10.5
        limiter(request)


if __name__ == "__main__":
    unittest.main()
