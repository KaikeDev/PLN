"""Avaliação do sentimento com LLM: amostra fixa → três variantes de prompt e a reserva → métricas → evidências.

Segue o experimento do Jev e a avaliação da interpretação (ADR 0019, 0030):

- as predições do TF-IDF e do BERTimbau vêm dos arquivos fora da dobra do experimento da Aula 9, pelo
  `review_id`; nada é retreinado, e falta de alguma crítica é erro;
- cada variante usa um provedor fixo, sem reserva entre provedores, para não misturar modelos numa mesma
  linha da comparação. As chamadas de cada provedor respeitam `request_interval_seconds` e, na cota por
  minuto, esperam e tentam de novo. Três falhas seguidas por cota suspendem o provedor até o fim da execução;
- a primeira chamada funciona como teste da chave e da resposta: se falhar, nada é gravado. As falhas
  seguintes ficam registradas com o motivo, fora das métricas, e `--reuse` pede de novo só o que faltou;
- as 20 críticas de estabilidade são pedidas uma segunda vez à variante escolhida, e o replay devolve
  cada resposta gravada na ordem.

Tudo é calculado em memória antes de criar a pasta de saída (ADR 0009). Com as mesmas respostas, os
arquivos de conteúdo são idênticos byte a byte; a latência fica só no manifesto.
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
from app.llm.ports import LanguageModel, LLMRequest, LLMResponse, LLMUnavailable
from app.llm.replay import RecordingModel, ReplayModel, ReuseModel
from app.sentiment.llm.classifier import LLMSentiment, result_of
from app.sentiment.llm.metrics import agreement, evaluate, stability, usage
from app.sentiment.llm.prompt import VARIANTS, SentimentLLMConfig, Variant, excerpt, load_config
from app.sentiment.llm.report import make_report
from app.sentiment.llm.sample import Review, load_reviews, load_sample
from app.sentiment.ports import SentimentAnalyzer
from app.shared.artifacts import (
    create_output,
    json_text,
    jsonl_text,
    read_json_array,
    read_json_object,
    read_jsonl,
    sha256,
    source_identity,
    write_json,
    write_text,
)
from app.shared.manifest import MANIFEST_NAME, hash_files, read_manifest, verify_hashes
from app.shared.validation import read_config_json

REFERENCES = ("tfidf", "bertimbau")
MAX_ERROR_CHARS = 300
QUOTA_STRIKES = 3
P95 = 19
ALIGNED_FILES = ("predictions.jsonl",)


@dataclass(frozen=True)
class Inputs:
    """Pastas e arquivos de entrada."""

    processed: Path
    experiment: Path
    config: Path
    sample: Path
    llm_config: Path


def run(
    inputs: Inputs,
    output: Path,
    models_factory: Callable[[], Mapping[str, LanguageModel]],
    reuse: Path | None = None,
    screen_analyzer: Callable[[], SentimentAnalyzer] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Avalia as variantes nas críticas da amostra e grava tudo numa pasta nova.

    `models_factory` devolve um modelo por provedor e só é chamado se algum pedido não estiver entre as respostas
    reaproveitadas. `screen_analyzer` é o analisador da tela (TF-IDF), usado nos casos da equipe.
    """
    if output.exists():
        raise FileExistsError(f"A pasta de saída já existe: {output}")
    config = load_config(inputs.config)
    reviews = load_reviews(inputs.processed, inputs.experiment)
    sample = load_sample(inputs.sample, reviews)
    references = _references(inputs.experiment, config, sample.review_ids)
    llm_config = load_llm_config(inputs.llm_config)
    records = _records(reuse) if reuse else []
    asker = _Asker(config, records, models_factory, llm_config.request_interval_seconds, sleep)

    started = time.perf_counter()
    rows = []
    for review_id in sample.review_ids:
        review = reviews[review_id]
        row = _row(review, config, references[review_id])
        for variant in VARIANTS:
            row[variant] = asker.ask(variant, review.text)
        rows.append(row)
    repeated: list[dict] = []
    chosen = config.chosen_variant
    by_id = {row["review_id"]: row for row in rows}
    for review_id in sample.stability:
        repeated.append(
            {
                "review_id": review_id,
                "primeira": _answer_only(by_id[review_id][chosen]),
                "segunda": asker.ask(chosen, reviews[review_id].text),
            }
        )
    cases = _team_cases(config, asker, screen_analyzer)
    request_seconds = round(time.perf_counter() - started, 3)

    systems = (*REFERENCES, *VARIANTS)
    sampled = set(sample.review_ids)
    outside = [
        float(document["nota"])
        for document in read_json_array(inputs.experiment / "documents.json")
        if document["review_id"] not in sampled
    ]
    metrics = {
        "avaliacao": evaluate(rows, systems, statistics.mean(outside), VARIANTS),
        "concordancia": agreement(rows, chosen, REFERENCES),
        "estabilidade": stability([(item["primeira"], item["segunda"]) for item in repeated]),
        "uso": {variant: usage(rows, variant) for variant in VARIANTS},
        "criticas_cortadas": sum(row["cortada"] for row in rows),
    }
    models = sorted({f"{record['provider']}:{record['model']}" for record in asker.records})
    files = {
        "config.json": json_text(read_config_json(inputs.config)),
        "sample.json": json_text(read_config_json(inputs.sample)),
        "responses.jsonl": jsonl_text(asker.records),
        "predictions.jsonl": jsonl_text(rows),
        "stability.jsonl": jsonl_text(repeated),
        "team_cases.json": json_text(cases),
        "metrics.json": json_text(metrics),
        "report.md": make_report(metrics, rows, cases, config, models, {review_id: reviews[review_id] for review_id in sample.review_ids}),
    }

    create_output(output)
    for filename, content in files.items():
        write_text(output / filename, content)
    write_json(
        output / MANIFEST_NAME,
        {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "source_processed_manifest_sha256": sha256(inputs.processed / "manifest.json"),
            "source_experiment_manifest_sha256": sha256(inputs.experiment / "manifest.json"),
            "config_sha256": sha256(inputs.config),
            "sample_sha256": sha256(inputs.sample),
            "llm_config_sha256": sha256(inputs.llm_config),
            "temperature": llm_config.temperature,
            "chosen_variant": chosen,
            "llm_models": models,
            "api_calls": asker.calls,
            "reused_responses": asker.reused,
            "reused_from": str(reuse) if reuse else None,
            "suspended_providers": sorted(asker.suspended),
            "latency_ms": {variant: _latency(values) for variant, values in asker.latencies.items()},
            "request_seconds": request_seconds,
            "source_identity": source_identity(),
            "python": platform.python_version(),
            "files": hash_files(output),
        },
    )
    verify(output)
    polarity = metrics["avaliacao"]["polaridade"]
    return {
        "criticas": len(rows),
        "api_calls": asker.calls,
        "falhas": {variant: polarity[variant]["falhas"] for variant in VARIANTS},
        "f1_macro": {system: polarity[system]["f1_macro"] for system in systems},
        "output": str(output),
    }


def verify(output: Path) -> dict:
    """Confere os hashes do manifesto e o alinhamento das previsões com a amostra."""
    manifest = read_manifest(output)
    verify_hashes(output, manifest["files"])
    for filename in ("sample.json", *ALIGNED_FILES, "responses.jsonl"):
        if filename not in manifest["files"]:
            raise ValueError(f"Arquivo fora da lista verificada: {filename}")
    ids = [item["review_id"] for item in read_json_object(output / "sample.json")["criticas"]]
    if [row["review_id"] for row in read_jsonl(output / "predictions.jsonl")] != ids:
        raise ValueError("Previsões desalinhadas da amostra")
    return {"status": "ok", "criticas": len(ids), "files_verified": len(manifest["files"])}


class _Asker:
    """Um encadeamento por provedor (replay → intervalo → nova tentativa na cota → modelo) e o registro de tudo."""

    def __init__(
        self,
        config: SentimentLLMConfig,
        records: list[dict],
        models_factory: Callable[[], Mapping[str, LanguageModel]],
        interval: float,
        sleep: Callable[[float], None],
    ) -> None:
        self._config = config
        self.records: list[dict] = []
        factory = _Once(models_factory)
        self._chains: dict[str, ReuseModel] = {}
        for provider in (config.main_provider, config.reserve_provider):
            real = PacedModel(QuotaRetryModel(LazyModel(factory.model(provider)), sleep=sleep), interval, sleep)
            self._chains[provider] = ReuseModel(ReplayModel(records, provider), real)
        self._answered = 0
        self._strikes = {provider: 0 for provider in self._chains}
        self.suspended: set[str] = set()
        self.latencies: dict[str, list[int]] = {variant: [] for variant in VARIANTS}

    @property
    def calls(self) -> int:
        return sum(chain.calls for chain in self._chains.values())

    @property
    def reused(self) -> int:
        return sum(chain.reused for chain in self._chains.values())

    def ask(self, variant: Variant, text: str) -> dict:
        provider = self._config.provider(variant)
        classifier = LLMSentiment(RecordingModel(self._chains[provider], self.records), self._config, variant)
        request = classifier.request(text)
        recorded = self._chains[provider].is_recorded(request)
        if provider in self.suspended and not recorded:
            return _failure("cota", f"{provider} suspenso depois de {QUOTA_STRIKES} falhas seguidas por cota")
        try:
            response = classifier.ask(text)
        except LLMUnavailable as exc:
            message = f"{exc.reason}: {exc}"[:MAX_ERROR_CHARS]
            if not self._answered:
                raise ValueError(f"A primeira chamada ao LLM falhou; nada foi gravado. {message}") from exc
            self._strike(provider, exc)
            return _failure(exc.reason, message)
        self._answered += 1
        self._strikes[provider] = 0
        if not recorded:
            self.latencies[variant].append(response.latency_ms)
        return _answer(response)

    def _strike(self, provider: str, error: LLMUnavailable) -> None:
        self._strikes[provider] = self._strikes[provider] + 1 if error.reason == "cota" else 0
        if self._strikes[provider] >= QUOTA_STRIKES:
            self.suspended.add(provider)


class _Once:
    """Chama a fábrica de modelos uma vez, na primeira chamada real de qualquer provedor."""

    def __init__(self, factory: Callable[[], Mapping[str, LanguageModel]]) -> None:
        self._factory = factory
        self._models: Mapping[str, LanguageModel] | None = None

    def model(self, provider: str) -> Callable[[], LanguageModel]:
        def create() -> LanguageModel:
            if self._models is None:
                self._models = self._factory()
            if provider not in self._models:
                return _Missing(provider)
            return self._models[provider]

        return create


class _Missing:
    def __init__(self, provider: str) -> None:
        self._provider = provider

    def generate(self, request: LLMRequest) -> LLMResponse:
        raise LLMUnavailable("sem_chave", f"Sem chave para {self._provider}")


def _answer(response: LLMResponse) -> dict:
    result = result_of(response)
    return {
        "polaridade": result.polarity,
        "nota": result.rating,
        "justificativa": result.reason,
        "provedor": result.provider,
        "modelo": result.model,
        "tokens_entrada": response.input_tokens,
        "tokens_saida": response.output_tokens,
        "motivo_da_falha": None,
        "erro": None,
    }


def _failure(reason: str, message: str) -> dict:
    return {
        "polaridade": None,
        "nota": None,
        "justificativa": None,
        "provedor": None,
        "modelo": None,
        "tokens_entrada": 0,
        "tokens_saida": 0,
        "motivo_da_falha": reason,
        "erro": message,
    }


def _answer_only(answer: dict) -> dict:
    return {key: answer[key] for key in ("polaridade", "nota", "justificativa", "provedor", "modelo", "motivo_da_falha")}


def _row(review: Review, config: SentimentLLMConfig, references: dict) -> dict:
    return {
        "review_id": review.review_id,
        "id": review.id,
        "titulo": review.title,
        "nota_real": review.rating,
        "polaridade_real": review.polarity,
        "autor_principal": review.main_author,
        "com_negacao": review.negation,
        "cortada": excerpt(review.text, config.sample.max_chars) != review.text,
        **references,
    }


def _references(experiment: Path, config: SentimentLLMConfig, review_ids: tuple[str, ...]) -> dict[str, dict]:
    """Predições fora da dobra das duas referências, por `review_id`; falha se faltar alguma crítica."""
    joined: dict[str, dict] = {review_id: {} for review_id in review_ids}
    for system in REFERENCES:
        name = config.references[system]
        polarity = {row["review_id"]: row for row in read_jsonl(experiment / f"{name}.polaridade.predictions.jsonl")}
        rating = {row["review_id"]: row for row in read_jsonl(experiment / f"{name}.nota.predictions.jsonl")}
        for review_id in review_ids:
            if review_id not in polarity or review_id not in rating:
                raise ValueError(f"Crítica {review_id} sem predição gravada de {name}")
            joined[review_id][system] = {
                "polaridade": polarity[review_id]["previsto"][0],
                "probabilidade_positiva": polarity[review_id]["probabilidades"]["positivo"],
                "nota": rating[review_id]["prevista"],
                "dobra": polarity[review_id]["dobra"],
            }
    return joined


def _team_cases(config: SentimentLLMConfig, asker: _Asker, screen_analyzer: Callable[[], SentimentAnalyzer] | None) -> list[dict]:
    analyzer = screen_analyzer() if screen_analyzer is not None else None
    cases = []
    for case in config.team_cases:
        screen = None
        if analyzer is not None:
            result = analyzer.analyze(case.text)
            screen = {"polaridade": result.polarity, "probabilidade_positiva": result.positive_probability, "nota": result.rating}
        cases.append(
            {
                "tipo": case.kind,
                "texto": case.text,
                "tfidf_da_tela": screen,
                "llm": _answer_only(asker.ask(config.chosen_variant, case.text)),
            }
        )
    return cases


def _records(folder: Path) -> list[dict]:
    verify(folder)
    return read_jsonl(folder / "responses.jsonl")


def _latency(values: list[int]) -> dict:
    if not values:
        return {"chamadas": 0, "mediana_ms": None, "p95_ms": None}
    p95 = statistics.quantiles(values, n=20)[P95 - 1] if len(values) > 1 else values[0]
    return {"chamadas": len(values), "mediana_ms": statistics.median(values), "p95_ms": round(p95)}
