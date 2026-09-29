"""Configuração validada do experimento com o Jev, perguntas enviadas e amostra de avaliação.

As perguntas e os critérios fazem parte da especificação da tarefa: ficam no arquivo de configuração,
não no código, e o hash do texto exato enviado vai para o manifesto. A amostra é estratificada por
gênero e sorteada com semente fixa, para que outra execução avalie os mesmos filmes.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.corpus.contracts import TEXT_STAGES, TOKEN_STAGES
from app.jev.ports import Question
from app.shared.validation import (
    read_config_json,
    require_int,
    require_name,
    require_number,
    require_object,
    require_unique,
)
from app.vectors.corpus import Document, ProcessedCorpus

MAX_TEXT_CHARS = 500
MAX_GENRES = 10
CHOICE_NAME = "genero"
NOUL_PREFIX = "e_"


@dataclass(frozen=True)
class GenreSpec:
    """Gênero de coleta do TMDB avaliado: `key` nomeia a opção da Choice e a pergunta Noul correspondente."""

    id: int
    key: str
    description: str
    question: str

    @property
    def noul_name(self) -> str:
        return NOUL_PREFIX + self.key


@dataclass(frozen=True)
class JevConfig:
    """Parâmetros do experimento: texto enviado, amostra, limiar, perguntas e o classificador de referência."""

    stage: str
    sample_per_genre: int
    multi_genre_sample: int
    random_state: int
    threshold: float
    request_interval_seconds: float
    choice_question: str
    genres: tuple[GenreSpec, ...]
    baseline_stage: str
    baseline_min_df: int
    baseline_c: float

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(genre.key for genre in self.genres)

    def questions(self) -> dict[str, Question]:
        """Uma Choice com o gênero principal e um Noul por gênero, respondidos na mesma chamada."""
        questions = {CHOICE_NAME: Question("choice", self.choice_question, tuple((g.key, g.description) for g in self.genres))}
        questions.update({genre.noul_name: Question("noul", genre.question) for genre in self.genres})
        return questions

    def gold(self, document: Document) -> tuple[str, ...]:
        """Gêneros avaliados dos recortes de coleta que retornaram o filme, na ordem da configuração."""
        return tuple(genre.key for genre in self.genres if genre.id in document.genres)


def load_config(path: Path) -> JevConfig:
    """Lê e valida a configuração; os gêneros ainda são conferidos contra o corpus em `draw_sample`."""
    data = require_object(
        read_config_json(path),
        "configuração do Jev",
        required={
            "stage",
            "sample_per_genre",
            "multi_genre_sample",
            "random_state",
            "threshold",
            "request_interval_seconds",
            "choice_question",
            "genres",
            "baseline",
        },
    )
    stage = data["stage"]
    if not isinstance(stage, str) or stage not in TEXT_STAGES:
        raise ValueError(f"stage deve ser uma etapa de texto corrido: {sorted(TEXT_STAGES)}")
    items = data["genres"]
    if not isinstance(items, list) or not 2 <= len(items) <= MAX_GENRES:
        raise ValueError(f"genres deve listar de 2 a {MAX_GENRES} gêneros")
    genres = tuple(_genre(item) for item in items)
    require_unique([str(genre.id) for genre in genres], "IDs de gênero repetidos")
    require_unique([genre.key for genre in genres], "Chaves de gênero repetidas")
    baseline = require_object(data["baseline"], "baseline", required={"stage", "min_df", "c"})
    if not isinstance(baseline["stage"], str) or baseline["stage"] not in TOKEN_STAGES:
        raise ValueError(f"baseline.stage deve ser uma etapa tokenizada: {sorted(TOKEN_STAGES)}")
    return JevConfig(
        stage=stage,
        sample_per_genre=require_int(data["sample_per_genre"], "sample_per_genre", 1, 200),
        multi_genre_sample=require_int(data["multi_genre_sample"], "multi_genre_sample", 0, 200),
        random_state=require_int(data["random_state"], "random_state", 0, 2**32 - 1),
        threshold=require_number(data["threshold"], "threshold", 0.01, 0.99),
        request_interval_seconds=require_number(data["request_interval_seconds"], "request_interval_seconds", 0, 10),
        choice_question=_text(data["choice_question"], "choice_question"),
        genres=genres,
        baseline_stage=baseline["stage"],
        baseline_min_df=require_int(baseline["min_df"], "baseline.min_df", 1, 1000),
        baseline_c=require_number(baseline["c"], "baseline.c", 0.001, 1000),
    )


def draw_sample(corpus: ProcessedCorpus, config: JevConfig) -> tuple[Document, ...]:
    """Sorteia `sample_per_genre` filmes de gênero único por gênero e `multi_genre_sample` com vários gêneros avaliados.

    Filmes de gênero único têm rótulo inequívoco para a Choice; os de vários gêneros testam os Nouls.
    O resultado fica em ordem de ID.
    """
    if unknown := sorted(genre.id for genre in config.genres if genre.id not in corpus.genre_names):
        raise ValueError(f"Gêneros ausentes da pasta processada: {unknown}")
    wanted = frozenset(genre.id for genre in config.genres)
    rng = np.random.default_rng(config.random_state)
    chosen: list[Document] = []
    for genre in config.genres:
        pool = [document for document in corpus.documents if document.genres == {genre.id}]
        chosen += _draw(rng, pool, config.sample_per_genre, f"filmes só de {genre.key}")
    multi = [document for document in corpus.documents if len(document.genres) > 1 and document.genres <= wanted]
    chosen += _draw(rng, multi, config.multi_genre_sample, "filmes com vários gêneros avaliados")
    return tuple(sorted(chosen, key=lambda document: document.id))


def _draw(rng: np.random.Generator, pool: list[Document], size: int, what: str) -> list[Document]:
    """Sorteia sem reposição, deixando ao menos um filme do grupo para o treino do classificador de referência."""
    if len(pool) <= size and size:
        raise ValueError(f"Há {len(pool)} {what}; a amostra pede {size} e precisa deixar filmes para o treino")
    return [pool[int(index)] for index in rng.choice(len(pool), size=size, replace=False)]


def _genre(item: object) -> GenreSpec:
    data = require_object(item, "gênero", required={"id", "key", "description", "question"})
    return GenreSpec(
        require_int(data["id"], "genres.id", 1, 10**9),
        require_name(data["key"], "genres.key"),
        _text(data["description"], "genres.description"),
        _text(data["question"], "genres.question"),
    )


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT_CHARS:
        raise ValueError(f"{where} deve ser texto não vazio com até {MAX_TEXT_CHARS} caracteres")
    return value.strip()
