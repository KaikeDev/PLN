"""Aplicação FastAPI da demonstração auxiliar de pesquisa de filmes.

Execução, a partir de `backend`: `uv run uvicorn app.main:app --host 127.0.0.1`. Documentação
interativa em http://127.0.0.1:8000/docs.

`create_app` monta a composição (Composition Root): configurações, cliente do TMDB, catálogo com
cache, índice de sinopses, classificador de gênero, recomendador, serviço de pesquisa e limite de requisições. Sem `catalog` injetado, a
inicialização falha quando `TMDB_BEARER_TOKEN` não está configurado. O índice de sinopses carrega os
modelos da busca por tema (ADR 0020); se não puder ser carregado, por exemplo sem o extra `semantico`,
a API sobe mesmo assim e o modo `sinopse` responde que está indisponível. O classificador de gênero da
tela (ADR 0021) e o recomendador de filmes parecidos (ADR 0023) reaproveitam uma representação do índice;
sem índice, `/classificacao` e `/filmes/{id}/parecidos` respondem 503. O CORS só libera origens de navegador conhecidas; ele
não é controle de acesso, papel do bind em localhost e do limite de requisições (ADR 0002).
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.rate_limit import RateLimiter
from app.api.router import api_router
from app.classification.ports import GenreClassifier
from app.recommendation.ports import SimilarMoviesProvider
from app.search.ports import MovieSource, SynopsisIndex
from app.search.service import SearchService
from app.settings import Settings, get_settings
from app.tmdb.cache import CachedMovieCatalog
from app.tmdb.catalog import TMDBMovieCatalog
from app.tmdb.client import TMDBClient

if TYPE_CHECKING:
    from app.search.synopsis_index import CorpusSynopsisIndex

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    catalog: MovieSource | None = None,
    synopsis_index: SynopsisIndex | None = None,
    genre_classifier: GenreClassifier | None = None,
    recommender: SimilarMoviesProvider | None = None,
) -> FastAPI:
    """Aplicação configurada; `catalog`, `synopsis_index`, `genre_classifier` e `recommender` substituem os reais (usados em testes).

    Com `catalog` injetado, o índice, o classificador e o recomendador reais não são carregados.
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
        similar = recommender
        if catalog is None and settings.synopsis_search:
            if index is None:
                loaded, origin = _load_synopsis_index(settings)
                index = loaded
                if loaded is not None:
                    app.state.catalog = {"origem": origin, "filmes": loaded.size}
                if loaded is not None and similar is None:
                    similar = _load_recommender(settings, loaded)
            if classifier is None:
                classifier = _load_genre_classifier(settings)
        app.state.details_provider = details
        app.state.genre_classifier = classifier
        app.state.recommender = similar
        app.state.synopsis_index = index
        app.state.catalog = getattr(app.state, "catalog", None)
        app.state.search_service = SearchService(CachedMovieCatalog(details), index)
        app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute)
        try:
            yield
        finally:
            if client is not None:
                client.close()

    app = FastAPI(
        title="API de Filmes (TMDB)",
        description="Demonstração auxiliar: pesquisa por título, por preferências ou por tema nas sinopses, classificação de gênero e filmes parecidos.",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET"], allow_headers=[])
    app.include_router(api_router)
    return app


CATALOG_HELP = "docs/tecnico/como-executar.md#catálogo-do-site"


def catalog_paths(settings: Settings) -> tuple[Path, Path, Path, str]:
    """Pastas (preparada, bruta, vetores) e origem do catálogo da busca: o do site, se foi gerado; senão, a amostra avaliada."""
    if settings.synopsis_processed_dir.exists() and settings.synopsis_raw_dir.exists():
        return settings.synopsis_processed_dir, settings.synopsis_raw_dir, settings.synopsis_vectors_dir, "catalogo_do_site"
    return settings.sample_processed_dir, settings.sample_raw_dir, settings.sample_vectors_dir, "amostra_avaliada"


def _load_synopsis_index(settings: Settings) -> tuple[CorpusSynopsisIndex | None, str]:
    from app.search.synopsis_index import CorpusSynopsisIndex

    processed, raw, vectors, origin = catalog_paths(settings)
    if origin == "amostra_avaliada":
        logger.warning(
            "\n%s\nCATÁLOGO DO SITE NÃO ENCONTRADO em %s.\n"
            "A busca por tema e os filmes parecidos vão usar só a amostra avaliada (428 filmes).\n"
            "Para usar o catálogo de cerca de 5.500 filmes, gere-o com os três comandos de %s.\n%s",
            "=" * 78,
            settings.synopsis_processed_dir,
            CATALOG_HELP,
            "=" * 78,
        )
    try:
        index = CorpusSynopsisIndex.load(
            processed,
            raw,
            settings.synopsis_vectors_config,
            settings.synopsis_search_config,
            vectors=vectors if vectors.exists() else None,
        )
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.warning("Busca por sinopse indisponível: %s", exc)
        return None, origin
    logger.info("Busca por sinopse carregada com %d filmes (%s)", index.size, origin)
    return index, origin


def _load_genre_classifier(settings: Settings) -> GenreClassifier | None:
    """Regressão logística da Etapa 3 treinada na amostra avaliada, com os vetores já calculados dela."""
    from app.classification.alternatives import ALTERNATIVES
    from app.classification.config import load_config
    from app.classification.live import GenreClassifier as TrainedClassifier
    from app.representations.methods import METHODS
    from app.representations.pipeline import build_one

    vectors = settings.sample_vectors_dir
    try:
        corpus, representation = build_one(
            settings.sample_processed_dir,
            settings.synopsis_vectors_config,
            settings.synopsis_classifier_representation,
            vectors=vectors if vectors.exists() else None,
        )
        config = load_config(settings.synopsis_classifier_config, METHODS, ALTERNATIVES)
        classifier = TrainedClassifier(corpus, representation, config)
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.warning("Classificação indisponível: %s", exc)
        return None
    logger.info("Classificador de gênero treinado com %d sinopses", classifier.training_size)
    return classifier


def _load_recommender(settings: Settings, index: CorpusSynopsisIndex) -> SimilarMoviesProvider | None:
    from app.recommendation.similar import SimilarMovies

    name = settings.synopsis_recommendation_representation
    representations = {representation.spec.name: representation for representation, _ in index.hybrid.members}
    if name not in representations:
        logger.warning("Recomendação indisponível: a representação %r não faz parte da busca por tema", name)
        return None
    return SimilarMovies(representations[name])


app = create_app()
