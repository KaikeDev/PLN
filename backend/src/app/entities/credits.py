"""Coleta dos créditos dos filmes de uma pasta processada, usados como referência parcial do NER (ADR 0027).

Para cada filme, `GET /movie/{id}/credits` e os primeiros `max_cast` nomes do elenco: o nome do ator e o do
personagem. Só esses dois campos são guardados. Erros registram apenas o tipo e o status HTTP.
"""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from app.corpus.verification import verify_processed
from app.shared.artifacts import create_output, read_jsonl, sha256, source_identity, write_json, write_jsonl
from app.shared.manifest import read_manifest, verify_hashes

Fetch = Callable[..., dict]
WORKERS = 4


def collect_credits(
    movies_folder: Path,
    output: Path,
    max_cast: int = 15,
    fetch: Fetch | None = None,
    interval: float = 0.05,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Coleta o elenco de cada filme de `movies_folder` numa pasta nova."""
    if output.exists():
        raise FileExistsError(f"A pasta de saída já existe: {output}")
    verify_processed(movies_folder)
    movies = read_jsonl(movies_folder / "metadata.jsonl")
    fetch = fetch or _tmdb_fetch()
    started = time.perf_counter()

    def one(movie: dict) -> tuple[dict, dict | None]:
        sleep(interval)
        try:
            data = fetch(f"/movie/{movie['id']}/credits")
        except Exception as exc:
            return {"movie_id": movie["id"], "cast": []}, {
                "movie_id": movie["id"],
                "error_type": type(exc).__name__,
                "http_status": getattr(exc, "status", None),
            }
        cast = sorted(data.get("cast") or [], key=lambda person: person.get("order", 0))[:max_cast]
        return {"movie_id": movie["id"], "cast": [{"name": p.get("name"), "character": p.get("character")} for p in cast]}, None

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        outcomes = list(pool.map(one, movies))
    rows = [row for row, _ in outcomes]
    errors = [error for _, error in outcomes if error]

    create_output(output)
    write_jsonl(output / "credits.jsonl", rows)
    write_json(
        output / "manifest.json",
        {
            "schema_version": 1,
            "source": "TMDB /movie/{id}/credits",
            "finished_at": datetime.now(UTC).isoformat(),
            "seconds": round(time.perf_counter() - started, 3),
            "status": "partial" if errors else "complete",
            "source_movies_manifest_sha256": sha256(movies_folder / "manifest.json"),
            "source_movies_folder": movies_folder.name,
            "max_cast": max_cast,
            "movies": len(rows),
            "errors": errors,
            "source_identity": source_identity(),
            "files": {"credits.jsonl": sha256(output / "credits.jsonl")},
        },
    )
    verify_credits(output)
    return {"status": "partial" if errors else "complete", "movies": len(rows), "errors": len(errors)}


def verify_credits(folder: Path) -> dict:
    """Confere o hash da coleta de créditos."""
    manifest = read_manifest(folder)
    verify_hashes(folder, manifest["files"])
    return {"status": "ok", "movies": manifest["movies"], "files_verified": len(manifest["files"])}


def _tmdb_fetch() -> Fetch:
    from app.settings import get_settings
    from app.tmdb.client import TMDBClient

    return TMDBClient.from_settings(get_settings()).get
