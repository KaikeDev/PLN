"""Agrega todas as rotas da API em um único router."""

from fastapi import APIRouter

from app.api.routes import classification, entities, health, movies, recommendation, sentiment

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(movies.router)
api_router.include_router(classification.router)
api_router.include_router(recommendation.router)
api_router.include_router(sentiment.router)
api_router.include_router(entities.router)
