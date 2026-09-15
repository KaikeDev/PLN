"""Registro dos métodos de representação (fábricas). Um método novo entra aqui sem alterar análises ou pipeline."""

from collections.abc import Mapping
from typing import Protocol

from app.vectors.config import ExperimentConfig, RepresentationSpec
from app.vectors.corpus import ProcessedCorpus
from app.vectors.embeddings import ContextualMethod, Word2VecMethod
from app.vectors.space import BOW, TFIDF, Representation


class Method(Protocol):
    name: str
    description: str
    input_kind: str
    requires_model: bool

    def build(self, spec: RepresentationSpec, corpus: ProcessedCorpus, config: ExperimentConfig) -> Representation: ...


METHODS: Mapping[str, Method] = {method.name: method for method in (BOW, TFIDF, Word2VecMethod(), ContextualMethod())}
