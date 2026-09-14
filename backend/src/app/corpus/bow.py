"""Representação numérica de texto utilizando o modelo Bag of Words (BoW).

Fornece vetorização determinística, métricas de esparsidade,
armazenamento em formato JSON/JSONL e cálculo de similaridade de cosseno.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class BagOfWordsVectorizer:
    """Vetorizador Bag of Words (BoW) determinístico.

    Mapeia coleções de tokens em vetores numéricos de frequência (TF),
    frequência binária ou TF normalizado.
    """

    def __init__(
        self,
        min_df: int = 1,
        max_df: float = 1.0,
        max_features: Optional[int] = None,
        binary: bool = False,
        normalize: bool = False,
    ):
        self.min_df = min_df
        self.max_df = max_df
        self.max_features = max_features
        self.binary = binary
        self.normalize = normalize

        self.vocabulary_: Dict[str, int] = {}
        self.feature_names_: List[str] = []
        self.doc_frequencies_: Dict[str, int] = {}
        self.term_frequencies_: Dict[str, int] = {}

    def fit(self, raw_documents: List[List[str]]) -> BagOfWordsVectorizer:
        """Constrói o vocabulário a partir de documentos tokenizados."""
        n_docs = len(raw_documents)
        doc_freqs: Counter[str] = Counter()
        term_freqs: Counter[str] = Counter()

        for doc in raw_documents:
            unique_terms = set(doc)
            doc_freqs.update(unique_terms)
            term_freqs.update(doc)

        filtered_terms: List[str] = []
        for term, df in doc_freqs.items():
            df_ratio = df / n_docs if n_docs > 0 else 0.0
            if df >= self.min_df and df_ratio <= self.max_df:
                filtered_terms.append(term)

        if self.max_features is not None and len(filtered_terms) > self.max_features:
            filtered_terms.sort(key=lambda t: (-term_freqs[t], t))
            filtered_terms = filtered_terms[: self.max_features]
        else:
            filtered_terms.sort()

        self.feature_names_ = filtered_terms
        self.vocabulary_ = {term: idx for idx, term in enumerate(filtered_terms)}
        self.doc_frequencies_ = {term: doc_freqs[term] for term in filtered_terms}
        self.term_frequencies_ = {term: term_freqs[term] for term in filtered_terms}
        return self

    def transform_document(self, tokens: List[str]) -> Dict[int, Union[int, float]]:
        """Converte uma lista de tokens num vetor esparso {índice_vocabulário: frequência/valor}."""
        counts = Counter(tokens)
        doc_len = float(len(tokens)) if (self.normalize and tokens) else 1.0
        vec: Dict[int, Union[int, float]] = {}

        for term, count in counts.items():
            if term in self.vocabulary_:
                idx = self.vocabulary_[term]
                if self.binary:
                    vec[idx] = 1
                elif self.normalize:
                    vec[idx] = round(count / doc_len, 6)
                else:
                    vec[idx] = count

        return dict(sorted(vec.items()))

    def transform(self, raw_documents: List[List[str]]) -> List[Dict[int, Union[int, float]]]:
        """Converte múltiplos documentos em vetores esparsos."""
        return [self.transform_document(doc) for doc in raw_documents]

    def fit_transform(self, raw_documents: List[List[str]]) -> List[Dict[int, Union[int, float]]]:
        """Ajusta o vocabulário e transforma a coleção de documentos."""
        self.fit(raw_documents)
        return self.transform(raw_documents)

    def to_dense(self, sparse_vector: Dict[int, Union[int, float]]) -> List[Union[int, float]]:
        """Converte vetor esparso em denso de dimensão |V|."""
        dense: List[Union[int, float]] = [0.0 if self.normalize else 0] * len(self.feature_names_)
        for idx, val in sparse_vector.items():
            dense[idx] = val
        return dense


def cosine_similarity(
    vec1: Dict[int, Union[int, float]],
    vec2: Dict[int, Union[int, float]]
) -> float:
    """Calcula a similaridade de cosseno entre dois vetores esparsos."""
    common_keys = set(vec1.keys()) & set(vec2.keys())
    if not common_keys:
        return 0.0

    dot_product = sum(float(vec1[k]) * float(vec2[k]) for k in common_keys)
    norm1 = math.sqrt(sum(float(v) ** 2 for v in vec1.values()))
    norm2 = math.sqrt(sum(float(v) ** 2 for v in vec2.values()))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return dot_product / (norm1 * norm2)


def generate_bow_dataset(processed_dir: Path) -> Dict[str, Any]:
    """Lê a etapa `06_without_stopwords.jsonl` e constrói a representação Bag of Words completa."""
    input_file = processed_dir / "06_without_stopwords.jsonl"
    if not input_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_file}")

    documents_data: List[Dict[str, Any]] = []
    with input_file.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                documents_data.append(json.loads(line))

    raw_docs = [doc["tokens"] for doc in documents_data]
    vectorizer = BagOfWordsVectorizer(binary=False, normalize=False)
    sparse_vectors = vectorizer.fit_transform(raw_docs)

    vocab_size = len(vectorizer.feature_names_)
    num_docs = len(documents_data)

    total_elements = vocab_size * num_docs
    non_zero_elements = sum(len(v) for v in sparse_vectors)
    sparsity = (1.0 - (non_zero_elements / total_elements)) * 100.0 if total_elements > 0 else 0.0

    documents_result = []
    for doc, vec in zip(documents_data, sparse_vectors):
        # Mapeamento do vetor por índice e por termo legível para inspeção
        vector_named = {vectorizer.feature_names_[idx]: val for idx, val in vec.items()}
        documents_result.append({
            "id": doc["id"],
            "total_tokens": len(doc["tokens"]),
            "distinct_terms": len(vec),
            "vector_sparse_indices": vec,
            "vector_sparse_terms": vector_named,
        })

    vocabulary_details = [
        {
            "index": idx,
            "term": term,
            "doc_frequency": vectorizer.doc_frequencies_[term],
            "term_frequency": vectorizer.term_frequencies_[term],
        }
        for idx, term in enumerate(vectorizer.feature_names_)
    ]

    top_terms = sorted(
        vocabulary_details, key=lambda item: (-item["term_frequency"], item["term"])
    )[:20]

    result = {
        "vocabulary_size": vocab_size,
        "total_documents": num_docs,
        "total_elements_matrix": total_elements,
        "non_zero_elements": non_zero_elements,
        "sparsity_percent": round(sparsity, 4),
        "top_20_terms": top_terms,
        "vocabulary": vocabulary_details,
        "documents": documents_result,
    }

    return result
