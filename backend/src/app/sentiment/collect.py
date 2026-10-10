"""Coleta das críticas em português dos filmes de uma pasta processada (ADR 0026).

Para cada filme, `GET /movie/{id}/reviews` com o idioma configurado, página a página, até acabar ou até o
limite de páginas. Cada crítica guarda o texto, a nota que o autor deu ao filme (`author_details.rating`,
de 0 a 10, ou null) e as datas. O autor vira um código anônimo (SHA-256 truncado do nome de usuário): ele
serve só para manter as críticas de uma mesma pessoa na mesma dobra, e nome, usuário e avatar não são
gravados. Erros registram apenas o tipo e o status HTTP, como na coleta da Etapa 1.
"""

import hashlib
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.corpus.verification import verify_processed
from app.shared.artifacts import create_output, read_jsonl, sha256, source_identity, write_json, write_jsonl
from app.shared.validation import read_config_json, require_int, require_number, require_object

Fetch = Callable[..., dict]
AUTHOR_KEY_CHARS = 16
LANGUAGES = frozenset({"pt-BR", "pt-PT"})


@dataclass(frozen=True)
class ReviewCollectionConfig:
    """Idioma pedido ao TMDB, limite de páginas por filme, intervalo entre chamadas e chamadas simultâneas."""

    language: str
    max_pages_per_movie: int
    request_interval_seconds: float
    workers: int


def load_collection_config(path: Path) -> ReviewCollectionConfig:
    """Lê e valida a configuração da coleta de críticas."""
    data = require_object(
        read_config_json(path),
        "configuração da coleta de críticas",
        required={"language", "max_pages_per_movie", "request_interval_seconds", "workers"},
        optional={"description"},
    )
    if data["language"] not in LANGUAGES:
        raise ValueError(f"language deve ser um de {sorted(LANGUAGES)}")
    return ReviewCollectionConfig(
        language=data["language"],
        max_pages_per_movie=require_int(data["max_pages_per_movie"], "max_pages_per_movie", 1, 50),
        request_interval_seconds=require_number(data["request_interval_seconds"], "request_interval_seconds", 0, 10),
        workers=require_int(data["workers"], "workers", 1, 8),
    )


def author_key(author: str | None) -> str | None:
    """Código anônimo e estável do autor; None quando o TMDB não informa o usuário."""
    if not author:
        return None
    return hashlib.sha256(author.encode("utf-8")).hexdigest()[:AUTHOR_KEY_CHARS]


def review_row(movie: dict, review: dict) -> dict:
    """Campos guardados de uma crítica; dados pessoais do autor ficam de fora."""
    details = review.get("author_details") or {}
    rating = details.get("rating")
    if not isinstance(review.get("id"), str) or not isinstance(review.get("content"), str):
        raise ValueError("Crítica sem id ou texto")
    return {
        "review_id": review["id"],
        "movie_id": movie["id"],
        "title": movie.get("title") or movie.get("original_title"),
        "rating": float(rating) if isinstance(rating, int | float) and not isinstance(rating, bool) else None,
        "author_key": author_key(details.get("username") or review.get("author")),
        "created_at": review.get("created_at"),
        "updated_at": review.get("updated_at"),
        "content": review["content"],
    }


def collect(
    movies_folder: Path,
    config_path: Path,
    output: Path,
    fetch: Fetch | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Coleta as críticas de todos os filmes de `movies_folder` (pasta processada da Etapa 1) numa pasta nova."""
    if output.exists():
        raise FileExistsError(f"A pasta de saída já existe: {output}")
    verify_processed(movies_folder)
    config = load_collection_config(config_path)
    movies = read_jsonl(movies_folder / "metadata.jsonl")
    fetch = fetch or _tmdb_fetch()
    started_at = datetime.now(UTC).isoformat()
    started = time.perf_counter()

    def one(movie: dict) -> tuple[list[dict], list[dict], int]:
        rows, errors, calls = [], [], 0
        for page in range(1, config.max_pages_per_movie + 1):
            sleep(config.request_interval_seconds)
            calls += 1
            try:
                data = fetch(f"/movie/{movie['id']}/reviews", language=config.language, page=page)
            except Exception as exc:
                errors.append(
                    {"movie_id": movie["id"], "page": page, "error_type": type(exc).__name__, "http_status": getattr(exc, "status", None)}
                )
                break
            results = data.get("results")
            if not isinstance(results, list):
                errors.append({"movie_id": movie["id"], "page": page, "error_type": "RespostaInvalida", "http_status": None})
                break
            rows += [review_row(movie, review) for review in results]
            if page >= int(data.get("total_pages") or 0):
                break
        return rows, errors, calls

    with ThreadPoolExecutor(max_workers=config.workers) as pool:
        outcomes = list(pool.map(one, movies))
    reviews = sorted((row for rows, _, _ in outcomes for row in rows), key=lambda row: (row["movie_id"], row["review_id"]))
    errors = [error for _, found, _ in outcomes for error in found]
    unique = sorted({row["review_id"]: row for row in reviews}.values(), key=lambda row: (row["movie_id"], row["review_id"]))

    create_output(output)
    write_json(output / "config.json", asdict(config))
    write_jsonl(output / "reviews.jsonl", unique)
    manifest = {
        "schema_version": 1,
        "source": "TMDB /movie/{id}/reviews",
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
        "seconds": round(time.perf_counter() - started, 3),
        "status": "partial" if errors else "complete",
        "config_sha256": sha256(config_path),
        "source_movies_manifest_sha256": sha256(movies_folder / "manifest.json"),
        "source_movies_folder": movies_folder.name,
        "movies": len(movies),
        "requests": sum(calls for _, _, calls in outcomes),
        "movies_with_reviews": len({row["movie_id"] for row in unique}),
        "reviews": len(unique),
        "duplicates_removed": len(reviews) - len(unique),
        "errors": errors,
        "source_identity": source_identity(),
        "files": {name: sha256(output / name) for name in ("config.json", "reviews.jsonl")},
    }
    write_json(output / "manifest.json", manifest)
    verify_collection(output)
    return {key: manifest[key] for key in ("status", "movies", "requests", "movies_with_reviews", "reviews", "seconds")}


def verify_collection(folder: Path) -> dict:
    """Confere os hashes da coleta de críticas."""
    from app.shared.manifest import read_manifest, verify_hashes

    manifest = read_manifest(folder)
    verify_hashes(folder, manifest["files"])
    return {"status": "ok", "reviews": manifest["reviews"], "files_verified": len(manifest["files"])}


def _tmdb_fetch() -> Fetch:
    from app.settings import get_settings
    from app.tmdb.client import TMDBClient

    return TMDBClient.from_settings(get_settings()).get
