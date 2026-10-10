"""Codificação de textos longos pelos transformers do projeto, por partes (ADR 0026).

Uma crítica tem em média centenas de tokens, e o embedding de sentença lê só os primeiros 128: o veredito,
que costuma vir no fim, ficaria de fora. `ChunkedEncoder` corta o texto em partes que cabem no modelo, pelas
posições de caractere do tokenizador, codifica cada parte com o mesmo modelo e tira a média dos vetores.
O modelo, a revisão e o pooling continuam os da Etapa 2; só a entrada é dividida.
"""

from collections.abc import Mapping

import numpy as np
from sklearn.preprocessing import normalize

from app.representations.config import RepresentationSpec
from app.representations.embeddings import ContextualMethod, SentenceTransformerEncoder, TextEncoder, _sentence_transformer
from app.representations.methods import METHODS, Method

SPECIAL_TOKENS = 2


class ChunkedEncoder:
    """Cumpre o contrato `TextEncoder`: cada texto vira a média normalizada dos vetores das suas partes."""

    max_tokens: int | None = None

    def __init__(self, inner: SentenceTransformerEncoder, chunk_tokens: int | None = None) -> None:
        limit = chunk_tokens or (inner.max_tokens or 512) - SPECIAL_TOKENS
        if limit < 1:
            raise ValueError("Partes precisam de ao menos um token")
        self.inner = inner
        self.chunk_tokens = limit
        self.parameters = inner.parameters
        self.chunks_per_text: list[int] = []

    def chunks(self, text: str) -> list[str]:
        """Partes consecutivas de até `chunk_tokens` tokens, cortadas nas posições de caractere do tokenizador."""
        offsets = self.inner.model.tokenizer(text, add_special_tokens=False, return_offsets_mapping=True, verbose=False)["offset_mapping"]
        if len(offsets) <= self.chunk_tokens:
            return [text]
        parts = []
        for start in range(0, len(offsets), self.chunk_tokens):
            window = offsets[start : start + self.chunk_tokens]
            parts.append(text[window[0][0] : window[-1][1]])
        return [part for part in parts if part.strip()] or [text]

    def encode(self, texts: list[str]) -> np.ndarray:
        pieces: list[str] = []
        owners: list[int] = []
        counts = []
        for index, text in enumerate(texts):
            parts = self.chunks(text)
            pieces += parts
            owners += [index] * len(parts)
            counts.append(len(parts))
        vectors = np.asarray(self.inner.encode(pieces), dtype=np.float64)
        total = np.zeros((len(texts), vectors.shape[1]))
        np.add.at(total, np.asarray(owners), vectors)
        self.chunks_per_text = counts
        return normalize(total / np.asarray(counts, dtype=np.float64)[:, None])

    def count_tokens(self, text: str) -> int:
        return self.inner.count_tokens(text)

    def word_vectors(self, text: str, word: str) -> list[np.ndarray]:
        return self.inner.word_vectors(text, word)


def chunked_loader(spec: RepresentationSpec) -> TextEncoder:
    """Carrega o modelo da Etapa 2 (com cache) e o envolve no codificador por partes."""
    return ChunkedEncoder(SentenceTransformerEncoder(_sentence_transformer(spec)))


def long_text_methods() -> Mapping[str, Method]:
    """Os métodos da Etapa 2, com o contextual lendo textos longos por partes."""
    return {**METHODS, "contextual": ContextualMethod(loader=chunked_loader)}
