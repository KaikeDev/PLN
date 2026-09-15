"""Processamento offline da amostra bruta: representações, metadados, estatísticas e evidências.

A amostra bruta é verificada pelos hashes antes do uso. Todas as etapas mantêm todos os IDs, na mesma
ordem, inclusive filmes sem sinopse. A pasta de saída é nova e termina com um manifesto verificado.
"""

import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.corpus.contracts import STAGES, Representations, stage_field
from app.corpus.report import render_report
from app.corpus.statistics import compute_statistics
from app.corpus.transform import PRESERVED_NEGATIONS, TOKEN_PATTERN, representations
from app.corpus.verification import verify_processed, verify_raw
from app.shared.artifacts import create_output, read_json_object, read_jsonl, sha256, source_identity, write_json, write_jsonl, write_text
from app.shared.manifest import hash_files

EXAMPLES_BEYOND_SEEDS = 2
NORMALIZATION_DESCRIPTION = "NFC na limpeza; casefold na representação normalizada; acentos preservados"


@dataclass(frozen=True)
class TransformedCorpus:
    """Resultado das transformações: linhas de cada etapa, metadados e representações por ID."""

    stage_rows: dict[str, list[dict]]
    metadata: list[dict]
    by_id: dict[int, Representations]


def load_stopwords(path: Path) -> set[str]:
    """Stopwords normalizadas por `casefold`, ignorando comentários e sem os marcadores de negação."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return {line.strip().casefold() for line in lines if line.strip() and not line.lstrip().startswith("#")} - PRESERVED_NEGATIONS


def load_movies(raw: Path) -> list[dict]:
    """Filmes da amostra bruta; exige ao menos um filme e IDs inteiros únicos."""
    movies = read_jsonl(raw / "movies.jsonl")
    if not movies:
        raise ValueError("A amostra não contém filmes; execute a coleta antes do processamento")
    ids = [movie["id"] for movie in movies]
    if len(set(ids)) != len(ids) or any(type(movie_id) is not int for movie_id in ids):
        raise ValueError("IDs devem ser inteiros únicos")
    return movies


def transform_movies(movies: list[dict], stopwords: set[str]) -> TransformedCorpus:
    """Gera as seis representações e os metadados de cada filme, preservando a ordem de entrada."""
    stage_rows: dict[str, list[dict]] = {filename: [] for filename in STAGES}
    metadata, by_id = [], {}
    for movie in movies:
        overview = movie.get("overview")
        stages = representations(overview, stopwords)
        by_id[movie["id"]] = stages
        values = {"original": overview, **stages}
        for filename, key in STAGES.items():
            stage_rows[filename].append({"id": movie["id"], stage_field(key): values[key]})
        metadata.append(_metadata(movie, overview))
    return TransformedCorpus(stage_rows, metadata, by_id)


def select_examples(corpus: TransformedCorpus, seed_ids: list[int]) -> list[dict]:
    """Filmes semente presentes na amostra seguidos dos primeiros demais filmes, com todas as representações."""
    ids = [row["id"] for row in corpus.metadata]
    seeds = [movie_id for movie_id in seed_ids if movie_id in corpus.by_id]
    chosen = seeds + [movie_id for movie_id in ids if movie_id not in seeds][:EXAMPLES_BEYOND_SEEDS]
    titles = {row["id"]: row["title"] for row in corpus.metadata}
    return [
        {"id": movie_id, "title": titles[movie_id], "original": _original(corpus, movie_id), **corpus.by_id[movie_id]}
        for movie_id in chosen
    ]


def process(raw: Path, output: Path, stopwords_path: Path) -> dict:
    """Processa a amostra bruta `raw` numa pasta nova `output` e devolve um resumo da execução."""
    collection = verify_raw(raw)
    movies = load_movies(raw)
    stopwords = load_stopwords(stopwords_path)
    corpus = transform_movies(movies, stopwords)
    memberships = read_json_object(raw / "memberships.json")
    genres = read_json_object(raw / "genres.json")
    seed_ids = read_json_object(raw / "config.json").get("seed_movie_ids", [])

    create_output(output)
    for filename, rows in corpus.stage_rows.items():
        write_jsonl(output / filename, rows)
    write_jsonl(output / "metadata.jsonl", corpus.metadata)
    write_json(output / "stopwords_used.json", sorted(stopwords))
    write_json(output / "memberships.json", memberships)
    write_json(output / "genres.json", genres)
    stats = compute_statistics(movies, corpus.metadata, corpus.by_id, memberships)
    write_json(output / "statistics.json", stats)
    examples = select_examples(corpus, seed_ids)
    write_json(output / "examples.json", examples)
    write_text(output / "report.md", render_report(stats, collection, examples))
    write_json(output / "manifest.json", _manifest(raw, output, stopwords_path, collection))
    verify_processed(output)
    valid = stats["valid_overviews"]
    return {"movies": len(movies), "valid_overviews": valid, "missing_overviews": len(movies) - valid, "output": str(output)}


def _metadata(movie: dict, overview: str | None) -> dict:
    return {
        "id": movie["id"],
        "title": movie.get("title"),
        "original_title": movie.get("original_title"),
        "original_language": movie.get("original_language"),
        "release_date": movie.get("release_date"),
        "genre_ids": movie.get("genre_ids", [genre["id"] for genre in movie.get("genres", [])]),
        "vote_average": movie.get("vote_average"),
        "vote_count": movie.get("vote_count"),
        "overview_missing": overview is None or not overview.strip(),
    }


def _original(corpus: TransformedCorpus, movie_id: int) -> str | None:
    rows = corpus.stage_rows["01_original.jsonl"]
    return next(row["text"] for row in rows if row["id"] == movie_id)


def _manifest(raw: Path, output: Path, stopwords_path: Path, collection: dict) -> dict:
    return {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "collection_status": collection["status"],
        "source_movies_sha256": sha256(raw / "movies.jsonl"),
        "collection_manifest_sha256": sha256(raw / "manifest.json"),
        "source_identity": source_identity(),
        "python": platform.python_version(),
        "normalization": NORMALIZATION_DESCRIPTION,
        "token_pattern": TOKEN_PATTERN,
        "preserved_negations": sorted(PRESERVED_NEGATIONS),
        "stopwords_source_sha256": sha256(stopwords_path),
        "stages": STAGES,
        "files": hash_files(output),
    }
