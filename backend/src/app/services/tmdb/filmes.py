"""Operacoes de dominio sobre filmes, pessoas e generos do TMDB.

Consumido hoje pelas rotas em `app.api.routes`; e o ponto de entrada que a
futura camada de PLN tambem vai usar para responder perguntas em linguagem
natural.
"""
from __future__ import annotations

from typing import Any

from app.services.tmdb.client import get


def buscar_filmes(
    consulta: str,
    pagina: int = 1,
    incluir_adulto: bool = False,
    ano: int | None = None,
) -> list[dict[str, Any]]:
    """/search/movie - lista de filmes que casam com o texto."""
    dados = get(
        "/search/movie",
        query=consulta,
        page=pagina,
        include_adult=str(incluir_adulto).lower(),
        year=ano,
    )
    return dados.get("results", [])


def detalhes_filme(filme_id: int, extras: str = "credits,videos") -> dict[str, Any]:
    """/movie/{id} - ficha completa; `extras` evita requisicoes separadas."""
    return get(f"/movie/{filme_id}", append_to_response=extras)


def filmes_similares(filme_id: int, pagina: int = 1) -> list[dict[str, Any]]:
    """/movie/{id}/similar - usado para responder 'recomende algo parecido'."""
    return get(f"/movie/{filme_id}/similar", page=pagina).get("results", [])


def buscar_pessoa(nome: str) -> list[dict[str, Any]]:
    """/search/person - para perguntas do tipo 'filmes do Nolan'."""
    return get("/search/person", query=nome).get("results", [])


def generos() -> dict[int, str]:
    """/genre/movie/list - mapa id -> nome, ja que a busca so devolve ids."""
    lista = get("/genre/movie/list").get("genres", [])
    return {g["id"]: g["name"] for g in lista}


def descobrir_filmes(
    *, generos: str | None = None, sem_generos: str | None = None,
    nota_minima: float | None = None, votos_minimos: int | None = None,
    lancado_apos: str | None = None, lancado_antes: str | None = None,
    ordenar_por: str = "popularity.desc", pagina: int = 1,
) -> list[dict[str, Any]]:
    """Consulta de preferências estruturadas em /discover/movie."""
    return get("/discover/movie", **{
        "with_genres": generos, "without_genres": sem_generos,
        "vote_average.gte": nota_minima, "vote_count.gte": votos_minimos,
        "primary_release_date.gte": lancado_apos, "primary_release_date.lte": lancado_antes,
        "sort_by": ordenar_por, "page": pagina, "include_adult": "false",
    }).get("results", [])
