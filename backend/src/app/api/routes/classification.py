"""Rota de classificação de gênero de uma sinopse digitada (ADR 0021).

Sem classificador carregado, por exemplo sem o extra `semantico`, responde 503. Texto que a
representação não consegue codificar vira 422.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import enforce_rate_limit, get_genre_classifier
from app.api.schemas import ClassificationResponse, GenreScore
from app.classification.ports import GenreClassifier

MAX_TEXT_LENGTH = 1000

router = APIRouter(tags=["classificacao"], dependencies=[Depends(enforce_rate_limit)])


@router.get("/classificacao")
def classify(
    classifier: Annotated[GenreClassifier | None, Depends(get_genre_classifier)],
    texto: Annotated[str, Query(min_length=1, max_length=MAX_TEXT_LENGTH, description="Sinopse ou descrição do filme")],
) -> ClassificationResponse:
    """Probabilidade de cada gênero para o texto, pela regressão logística sobre o embedding de sentença."""
    if classifier is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Classificação indisponível")
    try:
        scores = classifier.classify(texto)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return ClassificationResponse(
        genero_previsto=scores[0][0],
        generos=[GenreScore(genero=genre, probabilidade=probability) for genre, probability in scores],
        representacao=classifier.representation_name,
        sinopses_de_treino=classifier.training_size,
    )
