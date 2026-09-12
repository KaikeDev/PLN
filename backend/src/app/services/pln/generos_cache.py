"""Cache em memoria do mapa de generos do TMDB (id<->nome normalizado).

Unico modulo do pacote pln/ que fala com o TMDB - os demais sao puros. Cache
carregado sob demanda (na 1a pesquisa, nao no boot do servidor) e mantido para
sempre durante o processo, ja que a lista de generos do TMDB e essencialmente
estatica.
"""
from __future__ import annotations

from app.services.pln.normalizacao import normalizar
from app.services.tmdb import filmes as tmdb_filmes

_cache_id_para_nome: dict[int, str] | None = None
_cache_nome_para_id: dict[str, int] | None = None


def _definir(mapa: dict[int, str]) -> None:
    global _cache_id_para_nome, _cache_nome_para_id
    _cache_id_para_nome = dict(mapa)
    _cache_nome_para_id = {normalizar(nome): id_ for id_, nome in mapa.items()}


def mapa_id_para_nome() -> dict[int, str]:
    """Carrega tmdb_filmes.generos() na 1a chamada e cacheia em memoria pelo processo."""
    if _cache_id_para_nome is None:
        _definir(tmdb_filmes.generos())
    return _cache_id_para_nome  # type: ignore[return-value]


def mapa_nome_para_id() -> dict[str, int]:
    """Mapa nome normalizado (sem acento/minusculo) -> id, para casar com o vocabulario do lexico."""
    if _cache_nome_para_id is None:
        _definir(tmdb_filmes.generos())
    return _cache_nome_para_id  # type: ignore[return-value]


def definir_cache_para_teste(mapa: dict[int, str]) -> None:
    """Define o cache diretamente, sem chamar o TMDB - uso exclusivo em testes."""
    _definir(mapa)


def invalidar_cache() -> None:
    """Zera o cache; usado so em testes/depuracao manual."""
    global _cache_id_para_nome, _cache_nome_para_id
    _cache_id_para_nome = None
    _cache_nome_para_id = None
