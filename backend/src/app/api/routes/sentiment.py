"""Rotas de análise de sentimento de uma crítica digitada: o modelo treinado (ADR 0026) e o LLM (ADR 0031).

Sem analisador carregado, por exemplo sem as críticas preparadas, `/sentimento` responde 503, e texto que o
modelo não consegue ler vira 422. `/sentimento/llm` responde 503 sem LLM configurado ou quando a cota ou o
orçamento do dia acabam; críticas longas são cortadas no meio, como na avaliação.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import enforce_rate_limit, get_llm_sentiment, get_sentiment_analyzer
from app.api.schemas import SentimentLLMResponse, SentimentResponse, TermWeight
from app.llm.ports import LLMUnavailable
from app.sentiment.live import MAX_TEXT_CHARS
from app.sentiment.llm.classifier import LLMSentiment
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


@router.get("/sentimento/llm")
def analyze_with_llm(
    classifier: Annotated[LLMSentiment | None, Depends(get_llm_sentiment)],
    texto: Annotated[str, Query(min_length=1, max_length=MAX_TEXT_CHARS, description="Crítica ou opinião sobre um filme")],
) -> SentimentLLMResponse:
    """Polaridade, nota e justificativa dadas por um LLM sem treino, para comparar com o modelo treinado."""
    if classifier is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Sentimento por LLM indisponível: nenhum provedor configurado")
    if not texto.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Digite um texto")
    try:
        result = classifier.analyze(texto)
    except LLMUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Sentimento por LLM indisponível agora ({exc.reason})") from exc
    return SentimentLLMResponse(
        polaridade=result.polarity,
        nota=result.rating,
        justificativa=result.reason,
        provedor=result.provider,
        modelo=result.model,
        variante=classifier.variant,
    )
