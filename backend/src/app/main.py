"""API FastAPI que conversa com o TMDB.

Rode com:  uvicorn app.main:app --reload
Docs em:   http://127.0.0.1:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router

app = FastAPI(
    title="API de Filmes (TMDB)",
    description="Camada de conexao com a API do TMDB.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    # so o frontend estatico local pode chamar a API; evita que qualquer
    # site aberto no navegador use seu token do TMDB via este servidor.
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(api_router)
