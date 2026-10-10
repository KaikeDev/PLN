"""Orquestra o experimento de sentimentos: críticas preparadas → tarefas → representações → validação → evidências.

Segue as regras das outras etapas (ADR 0009): tudo é calculado em memória antes de criar a pasta de saída,
que nunca é sobrescrita, e o manifesto guarda hashes, versões e tempos.

- **Polaridade:** críticas com nota ≤ `negative_max` são negativas, e com nota ≥ `positive_min`, positivas.
  A mesma regressão logística da classificação de gêneros, com classes de peso balanceado.
- **Nota:** todas as críticas, com regressão Ridge.
- Nas duas, críticas de um mesmo filme ficam na mesma dobra; à parte, um teste entre autores (`across_authors`).
"""

import platform
import time
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from app.classification.dataset import Task
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
    top_terms,
)
from app.corpus.verification import verify_processed
from app.representations.corpus import ProcessedCorpus
from app.representations.methods import Method
from app.representations.pipeline import library_versions
from app.sentiment.collect import verify_collection
from app.sentiment.config import LABEL_NAMES, NEGATIVE, POSITIVE, SentimentConfig, load_config
from app.sentiment.encoders import ChunkedEncoder, long_text_methods
from app.sentiment.evaluation import across_authors, grouped_folds, mean_baseline, predict_ratings, rating_metrics, subset_accuracy
from app.sentiment.report import make_report
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
from app.shared.language import NEGATION_MARKERS
from app.shared.manifest import MANIFEST_NAME, hash_files, read_manifest, require_plain_filename, verify_hashes

POLARITY = "polaridade"
RATING = "nota"
MEAN_BASELINE = "media_do_treino"
EXCERPT_CHARS = 400


def build(processed: Path, output: Path, config_path: Path, methods: Mapping[str, Method] | None = None) -> dict:
    """Avalia polaridade e nota para cada representação, numa pasta nova, e verifica o resultado."""
    if output.exists():
        raise FileExistsError(f"A pasta de saída já existe: {output}")
    methods = methods if methods is not None else long_text_methods()
    config = load_config(config_path, methods)
    common = config.classification
    corpus = ProcessedCorpus.load(processed)
    metadata = {row["id"]: row for row in read_jsonl(processed / "metadata.jsonl")}
    reviews = [metadata[movie_id] for movie_id in corpus.ids]
    ratings = np.array([review["rating"] for review in reviews], dtype=np.float64)
    groups = [str(review["movie_id"]) for review in reviews]
    authors = Counter(review["author_key"] for review in reviews)
    main_author = authors.most_common(1)[0][0]
    task = _polarity_task(corpus, ratings, config)
    folds = grouped_folds(task.targets, [groups[row] for row in task.rows], common.folds, common.random_state)
    assignment = fold_of(task, folds)
    position_of = {review_id: position for position, review_id in enumerate(task.ids)}
    rating_rows = np.arange(len(reviews))
    rating_folds = grouped_folds(np.rint(ratings).astype(np.int64), groups, common.folds, common.random_state)
    rating_assignment = np.empty(len(reviews), dtype=np.int64)
    for number, (_, test) in enumerate(rating_folds):
        rating_assignment[test] = number
    titles = {review["id"]: review["title"] for review in reviews}
    texts = corpus.texts("02_clean.jsonl")
    words = corpus.tokens("05_without_punctuation.jsonl")
    negated = np.array([any(word in NEGATION_MARKERS for word in words[row]) for row in task.rows])
    by_main_author = np.array([reviews[row]["author_key"] == main_author for row in task.rows])

    results: dict[str, dict[str, dict]] = {POLARITY: {}, RATING: {}}
    results[POLARITY][BASELINE] = metrics(task, cross_validate(task, constant_features(len(reviews)), BASELINE, folds, common))
    results[RATING][MEAN_BASELINE] = rating_metrics(ratings, mean_baseline(ratings, rating_folds), rating_folds)
    files: dict[str, str] = {}
    row_files: dict[str, str] = {}
    representations: dict[str, dict] = {}
    terms: dict[str, dict] = {}
    errors: dict[str, list] = {}
    seconds: dict[str, float] = {}
    for spec in common.representations:
        started = time.perf_counter()
        representation = methods[spec.method].build(spec, corpus, common.vector_config())
        source = features(representation)
        seconds[f"{spec.name}/representacao"] = round(time.perf_counter() - started, 3)
        encoder = getattr(representation, "encoder", None)
        chunks = encoder.chunks_per_text if isinstance(encoder, ChunkedEncoder) else []
        representations[spec.name] = {
            **asdict(spec),
            "family": representation.family,
            "dimensions": representation.dimensions,
            "parameters": representation.parameters(),
            "interpretable_terms": source.lexical,
            "chunks_per_review": {"mean": round(float(np.mean(chunks)), 3), "max": max(chunks)} if chunks else None,
        }

        started = time.perf_counter()
        validation = cross_validate(task, source, LOGISTIC, folds, common)
        seconds[f"{spec.name}/{POLARITY}"] = round(time.perf_counter() - started, 3)
        rows = prediction_rows(task, validation.probabilities, titles, assignment)
        for row, position in zip(rows, task.rows, strict=True):
            row |= {"review_id": reviews[position]["review_id"], "nota": reviews[position]["rating"]}
        correct = np.array([row["acertou"] for row in rows])
        results[POLARITY][spec.name] = metrics(task, validation) | {
            "negacao": subset_accuracy(correct, negated),
            "entre_autores": across_authors(task, source, by_main_author, common),
        }
        errors[spec.name] = [
            row | {"trecho": _excerpt(texts[task.rows[position_of[row["id"]]]])} for row in confident_errors(rows, common.error_examples)
        ]
        filename = f"{spec.name}.{POLARITY}.predictions.jsonl"
        files[filename], row_files[filename] = jsonl_text(rows), POLARITY
        if source.lexical:
            terms[spec.name] = top_terms(task, source, common)

        started = time.perf_counter()
        predicted, alphas = predict_ratings(source, rating_rows, ratings, rating_folds, config.ridge_alphas)
        seconds[f"{spec.name}/{RATING}"] = round(time.perf_counter() - started, 3)
        results[RATING][spec.name] = rating_metrics(ratings, predicted, rating_folds, alphas)
        filename = f"{spec.name}.{RATING}.predictions.jsonl"
        files[filename] = jsonl_text(
            [
                {
                    "id": review["id"],
                    "review_id": review["review_id"],
                    "title": review["title"],
                    "dobra": int(rating_assignment[row]),
                    "nota": review["rating"],
                    "prevista": round(float(predicted[row]), 4),
                }
                for row, review in enumerate(reviews)
            ]
        )
        row_files[filename] = RATING

    documents = [
        {
            "id": review["id"],
            "review_id": review["review_id"],
            "movie_id": review["movie_id"],
            "title": review["title"],
            "nota": review["rating"],
            "polaridade": LABEL_NAMES[task.targets[position_of[review["id"]]]] if review["id"] in position_of else None,
            f"fold_{POLARITY}": assignment[position_of[review["id"]]] if review["id"] in position_of else None,
            f"fold_{RATING}": int(rating_assignment[row]),
        }
        for row, review in enumerate(reviews)
    ]
    dataset = {
        "reviews": len(reviews),
        "movies": len({review["movie_id"] for review in reviews}),
        "authors": len(authors),
        "main_author_share": round(authors[main_author] / len(reviews), 4),
        "polarity": {name: int((task.targets == value).sum()) for value, name in ((NEGATIVE, LABEL_NAMES[0]), (POSITIVE, LABEL_NAMES[1]))},
        "middle_excluded_from_polarity": len(reviews) - len(task.ids),
        "with_negation": int(negated.sum()),
    }
    files |= {
        "config.json": json_text(asdict(config)),
        "documents.json": json_text(documents),
        "dataset.json": json_text(dataset),
        "representations.json": json_text(representations),
        "results.json": json_text(results),
        "top_terms.json": json_text(terms),
        "errors.json": json_text(errors),
    }
    files["report.md"] = make_report(dataset, config, results, representations, terms, errors)

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
            "source_identity": source_identity(),
            "python": platform.python_version(),
            "libraries": library_versions(),
            "tasks": {POLARITY: len(task.ids), RATING: len(reviews)},
            "row_files": row_files,
            "seconds": seconds,
            "files": hash_files(output),
        },
    )
    verify(output)
    return {"reviews": len(reviews), "polarity": dataset["polarity"], "representations": list(representations), "output": str(output)}


def verify(output: Path) -> dict:
    """Confere os hashes do manifesto e se cada arquivo de previsões cobre exatamente as críticas da sua tarefa."""
    manifest = read_manifest(output)
    verify_hashes(output, manifest["files"])
    documents = read_json_array(output / "documents.json")
    for filename, task in manifest["row_files"].items():
        require_plain_filename(filename)
        if filename not in manifest["files"] or task not in manifest["tasks"]:
            raise ValueError(f"Arquivo de previsões fora da lista verificada: {filename!r}")
        expected = [document["id"] for document in documents if document[f"fold_{task}"] is not None]
        if sorted(row["id"] for row in read_jsonl(output / filename)) != sorted(expected):
            raise ValueError(f"Previsões desalinhadas das críticas da tarefa: {filename}")
    return {
        "status": "ok",
        "tasks": manifest["tasks"],
        "prediction_files": len(manifest["row_files"]),
        "files_verified": len(manifest["files"]),
    }


def verify_any(folder: Path) -> dict:
    """Verifica uma pasta de coleta de críticas, de críticas preparadas ou de experimento, conforme o conteúdo."""
    if (folder / "reviews.jsonl").exists():
        return verify_collection(folder)
    if "stages" in read_manifest(folder):
        return verify_processed(folder)
    return verify(folder)


def _polarity_task(corpus: ProcessedCorpus, ratings: np.ndarray, config: SentimentConfig) -> Task:
    labels = [config.polarity(float(rating)) for rating in ratings]
    rows = np.array([row for row, label in enumerate(labels) if label is not None], dtype=np.int64)
    targets = np.array([labels[row] for row in rows], dtype=np.int64)
    if (counts := np.bincount(targets, minlength=2)).min() < config.classification.folds:
        raise ValueError(f"Críticas negativas e positivas insuficientes para {config.classification.folds} dobras: {counts.tolist()}")
    return Task(POLARITY, (NEGATIVE, POSITIVE), LABEL_NAMES, rows, tuple(corpus.ids[row] for row in rows), targets)


def _excerpt(text: str) -> str:
    return text if len(text) <= EXCERPT_CHARS else text[:EXCERPT_CHARS].rsplit(" ", 1)[0] + "…"
