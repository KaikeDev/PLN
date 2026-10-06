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
REPOSITORY_DIR = BACKEND_DIR.parent
SAMPLE = "tmdb_2026-09-12"


class Settings(BaseSettings):
    """Parâmetros de integração com o TMDB e o Jev, da busca por sinopse e de exposição da API local.

    A busca por sinopse usa a amostra entregue e as configurações do repositório; `synopsis_search`
    falso desliga o carregamento dos modelos na inicialização. O classificador de gênero da tela usa a
    regressão logística da Etapa 3 sobre `synopsis_classifier_representation`, uma das representações da busca.
    """

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    tmdb_bearer_token: SecretStr | None = None
    tmdb_base_url: str = Field("https://api.themoviedb.org/3", pattern=r"^https://")
    tmdb_language: str = Field("pt-BR", pattern=r"^[a-z]{2}-[A-Z]{2}$")
    tmdb_timeout: float = Field(10.0, gt=0, le=60)
    cors_origins: list[str] = ["http://127.0.0.1:5500", "http://localhost:5500"]
    rate_limit_per_minute: int = Field(60, ge=1, le=10_000)
    typesafe_api_key: SecretStr | None = None
    synopsis_search: bool = True
    synopsis_processed_dir: Path = REPOSITORY_DIR / "data" / "preparacao" / SAMPLE
    synopsis_raw_dir: Path = REPOSITORY_DIR / "data" / "coleta" / SAMPLE
    synopsis_vectors_config: Path = REPOSITORY_DIR / "config" / "representacoes" / "vetorizacao_semantica.json"
    synopsis_search_config: Path = REPOSITORY_DIR / "config" / "busca" / "busca.json"
    synopsis_classifier_config: Path = REPOSITORY_DIR / "config" / "classificacao" / "classificacao_semantica.json"
    synopsis_classifier_representation: str = "sentenca_minilm"
    synopsis_recommendation_representation: str = "sentenca_minilm"

    def require_tmdb_token(self) -> str:
        """Token de leitura do TMDB; falha com mensagem orientativa quando não configurado."""
        if self.tmdb_bearer_token is None or not self.tmdb_bearer_token.get_secret_value().strip():
            raise ValueError("Defina TMDB_BEARER_TOKEN no ambiente ou em backend/.env")
        return self.tmdb_bearer_token.get_secret_value().strip()

    def require_typesafe_key(self) -> str:
        """Chave da API da TypeSafe AI (Jev); falha com mensagem orientativa quando não configurada."""
        if self.typesafe_api_key is None or not self.typesafe_api_key.get_secret_value().strip():
            raise ValueError("Defina TYPESAFE_API_KEY no ambiente ou em backend/.env")
        return self.typesafe_api_key.get_secret_value().strip()


@lru_cache
def get_settings() -> Settings:
    """Instância única das configurações, lida na primeira chamada."""
    return Settings()
