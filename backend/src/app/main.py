"""Aplicação FastAPI da demonstração auxiliar de pesquisa de filmes.

Execução, a partir de `backend`: `uv run uvicorn app.main:app --host 127.0.0.1`. Documentação
interativa em http://127.0.0.1:8000/docs.

`create_app` monta a composição (Composition Root): configurações, cliente do TMDB, catálogo com
cache, índice de sinopses, classificador de gênero, serviço de pesquisa e limite de requisições. Sem `catalog` injetado, a
inicialização falha quando `TMDB_BEARER_TOKEN` não está configurado. O índice de sinopses carrega os
modelos da busca por tema (ADR 0020); se não puder ser carregado, por exemplo sem o extra `semantico`,
a API sobe mesmo assim e o modo `sinopse` responde que está indisponível. O classificador de gênero da
tela (ADR 0021) reaproveita uma representação do índice; sem índice, `/classificacao` responde 503. O CORS só libera origens de navegador conhecidas; ele
não é controle de acesso, papel do bind em localhost e do limite de requisições (ADR 0002).
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.rate_limit import RateLimiter
from app.api.router import api_router
from app.domain.classification.ports import GenreClassifier
from app.domain.search.ports import MovieSource, SynopsisIndex
from app.domain.search.service import SearchService
from app.infra.tmdb.cache import CachedMovieCatalog
from app.infra.tmdb.catalog import TMDBMovieCatalog
from app.infra.tmdb.client import TMDBClient
from app.settings import Settings, get_settings

if TYPE_CHECKING:
    from app.infra.synopsis.index import CorpusSynopsisIndex

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    catalog: MovieSource | None = None,
    synopsis_index: SynopsisIndex | None = None,
    genre_classifier: GenreClassifier | None = None,
) -> FastAPI:
    """Aplicação configurada; `catalog`, `synopsis_index` e `genre_classifier` substituem os reais (usados em testes).

    Com `catalog` injetado, o índice e o classificador reais não são carregados.
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
        classifier = genre_classifier
        if catalog is None and settings.synopsis_search and index is None:
            loaded = _load_synopsis_index(settings)
            index = loaded
            if loaded is not None and classifier is None:
                classifier = _load_genre_classifier(settings, loaded)
        app.state.details_provider = details
        app.state.genre_classifier = classifier
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


def _load_synopsis_index(settings: Settings) -> CorpusSynopsisIndex | None:
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


def _load_genre_classifier(settings: Settings, index: CorpusSynopsisIndex) -> GenreClassifier | None:
    from app.classification.alternatives import ALTERNATIVES
    from app.classification.config import load_config
    from app.classification.live import GenreClassifier as TrainedClassifier
    from app.vectors.methods import METHODS

    name = settings.synopsis_classifier_representation
    try:
        representations = {representation.spec.name: representation for representation, _ in index.hybrid.members}
        if name not in representations:
            raise ValueError(f"a representação {name!r} não faz parte da busca por tema")
        config = load_config(settings.synopsis_classifier_config, METHODS, ALTERNATIVES)
        classifier = TrainedClassifier(index.hybrid.corpus, representations[name], config)
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.warning("Classificação indisponível: %s", exc)
        return None
    logger.info("Classificador de gênero treinado com %d sinopses", classifier.training_size)
    return classifier


app = create_app()
