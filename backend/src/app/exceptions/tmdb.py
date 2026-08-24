"""Erros da camada de integracao com o TMDB."""
from __future__ import annotations


class TMDBError(RuntimeError):
    """Falha ao consultar a API do TMDB.

    `status` guarda o codigo HTTP devolvido pelo TMDB (None se a conexao
    nem chegou a acontecer), para as rotas repassarem 404 como 404.
    """

    def __init__(self, mensagem: str, status: int | None = None) -> None:
        super().__init__(mensagem)
        self.status = status
