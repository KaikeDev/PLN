"""Configuração da aplicação lida de variáveis de ambiente e de `backend/.env`.

O arquivo `.env` é procurado na pasta `backend`, independentemente do diretório de execução.
Variáveis de ambiente têm precedência sobre o arquivo. Valores inválidos falham na leitura, antes de
qualquer requisição. A credencial é `SecretStr`, portanto não aparece em `repr`, logs ou tracebacks.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Parâmetros de integração com o TMDB e de exposição da API local."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    tmdb_bearer_token: SecretStr | None = None
    tmdb_base_url: str = Field("https://api.themoviedb.org/3", pattern=r"^https://")
    tmdb_language: str = Field("pt-BR", pattern=r"^[a-z]{2}-[A-Z]{2}$")
    tmdb_timeout: float = Field(10.0, gt=0, le=60)
    cors_origins: list[str] = ["http://127.0.0.1:5500", "http://localhost:5500"]
    rate_limit_per_minute: int = Field(60, ge=1, le=10_000)

    def require_tmdb_token(self) -> str:
        """Token de leitura do TMDB; falha com mensagem orientativa quando não configurado."""
        if self.tmdb_bearer_token is None or not self.tmdb_bearer_token.get_secret_value().strip():
            raise ValueError("Defina TMDB_BEARER_TOKEN no ambiente ou em backend/.env")
        return self.tmdb_bearer_token.get_secret_value().strip()


@lru_cache
def get_settings() -> Settings:
    """Instância única das configurações, lida na primeira chamada."""
    return Settings()
