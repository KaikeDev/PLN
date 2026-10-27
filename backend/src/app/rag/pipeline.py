"""Avaliação do RAG na amostra de 428 filmes: perguntas e consultas fixas → respostas → métricas → evidências.

- **A. Ordenação:** as 20 consultas anotadas com k = 5, 10 e 20 filmes no contexto; o LLM cita até 5.
- **B. Perguntas:** as 33 perguntas de `config/rag/perguntas.json` com a configuração do site; a resposta, o
  contexto e a conferência vão para `predictions.jsonl`, que é o que os juízes leem.
- **D. Ablação:** as mesmas perguntas sem trechos de crítica no contexto.

Os filtros vêm do LLM (variante do site, ADR 0030) e, se ele falhar, das regras; cada frase é interpretada
uma vez. Segue as regras das outras avaliações com LLM: respostas gravadas e `--reuse`, primeira chamada
como teste, falhas registradas e intervalo entre chamadas (ADR 0019, 0029). A latência fica no manifesto.
"""

import platform
import statistics
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.llm.batch import LazyModel, PacedModel, QuotaRetryModel
from app.llm.config import load_config as load_llm_config
from app.llm.ports import LanguageModel, LLMUnavailable
from app.llm.replay import RecordingModel, ReplayModel, ReuseModel
from app.rag.config import RagConfig, load_config
from app.rag.evaluation import agreement, injection_obeyed, question_scores, ranking_scores
from app.rag.retrieval import Retriever, TitleMatcher
from app.rag.reviews import ReviewStore
from app.rag.service import Answer, QuestionAnswering
from app.representations.config import load_queries
from app.search.filters import ExtractedFilters
from app.search.interpretation.dataset import StaticGenres, load_genres
from app.search.interpretation.llm_extractor import LLMFilterExtractor
from app.search.interpretation.prompt import load_prompt
from app.search.ports import SynopsisIndex
from app.search.rules.extractor import FilterExtractor
from app.shared.artifacts import (
    create_output,
    json_text,
    jsonl_text,
    read_json_object,
    read_jsonl,
    sha256,
    source_identity,
    write_json,
    write_text,
)
from app.shared.manifest import MANIFEST_NAME, hash_files, read_manifest, verify_hashes
from app.shared.validation import read_config_json, require_name, require_object, require_unique

CATEGORIES = ("tema", "opiniao", "sem_resposta", "injecao")
RANKING_KS = (5, 10, 20)
MAX_QUESTION_CHARS = 300
MAX_ERROR_CHARS = 300
P95 = 19


@dataclass(frozen=True)
class Question:
    id: str
    category: str
    text: str


@dataclass(frozen=True)
class Inputs:
    """Configurações e dados da avaliação; o índice e as críticas chegam prontos, porque exigem os modelos de sentença."""

    questions: Path
    queries: Path
    rag_config: Path
    interpretation_prompt: Path
    genres: Path
    llm_config: Path


def load_questions(path: Path) -> tuple[Question, ...]:
    data = require_object(read_config_json(path), "perguntas do RAG", required={"perguntas"}, optional={"description"})
    items = data["perguntas"]
    if not isinstance(items, list) or not items:
        raise ValueError("perguntas deve ser uma lista não vazia")
    questions = []
    for position, value in enumerate(items):
        item = require_object(value, f"pergunta {position}", required={"id", "categoria", "texto"})
        if item["categoria"] not in CATEGORIES:
            raise ValueError(f"pergunta {position}: categoria deve ser uma de {list(CATEGORIES)}")
        text = item["texto"]
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_QUESTION_CHARS:
            raise ValueError(f"pergunta {position}: texto de 1 a {MAX_QUESTION_CHARS} caracteres")
        questions.append(Question(require_name(item["id"], f"pergunta {position}: id"), item["categoria"], text))
    require_unique([question.id for question in questions], "Perguntas com id repetido")
    return tuple(questions)


def run(
    inputs: Inputs,
    output: Path,
    index: SynopsisIndex,
    titles: Mapping[int, str],
    reviews: ReviewStore,
    model_factory: Callable[[], LanguageModel],
    reuse: Path | None = None,
    ablation: bool = True,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Roda A, B e (com `ablation`) D e grava tudo numa pasta nova; `model_factory` só é chamado se faltar resposta gravada."""
    if output.exists():
        raise FileExistsError(f"A pasta de saída já existe: {output}")
    questions = load_questions(inputs.questions)
    queries = load_queries(inputs.queries)
    config = load_config(inputs.rag_config)
    genres = load_genres(inputs.genres)
    llm_config = load_llm_config(inputs.llm_config)
    records = _records(reuse) if reuse else []
    chain = ReuseModel(
        ReplayModel(records), PacedModel(QuotaRetryModel(LazyModel(model_factory), sleep=sleep), llm_config.request_interval_seconds, sleep)
    )
    recorded: list[dict] = []
    model = RecordingModel(chain, recorded)
    catalog = StaticGenres(genres)
    extractor = _Interpreter(LLMFilterExtractor(model, catalog, load_prompt(inputs.interpretation_prompt)), FilterExtractor(catalog))
    qa = QuestionAnswering(Retriever(index, reviews, extractor, TitleMatcher(titles), config), model, lambda: genres, config)
    asker = _Asker(qa, chain)

    started = time.perf_counter()
    ranking = [_ranking_row(query.id, k, asker.ask(query.text, config.with_k(k))) for k in RANKING_KS for query in queries]
    predictions = [_question_row(question, asker.ask(question.text, config)) for question in questions]
    without_reviews = (
        [_question_row(question, asker.ask(question.text, config.without_reviews())) for question in questions] if ablation else []
    )
    request_seconds = round(time.perf_counter() - started, 3)

    relevant = {query.id: query.relevant_ids for query in queries}
    hybrid = _hybrid_baseline(index, queries)
    metrics: dict = {
        "ordenacao": {
            "busca_hibrida_sozinha": hybrid,
            **{
                f"k_{k}": _without_detail(
                    ranking_scores([row for row in ranking if row["k"] == k and row["falha"] is None], relevant), k, ranking
                )
                for k in RANKING_KS
            },
        },
        "perguntas": question_scores(predictions),
        "sem_criticas": question_scores(without_reviews) if ablation else None,
        "uso": asker.usage(),
        "interpretacao": {"llm": extractor.by_llm, "regras": extractor.by_rules},
    }
    models = sorted({f"{record['provider']}:{record['model']}" for record in recorded})
    files = {
        "questions.json": json_text(read_config_json(inputs.questions)),
        "rag_config.json": json_text(read_config_json(inputs.rag_config)),
        "responses.jsonl": jsonl_text(recorded),
        "ranking.jsonl": jsonl_text(ranking),
        "predictions.jsonl": jsonl_text(predictions),
        "metrics.json": json_text(metrics),
    }
    if ablation:
        files["without_reviews.jsonl"] = jsonl_text(without_reviews)
    from app.rag.report import make_report

    files["report.md"] = make_report(metrics, predictions, without_reviews, models, config)

    create_output(output)
    for filename, content in files.items():
        write_text(output / filename, content)
    write_json(
        output / MANIFEST_NAME,
        {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "questions_sha256": sha256(inputs.questions),
            "queries_sha256": sha256(inputs.queries),
            "rag_config_sha256": sha256(inputs.rag_config),
            "interpretation_prompt_sha256": sha256(inputs.interpretation_prompt),
            "genres_sha256": sha256(inputs.genres),
            "llm_config_sha256": sha256(inputs.llm_config),
            "temperature": llm_config.temperature,
            "llm_models": models,
            "catalog_movies": len(titles),
            "movies_with_reviews": reviews.movies,
            "api_calls": chain.calls,
            "reused_responses": chain.reused,
            "reused_from": str(reuse) if reuse else None,
            "latency_ms": _latency(asker.latencies),
            "request_seconds": request_seconds,
            "source_identity": source_identity(),
            "python": platform.python_version(),
            "files": hash_files(output),
        },
    )
    verify(output)
    return {
        "perguntas": len(predictions),
        "api_calls": chain.calls,
        "falhas": sum(row["falha"] is not None for row in [*predictions, *without_reviews])
        + sum(row["falha"] is not None for row in ranking),
        "precisao_dos_citados": {key: value["precisao_dos_citados"] for key, value in metrics["ordenacao"].items() if key.startswith("k_")},
        "precisao_da_busca_at_5": hybrid["precisao_at_5"],
        "output": str(output),
    }


def verify(output: Path) -> dict:
    """Confere os hashes do manifesto e o alinhamento das respostas com as perguntas."""
    manifest = read_manifest(output)
    verify_hashes(output, manifest["files"])
    for filename in ("questions.json", "predictions.jsonl", "responses.jsonl"):
        if filename not in manifest["files"]:
            raise ValueError(f"Arquivo fora da lista verificada: {filename}")
    ids = [item["id"] for item in read_json_object(output / "questions.json")["perguntas"]]
    for filename in ("predictions.jsonl", "without_reviews.jsonl"):
        if filename in manifest["files"] and [row["id"] for row in read_jsonl(output / filename)] != ids:
            raise ValueError(f"Respostas desalinhadas das perguntas: {filename}")
    return {"status": "ok", "perguntas": len(ids), "files_verified": len(manifest["files"])}


def judgment_template(output: Path) -> dict:
    """Modelo de `julgamentos.json` para os dois juízes, com uma entrada por pergunta da avaliação."""
    verify(output)
    empty = {"fiel": "", "responde": "", "citacao": "", "nota": ""}
    return {
        "description": "Julgamento humano das respostas do RAG com a rubrica de config/rag/rubrica.md. Cada juiz preenche só a sua coluna, sem ver a outra.",
        "avaliacao": output.name,
        "juizes": {"a": "", "b": ""},
        "julgamentos": [{"id": row["id"], "a": dict(empty), "b": dict(empty)} for row in read_jsonl(output / "predictions.jsonl")],
    }


def judgment_agreement(output: Path, judgments: Path) -> dict:
    """Concordância entre os juízes de um `julgamentos.json` preenchido."""
    verify(output)
    data = require_object(
        read_config_json(judgments), judgments.name, required={"avaliacao", "juizes", "julgamentos"}, optional={"description"}
    )
    ids = {row["id"] for row in read_jsonl(output / "predictions.jsonl")}
    if unknown := sorted({item["id"] for item in data["julgamentos"]} - ids):
        raise ValueError(f"Julgamentos de perguntas fora da avaliação: {unknown}")
    return agreement(data["julgamentos"])


class _Interpreter:
    """Filtros do LLM com queda nas regras, uma vez por frase, contando a origem."""

    def __init__(self, llm: LLMFilterExtractor, rules: FilterExtractor) -> None:
        self._llm = llm
        self._rules = rules
        self._cache: dict[str, ExtractedFilters] = {}
        self.by_llm = 0
        self.by_rules = 0

    def extract(self, text: str) -> ExtractedFilters:
        if text not in self._cache:
            try:
                self._cache[text] = self._llm.extract(text)
                self.by_llm += 1
            except LLMUnavailable:
                self._cache[text] = self._rules.extract(text)
                self.by_rules += 1
        return self._cache[text]


class _Asker:
    """Responde e registra a falha; a primeira chamada que falha interrompe a avaliação."""

    def __init__(self, qa: QuestionAnswering, chain: ReuseModel) -> None:
        self._qa = qa
        self._chain = chain
        self._answered = 0
        self.latencies: list[int] = []
        self._tokens: list[tuple[int, int]] = []
        self._providers: dict[str, int] = {}
        self._failures: dict[str, int] = {}

    def ask(self, question: str, config: RagConfig) -> Answer | LLMUnavailable:
        calls = self._chain.calls
        started = time.perf_counter()
        try:
            answer = self._qa.answer(question, config)
        except LLMUnavailable as exc:
            if not self._answered:
                raise ValueError(f"A primeira chamada ao LLM falhou; nada foi gravado. {exc.reason}: {exc}"[:MAX_ERROR_CHARS]) from exc
            self._failures[exc.reason] = self._failures.get(exc.reason, 0) + 1
            return exc
        self._answered += 1
        if self._chain.calls > calls:
            self.latencies.append(round((time.perf_counter() - started) * 1000))
        self._tokens.append((answer.input_tokens, answer.output_tokens))
        self._providers[answer.provider] = self._providers.get(answer.provider, 0) + 1
        return answer

    def usage(self) -> dict:
        return {
            "respostas": len(self._tokens),
            "tokens_entrada_medio": round(statistics.mean(t[0] for t in self._tokens), 1) if self._tokens else None,
            "tokens_saida_medio": round(statistics.mean(t[1] for t in self._tokens), 1) if self._tokens else None,
            "provedores": dict(sorted(self._providers.items())),
            "falhas_por_motivo": dict(sorted(self._failures.items())),
        }


def _ranking_row(query_id: str, k: int, result: Answer | LLMUnavailable) -> dict:
    if isinstance(result, LLMUnavailable):
        return {"consulta": query_id, "k": k, "contexto": [], "citados": [], "tokens_entrada": 0, "falha": result.reason}
    return {
        "consulta": query_id,
        "k": k,
        "contexto": [movie.id for movie in result.retrieval.movies],
        "citados": [cited.id for cited in result.grounded.cited],
        "tokens_entrada": result.input_tokens,
        "falha": None,
    }


def _question_row(question: Question, result: Answer | LLMUnavailable) -> dict:
    base = {"id": question.id, "categoria": question.category, "pergunta": question.text}
    if isinstance(result, LLMUnavailable):
        return {
            **base,
            "falha": f"{result.reason}: {result}"[:MAX_ERROR_CHARS],
            "resposta": None,
            "citados": [],
            "contexto_suficiente": False,
            "inventadas": [],
            "trocada": False,
            "injecao_obedecida": None,
            "resposta_bruta": None,
            "filtros": None,
            "contexto": [],
        }
    grounded = result.grounded
    filters = result.retrieval.filters
    return {
        **base,
        "falha": None,
        "provedor": result.provider,
        "modelo": result.model,
        "resposta": grounded.answer,
        "citados": [{"id": cited.id, "titulo": _title(result, cited.id), "motivo": cited.reason} for cited in grounded.cited],
        "contexto_suficiente": grounded.sufficient,
        "inventadas": list(grounded.invented),
        "trocada": grounded.replaced,
        "injecao_obedecida": injection_obeyed(question.id, result.raw["resposta"]),
        "resposta_bruta": result.raw,
        "filtros": {
            "origem": filters.origin,
            "generos": list(filters.genres),
            "excluidos": list(filters.excluded_genres),
            "lancado_depois": filters.released_after,
            "lancado_antes": filters.released_before,
            "nota_minima": filters.min_rating,
        },
        "contexto": [
            {
                "id": movie.id,
                "titulo": movie.movie.get("title"),
                "pontuacao": movie.score,
                "criticas_do_filme": movie.reviews,
                "trechos": [{"texto": excerpt.text, "nota": excerpt.rating} for excerpt in movie.excerpts],
            }
            for movie in result.retrieval.movies
        ],
    }


def _title(result: Answer, movie_id: int) -> str | None:
    return next((movie.movie.get("title") for movie in result.retrieval.movies if movie.id == movie_id), None)


def _hybrid_baseline(index: SynopsisIndex, queries: tuple) -> dict:
    """Precisão @5 da busca híbrida sozinha, sem filtros, nas mesmas consultas (a referência de 0,57)."""
    values = [sum(movie_id in set(query.relevant_ids) for movie_id, _ in index.rank(query.text)[:5]) / 5 for query in queries]
    return {"precisao_at_5": round(statistics.mean(values), 4)}


def _without_detail(scores: dict, k: int, ranking: list[dict]) -> dict:
    rows = [row for row in ranking if row["k"] == k and row["falha"] is None]
    return {
        **{key: value for key, value in scores.items() if key != "por_consulta"},
        "tokens_entrada_medio": round(statistics.mean(row["tokens_entrada"] for row in rows), 1) if rows else None,
        "falhas": sum(row["falha"] is not None for row in ranking if row["k"] == k),
    }


def _records(folder: Path) -> list[dict]:
    verify(folder)
    return read_jsonl(folder / "responses.jsonl")


def _latency(values: list[int]) -> dict:
    if not values:
        return {"chamadas": 0, "mediana_ms": None, "p95_ms": None}
    p95 = statistics.quantiles(values, n=20)[P95 - 1] if len(values) > 1 else values[0]
    return {"chamadas": len(values), "mediana_ms": statistics.median(values), "p95_ms": round(p95)}
