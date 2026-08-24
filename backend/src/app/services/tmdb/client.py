"""Transporte HTTP com o TMDB: sessao, autenticacao, retry e tratamento de erro.

Todo acesso de rede do projeto passa por `get()`. Os modulos de dominio
(ex.: `filmes.py`) so conhecem caminhos e parametros da API, nunca `requests`.
"""
from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core import config
from app.exceptions.tmdb import TMDBError


def _criar_sessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update({"accept": "application/json"})
    if config.TMDB_BEARER_TOKEN:
        sessao.headers["Authorization"] = f"Bearer {config.TMDB_BEARER_TOKEN}"

    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    sessao.mount("https://", HTTPAdapter(max_retries=retry))
    return sessao


_sessao = _criar_sessao()


def get(caminho: str, **params: Any) -> dict[str, Any]:
    """GET em /3<caminho> com idioma padrao e tratamento de erro."""
    params = {k: v for k, v in params.items() if v is not None}
    params.setdefault("language", config.DEFAULT_LANGUAGE)

    if not config.TMDB_BEARER_TOKEN:
        if not config.TMDB_API_KEY:
            raise TMDBError("Defina TMDB_BEARER_TOKEN ou TMDB_API_KEY no arquivo .env")
        params["api_key"] = config.TMDB_API_KEY

    url = f"{config.TMDB_BASE_URL}{caminho}"
    try:
        resposta = _sessao.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
        resposta.raise_for_status()

    except requests.HTTPError as exc:
        status = exc.response.status_code
        detalhe = exc.response.json().get("status_message", exc.response.text[:200])
        raise TMDBError(f"TMDB respondeu {status}: {detalhe}", status=status) from exc

    except requests.RequestException as exc:
        raise TMDBError(f"Nao foi possivel falar com o TMDB: {exc}") from exc

    return resposta.json()
