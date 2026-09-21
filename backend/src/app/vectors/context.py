"""Dados compartilhados por todas as análises de um experimento."""

from dataclasses import dataclass, field

from app.vectors.config import ExperimentConfig, QuerySpec
from app.vectors.corpus import ProcessedCorpus
from app.vectors.probes import ProbeSet
from app.vectors.space import LexicalSpace


@dataclass(frozen=True)
class AnalysisContext:
    """Corpus, configuração, consultas e sondas linguísticas do experimento.

    `descriptor` é um TF-IDF de referência (sem stopwords) usado para descrever clusters com o mesmo
    vocabulário em qualquer representação, inclusive nas densas. `probes` reúne os exemplos da Aula 7
    (pares de frases, pares de palavras e sentidos de palavras polissêmicas); vazio quando não informado.
    """

    corpus: ProcessedCorpus
    config: ExperimentConfig
    descriptor: LexicalSpace
    queries: tuple[QuerySpec, ...] = ()
    probes: ProbeSet = field(default_factory=ProbeSet)

    @property
    def representation_names(self) -> list[str]:
        """Nomes das representações na ordem da configuração."""
        return [spec.name for spec in self.config.representations]
