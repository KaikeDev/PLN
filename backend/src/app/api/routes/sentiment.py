"""Rota de análise de sentimento de uma crítica digitada (ADR 0026).

Sem analisador carregado, por exemplo sem as críticas preparadas, responde 503. Texto que o modelo não
consegue ler vira 422.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import enforce_rate_limit, get_sentiment_analyzer
from app.api.schemas import SentimentResponse, TermWeight
from app.sentiment.live import MAX_TEXT_CHARS
from app.sentiment.ports import SentimentAnalyzer

router = APIRouter(tags=["sentimento"], dependencies=[Depends(enforce_rate_limit)])


@router.get("/sentimento")
def analyze(
    analyzer: Annotated[SentimentAnalyzer | None, Depends(get_sentiment_analyzer)],
    texto: Annotated[str, Query(min_length=1, max_length=MAX_TEXT_CHARS, description="Crítica ou opinião sobre um filme")],
) -> SentimentResponse:
    """Polaridade, probabilidade de ser positiva e nota prevista para o texto, com as palavras que mais pesaram."""
    if analyzer is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Análise de sentimento indisponível")
    try:
        result = analyzer.analyze(texto)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return SentimentResponse(
        polaridade=result.polarity,
        probabilidade_positiva=result.positive_probability,
        nota_prevista=result.rating,
        palavras_positivas=[TermWeight(palavra=term, peso=weight) for term, weight in result.positive_terms],
        palavras_negativas=[TermWeight(palavra=term, peso=weight) for term, weight in result.negative_terms],
        representacao=analyzer.representation_name,
        criticas_de_treino=analyzer.training_size,
    )
