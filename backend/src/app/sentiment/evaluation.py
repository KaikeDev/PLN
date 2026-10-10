"""Dobras por filme, teste entre autores, previsão da nota e recortes de análise do experimento de sentimentos.

A polaridade usa a validação cruzada da classificação (`app.classification.evaluation`). O que muda aqui:

- **Dobras por filme:** críticas de um mesmo filme ficam sempre na mesma dobra. Sem isso, o modelo poderia
  acertar pelo nome ou pelo elenco de um filme muito elogiado, e não pelo sentimento do texto.
- **Entre autores:** um autor escreveu dois terços das críticas, e agrupar por autor deixaria uma dobra com
  quase todos os dados. Por isso, à parte, o modelo é treinado sem esse autor e testado nele, e o contrário.
- **Nota:** regressão Ridge sobre a mesma entrada, com o alfa escolhido por validação interna do próprio
  treino; a nota prevista é limitada a 0–10. A referência prevê a média das notas do treino.
"""

from collections.abc import Sequence

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import RidgeCV
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline

from app.classification.config import ClassificationConfig
from app.classification.dataset import Task
from app.classification.evaluation import LOGISTIC, Features, Folds, estimator
from app.representations.metrics import rounded

MAX_RATING = 10.0
CLOSE_ENOUGH = 1.0


def grouped_folds(targets: np.ndarray, groups: Sequence[str], folds: int, random_state: int) -> Folds:
    """Dobras estratificadas pelo alvo em que nenhum grupo (filme) aparece em mais de uma dobra."""
    positions = np.arange(len(targets))
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=random_state)
    return list(splitter.split(positions, targets, np.asarray(groups)))


def predict_ratings(
    source: Features, rows: np.ndarray, ratings: np.ndarray, folds: Folds, alphas: Sequence[float]
) -> tuple[np.ndarray, list[float]]:
    """Nota prevista fora da dobra para cada linha e o alfa escolhido em cada dobra."""
    data = source.take(rows)
    predicted = np.zeros(len(rows))
    chosen = []
    for train, test in folds:
        model = Pipeline([("preparacao", source.prepare()), ("regressao", RidgeCV(alphas=list(alphas)))])
        model.fit(_take(data, train), ratings[train])
        predicted[test] = np.clip(model.predict(_take(data, test)), 0, MAX_RATING)
        chosen.append(float(model.named_steps["regressao"].alpha_))
    return predicted, chosen


def mean_baseline(ratings: np.ndarray, folds: Folds) -> np.ndarray:
    """Referência: a média das notas do treino de cada dobra."""
    predicted = np.zeros(len(ratings))
    for train, test in folds:
        predicted[test] = ratings[train].mean()
    return predicted


def rating_metrics(truth: np.ndarray, predicted: np.ndarray, folds: Folds, alphas: list[float] | None = None) -> dict:
    """Erro absoluto médio, raiz do erro quadrático, correlação de Spearman e parcela a até 1 ponto da nota real."""
    error = np.abs(truth - predicted)
    correlation = spearmanr(truth, predicted).statistic if np.ptp(predicted) > 0 else float("nan")
    return {
        "erro_absoluto_medio": rounded(error.mean()),
        "raiz_erro_quadratico": rounded(np.sqrt(((truth - predicted) ** 2).mean())),
        "spearman": None if np.isnan(correlation) else rounded(correlation),
        "ate_1_ponto": rounded((error <= CLOSE_ENOUGH).mean()),
        "erro_absoluto_dobras": [rounded(error[test].mean()) for _, test in folds],
        "alfa_escolhido": alphas or [],
    }


def across_authors(task: Task, source: Features, main_author: np.ndarray, config: ClassificationConfig) -> dict:
    """F1 macro e acurácia treinando sem o autor principal e testando nele, e o contrário."""
    data = source.take(task.rows)
    result = {}
    for name, train, test in (
        ("treino_sem_autor_principal", ~main_author, main_author),
        ("treino_so_autor_principal", main_author, ~main_author),
    ):
        fitted = estimator(LOGISTIC, task, source, config).fit(_take(data, np.flatnonzero(train)), task.targets[train])
        predicted = fitted.predict(_take(data, np.flatnonzero(test)))
        truth = task.targets[test]
        result[name] = {
            "treino": int(train.sum()),
            "teste": int(test.sum()),
            "f1_macro": rounded(f1_score(truth, predicted, average="macro", zero_division=0)),
            "acuracia": rounded(accuracy_score(truth, predicted)),
        }
    return result


def subset_accuracy(correct: np.ndarray, mask: np.ndarray) -> dict:
    """Acurácia dentro e fora de um recorte (por exemplo, críticas com negação)."""
    return {
        "com": {"criticas": int(mask.sum()), "acuracia": rounded(correct[mask].mean()) if mask.any() else None},
        "sem": {"criticas": int((~mask).sum()), "acuracia": rounded(correct[~mask].mean()) if (~mask).any() else None},
    }


def _take(data: list | np.ndarray, positions: np.ndarray) -> list | np.ndarray:
    if isinstance(data, np.ndarray):
        return data[positions]
    return [data[position] for position in positions]
