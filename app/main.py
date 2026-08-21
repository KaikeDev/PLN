"""API FastAPI que conversa com o TMDB.

Rode com:  uvicorn app.main:app --reload
Docs em:   http://127.0.0.1:8000/docs
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query

from . import tmdb

app = FastAPI(
    title="API de Filmes (TMDB)",
    description="Camada de conexao com a API do TMDB.",
    version="0.1.0",
)


# Endpoints sao `def` (sincronos) de proposito: usamos `requests`, que bloqueia.
# O FastAPI roda funcoes `def` em um threadpool, entao o event loop nao trava.

@app.get("/saude", tags=["infra"])
def saude() -> dict[str, str]:
    """Healthcheck: confirma que o servidor subiu."""
    return {"status": "ok"}


@app.get("/busca", tags=["tmdb"])
def busca(
    q: str = Query(min_length=1, description="Titulo a procurar"),
    pagina: int = Query(1, ge=1, le=500),
    ano: int | None = Query(None, ge=1874, description="Filtra pelo ano de lancamento"),
) -> dict[str, Any]:
    """Busca filmes por titulo (/search/movie do TMDB)."""
    try:
        resultados = tmdb.buscar_filmes(q, pagina=pagina, ano=ano)
    except tmdb.TMDBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"consulta": q, "pagina": pagina, "total": len(resultados), "resultados": resultados}


@app.get("/filmes/{filme_id}", tags=["tmdb"])
def filme(filme_id: int) -> dict[str, Any]:
    """Ficha completa de um filme, ja com elenco e equipe (/movie/{id})."""
    try:
        return tmdb.detalhes_filme(filme_id)
    except tmdb.TMDBError as exc:
        # id que nao existe no TMDB e erro do cliente (404), nao do gateway (502).
        if exc.status == 404:
            raise HTTPException(status_code=404, detail=f"Filme {filme_id} nao encontrado") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc
