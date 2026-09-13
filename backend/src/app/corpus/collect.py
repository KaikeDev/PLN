"""Coleta amostra intencional do TMDB e conserva respostas e proveniência."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.corpus.io import create_output, sha256, source_identity, write_json, write_jsonl


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_config(config: dict) -> None:
    if not 1 <= config["pages_per_slice"] <= 500:
        raise ValueError("pages_per_slice deve estar entre 1 e 500")
    if not config["genres"] or not config["periods"]:
        raise ValueError("Informe gêneros e períodos")
    for start, end in config["periods"]:
        if not 1874 <= start <= end <= 9998:
            raise ValueError("Período inválido")
    if config.get("request_interval_seconds", 0.3) < 0:
        raise ValueError("Intervalo negativo")


def collect(config_path: Path, output: Path, fetch=None) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    if fetch is None:
        from app.core import config as credentials
        from app.services.tmdb.client import get
        if not (credentials.TMDB_BEARER_TOKEN or credentials.TMDB_API_KEY):
            raise ValueError("Configure TMDB_BEARER_TOKEN ou TMDB_API_KEY no ambiente ou .env local")
        fetch = get
    create_output(output)
    (output / "responses").mkdir()
    write_json(output / "config.json", config)
    manifest = {
        "schema_version": 1, "source": "TMDB", "started_at": utc_now(),
        "status": "running", "sampling": "amostra intencional por gênero e período; ordenação por popularidade",
        "config_sha256": sha256(config_path), "source_identity": source_identity(),
        "requests": [], "errors": [], "stopped_slices": [],
    }
    movies, memberships = {}, {}
    received = 0
    interval = config.get("request_interval_seconds", 0.3)

    def request(endpoint: str, params: dict, label: str):
        time.sleep(interval)
        index = len(manifest["requests"]) + 1
        entry = {"endpoint": endpoint, "params": params, "slice": label, "collected_at": utc_now()}
        try:
            data = fetch(endpoint, **params)
            filename = f"responses/{index:03d}.json"
            write_json(output / filename, data)
            entry.update(status="ok", file=filename, sha256=sha256(output / filename))
            manifest["requests"].append(entry)
            return data
        except Exception as exc:
            # Não registrar URL, cabeçalhos ou mensagem de exceção que possa conter credencial.
            entry.update(status="error", error_type=type(exc).__name__, http_status=getattr(exc, "status", None))
            manifest["requests"].append(entry)
            manifest["errors"].append(entry)
            return None
        finally:
            write_json(output / "manifest.json", manifest)

    def add_movie(movie: dict, label: str) -> None:
        nonlocal received
        if type(movie.get("id")) is not int:
            raise ValueError("Resposta de filme sem id inteiro")
        received += 1
        movie_id = movie["id"]
        movies.setdefault(movie_id, movie)
        labels = memberships.setdefault(movie_id, [])
        if label not in labels:
            labels.append(label)

    try:
        genres = request("/genre/movie/list", {"language": config["language"]}, "genre_map")
        write_json(output / "genres.json", genres or {"genres": []})
        for genre in config["genres"]:
            for start, end in config["periods"]:
                label = f"genre_{genre}_{start}_{end}"
                for page in range(1, config["pages_per_slice"] + 1):
                    params = {
                        "language": config["language"], "with_genres": str(genre),
                        "primary_release_date.gte": f"{start}-01-01",
                        "primary_release_date.lte": f"{end}-12-31",
                        "vote_count.gte": config["vote_count_gte"], "sort_by": config["sort_by"],
                        "include_adult": str(config["include_adult"]).lower(), "page": page,
                    }
                    data = request("/discover/movie", params, label)
                    if data is None:
                        break
                    if not isinstance(data.get("results"), list) or not isinstance(data.get("total_pages"), int):
                        raise ValueError("Resposta de descoberta sem results/total_pages válidos")
                    for movie in data["results"]:
                        add_movie(movie, label)
                    if page >= data["total_pages"] or not data["results"]:
                        manifest["stopped_slices"].append({"slice": label, "last_page": page, "reason": "source_exhausted"})
                        break
        for movie_id in config.get("seed_movie_ids", []):
            label = f"seed_{movie_id}"
            data = request(f"/movie/{movie_id}", {"language": config["language"]}, label)
            if data is not None:
                add_movie(data, label)
        manifest["status"] = "partial" if manifest["errors"] else "complete"
    except BaseException:
        manifest["status"] = "interrupted"
        raise
    finally:
        write_jsonl(output / "movies.jsonl", [movies[key] for key in sorted(movies)])
        write_json(output / "memberships.json", {str(k): v for k, v in sorted(memberships.items())})
        manifest.update(
            finished_at=utc_now(), records_received=received, unique_movies=len(movies),
            duplicates_removed=received-len(movies), movies_sha256=sha256(output / "movies.jsonl"),
        )
        manifest["artifact_sha256"] = {name: sha256(output / name) for name in ["config.json", "movies.jsonl", "genres.json", "memberships.json"]}
        write_json(output / "manifest.json", manifest)
    return manifest
