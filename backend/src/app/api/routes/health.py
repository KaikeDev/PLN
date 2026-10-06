"""Rotas de infraestrutura."""

from fastapi import APIRouter, Request

from app.api.schemas import Health, SearchCatalog

router = APIRouter(tags=["infra"])


@router.get("/saude")
def health(request: Request) -> Health:
    """Confirma que o servidor está no ar e diz em qual catálogo a busca por tema procura.

    Não consulta o TMDB nem conta no limite de requisições. Com `origem` igual a `amostra_avaliada`, o
    catálogo do site não foi gerado (ADR 0024).
    """
    catalog = getattr(request.app.state, "catalog", None)
    return Health(catalogo=SearchCatalog(**catalog) if catalog else None)
