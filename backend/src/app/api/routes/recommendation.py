"""Rota de recomendação: filmes parecidos com um filme da amostra (ADR 0023).

Sem recomendador ou sem índice de sinopses, por exemplo sem o extra `semantico`, responde 503. Um
filme fora da amostra não é erro: a resposta diz `na_amostra: false` e traz a lista vazia.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.dependencies import enforce_rate_limit, get_recommender, get_synopsis_index
from app.api.schemas import SimilarMoviesResponse
from app.recommendation.ports import SimilarMoviesProvider
from app.search.ports import SynopsisIndex

MAX_SIMILAR = 20

router = APIRouter(tags=["recomendacao"], dependencies=[Depends(enforce_rate_limit)])


@router.get("/filmes/{filme_id}/parecidos")
def similar_movies(
    filme_id: Annotated[int, Path(ge=1, description="ID do filme no TMDB")],
    recommender: Annotated[SimilarMoviesProvider | None, Depends(get_recommender)],
    index: Annotated[SynopsisIndex | None, Depends(get_synopsis_index)],
    quantidade: Annotated[int, Query(ge=1, le=MAX_SIMILAR, description="Número de filmes recomendados")] = 5,
) -> SimilarMoviesResponse:
    """Filmes cuja sinopse mais se parece com a do filme, pelo embedding de sentença."""
    if recommender is None or index is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Recomendação indisponível")
    ranked = recommender.similar(filme_id, quantidade)
    movies = [{**index.movie(movie_id), "pontuacao": round(score, 4)} for movie_id, score in ranked or []]
    return SimilarMoviesResponse(
        filme_id=filme_id, na_amostra=ranked is not None, representacao=recommender.representation_name, parecidos=movies
    )
