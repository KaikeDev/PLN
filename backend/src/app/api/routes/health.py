"""Rotas de infraestrutura."""

from fastapi import APIRouter, Request

from app.api.schemas import Health, LLMStatus, SearchCatalog

router = APIRouter(tags=["infra"])


@router.get("/saude")
def health(request: Request) -> Health:
    """Confirma que o servidor está no ar e diz em qual catálogo a busca por tema procura e qual LLM está configurado.

    Não consulta o TMDB nem os LLMs, e não conta no limite de requisições. Com `origem` igual a `amostra_avaliada`, o
    catálogo do site não foi gerado (ADR 0024). Com `llm` nulo, nenhum provedor tem chave (ADR 0029).
    """
    catalog = getattr(request.app.state, "catalog", None)
    llm = getattr(request.app.state, "llm", None)
    return Health(catalogo=SearchCatalog(**catalog) if catalog else None, llm=LLMStatus(**llm.status()) if llm else None)
