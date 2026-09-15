"""Rotas de filmes: ficha completa e pesquisa por título ou preferências.

Falhas do catálogo viram 502, exceto filme inexistente, que vira 404. As mensagens de erro nunca
contêm URL ou credencial.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.dependencies import enforce_rate_limit, get_details_provider, get_search_service
from app.api.schemas import MovieDetails, SearchResponse
from app.domain.search.ports import CatalogError, MovieDetailsProvider
from app.domain.search.service import SearchMode, SearchService
from app.shared.language import MAX_RELEASE_YEAR, MIN_RELEASE_YEAR

MAX_QUERY_LENGTH = 200
MAX_PAGE = 500

router = APIRouter(tags=["filmes"], dependencies=[Depends(enforce_rate_limit)])


@router.get("/filmes/{filme_id}")
def movie_details(
    filme_id: Annotated[int, Path(ge=1, description="ID do filme no TMDB")],
    provider: Annotated[MovieDetailsProvider, Depends(get_details_provider)],
) -> MovieDetails:
    """Ficha completa de um filme, com elenco e vídeos."""
    try:
        return MovieDetails.model_validate(provider.movie_details(filme_id))
    except CatalogError as exc:
        if exc.status == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Filme {filme_id} não encontrado") from exc
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/pesquisa")
def search(
    service: Annotated[SearchService, Depends(get_search_service)],
    q: Annotated[str, Query(min_length=1, max_length=MAX_QUERY_LENGTH, description="Título ou preferências em linguagem natural")],
    pagina: Annotated[int, Query(ge=1, le=MAX_PAGE)] = 1,
    ano: Annotated[int | None, Query(ge=MIN_RELEASE_YEAR, le=MAX_RELEASE_YEAR, description="Ano de lançamento")] = None,
    modo: SearchMode = SearchMode.AUTO,
) -> SearchResponse:
    """Pesquisa por título exato, preferências reconhecidas por regras ou modo automático."""
    try:
        return SearchResponse.from_result(service.search(q, page=pagina, year=ano, mode=modo))
    except CatalogError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
