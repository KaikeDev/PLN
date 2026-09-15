"""Injeção de dependências das rotas: os objetos são criados na inicialização da aplicação."""

from fastapi import Request

from app.api.rate_limit import RateLimiter
from app.domain.search.ports import MovieDetailsProvider
from app.domain.search.service import SearchService


def get_search_service(request: Request) -> SearchService:
    """Serviço de pesquisa da aplicação."""
    return request.app.state.search_service


def get_details_provider(request: Request) -> MovieDetailsProvider:
    """Fonte de fichas completas de filmes."""
    return request.app.state.details_provider


def enforce_rate_limit(request: Request) -> None:
    """Aplica o limite de requisições configurado na aplicação."""
    limiter: RateLimiter = request.app.state.rate_limiter
    limiter(request)
