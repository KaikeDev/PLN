"""Coleta uma amostra intencional do TMDB e conserva respostas, proveniência e falhas.

Cada resposta bem-sucedida é salva como JSON com o seu hash. Uma falha interrompe somente o recorte
em que ocorreu. O manifesto é regravado a cada requisição, então uma interrupção preserva o que já
foi recebido. Erros registram apenas o tipo e o status HTTP: nunca URL, cabeçalhos ou a mensagem da
exceção, que poderiam conter a credencial.
"""

import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.corpus.config import CollectionConfig, load_collection_config
from app.shared.artifacts import create_output, sha256, source_identity, write_json, write_jsonl

Fetch = Callable[..., dict]
SAMPLING_DESCRIPTION = "amostra intencional por gênero e período; ordenação por popularidade"
ARTIFACTS = ("config.json", "movies.jsonl", "genres.json", "memberships.json")


def utc_now() -> str:
    """Instante atual em UTC no formato ISO 8601."""
    return datetime.now(UTC).isoformat()


def collect(config_path: Path, output: Path, fetch: Fetch | None = None) -> dict:
    """Executa a coleta descrita em `config_path` numa pasta nova e devolve o manifesto final."""
    config, raw_config = load_collection_config(config_path)
    collector = Collector(config, output, fetch or _tmdb_fetch())
    return collector.run(raw_config, sha256(config_path))


def _tmdb_fetch() -> Fetch:
    from app.infra.tmdb.client import TMDBClient
    from app.settings import get_settings

    return TMDBClient.from_settings(get_settings()).get


class Collector:
    """Percorre os recortes gênero × período, deduplica filmes por ID e mantém o manifesto atualizado."""

    def __init__(self, config: CollectionConfig, output: Path, fetch: Fetch, sleep: Callable[[float], None] = time.sleep):
        self.config = config
        self.output = output
        self.fetch = fetch
        self.sleep = sleep
        self.movies: dict[int, dict] = {}
        self.memberships: dict[int, list[str]] = {}
        self.received = 0
        self.manifest: dict = {}

    def run(self, raw_config: dict, config_sha256: str) -> dict:
        """Cria a pasta de saída, coleta todos os recortes e os filmes semente e grava os artefatos."""
        create_output(self.output)
        (self.output / "responses").mkdir()
        write_json(self.output / "config.json", raw_config)
        self.manifest = {
            "schema_version": 1,
            "source": "TMDB",
            "started_at": utc_now(),
            "status": "running",
            "sampling": SAMPLING_DESCRIPTION,
            "config_sha256": config_sha256,
            "source_identity": source_identity(),
            "requests": [],
            "errors": [],
            "stopped_slices": [],
        }
        try:
            self._collect_genres()
            for genre in self.config.genres:
                for start, end in self.config.periods:
                    self._collect_slice(genre, start, end)
            self._collect_seeds()
            self.manifest["status"] = "partial" if self.manifest["errors"] else "complete"
        except BaseException:
            self.manifest["status"] = "interrupted"
            raise
        finally:
            self._finish()
        return self.manifest

    def _collect_genres(self) -> None:
        genres = self._request("/genre/movie/list", {"language": self.config.language}, "genre_map")
        write_json(self.output / "genres.json", genres or {"genres": []})

    def _collect_slice(self, genre: int, start: int, end: int) -> None:
        label = f"genre_{genre}_{start}_{end}"
        for page in range(1, self.config.pages_per_slice + 1):
            params = {
                "language": self.config.language,
                "with_genres": str(genre),
                "primary_release_date.gte": f"{start}-01-01",
                "primary_release_date.lte": f"{end}-12-31",
                "vote_count.gte": self.config.vote_count_gte,
                "sort_by": self.config.sort_by,
                "include_adult": str(self.config.include_adult).lower(),
                "page": page,
            }
            data = self._request("/discover/movie", params, label)
            if data is None:
                return
            if not isinstance(data.get("results"), list) or not isinstance(data.get("total_pages"), int):
                raise ValueError("Resposta de descoberta sem results/total_pages válidos")
            for movie in data["results"]:
                self._add_movie(movie, label)
            if page >= data["total_pages"] or not data["results"]:
                self.manifest["stopped_slices"].append({"slice": label, "last_page": page, "reason": "source_exhausted"})
                return

    def _collect_seeds(self) -> None:
        for movie_id in self.config.seed_movie_ids:
            label = f"seed_{movie_id}"
            data = self._request(f"/movie/{movie_id}", {"language": self.config.language}, label)
            if data is not None:
                self._add_movie(data, label)

    def _request(self, endpoint: str, params: dict, label: str) -> dict | None:
        """Chama a fonte, salva a resposta e registra o resultado; devolve None em caso de falha."""
        self.sleep(self.config.request_interval_seconds)
        index = len(self.manifest["requests"]) + 1
        entry: dict[str, Any] = {"endpoint": endpoint, "params": params, "slice": label, "collected_at": utc_now()}
        try:
            data = self.fetch(endpoint, **params)
            filename = f"responses/{index:03d}.json"
            write_json(self.output / filename, data)
            entry.update(status="ok", file=filename, sha256=sha256(self.output / filename))
            self.manifest["requests"].append(entry)
            return data
        except Exception as exc:
            entry.update(status="error", error_type=type(exc).__name__, http_status=getattr(exc, "status", None))
            self.manifest["requests"].append(entry)
            self.manifest["errors"].append(entry)
            return None
        finally:
            write_json(self.output / "manifest.json", self.manifest)

    def _add_movie(self, movie: dict, label: str) -> None:
        if type(movie.get("id")) is not int:
            raise ValueError("Resposta de filme sem id inteiro")
        self.received += 1
        movie_id = movie["id"]
        self.movies.setdefault(movie_id, movie)
        labels = self.memberships.setdefault(movie_id, [])
        if label not in labels:
            labels.append(label)

    def _finish(self) -> None:
        write_jsonl(self.output / "movies.jsonl", [self.movies[key] for key in sorted(self.movies)])
        write_json(self.output / "memberships.json", {str(k): v for k, v in sorted(self.memberships.items())})
        self.manifest.update(
            finished_at=utc_now(),
            records_received=self.received,
            unique_movies=len(self.movies),
            duplicates_removed=self.received - len(self.movies),
            movies_sha256=sha256(self.output / "movies.jsonl"),
        )
        self.manifest["artifact_sha256"] = {name: sha256(self.output / name) for name in ARTIFACTS if (self.output / name).exists()}
        write_json(self.output / "manifest.json", self.manifest)
