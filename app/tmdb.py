"""Camada de acesso a API do TMDB.

Toda requisicao HTTP do projeto passa por aqui. 
"""
from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config


class TMDBError(RuntimeError):
    """Falha ao consultar a API do TMDB.

    `status` guarda o codigo HTTP devolvido pelo TMDB (None se a conexao
    nem chegou a acontecer), para o main.py repassar 404 como 404.
    """

    def __init__(self, mensagem: str, status: int | None = None) -> None:
        super().__init__(mensagem)
        self.status = status


def _criar_sessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update({"accept": "application/json"})
    if config.TMDB_BEARER_TOKEN:
        sessao.headers["Authorization"] = f"Bearer {config.TMDB_BEARER_TOKEN}"

    # A API tem rate limit; nova tentativa automatica em 429 e erros 5xx.
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    sessao.mount("https://", HTTPAdapter(max_retries=retry))
    return sessao


_sessao = _criar_sessao()


def _get(caminho: str, **params: Any) -> dict[str, Any]:
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


# ---------------------------------------------------------------- endpoints

def buscar_filmes(
    consulta: str,
    pagina: int = 1,
    incluir_adulto: bool = False,
    ano: int | None = None,
) -> list[dict[str, Any]]:
    """/search/movie - lista de filmes que casam com o texto."""
    dados = _get(
        "/search/movie",
        query=consulta,
        page=pagina,
        include_adult=str(incluir_adulto).lower(),
        year=ano,
    )
    return dados.get("results", [])


def detalhes_filme(filme_id: int, extras: str = "credits,videos") -> dict[str, Any]:
    """/movie/{id} - ficha completa; `extras` evita requisicoes separadas."""
    return _get(f"/movie/{filme_id}", append_to_response=extras)


def filmes_similares(filme_id: int, pagina: int = 1) -> list[dict[str, Any]]:
    """/movie/{id}/similar - usado para responder 'recomende algo parecido'."""
    return _get(f"/movie/{filme_id}/similar", page=pagina).get("results", [])


def buscar_pessoa(nome: str) -> list[dict[str, Any]]:
    """/search/person - para perguntas do tipo 'filmes do Nolan'."""
    return _get("/search/person", query=nome).get("results", [])


def generos() -> dict[int, str]:
    """/genre/movie/list - mapa id -> nome, ja que a busca so devolve ids."""
    lista = _get("/genre/movie/list").get("genres", [])
    return {g["id"]: g["name"] for g in lista}


