"""Agrega todas as rotas da API em um unico router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import filmes, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(filmes.router)
