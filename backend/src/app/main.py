"""Aplicação FastAPI da demonstração auxiliar de pesquisa de filmes.

Execução, a partir de `backend`: `uv run uvicorn app.main:app --host 127.0.0.1`. Documentação
interativa em http://127.0.0.1:8000/docs.

`create_app` monta a composição (Composition Root): configurações, cliente do TMDB, catálogo com
cache, índice de sinopses, serviço de pesquisa e limite de requisições. Sem `catalog` injetado, a
inicialização falha quando `TMDB_BEARER_TOKEN` não está configurado. O índice de sinopses carrega os
modelos da busca por tema (ADR 0018); se não puder ser carregado, por exemplo sem o extra `semantico`,
a API sobe mesmo assim e o modo `sinopse` responde que está indisponível. O CORS só libera origens de navegador conhecidas; ele
não é controle de acesso, papel do bind em localhost e do limite de requisições (ADR 0002).
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.rate_limit import RateLimiter
from app.api.router import api_router
from app.domain.search.ports import MovieSource, SynopsisIndex
from app.domain.search.service import SearchService
from app.infra.tmdb.cache import CachedMovieCatalog
from app.infra.tmdb.catalog import TMDBMovieCatalog
from app.infra.tmdb.client import TMDBClient
from app.settings import Settings, get_settings

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None, catalog: MovieSource | None = None, synopsis_index: SynopsisIndex | None = None
) -> FastAPI:
    """Aplicação configurada; `catalog` e `synopsis_index` substituem o TMDB e o índice reais (usados em testes).

    Com `catalog` injetado e sem `synopsis_index`, o índice real não é carregado.
    """
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = None
        details: MovieSource | None = catalog
        if details is None:
            client = TMDBClient.from_settings(settings)
            details = TMDBMovieCatalog(client.get)
        index = synopsis_index
        if index is None and catalog is None and settings.synopsis_search:
            index = _load_synopsis_index(settings)
        app.state.details_provider = details
        app.state.search_service = SearchService(CachedMovieCatalog(details), index)
        app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute)
        try:
            yield
        finally:
            if client is not None:
                client.close()

    app = FastAPI(
        title="API de Filmes (TMDB)",
        description="Demonstração auxiliar: pesquisa por título, por preferências reconhecidas por regras ou por tema nas sinopses.",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET"], allow_headers=[])
    app.include_router(api_router)
    return app


def _load_synopsis_index(settings: Settings) -> SynopsisIndex | None:
    from app.infra.synopsis.index import CorpusSynopsisIndex

    try:
        index = CorpusSynopsisIndex.load(
            settings.synopsis_processed_dir, settings.synopsis_raw_dir, settings.synopsis_vectors_config, settings.synopsis_search_config
        )
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.warning("Busca por sinopse indisponível: %s", exc)
        return None
    logger.info("Busca por sinopse carregada")
    return index


app = create_app()
