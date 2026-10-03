"""Orquestra a Etapa 3: corpus verificado → tarefas → representações → validação cruzada → evidências.

Segue as regras da Etapa 2 (ADR 0009): tudo é calculado e serializado em memória antes de criar a
pasta de saída, que nunca é sobrescrita; o manifesto registra hashes, versões e tempos, e os arquivos
de conteúdo não têm nada que varie entre execuções. Com `vectors`, as representações densas são lidas
de uma pasta verificada da Etapa 2 em vez de recalculadas (ADR 0018).
"""

import platform
import time
from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from app.classification.alternatives import ALTERNATIVES, compare
from app.classification.config import ClassificationConfig, load_config
from app.classification.dataset import Task, make_tasks
from app.classification.evaluation import (
    BASELINE,
    LOGISTIC,
    confident_errors,
    constant_features,
    cross_validate,
    features,
    fold_of,
    metrics,
    prediction_rows,
    splits,
    top_terms,
)
from app.classification.grouping import cluster
from app.classification.report import Findings, make_report
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
from app.shared.manifest import MANIFEST_NAME, hash_files, read_manifest, require_plain_filename, verify_hashes
from app.vectors.corpus import ProcessedCorpus
from app.vectors.methods import METHODS, Method
from app.vectors.pipeline import DESCRIPTOR, library_versions
from app.vectors.space import TFIDF
from app.vectors.stored import StoredVectors


def prepare(
    processed: Path, config_path: Path, methods: Mapping[str, Method] = METHODS
) -> tuple[ProcessedCorpus, ClassificationConfig, tuple[Task, Task]]:
    """Valida configuração, corpus e tarefas antes de qualquer cálculo ou download de modelo."""
    config = load_config(config_path, methods, ALTERNATIVES)
    corpus = ProcessedCorpus.load(processed)
    if unknown := sorted(set(config.labels) - corpus.genre_names.keys()):
        raise ValueError(f"Gêneros ausentes da lista do TMDB na pasta processada: {unknown}")
    return corpus, config, make_tasks(corpus, config.labels, config.folds)


def build(processed: Path, output: Path, config_path: Path, methods: Mapping[str, Method] = METHODS, vectors: Path | None = None) -> dict:
    """Avalia a referência e cada representação nas duas tarefas, numa pasta nova, e verifica o resultado.

    Na tarefa multiclasse, cada representação também é agrupada pelo K-Means (sem rótulos) e avaliada com os
    classificadores alternativos da configuração, para comparar agrupar × classificar e um classificador × outro.
    """
    if output.exists():
        raise FileExistsError(f"A pasta de saída já existe: {output}")
    corpus, config, tasks = prepare(processed, config_path, methods)
    stored = StoredVectors(vectors, corpus) if vectors else None
    multiclass = tasks[0]
    folds = {task.name: splits(task, config.folds, config.random_state) for task in tasks}
    assignment = {task.name: fold_of(task, folds[task.name]) for task in tasks}
    titles = {document.id: document.title for document in corpus.documents}
    results: dict[str, dict[str, dict]] = {task.name: {} for task in tasks}
    baseline = constant_features(len(corpus.documents))
    for task in tasks:
        results[task.name][BASELINE] = metrics(task, cross_validate(task, baseline, BASELINE, folds[task.name], config))

    files: dict[str, str] = {}
    row_files: dict[str, str] = {}
    representations: dict[str, dict] = {}
    terms: dict[str, dict] = {}
    errors: dict[str, list] = {}
    clusters: dict[str, dict] = {}
    alternatives: dict[str, dict] = {}
    seconds: dict[str, float] = {}
    reused: list[str] = []
    descriptor = TFIDF.build(DESCRIPTOR, corpus, config.vector_config())
    for spec in config.representations:
        started = time.perf_counter()
        loaded = stored.load(spec) if stored else None
        if loaded is None:
            representation = methods[spec.method].build(spec, corpus, config.vector_config())
        else:
            representation = loaded
            reused.append(spec.name)
        source = features(representation)
        seconds[f"{spec.name}/representacao"] = round(time.perf_counter() - started, 3)
        representations[spec.name] = {
            **asdict(spec),
            "family": representation.family,
            "dimensions": representation.dimensions,
            "parameters": representation.parameters(),
            "interpretable_terms": source.lexical,
            "vectors": "lidos da Etapa 2" if loaded is not None else "calculados nesta execução",
        }
        for task in tasks:
            started = time.perf_counter()
            validation = cross_validate(task, source, LOGISTIC, folds[task.name], config)
            seconds[f"{spec.name}/{task.name}"] = round(time.perf_counter() - started, 3)
            results[task.name][spec.name] = metrics(task, validation)
            rows = prediction_rows(task, validation.probabilities, titles, assignment[task.name])
            filename = f"{spec.name}.{task.name}.predictions.jsonl"
            files[filename], row_files[filename] = jsonl_text(rows), task.name
            if task is multiclass:
                errors[spec.name] = confident_errors(rows, config.error_examples)
        if source.lexical:
            terms[spec.name] = top_terms(multiclass, source, config)
        started = time.perf_counter()
        clusters[spec.name] = cluster(multiclass, representation, descriptor, corpus, config.random_state, config.top_features)
        seconds[f"{spec.name}/kmeans"] = round(time.perf_counter() - started, 3)
        alternatives[spec.name], spent = compare(multiclass, source, folds[multiclass.name], config)
        seconds |= {f"{spec.name}/{name}": value for name, value in spent.items()}

    documents = []
    positions = {task.name: {movie_id: position for position, movie_id in enumerate(task.ids)} for task in tasks}
    for document in corpus.documents:
        genres = sorted(document.tmdb_genres & set(config.labels))
        documents.append(
            {
                "id": document.id,
                "title": document.title,
                "genres": [corpus.genre_names[genre] for genre in genres],
                **{f"fold_{task.name}": _fold(assignment[task.name], positions[task.name].get(document.id)) for task in tasks},
            }
        )
    files |= {
        "config.json": json_text(asdict(config)),
        "documents.json": json_text(documents),
        "representations.json": json_text(representations),
        "results.json": json_text(results),
        "top_terms.json": json_text(terms),
        "errors.json": json_text(errors),
        "clustering.json": json_text(clusters),
        "alternatives.json": json_text(alternatives),
    }
    files["report.md"] = make_report(tasks, config, Findings(results, representations, terms, errors, clusters, alternatives))

    create_output(output)
    for filename, content in files.items():
        write_text(output / filename, content)
    write_json(
        output / MANIFEST_NAME,
        {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "source_processed_manifest_sha256": corpus.manifest_sha256,
            "source_vectors_manifest_sha256": stored.manifest_sha256 if stored else None,
            "reused_representations": reused,
            "config_sha256": sha256(config_path),
            "source_identity": source_identity(),
            "python": platform.python_version(),
            "libraries": library_versions(),
            "tasks": {task.name: len(task.ids) for task in tasks},
            "row_files": row_files,
            "seconds": seconds,
            "files": hash_files(output),
        },
    )
    verify(output)
    return {"tasks": {task.name: len(task.ids) for task in tasks}, "representations": list(representations), "output": str(output)}


def verify(output: Path) -> dict:
    """Confere hashes do manifesto e se cada arquivo de previsões cobre exatamente as sinopses da sua tarefa."""
    manifest = read_manifest(output)
    verify_hashes(output, manifest["files"])
    documents = read_json_array(output / "documents.json")
    for filename, task in manifest["row_files"].items():
        require_plain_filename(filename)
        if filename not in manifest["files"] or task not in manifest["tasks"]:
            raise ValueError(f"Arquivo de previsões fora da lista verificada: {filename!r}")
        expected = [document["id"] for document in documents if document[f"fold_{task}"] is not None]
        if sorted(row["id"] for row in read_jsonl(output / filename)) != sorted(expected):
            raise ValueError(f"Previsões desalinhadas das sinopses da tarefa: {filename}")
    return {
        "status": "ok",
        "tasks": manifest["tasks"],
        "prediction_files": len(manifest["row_files"]),
        "files_verified": len(manifest["files"]),
    }


def _fold(assignment: list[int], position: int | None) -> int | None:
    return None if position is None else assignment[position]
