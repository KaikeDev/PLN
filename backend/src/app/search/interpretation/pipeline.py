"""Avaliação da interpretação: frases anotadas → regras, LLM zero-shot e few-shot → métricas → evidências rastreáveis.

Segue o experimento do Jev (ADR 0019):

- a primeira chamada ao LLM funciona como teste da chave e da resposta: se falhar, nada é gravado;
- as seguintes que falharem ficam registradas com o motivo e contam como erro nas métricas;
- as respostas validadas vão para `responses.jsonl`, e `--reuse` reaproveita as de uma execução anterior
  sem novas chamadas; um prompt diferente gera pedidos novos;
- as chamadas novas respeitam `request_interval_seconds` de `config/llm/llm.json`.

Tudo é calculado em memória antes de a pasta de saída ser criada (ADR 0009). Com as mesmas respostas,
os arquivos de conteúdo são idênticos byte a byte; a latência e o tempo das chamadas vão só para o manifesto.
"""

import platform
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.llm.batch import LazyModel, PacedModel
from app.llm.config import load_config as load_llm_config
from app.llm.ports import LanguageModel, LLMUnavailable
from app.llm.replay import RecordingModel, ReplayModel, ReuseModel
from app.search.filters import ExtractedFilters
from app.search.interpretation.dataset import Phrase, StaticGenres, judgement, load_genres, load_phrases
from app.search.interpretation.evaluation import evaluate, usage
from app.search.interpretation.llm_extractor import LLMFilterExtractor
from app.search.interpretation.prompt import VARIANTS, Variant, load_prompt
from app.search.interpretation.report import make_report
from app.search.interpretation.search_effect import search_effect
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
from app.shared.validation import read_config_json

SYSTEMS = ("regras", "zero_shot", "few_shot", "reserva")
MAX_ERROR_CHARS = 300
P95 = 19


@dataclass(frozen=True)
class Inputs:
    """Arquivos de entrada: frases anotadas, prompt, gêneros da amostra e configuração do LLM."""

    phrases: Path
    prompt: Path
    genres: Path
    llm_config: Path


@dataclass(frozen=True)
class SearchEffectInputs:
    """Consultas anotadas e o índice da amostra para medir o efeito na busca (exige o extra `semantico`)."""

    queries: Path
    index_factory: Callable[[], SynopsisIndex]


def run(
    inputs: Inputs,
    output: Path,
    model_factory: Callable[[], LanguageModel],
    reuse: Path | None = None,
    effect: SearchEffectInputs | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Avalia as regras e as duas variantes do LLM nas frases anotadas e grava tudo numa pasta nova.

    `model_factory` só é chamado se algum pedido não estiver entre as respostas reaproveitadas.
    """
    if output.exists():
        raise FileExistsError(f"A pasta de saída já existe: {output}")
    genres = load_genres(inputs.genres)
    phrase_set = load_phrases(inputs.phrases, genres.values())
    prompt = load_prompt(inputs.prompt)
    llm_config = load_llm_config(inputs.llm_config)
    replay = _replay(reuse) if reuse else ReplayModel([])
    reuse_model = ReuseModel(replay, PacedModel(LazyModel(model_factory), llm_config.request_interval_seconds, sleep))
    recorder = RecordingModel(reuse_model)
    catalog = StaticGenres(genres)
    reference = phrase_set.reference_date
    rules = FilterExtractor(catalog, current_year=reference.year)
    extractors = {
        variant: LLMFilterExtractor(recorder, catalog, prompt, variant, lambda: reference, use_theme=True) for variant in VARIANTS
    }
    asker = _Asker(reuse_model)

    started = time.perf_counter()
    predictions = []
    for phrase in phrase_set.phrases:
        row = _row(phrase, judgement(rules.extract(phrase.text), genres))
        for variant in VARIANTS:
            row[variant] = asker.ask(extractors[variant], phrase.text, variant, genres)
        site = row[prompt.site_variant]
        fell_back = site["filtros"] is None
        row["reserva"] = {"filtros": row["regras"]["filtros"] if fell_back else site["filtros"], "origem": "regras" if fell_back else "llm"}
        predictions.append(row)
    effect_result = None
    if effect is not None:
        from app.representations.config import load_queries

        site_extractor = extractors[prompt.site_variant]

        def interpret(text: str) -> ExtractedFilters | None:
            try:
                return site_extractor.extract(text)
            except LLMUnavailable:
                return None

        effect_result = search_effect(effect.index_factory(), load_queries(effect.queries), rules, interpret)
    request_seconds = round(time.perf_counter() - started, 3)

    metrics = {
        "avaliacao": evaluate(predictions, SYSTEMS),
        "uso": {variant: usage(predictions, variant) for variant in VARIANTS},
        "reserva": {"quedas_para_regras": sum(row["reserva"]["origem"] == "regras" for row in predictions)},
    }
    models = sorted({f"{record['provider']}:{record['model']}" for record in recorder.records})
    files = {
        "phrases.json": json_text(read_config_json(inputs.phrases)),
        "prompt.json": json_text(read_config_json(inputs.prompt)),
        "responses.jsonl": jsonl_text(recorder.records),
        "predictions.jsonl": jsonl_text(predictions),
        "metrics.json": json_text(metrics),
        "report.md": make_report(metrics, predictions, prompt.site_variant, reference.isoformat(), models, effect_result),
    }
    if effect_result is not None:
        files["search_effect.json"] = json_text(effect_result)

    create_output(output)
    for filename, content in files.items():
        write_text(output / filename, content)
    write_json(
        output / MANIFEST_NAME,
        {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "reference_date": reference.isoformat(),
            "phrases_sha256": sha256(inputs.phrases),
            "prompt_sha256": sha256(inputs.prompt),
            "genres_sha256": sha256(inputs.genres),
            "llm_config_sha256": sha256(inputs.llm_config),
            "queries_sha256": sha256(effect.queries) if effect is not None else None,
            "site_variant": prompt.site_variant,
            "temperature": llm_config.temperature,
            "llm_models": models,
            "api_calls": reuse_model.calls,
            "reused_responses": reuse_model.reused,
            "reused_from": str(reuse) if reuse else None,
            "latency_ms": {variant: _latency(asker.latencies[variant]) for variant in VARIANTS},
            "request_seconds": request_seconds,
            "source_identity": source_identity(),
            "python": platform.python_version(),
            "files": hash_files(output),
        },
    )
    verify(output)
    total = metrics["avaliacao"]["total"]
    return {
        "frases": len(predictions),
        "api_calls": reuse_model.calls,
        "acerto_exato": {system: total[system]["acerto_exato"] for system in SYSTEMS},
        "output": str(output),
    }


def verify(output: Path) -> dict:
    """Confere os hashes do manifesto e o alinhamento das previsões com as frases."""
    manifest = read_manifest(output)
    verify_hashes(output, manifest["files"])
    for filename in ("phrases.json", "predictions.jsonl", "responses.jsonl"):
        if filename not in manifest["files"]:
            raise ValueError(f"Arquivo fora da lista verificada: {filename}")
    ids = [phrase["id"] for phrase in read_json_object(output / "phrases.json")["frases"]]
    if [row["id"] for row in read_jsonl(output / "predictions.jsonl")] != ids:
        raise ValueError("Previsões desalinhadas das frases")
    return {"status": "ok", "frases": len(ids), "files_verified": len(manifest["files"])}


class _Asker:
    """Pergunta ao LLM e registra a resposta ou a falha; a primeira chamada que falha interrompe a avaliação."""

    def __init__(self, reuse_model: ReuseModel) -> None:
        self._reuse = reuse_model
        self._answered = 0
        self.latencies: dict[Variant, list[int]] = {variant: [] for variant in VARIANTS}

    def ask(self, extractor: LLMFilterExtractor, text: str, variant: Variant, genres: dict[int, str]) -> dict:
        recorded = self._reuse.is_recorded(extractor.request(text))
        try:
            response = extractor.ask(text)
        except LLMUnavailable as exc:
            message = f"{exc.reason}: {exc}"[:MAX_ERROR_CHARS]
            if not self._answered:
                raise ValueError(f"A primeira chamada ao LLM falhou; nada foi gravado. {message}") from exc
            return {
                "filtros": None,
                "tema": None,
                "provedor": None,
                "modelo": None,
                "tokens_entrada": 0,
                "tokens_saida": 0,
                "motivo_da_falha": exc.reason,
                "erro": message,
            }
        self._answered += 1
        if not recorded:
            self.latencies[variant].append(response.latency_ms)
        filters = extractor.to_filters(response.data)
        return {
            "filtros": judgement(filters, genres),
            "tema": filters.theme,
            "provedor": response.provider,
            "modelo": response.model,
            "tokens_entrada": response.input_tokens,
            "tokens_saida": response.output_tokens,
            "motivo_da_falha": None,
            "erro": None,
        }


def _row(phrase: Phrase, rules: dict) -> dict:
    return {"id": phrase.id, "texto": phrase.text, "categoria": phrase.category, "esperado": phrase.expected, "regras": {"filtros": rules}}


def _replay(folder: Path) -> ReplayModel:
    verify(folder)
    return ReplayModel.from_file(folder / "responses.jsonl")


def _latency(values: list[int]) -> dict:
    if not values:
        return {"chamadas": 0, "mediana_ms": None, "p95_ms": None}
    p95 = statistics.quantiles(values, n=20)[P95 - 1] if len(values) > 1 else values[0]
    return {"chamadas": len(values), "mediana_ms": statistics.median(values), "p95_ms": round(p95)}
