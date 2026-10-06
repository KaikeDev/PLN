"""Injeção de dependências das rotas: os objetos são criados na inicialização da aplicação."""

from fastapi import Request

from app.api.rate_limit import RateLimiter
from app.classification.ports import GenreClassifier
from app.recommendation.ports import SimilarMoviesProvider
from app.search.ports import MovieDetailsProvider, SynopsisIndex
from app.search.service import SearchService


def get_search_service(request: Request) -> SearchService:
    """Serviço de pesquisa da aplicação."""
    return request.app.state.search_service


def get_details_provider(request: Request) -> MovieDetailsProvider:
    """Fonte de fichas completas de filmes."""
    return request.app.state.details_provider


def get_genre_classifier(request: Request) -> GenreClassifier | None:
    """Classificador de gênero da aplicação, ou None quando não pôde ser carregado."""
    return request.app.state.genre_classifier


def get_recommender(request: Request) -> SimilarMoviesProvider | None:
    """Recomendador de filmes parecidos, ou None quando não pôde ser carregado."""
    return request.app.state.recommender


def get_synopsis_index(request: Request) -> SynopsisIndex | None:
    """Índice de sinopses da amostra, com os dados de exibição de cada filme."""
    return request.app.state.synopsis_index


def enforce_rate_limit(request: Request) -> None:
    """Aplica o limite de requisições configurado na aplicação."""
    limiter: RateLimiter = request.app.state.rate_limiter
    limiter(request)
