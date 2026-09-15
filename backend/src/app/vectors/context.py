"""Dados compartilhados por todas as análises de um experimento."""

from dataclasses import dataclass

from app.vectors.config import ExperimentConfig, QuerySpec
from app.vectors.corpus import ProcessedCorpus
from app.vectors.space import LexicalSpace


@dataclass(frozen=True)
class AnalysisContext:
    """Corpus, configuração e consultas do experimento.

    `descriptor` é um TF-IDF de referência (sem stopwords) usado para descrever clusters com o mesmo
    vocabulário em qualquer representação, inclusive nas densas.
    """

    corpus: ProcessedCorpus
    config: ExperimentConfig
    descriptor: LexicalSpace
    queries: tuple[QuerySpec, ...] = ()

    @property
    def representation_names(self) -> list[str]:
        """Nomes das representações na ordem da configuração."""
        return [spec.name for spec in self.config.representations]
