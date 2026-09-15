"""Rotas de infraestrutura."""

from fastapi import APIRouter

from app.api.schemas import Health

router = APIRouter(tags=["infra"])


@router.get("/saude")
def health() -> Health:
    """Confirma que o servidor está no ar; não consulta o TMDB nem conta no limite de requisições."""
    return Health()
