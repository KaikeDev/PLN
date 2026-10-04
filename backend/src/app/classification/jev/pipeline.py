"""Orquestra o experimento: corpus verificado → amostra → Jev e TF-IDF + RL → métricas → evidências rastreáveis.

Cada chamada ao Jev é paga e o alias do modelo pode mudar, por isso:

- a primeira chamada funciona como teste da chave e da resposta: se falhar, nada é gravado;
- as seguintes que falharem ficam registradas com o erro e fora das métricas;
- as respostas brutas validadas vão para `responses.jsonl`, e `--reuse` reaproveita as de uma
  execução anterior com as mesmas perguntas, sem novas chamadas.

Como na Etapa 2, tudo é calculado em memória antes de a pasta de saída ser criada (ADR 0009).
Com as mesmas respostas, os arquivos de conteúdo são idênticos byte a byte; o tempo das chamadas vai
só para o manifesto.
"""

import hashlib
import platform
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from app.classification.jev.baseline import baseline_predictions
from app.classification.jev.config import CHOICE_NAME, JevConfig, draw_sample, load_config
from app.classification.jev.evaluation import evaluate
from app.classification.jev.ports import DecisionClient, Question
from app.classification.jev.report import make_report
from app.classification.jev.responses import validate_response
from app.representations.corpus import Document, ProcessedCorpus
from app.shared.artifacts import (
    create_output,
    json_text,
    jsonl_text,
    read_json_array,
    read_jsonl,
    sha256,
    source_identity,
    write_json,
    write_text,
)
from app.shared.manifest import MANIFEST_NAME, hash_files, read_manifest, verify_hashes

LIBRARIES = ("typesafe-sdk", "scikit-learn", "numpy", "scipy")
MAX_ERROR_CHARS = 300
ALIGNED_FILES = ("responses.jsonl", "predictions.jsonl")

ClientFactory = Callable[[], AbstractContextManager[DecisionClient]]


def run(
    processed: Path,
    output: Path,
    config_path: Path,
    client_factory: ClientFactory,
    reuse: Path | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Avalia o Jev na amostra configurada e grava previsões, métricas e relatório numa pasta nova.

    `client_factory` só é chamado se restar algum filme sem resposta reaproveitada.
    """
    if output.exists():
        raise FileExistsError(f"A pasta de saída já existe: {output}")
    config = load_config(config_path)
    corpus = ProcessedCorpus.load(processed)
    sample = draw_sample(corpus, config)
    questions = config.questions()
    questions_text = json_text({name: asdict(question) for name, question in questions.items()})
    questions_sha256 = hashlib.sha256(questions_text.encode("utf-8")).hexdigest()
    reused = _reusable(reuse, questions_sha256, config.stage) if reuse else {}
    texts = dict(zip(corpus.ids, corpus.texts(config.stage), strict=True))
    pending = [document for document in sample if document.id not in reused]
    started = time.perf_counter()
    answered = _ask(pending, texts, questions, client_factory, config.request_interval_seconds, sleep) if pending else {}
    request_seconds = round(time.perf_counter() - started, 3)
    responses = [reused.get(document.id) or answered[document.id] for document in sample]

    baseline = baseline_predictions(corpus, config, sample)
    predictions = [
        _prediction(document, response, baseline[document.id], config) for document, response in zip(sample, responses, strict=True)
    ]
    metrics = evaluate(predictions, config.keys, config.threshold)
    names = {genre.key: corpus.genre_names[genre.id] for genre in config.genres}
    models = sorted({response["model"] for response in responses if response.get("model")})
    files = {
        "config.json": json_text(asdict(config)),
        "questions.json": questions_text,
        "sample.json": json_text([{"id": d.id, "title": d.title, "gold": list(config.gold(d))} for d in sample]),
        "responses.jsonl": jsonl_text(responses),
        "predictions.jsonl": jsonl_text(predictions),
        "metrics.json": json_text(metrics),
        "report.md": make_report(metrics, predictions, config, names, models),
    }

    create_output(output)
    for filename, content in files.items():
        write_text(output / filename, content)
    write_json(
        output / MANIFEST_NAME,
        {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "source_processed_manifest_sha256": corpus.manifest_sha256,
            "config_sha256": sha256(config_path),
            "questions_sha256": questions_sha256,
            "stage": config.stage,
            "jev_models": models,
            "api_calls": len(pending),
            "reused_responses": len(sample) - len(pending),
            "reused_from": str(reuse) if reuse else None,
            "request_seconds": request_seconds,
            "source_identity": source_identity(),
            "python": platform.python_version(),
            "libraries": _library_versions(),
            "files": hash_files(output),
        },
    )
    verify(output)
    return {
        "films": len(sample),
        "api_calls": len(pending),
        "evaluated": metrics["evaluated"],
        "failed": metrics["failed"],
        "output": str(output),
    }


def verify(output: Path) -> dict:
    """Confere os hashes do manifesto e o alinhamento das respostas e previsões com a amostra."""
    manifest = read_manifest(output)
    verify_hashes(output, manifest["files"])
    ids = [row["id"] for row in read_json_array(output / "sample.json")]
    for filename in ALIGNED_FILES:
        if filename not in manifest["files"]:
            raise ValueError(f"Arquivo fora da lista verificada: {filename}")
        if [row["id"] for row in read_jsonl(output / filename)] != ids:
            raise ValueError(f"Linhas desalinhadas da amostra: {filename}")
    return {"status": "ok", "films": len(ids), "files_verified": len(manifest["files"])}


def _ask(
    documents: Sequence[Document],
    texts: Mapping[int, str],
    questions: Mapping[str, Question],
    client_factory: ClientFactory,
    interval: float,
    sleep: Callable[[float], None],
) -> dict[int, dict]:
    """Uma chamada por filme, em sequência. A primeira falha interrompe; as demais são registradas."""
    answered: dict[int, dict] = {}
    with client_factory() as client:
        for index, document in enumerate(documents):
            if index:
                sleep(interval)
            try:
                response = validate_response(client.decide(texts[document.id], questions), questions)
                answered[document.id] = {"id": document.id, **response, "error": None}
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"[:MAX_ERROR_CHARS]
                if not index:
                    raise ValueError(f"A primeira chamada ao Jev falhou; nada foi gravado. {message}") from exc
                answered[document.id] = {"id": document.id, "model": None, "usage": None, "answers": None, "error": message}
    return answered


def _reusable(folder: Path, questions_sha256: str, stage: str) -> dict[int, dict]:
    """Respostas sem erro de uma execução verificada que usou as mesmas perguntas e o mesmo texto."""
    verify(folder)
    manifest = read_manifest(folder)
    if manifest.get("questions_sha256") != questions_sha256 or manifest.get("stage") != stage:
        raise ValueError("As respostas a reaproveitar foram geradas com outras perguntas ou outra etapa de texto")
    return {row["id"]: row for row in read_jsonl(folder / "responses.jsonl") if row["error"] is None}


def _prediction(document: Document, response: dict, baseline: dict, config: JevConfig) -> dict:
    jev = None
    if response["error"] is None:
        answers = response["answers"]
        choice = answers[CHOICE_NAME]
        jev = {
            "choice": choice["choice"],
            "choice_probabilities": choice["probabilities"],
            "confidence": choice["confidence"],
            "labels": {genre.key: answers[genre.noul_name]["noul"] for genre in config.genres},
        }
    return {
        "id": document.id,
        "title": document.title,
        "gold": list(config.gold(document)),
        "jev": jev,
        "tfidf_logreg": baseline,
        "error": response["error"],
    }


def _library_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in LIBRARIES:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    return versions
