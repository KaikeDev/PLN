"""Frases anotadas da interpretação (`config/busca/interpretacao.json`) e os gêneros da amostra.

O conjunto é validado no carregamento: ids únicos, categorias conhecidas, gêneros que existem no catálogo
e datas reais no formato AAAA-MM-DD. O gabarito e as previsões são comparados no mesmo formato
(`Judgement`): nomes de gênero ordenados, os dois limites de data e o booleano de qualidade.
"""

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.search.filters import ExtractedFilters
from app.shared.validation import read_config_json, require_bool, require_name, require_object, require_unique

CATEGORIES = ("explicita", "parafrase", "negacao", "periodo", "armadilha_lexica", "sem_filtro")
JUDGEMENT_FIELDS = ("generos", "generos_excluidos", "lancado_depois", "lancado_antes", "bem_avaliado")
MAX_PHRASES = 500
MAX_TEXT_CHARS = 200

Judgement = dict


@dataclass(frozen=True)
class Phrase:
    """Frase anotada: texto, categoria e filtros esperados."""

    id: str
    text: str
    category: str
    expected: Judgement
    note: str | None = None


@dataclass(frozen=True)
class PhraseSet:
    """Frases anotadas e a data a que os termos relativos ("recente", "deste ano") se referem."""

    reference_date: date
    phrases: tuple[Phrase, ...]


class StaticGenres:
    """`GenreSource` com os gêneros de um `genres.json` da coleta."""

    def __init__(self, genres: Mapping[int, str]) -> None:
        self._genres = dict(genres)

    def genres(self) -> Mapping[int, str]:
        return self._genres


def load_genres(path: Path) -> dict[int, str]:
    """Gêneros de um `genres.json` da coleta do TMDB."""
    data = require_object(read_config_json(path), path.name, required={"genres"})
    items = data["genres"]
    if not isinstance(items, list) or not items:
        raise ValueError(f"{path.name}: genres deve ser uma lista não vazia")
    genres: dict[int, str] = {}
    for item in items:
        genre = require_object(item, f"{path.name}: gênero", required={"id", "name"})
        if type(genre["id"]) is not int or not isinstance(genre["name"], str) or not genre["name"]:
            raise ValueError(f"{path.name}: gênero com id ou nome inválido")
        genres[genre["id"]] = genre["name"]
    return genres


def load_phrases(path: Path, genre_names: Collection[str]) -> PhraseSet:
    """Lê e valida as frases anotadas contra os nomes de gênero do catálogo."""
    data = require_object(
        read_config_json(path), "frases anotadas", required={"data_referencia", "frases"}, optional={"description", "criterios"}
    )
    items = data["frases"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_PHRASES:
        raise ValueError(f"frases deve listar de 1 a {MAX_PHRASES} frases")
    phrases = tuple(_phrase(item, position, set(genre_names)) for position, item in enumerate(items))
    require_unique([phrase.id for phrase in phrases], "Frases com id repetido")
    return PhraseSet(_date(data["data_referencia"], "data_referencia"), phrases)


def judgement(filters: ExtractedFilters, genre_names: Mapping[int, str]) -> Judgement:
    """Filtros no formato do gabarito; os dois níveis de qualidade das regras contam como `bem_avaliado`."""
    return {
        "generos": sorted(genre_names.get(genre, str(genre)) for genre in filters.genres),
        "generos_excluidos": sorted(genre_names.get(genre, str(genre)) for genre in filters.excluded_genres),
        "lancado_depois": filters.released_after,
        "lancado_antes": filters.released_before,
        "bem_avaliado": filters.min_rating is not None,
    }


def _phrase(value: object, position: int, genre_names: set[str]) -> Phrase:
    where = f"frase {position}"
    item = require_object(value, where, required={"id", "texto", "categoria", "esperado"}, optional={"observacao"})
    text = item["texto"]
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"{where}: texto deve ter de 1 a {MAX_TEXT_CHARS} caracteres")
    if item["categoria"] not in CATEGORIES:
        raise ValueError(f"{where}: categoria deve ser uma de {list(CATEGORIES)}")
    note = item.get("observacao")
    if note is not None and not isinstance(note, str):
        raise ValueError(f"{where}: observacao deve ser texto")
    return Phrase(require_name(item["id"], f"{where}: id"), text, item["categoria"], _expected(item["esperado"], where, genre_names), note)


def _expected(value: object, where: str, genre_names: set[str]) -> Judgement:
    expected = require_object(value, f"{where}: esperado", required=JUDGEMENT_FIELDS)
    lists = {}
    for field in ("generos", "generos_excluidos"):
        names = expected[field]
        if not isinstance(names, list) or any(name not in genre_names for name in names) or len(set(names)) != len(names):
            raise ValueError(f"{where}: {field} deve listar gêneros do catálogo, sem repetição")
        lists[field] = sorted(names)
    bounds = {
        field: None if expected[field] is None else _date(expected[field], f"{where}: {field}").isoformat()
        for field in ("lancado_depois", "lancado_antes")
    }
    return {**lists, **bounds, "bem_avaliado": require_bool(expected["bem_avaliado"], f"{where}: bem_avaliado")}


def _date(value: object, where: str) -> date:
    if not isinstance(value, str) or len(value) != len("AAAA-MM-DD"):
        raise ValueError(f"{where} deve ser uma data AAAA-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{where} deve ser uma data AAAA-MM-DD válida") from exc
