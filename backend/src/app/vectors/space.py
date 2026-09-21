"""Contrato comum das representações e a representação lexical (BoW e TF-IDF)."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property

import numpy as np
from scipy.sparse import csr_matrix, issparse, spmatrix
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.preprocessing import normalize

from app.vectors.config import ExperimentConfig, RepresentationSpec
from app.vectors.corpus import ProcessedCorpus
from app.vectors.metrics import rounded


@dataclass(frozen=True)
class Encoded:
    """Um texto já no espaço vetorial: vetor 1 × d com norma L2 (ou nulo) e os tokens que o formaram."""

    vector: np.ndarray | csr_matrix
    tokens: tuple[str, ...] = ()
    out_of_vocabulary: tuple[str, ...] = ()

    @property
    def null(self) -> bool:
        """Verdadeiro quando nenhuma dimensão do vetor é diferente de zero."""
        return count_nonzero(self.vector) == 0


def count_nonzero(matrix: np.ndarray | csr_matrix) -> int:
    """Quantidade de valores diferentes de zero em matriz densa ou esparsa."""
    return int(matrix.nnz) if isinstance(matrix, spmatrix) else int(np.count_nonzero(matrix))


def encoded_cosine(left: Encoded, right: Encoded) -> float:
    """Cosseno entre dois textos codificados (vetores já com norma L2); zero quando um deles é nulo."""
    product = left.vector @ right.vector.T
    return float(product.toarray()[0, 0] if issparse(product) else np.asarray(product)[0, 0])


class Representation(ABC):
    """Linhas = sinopses na ordem do corpus. As análises dependem só deste contrato (inversão de dependência).

    Atributos de classe descrevem a família da representação, usados na síntese comparativa:

    - `family`: `lexical` (dimensões = termos do vocabulário), `static` (um vetor aprendido por palavra,
      igual em qualquer contexto) ou `contextual` (vetor da palavra depende da frase);
    - `learned`: os vetores vêm de treinamento sobre grandes corpora, e não de contagens;
    - `supports_words`: há vetores por palavra fora de contexto (vizinhança e pares de palavras);
    - `supports_word_in_context`: é possível obter o vetor de uma palavra dentro de uma frase (polissemia).
    """

    family = "lexical"
    learned = False
    supports_words = False
    supports_word_in_context = False

    def __init__(self, spec: RepresentationSpec, ids: tuple[int, ...], matrix: np.ndarray | csr_matrix):
        self.spec, self.ids, self.matrix = spec, ids, matrix

    @cached_property
    def unit(self) -> np.ndarray | csr_matrix:
        """Linhas com norma L2: o produto escalar vira cosseno, que mede direção e ignora o tamanho da sinopse."""
        return normalize(self.matrix.astype(np.float64), norm="l2")

    @property
    def dimensions(self) -> int:
        return self.matrix.shape[1]

    @abstractmethod
    def encode(self, text: str, corpus: ProcessedCorpus) -> Encoded:
        """Leva uma consulta ao mesmo espaço, com as mesmas regras de preparação dos documentos."""

    @abstractmethod
    def document(self, row: int) -> Encoded: ...

    @abstractmethod
    def export(self) -> dict[str, list | dict]:
        """Arquivos da representação: listas viram JSONL, dicionários viram JSON."""

    def summary(self, config: ExperimentConfig) -> dict:
        return {}

    def explain(self, left: Encoded, right: Encoded, limit: int) -> list[str]:
        """Por que dois textos estão próximos; vazio quando o método não é interpretável por palavras."""
        return []

    def nearest_words(self, word: str, limit: int) -> list[list] | None:
        """Palavras mais próximas de `word`; None quando o método não possui vetores de palavras."""
        return None

    def word_similarity(self, left: str, right: str) -> float | None:
        """Cosseno entre duas palavras fora de contexto; None quando não há vetores de palavras ou uma delas é desconhecida."""
        return None

    def word_in_context(self, text: str, word: str) -> np.ndarray | None:
        """Vetor com norma L2 de `word` na frase `text`; None quando não suportado ou a palavra não é encontrada."""
        return None

    def parameters(self) -> int | None:
        """Quantidade de parâmetros aprendidos do modelo carregado; None para representações sem treinamento."""
        return None

    def cosine(self, vectors: np.ndarray | csr_matrix) -> np.ndarray:
        scores = vectors @ self.unit.T
        return scores.toarray() if issparse(scores) else np.asarray(scores)

    def ranking(self, scores: np.ndarray) -> np.ndarray:
        """Linhas por similaridade decrescente; empates resolvidos pelo ID para saídas determinísticas."""
        return np.lexsort((np.asarray(self.ids), -scores))


def pretokenized(tokens: list[str]) -> list[str]:
    """Reaproveita a tokenização versionada da Etapa 1 em vez de tokenizar outra vez."""
    return tokens


class LexicalSpace(Representation):
    """Matriz documento × termo esparsa: cada dimensão é uma palavra do vocabulário do corpus."""

    matrix: csr_matrix

    def __init__(self, spec: RepresentationSpec, ids: tuple[int, ...], tokens: list[list[str]], vectorizer: CountVectorizer):
        super().__init__(spec, ids, csr_matrix(vectorizer.fit_transform(tokens)))
        self.vectorizer = vectorizer
        self.terms = tuple(vectorizer.get_feature_names_out().tolist())
        self.tokens = [tuple(document) for document in tokens]

    @cached_property
    def term_index(self) -> dict[str, int]:
        return {term: column for column, term in enumerate(self.terms)}

    @cached_property
    def document_frequency(self) -> np.ndarray:
        return np.asarray((self.matrix > 0).sum(axis=0)).ravel()

    def encode(self, text: str, corpus: ProcessedCorpus) -> Encoded:
        tokens = corpus.query_tokens(text, self.spec.stage_key)
        vector = normalize(self.vectorizer.transform([tokens]).astype(np.float64), norm="l2")
        return Encoded(vector, tuple(tokens), tuple(sorted({t for t in tokens if t not in self.term_index})))

    def document(self, row: int) -> Encoded:
        return Encoded(self.unit[row], self.tokens[row])

    def explain(self, left: Encoded, right: Encoded, limit: int) -> list[str]:
        """Termos que mais contribuem para o cosseno: só palavras idênticas nos dois textos."""
        product = csr_matrix(left.vector).multiply(csr_matrix(right.vector)).tocoo()
        pairs = sorted(zip(product.data.tolist(), product.col.tolist(), strict=True), key=lambda pair: (-pair[0], self.terms[pair[1]]))
        return [self.terms[column] for _, column in pairs[:limit]]

    def summary(self, config: ExperimentConfig) -> dict:
        weights = np.asarray(self.matrix.sum(axis=0), dtype=np.float64).ravel()
        top = np.lexsort((np.arange(len(weights)), -weights))[: config.top_terms]
        return {"top_terms": [[self.terms[column], rounded(weights[column])] for column in top]}

    def export(self) -> dict[str, list | dict]:
        idf = getattr(self.vectorizer, "idf_", None)
        terms = []
        for column, (term, frequency) in enumerate(zip(self.terms, self.document_frequency.tolist(), strict=True)):
            terms.append({"term": term, "document_frequency": frequency, **({"idf": rounded(idf[column])} if idf is not None else {})})
        integer = np.issubdtype(self.matrix.dtype, np.integer)
        rows = []
        indptr, indices, data = self.matrix.indptr.tolist(), self.matrix.indices.tolist(), self.matrix.data.tolist()
        for row, movie_id in enumerate(self.ids):
            cells = range(indptr[row], indptr[row + 1])
            pairs = sorted(((self.terms[indices[c]], data[c]) for c in cells), key=lambda p: (-p[1], p[0]))
            rows.append({"id": movie_id, "weights": {term: value if integer else rounded(value) for term, value in pairs}})
        return {
            "matrix.jsonl": rows,
            "vocabulary.json": {"representation": self.spec.name, "method": self.spec.method, "stage": self.spec.stage, "terms": terms},
        }


class LexicalMethod:
    """Fábrica de representações lexicais; a ponderação é a estratégia escolhida (contagem ou TF-IDF)."""

    input_kind, requires_model = "tokens", False

    def __init__(self, name: str, description: str, vectorizer: Callable[[int], CountVectorizer]):
        self.name, self.description, self._vectorizer = name, description, vectorizer

    def build(self, spec: RepresentationSpec, corpus: ProcessedCorpus, config: ExperimentConfig) -> LexicalSpace:
        return LexicalSpace(spec, corpus.ids, corpus.tokens(spec.stage), self._vectorizer(config.min_df))


BOW = LexicalMethod(
    "bow", "Contagem de ocorrências por documento (bag of words)", lambda min_df: CountVectorizer(analyzer=pretokenized, min_df=min_df)
)
TFIDF = LexicalMethod(
    "tfidf",
    "tf × idf suavizado, idf = ln((1 + n) / (1 + df)) + 1, norma L2 por documento",
    lambda min_df: TfidfVectorizer(analyzer=pretokenized, min_df=min_df),
)
