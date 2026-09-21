"""Sondas linguísticas da Aula 7: pares de frases, pares de palavras e sentidos de palavras polissêmicas.

São exemplos escritos pela equipe (não pertencem ao corpus) para comparar as representações quanto a
sobreposição lexical versus proximidade semântica, hipótese distribucional e polissemia. O arquivo é
dado, nunca código, e segue as mesmas regras de validação das consultas.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from app.shared.validation import read_config_json, require_name, require_object, require_unique
from app.vectors.config import MAX_QUERY_CHARS, validate_query_text

MAX_PROBES = 30
MAX_CONTEXTS = 12
EXPECTATIONS = frozenset({"proximas", "distantes"})
WORD_RE = re.compile(r"[^\W\d_]{1,40}(?:-[^\W\d_]{1,40})?")


@dataclass(frozen=True)
class SentencePair:
    """Duas frases e a relação semântica esperada entre elas (`proximas` ou `distantes`)."""

    id: str
    left: str
    right: str
    expected: str
    note: str = ""


@dataclass(frozen=True)
class SenseContext:
    """Uma frase em que a palavra-alvo aparece com um sentido rotulado."""

    sense: str
    text: str


@dataclass(frozen=True)
class WordSense:
    """Palavra polissêmica e frases rotuladas por sentido; exige ao menos dois sentidos distintos."""

    id: str
    word: str
    contexts: tuple[SenseContext, ...]


@dataclass(frozen=True)
class ProbeSet:
    """Conjunto de sondas carregado de `config/sondas_semanticas.json`."""

    sentence_pairs: tuple[SentencePair, ...] = ()
    word_pairs: tuple[tuple[str, str], ...] = ()
    word_senses: tuple[WordSense, ...] = ()


def contains_word(text: str, word: str) -> bool:
    """Verdadeiro quando `word` aparece em `text` como palavra inteira, sem diferenciar maiúsculas."""
    return re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text, flags=re.IGNORECASE) is not None


def load_probes(path: Path) -> ProbeSet:
    """Lê e valida as sondas; palavras são comparadas em minúsculas (`casefold`)."""
    data = require_object(
        read_config_json(path), "arquivo de sondas", required=set(), optional={"description", "sentence_pairs", "word_pairs", "word_senses"}
    )
    pairs = tuple(_sentence_pair(item) for item in _items(data, "sentence_pairs"))
    words = tuple(_word_pair(item) for item in _items(data, "word_pairs"))
    senses = tuple(_word_sense(item) for item in _items(data, "word_senses"))
    require_unique([pair.id for pair in pairs], "IDs de pares de frases repetidos")
    require_unique([sense.id for sense in senses], "IDs de palavras polissêmicas repetidos")
    if not (pairs or words or senses):
        raise ValueError("O arquivo de sondas não contém nenhuma sonda")
    return ProbeSet(pairs, words, senses)


def _items(data: dict, key: str) -> list:
    items = data.get(key, [])
    if not isinstance(items, list) or len(items) > MAX_PROBES:
        raise ValueError(f"{key} deve ser uma lista com até {MAX_PROBES} itens")
    return items


def _word(value: object, where: str) -> str:
    if not isinstance(value, str) or not WORD_RE.fullmatch(value):
        raise ValueError(f"{where} deve ser uma única palavra com até 40 letras")
    return value.casefold()


def _note(data: dict) -> str:
    note = data.get("note", "")
    if not isinstance(note, str) or len(note) > MAX_QUERY_CHARS:
        raise ValueError(f"note deve ser texto com até {MAX_QUERY_CHARS} caracteres")
    return note


def _sentence_pair(item: object) -> SentencePair:
    data = require_object(item, "par de frases", required={"id", "left", "right", "expected"}, optional={"note"})
    expected = data["expected"]
    if expected not in EXPECTATIONS:
        raise ValueError(f"expected deve ser um de {sorted(EXPECTATIONS)}")
    return SentencePair(
        require_name(data["id"], "id"), validate_query_text(data["left"]), validate_query_text(data["right"]), expected, _note(data)
    )


def _word_pair(item: object) -> tuple[str, str]:
    if not isinstance(item, list) or len(item) != 2:
        raise ValueError("Cada par de palavras deve ser uma lista com duas palavras")
    left, right = _word(item[0], "word_pairs"), _word(item[1], "word_pairs")
    if left == right:
        raise ValueError("Um par de palavras precisa de duas palavras diferentes")
    return left, right


def _word_sense(item: object) -> WordSense:
    data = require_object(item, "palavra polissêmica", required={"id", "word", "contexts"})
    word = _word(data["word"], "word")
    contexts = data["contexts"]
    if not isinstance(contexts, list) or not 2 <= len(contexts) <= MAX_CONTEXTS:
        raise ValueError(f"contexts deve listar de 2 a {MAX_CONTEXTS} frases")
    parsed = []
    for context in contexts:
        entry = require_object(context, "contexto", required={"sense", "text"})
        sense, text = entry["sense"], validate_query_text(entry["text"])
        if not isinstance(sense, str) or not 1 <= len(sense.strip()) <= 60:
            raise ValueError("sense deve ser um rótulo com até 60 caracteres")
        if not contains_word(text, word):
            raise ValueError(f"A palavra {word!r} não aparece no contexto {text!r}")
        parsed.append(SenseContext(sense.strip(), text))
    if len({context.sense for context in parsed}) < 2:
        raise ValueError(f"{word!r}: são necessários ao menos dois sentidos diferentes")
    return WordSense(require_name(data["id"], "id"), word, tuple(parsed))
