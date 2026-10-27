"""Críticas preparadas por filme e a escolha dos trechos que entram no contexto do RAG.

Cada crítica é dividida em janelas de cerca de `excerpt_chars` caracteres, cortadas entre palavras. Com um
codificador de sentenças (o MiniLM que a busca por tema já carrega), o trecho de cada crítica é a janela mais
parecida com a pergunta, e as críticas entram em ordem dessa semelhança; sem codificador, entra o começo das
críticas, na ordem do arquivo. O trecho leva a nota que o autor deu, nunca o autor (ADR 0026).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from app.corpus.verification import verify_processed
from app.representations.corpus import ProcessedCorpus
from app.shared.artifacts import read_jsonl

CLEAN_STAGE = "02_clean.jsonl"


class SentenceEncoder(Protocol):
    """Codificador de textos em vetores (o `TextEncoder` das representações cumpre)."""

    def encode(self, texts: list[str]) -> np.ndarray: ...


@dataclass(frozen=True)
class Review:
    review_id: str
    rating: float | None
    text: str


@dataclass(frozen=True)
class Excerpt:
    """Trecho de uma crítica e a nota do autor."""

    review_id: str
    rating: float | None
    text: str


def windows(text: str, size: int) -> list[str]:
    """Janelas consecutivas de até `size` caracteres, cortadas entre palavras; uma palavra maior que `size` fica inteira."""
    parts: list[str] = []
    current: list[str] = []
    length = 0
    for word in text.split():
        if current and length + 1 + len(word) > size:
            parts.append(" ".join(current))
            current, length = [], 0
        current.append(word)
        length += len(word) + (1 if length else 0)
    if current:
        parts.append(" ".join(current))
    return parts


class ReviewStore:
    """Críticas indexadas pelo ID do filme no TMDB."""

    def __init__(self, reviews: dict[int, list[Review]], encoder: SentenceEncoder | None = None) -> None:
        self._reviews = reviews
        self._encoder = encoder

    @classmethod
    def load(cls, processed: Path, encoder: SentenceEncoder | None = None) -> ReviewStore:
        """Críticas de uma pasta preparada por `python -m app.sentiment process`, verificada."""
        verify_processed(processed)
        corpus = ProcessedCorpus.load(processed)
        metadata = {row["id"]: row for row in read_jsonl(processed / "metadata.jsonl")}
        reviews: dict[int, list[Review]] = {}
        for number, text in zip(corpus.ids, corpus.texts(CLEAN_STAGE), strict=True):
            row = metadata[number]
            reviews.setdefault(int(row["movie_id"]), []).append(Review(row["review_id"], row["rating"], text))
        return cls(reviews, encoder)

    @property
    def movies(self) -> int:
        return len(self._reviews)

    def count(self, movie_id: int) -> int:
        return len(self._reviews.get(movie_id, ()))

    def excerpts(self, movie_id: int, question: str, limit: int, size: int) -> list[Excerpt]:
        """Até `limit` trechos de críticas diferentes do filme, os mais parecidos com a pergunta primeiro."""
        reviews = self._reviews.get(movie_id, [])
        if not reviews or limit <= 0:
            return []
        candidates = [(review, windows(review.text, size)) for review in reviews]
        candidates = [(review, parts) for review, parts in candidates if parts]
        if self._encoder is None:
            return [Excerpt(review.review_id, review.rating, parts[0]) for review, parts in candidates[:limit]]
        flat = [part for _, parts in candidates for part in parts]
        vectors = _unit(self._encoder.encode([question, *flat]))
        scores = vectors[1:] @ vectors[0]
        best: list[tuple[float, int, Excerpt]] = []
        offset = 0
        for position, (review, parts) in enumerate(candidates):
            local = scores[offset : offset + len(parts)]
            choice = int(np.argmax(local))
            best.append((float(local[choice]), position, Excerpt(review.review_id, review.rating, parts[choice])))
            offset += len(parts)
        best.sort(key=lambda item: (-item[0], item[1]))
        return [excerpt for _, _, excerpt in best[:limit]]


def _unit(matrix: Sequence | np.ndarray) -> np.ndarray:
    array = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    return array / np.where(norms == 0, 1, norms)
