"""Classificador de gênero para textos avulsos, usado pela tela do site (ADR 0021).

Ajusta a mesma regressão logística avaliada na Etapa 3 (`estimator`: padronização, `C` escolhido pela
log loss em dobras internas e classes balanceadas) com todas as sinopses da tarefa multiclasse, numa
representação densa já construída. A qualidade esperada é a medida por validação cruzada em
`data/classificacao`; aqui o modelo só é ajustado para uso.

Textos acima de `MAX_QUERY_CHARS` são cortados no último espaço antes do limite: o modelo de sentença já
trunca a entrada em 128 tokens, de tamanho parecido, então o corte quase não muda a previsão.
"""

import numpy as np

from app.classification.config import ClassificationConfig
from app.classification.dataset import make_tasks
from app.classification.evaluation import LOGISTIC, estimator, features
from app.representations.config import MAX_QUERY_CHARS
from app.representations.corpus import ProcessedCorpus
from app.representations.space import LexicalSpace, Representation


class GenreClassifier:
    """Regressão logística multiclasse sobre uma representação densa das sinopses."""

    def __init__(self, corpus: ProcessedCorpus, representation: Representation, config: ClassificationConfig) -> None:
        if isinstance(representation, LexicalSpace):
            raise ValueError("A tela de classificação usa uma representação densa")
        task, _ = make_tasks(corpus, config.labels, config.inner_folds)
        source = features(representation)
        self._model = estimator(LOGISTIC, task, source, config).fit(source.take(task.rows), task.targets)
        self._names = task.label_names
        self._corpus = corpus
        self._representation = representation
        self.representation_name = representation.spec.name
        self.training_size = len(task.rows)

    def classify(self, text: str) -> list[tuple[str, float]]:
        """Pares (gênero, probabilidade) do mais ao menos provável; `ValueError` para texto inválido."""
        encoded = self._representation.encode(_truncate(text), self._corpus)
        if encoded.null:
            raise ValueError("O texto não tem palavras que a representação conheça")
        probabilities = self._model.predict_proba(np.asarray(encoded.vector, dtype=np.float64))[0]
        classes = [int(label) for label in self._model.classes_]
        result = [(self._names[label], round(float(probability), 4)) for label, probability in zip(classes, probabilities, strict=True)]
        return sorted(result, key=lambda item: (-item[1], item[0]))


def _truncate(text: str) -> str:
    if len(text) <= MAX_QUERY_CHARS:
        return text
    cut = text[:MAX_QUERY_CHARS]
    return cut[: cut.rfind(" ")] if " " in cut else cut
