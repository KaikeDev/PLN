"""Configuração validada da coleta. O arquivo é dado: nenhum campo é interpolado sem validação."""

import re
from dataclasses import dataclass
from pathlib import Path

from app.shared.language import MAX_RELEASE_YEAR, MIN_RELEASE_YEAR
from app.shared.validation import (
    read_config_json,
    require_bool,
    require_ids,
    require_int,
    require_number,
    require_object,
)

LANGUAGE_RE = re.compile(r"[a-z]{2}-[A-Z]{2}")
SORT_RE = re.compile(r"[a-z_]{1,40}\.(asc|desc)")
MAX_PAGES_PER_SLICE = 500
MAX_REQUEST_INTERVAL_SECONDS = 60
DEFAULT_REQUEST_INTERVAL_SECONDS = 0.3
REQUIRED_FIELDS = frozenset({"language", "pages_per_slice", "genres", "periods", "vote_count_gte", "sort_by", "include_adult"})
OPTIONAL_FIELDS = frozenset({"seed_movie_ids", "request_interval_seconds"})


@dataclass(frozen=True)
class CollectionConfig:
    """Parâmetros de uma coleta intencional: recortes gênero × período, páginas e filmes semente."""

    language: str
    pages_per_slice: int
    genres: tuple[int, ...]
    periods: tuple[tuple[int, int], ...]
    vote_count_gte: int
    sort_by: str
    include_adult: bool
    seed_movie_ids: tuple[int, ...]
    request_interval_seconds: float


def parse_collection_config(data: object) -> CollectionConfig:
    """Valida o objeto de configuração da coleta e devolve a versão tipada."""
    data = require_object(data, "configuração da coleta", REQUIRED_FIELDS, OPTIONAL_FIELDS)
    if not isinstance(data["language"], str) or not LANGUAGE_RE.fullmatch(data["language"]):
        raise ValueError("language deve seguir o formato xx-XX, por exemplo pt-BR")
    if not isinstance(data["sort_by"], str) or not SORT_RE.fullmatch(data["sort_by"]):
        raise ValueError("sort_by deve seguir o formato campo.asc ou campo.desc")
    return CollectionConfig(
        language=data["language"],
        pages_per_slice=require_int(data["pages_per_slice"], "pages_per_slice", 1, MAX_PAGES_PER_SLICE),
        genres=require_ids(data["genres"], "genres"),
        periods=_periods(data["periods"]),
        vote_count_gte=require_int(data["vote_count_gte"], "vote_count_gte", 0, 10_000_000),
        sort_by=data["sort_by"],
        include_adult=require_bool(data["include_adult"], "include_adult"),
        seed_movie_ids=require_ids(data.get("seed_movie_ids", []), "seed_movie_ids", allow_empty=True),
        request_interval_seconds=require_number(
            data.get("request_interval_seconds", DEFAULT_REQUEST_INTERVAL_SECONDS),
            "request_interval_seconds",
            0,
            MAX_REQUEST_INTERVAL_SECONDS,
        ),
    )


def load_collection_config(path: Path) -> tuple[CollectionConfig, dict]:
    """Lê e valida o arquivo; devolve também o objeto original, copiado sem alteração para a pasta bruta."""
    raw = require_object(read_config_json(path), "configuração da coleta", REQUIRED_FIELDS, OPTIONAL_FIELDS)
    return parse_collection_config(raw), raw


def _periods(value: object) -> tuple[tuple[int, int], ...]:
    message = f"periods deve listar pares [início, fim] com {MIN_RELEASE_YEAR} ≤ início ≤ fim ≤ {MAX_RELEASE_YEAR}"
    if not isinstance(value, list) or not value:
        raise ValueError(message)
    periods = []
    for item in value:
        if not isinstance(item, list) or len(item) != 2 or any(type(year) is not int for year in item):
            raise ValueError(message)
        start, end = item
        if not MIN_RELEASE_YEAR <= start <= end <= MAX_RELEASE_YEAR:
            raise ValueError(message)
        periods.append((start, end))
    return tuple(periods)
