"""Outros classificadores na tarefa multiclasse: mesmas dobras externas, mesma preparação e ajuste interno próprio.

A regressão logística é o classificador principal (ADR 0017). Estes existem para justificar a escolha com
medidas no mesmo conjunto de avaliação, como pede a Aula 8, e não só com argumentos. Cada um escolhe o
próprio hiperparâmetro em dobras internas do treino, como a regressão logística escolhe `C`; a floresta
aleatória usa parâmetros fixos. Só se comparam métricas do gênero previsto, porque o SVM linear não
produz probabilidades.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GridSearchCV
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from app.classification.config import ClassificationConfig
from app.classification.dataset import Task
from app.classification.evaluation import Features, Folds, f1_macro_score
from app.representations.metrics import rounded

NAIVE_BAYES_ALPHAS = [0.001, 0.01, 0.1, 0.5, 1.0]
NEIGHBORS = [1, 5, 9, 15, 25, 35, 51, 75]
TREES = 300


@dataclass(frozen=True)
class Alternative:
    """Classificador alternativo: nome no relatório, fábrica e se exige atributos não negativos.

    O Naive Bayes multinomial modela contagens; aceita BoW e TF-IDF, mas não vetores densos padronizados,
    que têm valores negativos.
    """

    label: str
    make: Callable[[ClassificationConfig], BaseEstimator]
    lexical_only: bool = False


def _tuned(model: BaseEstimator, grid: dict[str, list], config: ClassificationConfig) -> GridSearchCV:
    return GridSearchCV(model, grid, cv=config.inner_folds, scoring=f1_macro_score)


ALTERNATIVES: dict[str, Alternative] = {
    "naive_bayes": Alternative(
        "Naive Bayes multinomial", lambda config: _tuned(MultinomialNB(), {"alpha": NAIVE_BAYES_ALPHAS}, config), lexical_only=True
    ),
    "svm_linear": Alternative(
        "SVM linear",
        lambda config: _tuned(LinearSVC(class_weight="balanced", max_iter=20000), {"C": list(config.regularization_grid)}, config),
    ),
    "floresta_aleatoria": Alternative(
        "Floresta aleatória",
        lambda config: RandomForestClassifier(n_estimators=TREES, class_weight="balanced", random_state=config.random_state),
    ),
    "knn": Alternative(
        "k vizinhos (cosseno)", lambda config: _tuned(KNeighborsClassifier(metric="cosine"), {"n_neighbors": NEIGHBORS}, config)
    ),
}


def compare(task: Task, source: Features, folds: Folds, config: ClassificationConfig) -> tuple[dict[str, dict | None], dict[str, float]]:
    """Métricas de cada alternativa configurada (None quando não se aplica à representação) e os segundos gastos.

    Os segundos vão só para o manifesto, porque variam entre execuções.
    """
    results: dict[str, dict | None] = {}
    seconds: dict[str, float] = {}
    for name in config.alternatives:
        alternative = ALTERNATIVES[name]
        if alternative.lexical_only and not source.lexical:
            results[name] = None
            continue
        started = time.perf_counter()
        predicted = np.zeros(len(task.ids), dtype=np.int64)
        fold_f1: list[float] = []
        chosen: list[dict | None] = []
        for train, test in folds:
            model = Pipeline([("preparacao", source.prepare()), ("classificador", alternative.make(config))])
            model.fit(source.take(task.rows[train]), task.targets[train])
            predicted[test] = model.predict(source.take(task.rows[test]))
            fold_f1.append(float(f1_score(task.targets[test], predicted[test], average="macro", zero_division=0)))
            chosen.append(getattr(model.named_steps["classificador"], "best_params_", None))
        seconds[name] = round(time.perf_counter() - started, 3)
        per_genre = f1_score(task.targets, predicted, labels=list(range(len(task.labels))), average=None, zero_division=0)
        results[name] = {
            "acuracia": rounded(accuracy_score(task.targets, predicted)),
            "f1_macro": rounded(f1_score(task.targets, predicted, average="macro", zero_division=0)),
            "f1_macro_dobras": {"media": rounded(np.mean(fold_f1)), "desvio": rounded(np.std(fold_f1))},
            "f1_por_genero": {genre: rounded(value) for genre, value in zip(task.label_names, per_genre, strict=True)},
            "parametro_escolhido": chosen,
        }
    return results, seconds
