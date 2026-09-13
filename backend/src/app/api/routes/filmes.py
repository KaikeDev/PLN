"""Rotas relacionadas a filmes, consumindo app.services.tmdb."""
from __future__ import annotations

from typing import Any, Literal
from dataclasses import asdict

from app.services.pln.pesquisa import pesquisar

from fastapi import APIRouter, HTTPException, Query

from app.exceptions.tmdb import TMDBError
from app.services.tmdb import filmes as tmdb_filmes

router = APIRouter(tags=["tmdb"])


@router.get("/busca")
def busca(
    q: str = Query(min_length=1, description="Titulo a procurar"),
    pagina: int = Query(1, ge=1, le=500),
    ano: int | None = Query(None, ge=1874, description="Filtra pelo ano de lancamento"),
) -> dict[str, Any]:
    """Busca filmes por titulo (/search/movie do TMDB)."""
    try:
        resultados = tmdb_filmes.buscar_filmes(q, pagina=pagina, ano=ano)

    except TMDBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"consulta": q, "pagina": pagina, "total": len(resultados), "resultados": resultados}


@router.get("/filmes/{filme_id}")
def filme(filme_id: int) -> dict[str, Any]:
    """Ficha completa de um filme, ja com elenco e equipe (/movie/{id})."""
    try:
        return tmdb_filmes.detalhes_filme(filme_id)

    except TMDBError as exc:
        if exc.status == 404:
            raise HTTPException(status_code=404, detail=f"Filme {filme_id} nao encontrado") from exc

        raise HTTPException(status_code=502, detail=str(exc)) from exc

@router.get("/pesquisa")
def pesquisa(
    q: str = Query(min_length=1),
    pagina: int = Query(1, ge=1, le=500),
    ano: int | None = Query(None, ge=1874, le=9998),
    modo: Literal["auto", "titulo", "descoberta"] = "auto",
) -> dict[str, Any]:
    """Pesquisa auxiliar por título ou preferências reconhecidas por regras."""
    try:
        return asdict(pesquisar(q, pagina=pagina, ano=ano, modo=modo))
    except TMDBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
