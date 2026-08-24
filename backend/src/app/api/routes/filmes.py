"""Rotas relacionadas a filmes, consumindo app.services.tmdb."""
from __future__ import annotations

from typing import Any

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

# melhorias:
"""
There are 3 ways to search for and find movies, TV shows and people on TMDB. They're outlined below.

/search - Text based search is the most common way. You provide a query string and we provide the closest match. Searching by text takes into account all original, translated, alternative names and titles.
/discover - Sometimes it useful to search for movies and TV shows based on filters or definable values like ratings, certifications or release dates. The discover method make this easy.
/find - The last but still very useful way to find data is with existing external IDs. For example, if you know the IMDB ID of a movie, TV show or person, you can plug that value into this method and we'll return anything that matches. This can be very useful when you have an existing tool and are adding our service to the mix.
"""


