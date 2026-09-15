"""Configuração validada dos experimentos. Arquivos de entrada são dados, nunca código.

O arquivo de entrada de cada representação vem de uma lista fixa de etapas da Etapa 1, compatível
com o tipo de entrada do método (tokens ou texto corrido); assim a configuração não aponta para fora
da pasta processada. Modelos pré-treinados exigem identificador do Hugging Face e revisão fixada por
hash de commit, para que o conteúdo do modelo não mude entre execuções.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.corpus.contracts import STAGES, TEXT_STAGES, TOKEN_STAGES, StageKey
from app.shared.validation import (
    read_config_json,
    require_ids,
    require_int,
    require_name,
    require_object,
    require_unique,
)

MAX_QUERY_CHARS = 500
MAX_REPRESENTATIONS = 20
MAX_QUERIES = 100
MAX_PROBE_WORDS = 30
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}/[A-Za-z0-9][A-Za-z0-9_.-]{0,95}")
REVISION_RE = re.compile(r"[0-9a-f]{40}")
STAGE_KINDS: dict[str, frozenset[str]] = {"tokens": TOKEN_STAGES, "text": TEXT_STAGES}
DEFAULTS = {"min_df": 1, "neighbors_k": 5, "example_ids": [], "clusters": 4, "top_terms": 10, "random_state": 42, "probe_words": []}


class MethodInfo(Protocol):
    """O que a validação precisa saber de um método, sem depender da sua implementação.

    `input_kind` é `tokens` para etapas tokenizadas ou `text` para textos corridos.
    """

    input_kind: str
    requires_model: bool


@dataclass(frozen=True)
class RepresentationSpec:
    """Uma representação a construir: nome de saída, método, etapa de entrada e modelo opcional."""

    name: str
    method: str
    stage: str
    model: str | None = None
    revision: str | None = None

    @property
    def stage_key(self) -> StageKey:
        """Chave de `app.corpus.transform.representations` equivalente à etapa de entrada."""
        return STAGES[self.stage]


@dataclass(frozen=True)
class ExperimentConfig:
    """Parâmetros comuns a todas as representações e análises de um experimento."""

    representations: tuple[RepresentationSpec, ...]
    min_df: int
    neighbors_k: int
    example_ids: tuple[int, ...]
    clusters: int
    top_terms: int
    random_state: int
    probe_words: tuple[str, ...]


@dataclass(frozen=True)
class QuerySpec:
    """Consulta anotada com os filmes considerados relevantes (lista parcial)."""

    id: str
    text: str
    relevant_ids: tuple[int, ...]
    note: str = ""


def validate_query_text(text: object) -> str:
    """Consulta não vazia com até `MAX_QUERY_CHARS` caracteres."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("A consulta deve ser um texto não vazio")
    if len(text) > MAX_QUERY_CHARS:
        raise ValueError(f"A consulta excede {MAX_QUERY_CHARS} caracteres")
    return text


def load_config(path: Path, methods: Mapping[str, MethodInfo]) -> ExperimentConfig:
    """Lê e valida a configuração do experimento contra os métodos disponíveis."""
    data = require_object(read_config_json(path), "configuração", required={"representations"}, optional=set(DEFAULTS))
    items = data["representations"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_REPRESENTATIONS:
        raise ValueError(f"representations deve listar de 1 a {MAX_REPRESENTATIONS} representações")
    specs = tuple(_representation(item, methods) for item in items)
    require_unique([spec.name for spec in specs], "Nomes de representação repetidos")
    values = {**DEFAULTS, **data}
    probe_words = values["probe_words"]
    if (
        not isinstance(probe_words, list)
        or len(probe_words) > MAX_PROBE_WORDS
        or any(not isinstance(w, str) or not 1 <= len(w) <= 40 for w in probe_words)
    ):
        raise ValueError(f"probe_words deve listar até {MAX_PROBE_WORDS} palavras com até 40 caracteres")
    return ExperimentConfig(
        representations=specs,
        min_df=require_int(values["min_df"], "min_df", 1, 1000),
        neighbors_k=require_int(values["neighbors_k"], "neighbors_k", 1, 50),
        example_ids=require_ids(values["example_ids"], "example_ids", allow_empty=True),
        clusters=require_int(values["clusters"], "clusters", 2, 50),
        top_terms=require_int(values["top_terms"], "top_terms", 1, 50),
        random_state=require_int(values["random_state"], "random_state", 0, 2**32 - 1),
        probe_words=tuple(dict.fromkeys(word.casefold() for word in probe_words)),
    )


def load_queries(path: Path) -> tuple[QuerySpec, ...]:
    """Lê e valida as consultas anotadas."""
    data = require_object(read_config_json(path), "arquivo de consultas", required={"queries"}, optional={"description"})
    items = data["queries"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_QUERIES:
        raise ValueError(f"queries deve listar de 1 a {MAX_QUERIES} consultas")
    queries = tuple(_query(item) for item in items)
    require_unique([query.id for query in queries], "IDs de consulta repetidos")
    return queries


def _representation(item: object, methods: Mapping[str, MethodInfo]) -> RepresentationSpec:
    data = require_object(item, "representação", required={"name", "method", "stage"}, optional={"model", "revision"})
    name, method, stage = require_name(data["name"], "name"), data["method"], data["stage"]
    if not isinstance(method, str) or method not in methods:
        raise ValueError(f"Método desconhecido: {method!r}; use um de {sorted(methods)}")
    info = methods[method]
    allowed = STAGE_KINDS[info.input_kind]
    if not isinstance(stage, str) or stage not in allowed:
        raise ValueError(f"{name}: etapa de entrada não permitida para {method}: {stage!r}; use uma de {sorted(allowed)}")
    model, revision = data.get("model"), data.get("revision")
    if info.requires_model:
        if not isinstance(model, str) or not MODEL_RE.fullmatch(model) or ".." in model:
            raise ValueError(f"{name}: model deve ser um identificador organização/modelo do Hugging Face")
        if not isinstance(revision, str) or not REVISION_RE.fullmatch(revision):
            raise ValueError(f"{name}: revision deve ser o hash de commit (40 caracteres hexadecimais) do modelo")
    elif model is not None or revision is not None:
        raise ValueError(f"{name}: o método {method} não usa model nem revision")
    return RepresentationSpec(name, method, stage, model, revision)


def _query(item: object) -> QuerySpec:
    data = require_object(item, "consulta", required={"id", "text", "relevant_ids"}, optional={"note"})
    note = data.get("note", "")
    if not isinstance(note, str) or len(note) > MAX_QUERY_CHARS:
        raise ValueError(f"note deve ser texto com até {MAX_QUERY_CHARS} caracteres")
    return QuerySpec(
        require_name(data["id"], "id"), validate_query_text(data["text"]), require_ids(data["relevant_ids"], "relevant_ids"), note
    )
