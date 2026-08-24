"""Rotas de infraestrutura."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["infra"])


@router.get("/saude")
def saude() -> dict[str, str]:
    """Healthcheck: confirma que o servidor subiu."""
    return {"status": "ok"}
