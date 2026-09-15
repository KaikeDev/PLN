"""Transporte HTTP com o TMDB: autenticação, idioma padrão, timeout, retry e tradução de erros.

Todo acesso de rede ao TMDB passa por `TMDBClient.get`. A autenticação usa apenas o token Bearer em
cabeçalho; a credencial nunca entra na URL, que pode aparecer em logs (ADR 0002). Cada thread usa a
própria `requests.Session`, porque a sessão não é garantidamente segura entre threads e as rotas
síncronas do FastAPI rodam num pool de threads. O retry repete GET até três vezes, com backoff
exponencial, para 429 e erros 5xx transitórios.
"""

import threading
from collections.abc import Callable
from typing import Any, Self

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.domain.search.ports import CatalogError
from app.settings import Settings

RETRY_TOTAL = 3
RETRY_BACKOFF_FACTOR = 0.5
RETRY_STATUSES = (429, 500, 502, 503, 504)


class TMDBError(CatalogError):
    """Falha ao consultar o TMDB. A mensagem nunca inclui URL, cabeçalhos ou credencial."""


def create_session(token: str) -> requests.Session:
    """Sessão autenticada por Bearer, com política de retry para GET."""
    session = requests.Session()
    session.headers.update({"accept": "application/json", "Authorization": f"Bearer {token}"})
    retry = Retry(total=RETRY_TOTAL, backoff_factor=RETRY_BACKOFF_FACTOR, status_forcelist=RETRY_STATUSES, allowed_methods=("GET",))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


class TMDBClient:
    """Cliente GET da API v3 do TMDB."""

    def __init__(
        self,
        token: str,
        base_url: str,
        language: str,
        timeout: float,
        session_factory: Callable[[str], requests.Session] = create_session,
    ) -> None:
        if not token:
            raise ValueError("Defina TMDB_BEARER_TOKEN no ambiente ou em backend/.env")
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._language = language
        self._timeout = timeout
        self._session_factory = session_factory
        self._local = threading.local()
        self._sessions: list[requests.Session] = []
        self._lock = threading.Lock()

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        """Cliente configurado a partir de `Settings`; falha quando não há token."""
        return cls(settings.require_tmdb_token(), settings.tmdb_base_url, settings.tmdb_language, settings.tmdb_timeout)

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        """GET em `<base_url><path>`; parâmetros None são omitidos e o idioma padrão é aplicado."""
        query = {key: value for key, value in params.items() if value is not None}
        query.setdefault("language", self._language)
        try:
            response = self._session().get(f"{self._base_url}{path}", params=query, timeout=self._timeout)
            response.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            raise TMDBError(f"TMDB respondeu HTTP {status}", status=status) from exc
        except requests.RequestException as exc:
            raise TMDBError(f"Falha de comunicação com TMDB ({type(exc).__name__})") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise TMDBError("TMDB retornou uma resposta que não é JSON") from exc
        if not isinstance(data, dict):
            raise TMDBError("TMDB retornou uma estrutura inesperada")
        return data

    def close(self) -> None:
        """Fecha as sessões abertas por todas as threads."""
        with self._lock:
            for session in self._sessions:
                session.close()
            self._sessions.clear()
        self._local = threading.local()

    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = self._session_factory(self._token)
            self._local.session = session
            with self._lock:
                self._sessions.append(session)
        return session
