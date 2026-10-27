"""POST de JSON para os provedores de LLM, com retry só para falhas transitórias e erros traduzidos em `LLMUnavailable`.

Segue a política do cliente do TMDB (ADR 0007): uma `requests.Session` por thread e chave só em cabeçalho,
nunca na URL (ADR 0002). Erros 5xx são repetidos com backoff. O 429 não é repetido: na cota gratuita, esperar
pode levar minutos, então a falha vai direto para o provedor reserva (`app.llm.fallback`). As mensagens trazem o
provedor e o status, nunca a URL, os cabeçalhos ou a chave.
"""

import threading
from collections.abc import Callable, Mapping

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.llm.ports import LLMUnavailable

RETRY_TOTAL = 2
RETRY_BACKOFF_FACTOR = 0.5
RETRY_STATUSES = (500, 502, 503, 504)
MAX_DETAIL_CHARS = 200


def create_session() -> requests.Session:
    """Sessão com retry de POST para erros 5xx; o status final é devolvido em vez de virar exceção."""
    session = requests.Session()
    retry = Retry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=RETRY_STATUSES,
        allowed_methods=("POST",),
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


class JsonPoster:
    """Envia um corpo JSON e devolve o objeto JSON da resposta ou levanta `LLMUnavailable`."""

    def __init__(self, provider: str, timeout: float, session_factory: Callable[[], requests.Session] = create_session) -> None:
        self._provider = provider
        self._timeout = timeout
        self._session_factory = session_factory
        self._local = threading.local()
        self._sessions: list[requests.Session] = []
        self._lock = threading.Lock()

    def post(self, url: str, headers: Mapping[str, str], body: dict) -> dict:
        try:
            response = self._session().post(url, json=body, headers={"accept": "application/json", **headers}, timeout=self._timeout)
        except requests.Timeout as exc:
            raise LLMUnavailable("timeout", f"{self._provider} não respondeu em {self._timeout:g} s") from exc
        except requests.RequestException as exc:
            raise LLMUnavailable("indisponivel", f"Falha de comunicação com {self._provider} ({type(exc).__name__})") from exc
        status = response.status_code
        if status == 429:
            raise LLMUnavailable("cota", f"{self._provider} recusou por cota (HTTP 429)")
        if status in (401, 403):
            raise LLMUnavailable("sem_chave", f"{self._provider} recusou a chave (HTTP {status})")
        if status == 400 and "json_validate_failed" in response.text:
            raise LLMUnavailable("json_invalido", f"{self._provider} gerou JSON inválido")
        if status >= 400:
            raise LLMUnavailable("indisponivel", f"{self._provider} respondeu HTTP {status}{_detail(response)}")
        try:
            data = response.json()
        except ValueError as exc:
            raise LLMUnavailable("indisponivel", f"{self._provider} devolveu uma resposta que não é JSON") from exc
        if not isinstance(data, dict):
            raise LLMUnavailable("indisponivel", f"{self._provider} devolveu uma estrutura inesperada")
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
            session = self._session_factory()
            self._local.session = session
            with self._lock:
                self._sessions.append(session)
        return session


def _detail(response: requests.Response) -> str:
    """Mensagem de erro do provedor em 400, útil para corrigir esquemas; os provedores não ecoam a chave nela."""
    if response.status_code != 400:
        return ""
    try:
        error = response.json().get("error", {})
        message = error.get("message") if isinstance(error, dict) else None
    except ValueError, AttributeError:
        return ""
    return f": {str(message)[:MAX_DETAIL_CHARS]}" if message else ""
