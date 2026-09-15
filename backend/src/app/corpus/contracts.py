"""Contrato público da pasta processada, consumido por `app.vectors` sem depender do processamento.

`STAGES` associa cada arquivo de etapa à chave de `Representations` que ele serializa. A ordem é a
ordem de produção e é registrada no manifesto; alterá-la muda o formato da pasta processada.
"""

from typing import Final, Literal, TypedDict

StageKey = Literal["original", "clean", "normalized", "tokens", "words", "filtered"]


class Representations(TypedDict):
    """Representações sucessivas de uma sinopse, produzidas por `app.corpus.transform.representations`."""

    clean: str | None
    normalized: str | None
    tokens: list[str]
    words: list[str]
    filtered: list[str]


STAGES: Final[dict[str, StageKey]] = {
    "01_original.jsonl": "original",
    "02_clean.jsonl": "clean",
    "03_normalized.jsonl": "normalized",
    "04_tokens.jsonl": "tokens",
    "05_without_punctuation.jsonl": "words",
    "06_without_stopwords.jsonl": "filtered",
}

TEXT_KEYS: Final = frozenset({"original", "clean", "normalized"})
TOKEN_KEYS: Final = frozenset({"tokens", "words", "filtered"})

TEXT_STAGES: Final = frozenset(filename for filename, key in STAGES.items() if key in TEXT_KEYS - {"original"})
TOKEN_STAGES: Final = frozenset(filename for filename, key in STAGES.items() if key in TOKEN_KEYS)


def stage_field(key: StageKey) -> Literal["text", "tokens"]:
    """Campo JSONL que guarda o conteúdo da etapa: `text` para textos corridos, `tokens` para listas."""
    return "text" if key in TEXT_KEYS else "tokens"
