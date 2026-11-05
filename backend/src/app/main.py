"""Aplicação FastAPI da demonstração auxiliar de pesquisa de filmes.

Execução, a partir de `backend`: `uv run uvicorn app.main:app --host 127.0.0.1`. Documentação
interativa em http://127.0.0.1:8000/docs.

`create_app` monta a composição (Composition Root): configurações, cliente do TMDB, catálogo com
cache, índice de sinopses, classificador de gênero, recomendador, serviço de pesquisa e limite de requisições. Sem `catalog` injetado, a
inicialização falha quando `TMDB_BEARER_TOKEN` não está configurado. O índice de sinopses carrega os
modelos da busca por tema (ADR 0020); se não puder ser carregado, por exemplo sem o extra `semantico`,
a API sobe mesmo assim e o modo `sinopse` responde que está indisponível. O classificador de gênero da
tela (ADR 0021) e o recomendador de filmes parecidos (ADR 0023) reaproveitam uma representação do índice;
sem índice, `/classificacao` e `/filmes/{id}/parecidos` respondem 503. O LLM (Gemini e Groq, ADR 0029) só é montado
para os provedores com chave; sem nenhuma, as funções com LLM respondem 503 e o restante funciona. Com LLM, a pesquisa
interpreta a frase por ele e recorre às regras quando ele falha (ADR 0030). O CORS só libera origens de navegador conhecidas; ele
não é controle de acesso, papel do bind em localhost e do limite de requisições (ADR 0002).

Com `SERVE_FRONTEND=true`, a API serve também as telas de `frontend/` na mesma origem, montadas depois das rotas para não
sombreá-las. É assim no contêiner do Hugging Face Spaces (ADR 0033), o único lugar onde a API escuta em `0.0.0.0`: lá ela roda
atrás do proxy do Space com `--proxy-headers`, para que o limite por IP veja o visitante, e com o limite próprio das rotas de LLM.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.rate_limit import RateLimiter
from app.api.router import api_router
from app.classification.ports import GenreClassifier
from app.entities.ports import EntityExtractor
from app.recommendation.ports import SimilarMoviesProvider
from app.search.ports import GenreSource, MovieSource, PreferenceExtractor, SynopsisIndex
from app.search.service import SearchService
from app.sentiment.ports import SentimentAnalyzer
from app.settings import Settings, get_settings
from app.tmdb.cache import CachedMovieCatalog
from app.tmdb.catalog import TMDBMovieCatalog
from app.tmdb.client import TMDBClient

if TYPE_CHECKING:
    from app.llm.compose import LLMStack
    from app.rag.service import QuestionAnswering
    from app.search.synopsis_index import CorpusSynopsisIndex
    from app.sentiment.llm.classifier import LLMSentiment

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    catalog: MovieSource | None = None,
    synopsis_index: SynopsisIndex | None = None,
    genre_classifier: GenreClassifier | None = None,
    recommender: SimilarMoviesProvider | None = None,
    sentiment_analyzer: SentimentAnalyzer | None = None,
    entity_extractor: EntityExtractor | None = None,
    llm: LLMStack | None = None,
    question_answering: QuestionAnswering | None = None,
) -> FastAPI:
    """Aplicação configurada; `catalog`, `synopsis_index`, `genre_classifier`, `recommender`, `sentiment_analyzer`, `entity_extractor`, `llm` e `question_answering` substituem os reais (usados em testes).

    Com `catalog` injetado, o índice, o classificador, o recomendador, o analisador de sentimento, o extrator de entidades e o LLM reais não são carregados.
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
        sentiment = sentiment_analyzer
        extractor = entity_extractor
        language_model = llm
        if catalog is None and language_model is None:
            language_model = _load_llm(settings)
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
            if sentiment is None:
                sentiment = _load_sentiment_analyzer(settings)
            if extractor is None:
                extractor = _load_entity_extractor()
        app.state.details_provider = details
        app.state.genre_classifier = classifier
        app.state.recommender = similar
        app.state.sentiment_analyzer = sentiment
        app.state.entity_extractor = extractor
        app.state.llm = language_model
        app.state.llm_sentiment = _load_llm_sentiment(settings, language_model)
        app.state.synopsis_index = index
        app.state.catalog = getattr(app.state, "catalog", None)
        cached = CachedMovieCatalog(details)
        app.state.search_service = SearchService(cached, index, _load_llm_extractor(settings, language_model, cached))
        app.state.question_answering = question_answering or _load_question_answering(
            settings, index, language_model, app.state.search_service, cached
        )
        app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute)
        app.state.llm_limiter = RateLimiter(settings.llm_rate_limit_per_minute)
        try:
            yield
        finally:
            if client is not None:
                client.close()

    app = FastAPI(
        title="API de Filmes (TMDB)",
        description="Demonstração auxiliar: pesquisa por título, por preferências ou por tema nas sinopses, classificação de gênero, filmes parecidos, análise de sentimento e entidades e relações.",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET"], allow_headers=[])
    app.include_router(api_router)
    if settings.serve_frontend:
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
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


def _load_sentiment_analyzer(settings: Settings) -> SentimentAnalyzer | None:
    """Polaridade e nota ajustadas com as críticas preparadas, na representação configurada."""
    from app.sentiment.live import SentimentAnalyzer as TrainedAnalyzer

    try:
        analyzer = TrainedAnalyzer.load(settings.sentiment_processed_dir, settings.sentiment_config, settings.sentiment_representation)
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.warning("Análise de sentimento indisponível: %s", exc)
        return None
    logger.info("Análise de sentimento treinada com %d críticas (%s)", analyzer.training_size, analyzer.representation_name)
    return analyzer


def _load_entity_extractor() -> EntityExtractor | None:
    """spaCy `pt_core_news_sm`, instalado pelo extra `entidades`."""
    from app.entities.live import EntityExtractor as SpacyExtractor

    try:
        extractor = SpacyExtractor()
    except ValueError as exc:
        logger.warning("Entidades e relações indisponíveis: %s", exc)
        return None
    logger.info("Entidades e relações com o spaCy %s", extractor.model_name)
    return extractor


def _load_llm(settings: Settings) -> LLMStack | None:
    """Pilha de LLM com os provedores que têm chave em `backend/.env` (ADR 0029)."""
    from app.llm.compose import build_llm

    try:
        stack = build_llm(settings)
    except (ValueError, FileNotFoundError) as exc:
        logger.warning("LLM indisponível: %s", exc)
        return None
    if stack is None:
        logger.warning("LLM indisponível: defina GEMINI_API_KEY ou GROQ_API_KEY em backend/.env")
        return None
    logger.info("LLM com %s", ", ".join(stack.providers))
    return stack


def _load_llm_extractor(settings: Settings, llm: LLMStack | None, genres: GenreSource) -> PreferenceExtractor | None:
    """Interpretação da frase pelo LLM, com o prompt versionado (ADR 0030); None sem LLM ou com prompt inválido."""
    if llm is None:
        return None
    from app.search.interpretation.llm_extractor import LLMFilterExtractor
    from app.search.interpretation.prompt import load_prompt

    try:
        prompt = load_prompt(settings.interpretation_prompt)
    except (ValueError, FileNotFoundError) as exc:
        logger.warning("Interpretação por LLM indisponível: %s", exc)
        return None
    return LLMFilterExtractor(llm.model, genres, prompt)


def _load_llm_sentiment(settings: Settings, llm: LLMStack | None) -> LLMSentiment | None:
    """Sentimento por LLM com a variante escolhida na avaliação (ADR 0031); None sem LLM ou com configuração inválida."""
    if llm is None:
        return None
    from app.sentiment.llm.classifier import LLMSentiment as Classifier
    from app.sentiment.llm.prompt import load_config

    try:
        return Classifier(llm.model, load_config(settings.sentiment_llm_config))
    except (ValueError, FileNotFoundError) as exc:
        logger.warning("Sentimento por LLM indisponível: %s", exc)
        return None


def _load_question_answering(
    settings: Settings, index: SynopsisIndex | None, llm: LLMStack | None, search: SearchService, genres: GenreSource
) -> QuestionAnswering | None:
    """RAG sobre o índice de sinopses e as críticas preparadas, com o intérprete da pesquisa (ADR 0032)."""
    from app.search.synopsis_index import CorpusSynopsisIndex

    if llm is None or not isinstance(index, CorpusSynopsisIndex):
        return None
    from app.rag.config import load_config
    from app.rag.retrieval import Retriever, TitleMatcher
    from app.rag.reviews import ReviewStore
    from app.rag.service import QuestionAnswering as Service

    try:
        config = load_config(settings.rag_config)
        reviews = ReviewStore.load(settings.sentiment_processed_dir, index.sentence_encoder())
    except (ValueError, FileNotFoundError) as exc:
        logger.warning("Perguntas (RAG) indisponíveis: %s", exc)
        return None
    retriever = Retriever(index, reviews, search.interpreter(), TitleMatcher(index.titles()), config)
    logger.info("Perguntas (RAG) com %d filmes e críticas de %d deles", index.size, reviews.movies)
    return Service(retriever, llm.model, genres.genres, config)


def _load_recommender(settings: Settings, index: CorpusSynopsisIndex) -> SimilarMoviesProvider | None:
    from app.recommendation.similar import SimilarMovies

    name = settings.synopsis_recommendation_representation
    representations = {representation.spec.name: representation for representation, _ in index.hybrid.members}
    if name not in representations:
        logger.warning("Recomendação indisponível: a representação %r não faz parte da busca por tema", name)
        return None
    return SimilarMovies(representations[name])


app = create_app()
