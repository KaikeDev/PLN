"""Análises próprias das representações: dimensões, sondas da Aula 7 e síntese comparativa.

`Analysis` é a estratégia comum; as análises das tarefas ficam nos pacotes `app.search`,
`app.recommendation` e `app.clustering`, e o pipeline as reúne em `DEFAULT_ANALYSES`.
"""

from abc import ABC, abstractmethod
from itertools import combinations
from statistics import mean

import numpy as np
from scipy.sparse import issparse

from app.representations import report
from app.representations.context import AnalysisContext
from app.representations.metrics import rounded
from app.representations.space import Representation, count_nonzero, encoded_cosine


class Analysis(ABC):
    """Estratégia de análise: incluir uma nova análise não exige alterar o pipeline nem o relatório."""

    name: str

    @abstractmethod
    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        """Resultado serializável em JSON da análise sobre uma representação."""

    @abstractmethod
    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        """Linhas Markdown da seção do relatório, a partir dos resultados de todas as representações."""

    def artifacts(self, representation: Representation, result: dict, context: AnalysisContext) -> dict[str, str]:
        """Arquivos textuais extras. Os nomes derivam de nomes de representação já validados."""
        return {}


class Dimensions(Analysis):
    """Tamanho, esparsidade e resumo específico de cada representação."""

    name = "dimensions"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.dimensions_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        matrix, spec = representation.matrix, representation.spec
        documents, dimensions = matrix.shape
        nonzero = count_nonzero(matrix)
        return {
            "method": spec.method,
            "stage": spec.stage,
            "documents": documents,
            "dimensions": dimensions,
            "sparse": issparse(matrix),
            "nonzero": nonzero,
            "density": rounded(nonzero / (documents * dimensions)),
            "mean_nonzero_per_document": rounded(nonzero / documents),
            **representation.summary(context.config),
        }


class WordNeighbors(Analysis):
    """Palavras do corpus mais próximas de cada palavra de sondagem, quando há vetores por palavra."""

    name = "word_neighbors"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.word_neighbors_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        if not representation.supports_words:
            return {"supported": False}
        limit = context.config.top_terms
        pairs = [[left, right, _optional_round(representation.word_similarity(left, right))] for left, right in context.probes.word_pairs]
        return {
            "supported": True,
            "words": {word: representation.nearest_words(word, limit) for word in context.config.probe_words},
            "pairs": pairs,
        }


class SentencePairs(Analysis):
    """Cosseno entre pares de frases da aula: paráfrases sem palavras em comum e frases que só compartilham uma palavra polissêmica.

    Cada frase passa pelas mesmas regras de preparação da entrada da representação. A explicação usa
    `Representation.explain` (termos idênticos, pares de palavras próximas ou nada, conforme a família).
    """

    name = "sentence_pairs"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.sentence_pairs_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        pairs = []
        for pair in context.probes.sentence_pairs:
            left, right = representation.encode(pair.left, context.corpus), representation.encode(pair.right, context.corpus)
            pairs.append(
                {
                    "id": pair.id,
                    "expected": pair.expected,
                    "cosine": rounded(encoded_cosine(left, right)),
                    "null_vector": left.null or right.null,
                    "out_of_vocabulary": sorted(set(left.out_of_vocabulary) | set(right.out_of_vocabulary)),
                    "explanation": representation.explain(left, right, 5),
                }
            )
        return {"pairs": pairs}


class WordSenses(Analysis):
    """Polissemia: cosseno entre os vetores de uma mesma palavra em frases com sentidos iguais e diferentes.

    Em representações estáticas o vetor não muda com a frase, então a diferença entre os dois grupos é
    zero; em representações contextuais espera-se cosseno maior dentro do mesmo sentido.
    """

    name = "word_senses"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.word_senses_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        if not representation.supports_word_in_context:
            return {"supported": False}
        words = []
        for item in context.probes.word_senses:
            vectors = [representation.word_in_context(entry.text, item.word) for entry in item.contexts]
            if any(vector is None for vector in vectors):
                words.append({"id": item.id, "word": item.word, "found": False})
                continue
            matrix = np.vstack([vector for vector in vectors if vector is not None])
            similarity = matrix @ matrix.T
            same: list[float] = []
            different: list[float] = []
            for i, j in combinations(range(len(item.contexts)), 2):
                (same if item.contexts[i].sense == item.contexts[j].sense else different).append(float(similarity[i, j]))
            same_mean, different_mean = mean(same) if same else None, mean(different)
            words.append(
                {
                    "id": item.id,
                    "word": item.word,
                    "found": True,
                    "senses": [entry.sense for entry in item.contexts],
                    "similarity": [[rounded(value, 4) for value in row] for row in similarity.tolist()],
                    "same_sense_mean": _optional_round(same_mean),
                    "different_sense_mean": rounded(different_mean),
                    "gap": _optional_round(same_mean - different_mean if same_mean is not None else None),
                }
            )
        return {"supported": True, "family": representation.family, "words": words}


class Synthesis(Analysis):
    """Propriedades de cada representação para a síntese comparativa da aula: informação, custo e interpretabilidade."""

    name = "synthesis"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.synthesis_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        return {
            "family": representation.family,
            "sparse": issparse(representation.matrix),
            "dimensions": representation.dimensions,
            "dimensions_are_vocabulary": representation.family == "lexical",
            "learned": representation.learned,
            "word_depends_on_context": representation.family == "contextual",
            "interpretable_by_words": representation.family != "contextual",
            "parameters": representation.parameters(),
            "model": representation.spec.model,
        }


def _optional_round(value: float | None) -> float | None:
    return None if value is None else rounded(value)
