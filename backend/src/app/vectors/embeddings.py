"""Representações densas: word2vec pré-treinado (média de vetores de palavras) e embeddings contextuais.

As bibliotecas pesadas só são importadas ao carregar um modelo, então BoW e TF-IDF funcionam sem o extra `semantico`.
"""

import re
from collections.abc import Callable
from functools import cached_property
from typing import Protocol

import numpy as np
from sklearn.preprocessing import normalize

from app.vectors.config import ExperimentConfig, RepresentationSpec
from app.vectors.corpus import ProcessedCorpus
from app.vectors.metrics import rounded
from app.vectors.probes import contains_word
from app.vectors.space import Encoded, Representation

DIGIT_RE = re.compile(r"\d")


class WordVectors(Protocol):
    """Vetores estáticos: uma palavra tem sempre o mesmo vetor, qualquer que seja a frase."""

    dimension: int
    parameters: int

    def vector(self, word: str) -> np.ndarray | None: ...


class TextEncoder(Protocol):
    """Codificador contextual: textos inteiros e vetores de uma palavra dentro de uma frase."""

    max_tokens: int | None
    parameters: int | None

    def encode(self, texts: list[str]) -> np.ndarray: ...

    def count_tokens(self, text: str) -> int: ...

    def word_vectors(self, text: str, word: str) -> list[np.ndarray]: ...


def _unit(vector: np.ndarray) -> np.ndarray:
    return normalize(np.asarray(vector, dtype=np.float64).reshape(1, -1)).ravel()


def _dense_rows(representation: Representation) -> list[dict]:
    return [
        {"id": movie_id, "vector": [rounded(value) for value in row]}
        for movie_id, row in zip(representation.ids, representation.matrix.tolist(), strict=True)
    ]


def _unique_known(tokens: tuple[str, ...], vectors: WordVectors) -> list[str]:
    return sorted({token for token in tokens if vectors.vector(token) is not None})


def _stack_known(words: list[str] | tuple[str, ...], vectors: WordVectors) -> np.ndarray:
    return np.vstack([vector for word in words if (vector := vectors.vector(word)) is not None])


class Word2VecSpace(Representation):
    """Cada sinopse é a média dos vetores das suas palavras; palavras desconhecidas pelo modelo são ignoradas.

    O vetor de uma palavra é estático: `word_in_context` devolve o mesmo vetor em qualquer frase, o que
    torna visível a limitação do word2vec diante da polissemia.
    """

    family = "static"
    learned = True
    supports_words = True
    supports_word_in_context = True

    def __init__(self, spec: RepresentationSpec, ids: tuple[int, ...], tokens: list[list[str]], vectors: WordVectors):
        self.vectors = vectors
        self.tokens = [tuple(document) for document in tokens]
        super().__init__(spec, ids, np.vstack([self._mean(document) for document in self.tokens]))

    def _mean(self, tokens: tuple[str, ...] | list[str]) -> np.ndarray:
        known = [vector for token in tokens if (vector := self.vectors.vector(token)) is not None]
        return np.mean(known, axis=0, dtype=np.float64) if known else np.zeros(self.vectors.dimension, dtype=np.float64)

    @cached_property
    def vocabulary(self) -> tuple[str, ...]:
        """Palavras do corpus conhecidas pelo modelo: universo das palavras vizinhas."""
        return tuple(sorted({token for document in self.tokens for token in document if self.vectors.vector(token) is not None}))

    @cached_property
    def vocabulary_unit(self) -> np.ndarray:
        return normalize(_stack_known(self.vocabulary, self.vectors).astype(np.float64))

    def encode(self, text: str, corpus: ProcessedCorpus) -> Encoded:
        tokens = corpus.query_tokens(text, self.spec.stage_key)
        unknown = tuple(sorted({token for token in tokens if self.vectors.vector(token) is None}))
        return Encoded(normalize(self._mean(tokens).reshape(1, -1)), tuple(tokens), unknown)

    def document(self, row: int) -> Encoded:
        return Encoded(self.unit[row : row + 1], self.tokens[row])

    def explain(self, left: Encoded, right: Encoded, limit: int) -> list[str]:
        """Pares de palavras com vetores mais próximos: aproxima sinônimos que BoW e TF-IDF não ligam."""
        words_left, words_right = _unique_known(left.tokens, self.vectors), _unique_known(right.tokens, self.vectors)
        if not words_left or not words_right:
            return []
        similarity = normalize(_stack_known(words_left, self.vectors)) @ normalize(_stack_known(words_right, self.vectors)).T
        pairs: list[str] = []
        used_left: set[int] = set()
        used_right: set[int] = set()
        for flat in np.argsort(-similarity, axis=None, kind="stable"):
            i, j = divmod(int(flat), len(words_right))
            if len(pairs) == limit or similarity[i, j] <= 0:
                break
            if i in used_left or j in used_right:
                continue
            used_left.add(i)
            used_right.add(j)
            pairs.append(words_left[i] if words_left[i] == words_right[j] else f"{words_left[i]} ≈ {words_right[j]}")
        return pairs

    def nearest_words(self, word: str, limit: int) -> list[list] | None:
        vector = self.vectors.vector(word)
        if vector is None or not self.vocabulary:
            return None
        scores = self.vocabulary_unit @ normalize(vector.reshape(1, -1).astype(np.float64)).ravel()
        order = np.lexsort((np.arange(len(scores)), -scores))
        return [[self.vocabulary[i], rounded(scores[i])] for i in order if self.vocabulary[i] != word][:limit]

    def word_similarity(self, left: str, right: str) -> float | None:
        left_vector, right_vector = self.vectors.vector(left), self.vectors.vector(right)
        if left_vector is None or right_vector is None:
            return None
        return float(_unit(left_vector) @ _unit(right_vector))

    def word_in_context(self, text: str, word: str) -> np.ndarray | None:
        vector = self.vectors.vector(word)
        return _unit(vector) if vector is not None and contains_word(text, word) else None

    def parameters(self) -> int | None:
        return self.vectors.parameters

    def summary(self, config: ExperimentConfig) -> dict:
        total = sum(len(document) for document in self.tokens)
        known = sum(self.vectors.vector(token) is not None for document in self.tokens for token in document)
        return {
            "model": self.spec.model,
            "revision": self.spec.revision,
            "token_coverage": rounded(known / total) if total else None,
            "documents_without_known_words": sum(not np.any(row) for row in self.matrix),
            "corpus_words_in_model": len(self.vocabulary),
            "parameters": self.vectors.parameters,
        }

    def export(self) -> dict[str, list | dict]:
        return {"embeddings.jsonl": _dense_rows(self)}


class ContextualSpace(Representation):
    """Transformer: o modelo tokeniza em subpalavras e cada token recebe um vetor que depende da frase inteira.

    O vetor da sinopse é a média dos vetores dos tokens (mean pooling). Serve tanto a um BERT pré-treinado
    apenas com modelagem de linguagem mascarada quanto a um modelo ajustado para similaridade de
    sentenças; a diferença está no modelo configurado, não no código.
    """

    family = "contextual"
    learned = True
    supports_word_in_context = True

    def __init__(self, spec: RepresentationSpec, ids: tuple[int, ...], texts: list[str], encoder: TextEncoder):
        self.encoder, self.texts = encoder, texts
        super().__init__(spec, ids, np.asarray(encoder.encode(texts), dtype=np.float64))

    def encode(self, text: str, corpus: ProcessedCorpus) -> Encoded:
        prepared = corpus.query_text(text, self.spec.stage_key)
        return Encoded(normalize(np.asarray(self.encoder.encode([prepared]), dtype=np.float64)))

    def document(self, row: int) -> Encoded:
        return Encoded(self.unit[row : row + 1])

    def summary(self, config: ExperimentConfig) -> dict:
        limit = self.encoder.max_tokens
        truncated = sum(self.encoder.count_tokens(text) > limit for text in self.texts) if limit else None
        return {
            "model": self.spec.model,
            "revision": self.spec.revision,
            "max_tokens": limit,
            "truncated_documents": truncated,
            "parameters": self.encoder.parameters,
        }

    def word_in_context(self, text: str, word: str) -> np.ndarray | None:
        vectors = self.encoder.word_vectors(text, word)
        return _unit(vectors[0]) if vectors else None

    def parameters(self) -> int | None:
        return self.encoder.parameters

    def export(self) -> dict[str, list | dict]:
        return {"embeddings.jsonl": _dense_rows(self)}


def _sentence_transformer(spec: RepresentationSpec):
    """Carrega o modelo na revisão fixada, com `trust_remote_code=False`: nenhum código do repositório do modelo é executado."""
    try:
        from sentence_transformers import SentenceTransformer
        from transformers.utils import logging as transformers_logging
    except ImportError as exc:
        raise ValueError("Métodos semânticos exigem o extra opcional: uv sync --frozen --extra semantico") from exc
    transformers_logging.set_verbosity_error()
    return SentenceTransformer(spec.model, revision=spec.revision, device="cpu", trust_remote_code=False)


class SentenceTransformerWordVectors:
    """Adapta um modelo sentence-transformers do tipo WordEmbeddings ao contrato `WordVectors`.

    A referência ao modelo é mantida para preservar o tensor compartilhado com a matriz NumPy. Os
    vetores do NILC foram treinados com dígitos trocados por 0, e a consulta aplica a mesma troca.
    """

    def __init__(self, model):
        module = model[0]
        index = getattr(getattr(module, "tokenizer", None), "word2idx", None)
        if index is None or not hasattr(module, "emb_layer"):
            raise ValueError("O modelo informado não é um conjunto de vetores de palavras (WordEmbeddings)")
        self._model = model
        self.index = index
        self.weights = module.emb_layer.weight.detach().cpu().numpy()
        self.dimension = int(self.weights.shape[1])
        self.parameters = int(self.weights.size)

    def vector(self, word: str) -> np.ndarray | None:
        position = self.index.get(DIGIT_RE.sub("0", word))
        return None if position is None else self.weights[position]


class SentenceTransformerEncoder:
    """Adapta um modelo sentence-transformers ao contrato `TextEncoder`, com embeddings normalizados.

    `word_vectors` roda o transformer subjacente e usa os deslocamentos de caracteres do tokenizador
    para achar as subpalavras de cada ocorrência da palavra; o vetor da ocorrência é a média delas.
    """

    def __init__(self, model):
        self.model = model
        self.max_tokens = getattr(model, "max_seq_length", None)
        self.parameters = sum(parameter.numel() for parameter in model.parameters())

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, batch_size=32, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)

    def count_tokens(self, text: str) -> int:
        """Tokens do texto, só para medir truncamento; `verbose=False` evita o aviso de sequência longa."""
        return len(self.model.tokenizer(text, verbose=False)["input_ids"])

    def word_vectors(self, text: str, word: str) -> list[np.ndarray]:
        import torch

        encoded = self.model.tokenizer(text, return_offsets_mapping=True, return_tensors="pt", truncation=True, max_length=self.max_tokens)
        offsets = encoded.pop("offset_mapping")[0].tolist()
        with torch.no_grad():
            hidden = self.model[0].auto_model(**encoded).last_hidden_state[0].cpu().numpy()
        vectors = []
        for match in re.finditer(rf"(?<!\w){re.escape(word)}(?!\w)", text, flags=re.IGNORECASE):
            start, end = match.span()
            rows = [index for index, (left, right) in enumerate(offsets) if right > left and left >= start and right <= end]
            if rows:
                vectors.append(hidden[rows].mean(axis=0))
        return vectors


class Word2VecMethod:
    name, description = "word2vec", "Média dos vetores word2vec pré-treinados das palavras da sinopse"
    input_kind, requires_model = "tokens", True

    def __init__(
        self, loader: Callable[[RepresentationSpec], WordVectors] = lambda spec: SentenceTransformerWordVectors(_sentence_transformer(spec))
    ):
        self._loader = loader

    def build(self, spec: RepresentationSpec, corpus: ProcessedCorpus, config: ExperimentConfig) -> Word2VecSpace:
        return Word2VecSpace(spec, corpus.ids, corpus.tokens(spec.stage), self._loader(spec))


class ContextualMethod:
    name, description = "contextual", "Embedding de sentença de um transformer (média dos vetores contextuais dos tokens)"
    input_kind, requires_model = "text", True

    def __init__(
        self, loader: Callable[[RepresentationSpec], TextEncoder] = lambda spec: SentenceTransformerEncoder(_sentence_transformer(spec))
    ):
        self._loader = loader

    def build(self, spec: RepresentationSpec, corpus: ProcessedCorpus, config: ExperimentConfig) -> ContextualSpace:
        return ContextualSpace(spec, corpus.ids, corpus.texts(spec.stage), self._loader(spec))
