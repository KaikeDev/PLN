"""Rota de entidades nomeadas e relações de um texto, usada na ficha do filme (ADR 0027).

Sem o extra `entidades`, responde 503.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import enforce_rate_limit, get_entity_extractor
from app.api.schemas import EntitiesResponse, EntityMention, RelationTriple
from app.entities.live import MAX_TEXT_CHARS
from app.entities.ports import EntityExtractor

router = APIRouter(tags=["entidades"], dependencies=[Depends(enforce_rate_limit)])


@router.get("/entidades")
def extract(
    extractor: Annotated[EntityExtractor | None, Depends(get_entity_extractor)],
    texto: Annotated[str, Query(min_length=1, max_length=MAX_TEXT_CHARS, description="Sinopse ou outro texto em português")],
) -> EntitiesResponse:
    """Pessoas, lugares, organizações e outras menções do texto, e as triplas sujeito — relação → objeto."""
    if extractor is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Entidades e relações indisponíveis")
    try:
        result = extractor.extract(texto)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return EntitiesResponse(
        entidades=[EntityMention(texto=e["entidade"], categoria=e["categoria"], inicio=e["inicio"], fim=e["fim"]) for e in result.entities],
        relacoes=[
            RelationTriple(sujeito=t.subject, relacao=t.relation, objeto=t.object, sentenca=t.sentence, regra=t.rule)
            for t in result.triples
        ],
        modelo=extractor.model_name,
    )
