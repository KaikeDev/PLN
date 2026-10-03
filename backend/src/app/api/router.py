"""Agrega todas as rotas da API em um único router."""

from fastapi import APIRouter

from app.api.routes import classification, health, movies

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(movies.router)
api_router.include_router(classification.router)
