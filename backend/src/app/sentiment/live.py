"""Análise de sentimento de textos avulsos, usada pela tela do site (ADR 0026).

Ajusta os mesmos modelos avaliados no experimento (regressão logística para a polaridade e Ridge para a
nota) com todas as críticas preparadas, numa representação da configuração. A qualidade esperada é a
medida por validação cruzada em `data/sentimento`; aqui os modelos só são ajustados para uso.

O texto passa pela mesma limpeza das críticas (`app.corpus.transform`), com até `MAX_TEXT_CHARS` caracteres,
sem o limite curto das consultas de busca: uma crítica tem em média 2 mil caracteres. Com BoW ou TF-IDF, a
resposta também traz as palavras do texto que mais empurraram para cada polaridade.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import normalize

from app.classification.evaluation import LOGISTIC, estimator, features
from app.corpus.transform import representations
from app.representations.corpus import ProcessedCorpus
from app.representations.embeddings import ContextualSpace
from app.representations.space import LexicalSpace, Representation
from app.sentiment.config import LABEL_NAMES, POSITIVE, SentimentConfig, load_config
from app.sentiment.encoders import long_text_methods
from app.sentiment.evaluation import MAX_RATING
from app.shared.artifacts import read_jsonl

MAX_TEXT_CHARS = 5000
MAX_TERMS = 6


@dataclass(frozen=True)
class SentimentResult:
    """Polaridade prevista, probabilidade de ser positiva, nota prevista (0–10) e palavras que mais pesaram."""

    polarity: str
    positive_probability: float
    rating: float
    positive_terms: tuple[tuple[str, float], ...] = ()
    negative_terms: tuple[tuple[str, float], ...] = ()


class SentimentAnalyzer:
    """Polaridade e nota de um texto livre, com uma representação lexical ou contextual."""

    def __init__(self, corpus: ProcessedCorpus, representation: Representation, ratings: np.ndarray, config: SentimentConfig) -> None:
        if not isinstance(representation, LexicalSpace | ContextualSpace):
            raise ValueError("A tela de sentimento usa BoW, TF-IDF ou um transformer")
        labels = [config.polarity(float(rating)) for rating in ratings]
        rows = np.array([row for row, label in enumerate(labels) if label is not None], dtype=np.int64)
        targets = np.array([labels[row] for row in rows], dtype=np.int64)
        from app.classification.dataset import Task

        task = Task("polaridade", (0, 1), LABEL_NAMES, rows, tuple(corpus.ids[row] for row in rows), targets)
        source = features(representation)
        common = config.classification
        self._polarity = estimator(LOGISTIC, task, source, common).fit(source.take(rows), targets)
        self._rating = Pipeline([("preparacao", source.prepare()), ("regressao", RidgeCV(alphas=list(config.ridge_alphas)))])
        self._rating.fit(source.data, ratings)
        self._representation = representation
        self._stopwords = set(corpus.stopwords)
        self.representation_name = representation.spec.name
        self.training_size = len(rows)

    @classmethod
    def load(cls, processed: Path, config_path: Path, name: str) -> SentimentAnalyzer:
        """Constrói a representação `name` da configuração sobre as críticas preparadas e ajusta os modelos."""
        methods = long_text_methods()
        config = load_config(config_path, methods)
        specs = {spec.name: spec for spec in config.classification.representations}
        if name not in specs:
            raise ValueError(f"Representação {name!r} ausente de {config_path.name}")
        corpus = ProcessedCorpus.load(processed)
        metadata = {row["id"]: row for row in read_jsonl(processed / "metadata.jsonl")}
        ratings = np.array([metadata[review_id]["rating"] for review_id in corpus.ids], dtype=np.float64)
        spec = specs[name]
        representation = methods[spec.method].build(spec, corpus, config.classification.vector_config())
        return cls(corpus, representation, ratings, config)

    def analyze(self, text: str) -> SentimentResult:
        """Polaridade e nota do texto; `ValueError` para texto vazio, longo demais ou sem palavras conhecidas."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Digite um texto")
        if len(text) > MAX_TEXT_CHARS:
            raise ValueError(f"O texto excede {MAX_TEXT_CHARS} caracteres")
        stages: dict = dict(representations(text, self._stopwords))
        spec = self._representation.spec
        if isinstance(self._representation, LexicalSpace):
            entry: list | np.ndarray = [stages[spec.stage_key]]
            if not self._polarity.named_steps["preparacao"].transform(entry).nnz:
                raise ValueError("O texto não tem palavras que o modelo conheça")
        else:
            entry = normalize(np.asarray(self._representation.encoder.encode([stages[spec.stage_key]]), dtype=np.float64))
        probability = float(self._polarity.predict_proba(entry)[0][list(self._polarity.classes_).index(POSITIVE)])
        rating = float(np.clip(self._rating.predict(entry)[0], 0, MAX_RATING))
        positive, negative = self._terms(entry) if isinstance(self._representation, LexicalSpace) else ((), ())
        return SentimentResult(
            LABEL_NAMES[POSITIVE] if probability >= 0.5 else LABEL_NAMES[1 - POSITIVE],
            round(probability, 4),
            round(rating, 2),
            positive,
            negative,
        )

    def _terms(self, entry: list | np.ndarray) -> tuple[tuple[tuple[str, float], ...], tuple[tuple[str, float], ...]]:
        """Palavras do texto com maior contribuição (peso × valor) para cada polaridade."""
        vectorizer = self._polarity.named_steps["preparacao"]
        weights = self._polarity.named_steps["classificador"].coef_[0]
        if list(self._polarity.classes_).index(POSITIVE) == 0:
            weights = -weights
        row = vectorizer.transform(entry).tocoo()
        terms = vectorizer.get_feature_names_out()
        contributions = sorted(
            ((str(terms[column]), float(value * weights[column])) for column, value in zip(row.col, row.data, strict=True)),
            key=lambda item: item[1],
        )
        positive = tuple((term, round(score, 4)) for term, score in reversed(contributions[-MAX_TERMS:]) if score > 0)
        negative = tuple((term, round(score, 4)) for term, score in contributions[:MAX_TERMS] if score < 0)
        return positive, negative
