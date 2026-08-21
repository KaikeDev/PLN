"""Configuracoes lidas do .env."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p"

# Token v4 (Bearer) tem prioridade; se estiver vazio caimos no api_key v3.
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN", "").strip()
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()

DEFAULT_LANGUAGE = os.getenv("TMDB_LANGUAGE", "pt-BR")
REQUEST_TIMEOUT = float(os.getenv("TMDB_TIMEOUT", "10"))
