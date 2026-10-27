"""Rota da aba "Perguntar": RAG sobre os filmes do catálogo com citações conferidas (ADR 0032).

Fica em GET, como as demais, para o CORS continuar só com GET (ADR 0002). Além do limite geral, tem um
limite próprio por IP, porque cada pergunta é uma chamada grande ao LLM; o orçamento diário `rag` também
vale (ADR 0029). Sem RAG montado, ou quando o LLM não responde, a resposta é 503, e o site mostra os
exemplos gravados. A pergunta não vai para o log.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import enforce_question_rate_limit, enforce_rate_limit, get_question_answering
from app.api.schemas import CitedFilm, ContextFilm, MovieSummary, QuestionResponse, ReviewExcerpt
from app.llm.ports import LLMUnavailable
from app.rag.service import Answer, QuestionAnswering

MAX_QUESTION_CHARS = 300
UNAVAILABLE = "Perguntas indisponíveis no momento"

router = APIRouter(tags=["perguntas"], dependencies=[Depends(enforce_rate_limit), Depends(enforce_question_rate_limit)])


@router.get("/pergunta")
def ask(
    service: Annotated[QuestionAnswering | None, Depends(get_question_answering)],
    q: Annotated[str, Query(min_length=1, max_length=MAX_QUESTION_CHARS, description="Pergunta sobre os filmes do catálogo")],
) -> QuestionResponse:
    """Resposta do LLM apoiada nos filmes recuperados, com os filmes citados e o contexto usado."""
    if service is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE)
    if not q.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Escreva uma pergunta")
    try:
        answer = service.answer(q.strip())
    except LLMUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"{UNAVAILABLE} ({exc.reason})") from exc
    return response_of(answer)


def response_of(answer: Answer) -> QuestionResponse:
    movies = {item.id: item.movie for item in answer.retrieval.movies}
    grounded = answer.grounded
    return QuestionResponse(
        pergunta=answer.question,
        resposta=grounded.answer,
        contexto_suficiente=grounded.sufficient,
        filmes_citados=[
            CitedFilm(id=cited.id, motivo=cited.reason, filme=MovieSummary.model_validate(movies[cited.id])) for cited in grounded.cited
        ],
        contexto=[
            ContextFilm(
                id=item.id,
                titulo=item.movie.get("title"),
                pontuacao=item.score,
                criticas=item.reviews,
                trechos=[ReviewExcerpt(texto=excerpt.text, nota=excerpt.rating) for excerpt in item.excerpts],
            )
            for item in answer.retrieval.movies
        ],
        provedor=answer.provider,
        modelo=answer.model,
        latencia_ms=answer.latency_ms,
        citacoes_removidas=len(grounded.invented),
        exemplo_gravado=False,
    )
