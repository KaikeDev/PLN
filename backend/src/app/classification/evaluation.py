"""Validação cruzada, métricas e interpretação dos classificadores.

Tudo o que aprende com os dados de treino fica dentro da dobra: o vocabulário e o idf do BoW/TF-IDF,
a padronização dos vetores densos e a escolha da regularização `C` (por dobras internas) usam só as
sinopses de treino. Os vetores pré-treinados (word2vec e transformers) não usam rótulos nem estatísticas
do corpus, então são calculados uma vez.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import numpy as np
from sklearn.base import BaseEstimator, clone
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegressionCV
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, hamming_loss, log_loss, precision_recall_fscore_support
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.classification.config import ClassificationConfig
from app.classification.dataset import Task
from app.classification.grouping import agreement
from app.vectors.metrics import rounded
from app.vectors.space import LexicalSpace, Representation

BASELINE = "maioria"
LOGISTIC = "regressao_logistica"
THRESHOLD = 0.5
Folds = list[tuple[np.ndarray, np.ndarray]]


@dataclass(frozen=True)
class Features:
    """Entrada do classificador para todas as sinopses, na ordem do corpus.

    Representações lexicais entregam tokens e um vetorizador ainda não ajustado; densas entregam a
    matriz com norma L2 e um padronizador. `lexical` indica se os coeficientes são legíveis como termos.
    """

    data: list | np.ndarray
    prepare: Callable[[], BaseEstimator]
    lexical: bool

    def take(self, rows: np.ndarray) -> list | np.ndarray:
        """Linhas `rows`, na ordem dada."""
        if isinstance(self.data, np.ndarray):
            return self.data[rows]
        return [self.data[row] for row in rows]


def features(representation: Representation) -> Features:
    """Entrada do classificador para uma representação da Etapa 2."""
    if isinstance(representation, LexicalSpace):
        vectorizer = representation.vectorizer
        return Features([list(tokens) for tokens in representation.tokens], lambda: clone(vectorizer), True)
    return Features(np.asarray(representation.unit, dtype=np.float64), StandardScaler, False)


def constant_features(size: int) -> Features:
    """Entrada sem informação, para o classificador de referência que ignora o texto."""
    return Features(np.zeros((size, 1)), StandardScaler, False)


def estimator(model: str, task: Task, source: Features, config: ClassificationConfig) -> Pipeline:
    """Pipeline preparação → classificador; em multirrótulo, um classificador binário por gênero.

    A regressão logística escolhe `C` na grade configurada pela log loss em dobras internas estratificadas do
    próprio treino e depois é reajustada com todo o treino. A log loss avalia as probabilidades, que são usadas
    na decisão multirrótulo e na análise de incerteza; escolher por F1 favorecia regularização excessiva, que
    mantém o gênero mais provável mas achata as probabilidades.
    """
    classifier: BaseEstimator
    if model == BASELINE:
        classifier = DummyClassifier(strategy="prior")
    elif model == LOGISTIC:
        classifier = LogisticRegressionCV(
            Cs=list(config.regularization_grid),
            l1_ratios=(0.0,),
            cv=config.inner_folds,
            scoring=neg_log_loss_score,
            class_weight="balanced",
            max_iter=10000,
            use_legacy_attributes=False,
        )
    else:
        raise ValueError(f"Modelo desconhecido: {model!r}")
    if task.multilabel:
        classifier = OneVsRestClassifier(classifier)
    return Pipeline([("preparacao", source.prepare()), ("classificador", classifier)])


def splits(task: Task, folds: int, random_state: int) -> Folds:
    """Dobras em posições da tarefa, iguais para todas as representações e modelos.

    Multiclasse usa estratificação por gênero. Multirrótulo usa dobras embaralhadas simples: o
    scikit-learn não estratifica combinações de rótulos, e várias combinações têm menos filmes que dobras.
    """
    positions = np.arange(len(task.ids))
    iterator: Iterator
    if task.multilabel:
        iterator = KFold(folds, shuffle=True, random_state=random_state).split(positions)
    else:
        iterator = StratifiedKFold(folds, shuffle=True, random_state=random_state).split(positions, task.targets)
    return list(iterator)


def fold_of(task: Task, folds: Folds) -> list[int]:
    """Dobra de teste de cada posição da tarefa."""
    assignment = np.empty(len(task.ids), dtype=np.int64)
    for number, (_, test) in enumerate(folds):
        assignment[test] = number
    return assignment.tolist()


@dataclass(frozen=True)
class Validation:
    """Resultado da validação cruzada: probabilidades fora da dobra, F1 macro e `C` escolhido por dobra.

    Em multirrótulo, `chosen_c` tem um valor por gênero em cada dobra; na referência, fica vazio.
    """

    probabilities: np.ndarray
    fold_f1: list[float]
    chosen_c: list


def cross_validate(task: Task, source: Features, model: str, folds: Folds, config: ClassificationConfig) -> Validation:
    """Cada sinopse é prevista por um modelo que não a viu no treino."""
    data = source.take(task.rows)
    probabilities = np.zeros((len(task.ids), len(task.labels)), dtype=np.float64)
    fold_f1: list[float] = []
    chosen_c: list = []
    for train, test in folds:
        fitted = estimator(model, task, source, config).fit(_take(data, train), task.targets[train])
        probabilities[test] = fitted.predict_proba(_take(data, test))
        fold_f1.append(float(f1_score(task.targets[test], decide(task, probabilities[test]), average="macro", zero_division=0)))
        if model == LOGISTIC:
            classifier = fitted.named_steps["classificador"]
            chosen_c.append([float(e.C_) for e in classifier.estimators_] if task.multilabel else float(classifier.C_))
    return Validation(probabilities, fold_f1, chosen_c)


def decide(task: Task, probabilities: np.ndarray) -> np.ndarray:
    """Multiclasse: gênero mais provável. Multirrótulo: gêneros com probabilidade ≥ 0,5 e, no mínimo, o mais provável.

    Todo filme da tarefa multirrótulo tem ao menos um gênero; sem essa garantia, um filme poderia ficar sem nenhum.
    """
    if not task.multilabel:
        return probabilities.argmax(axis=1)
    chosen = (probabilities >= THRESHOLD).astype(np.int64)
    chosen[np.arange(len(chosen)), probabilities.argmax(axis=1)] = 1
    return chosen


def metrics(task: Task, validation: Validation) -> dict:
    """Métricas globais das previsões fora da dobra, métricas por gênero, variação entre dobras e `C` escolhido."""
    probabilities, fold_f1 = validation.probabilities, validation.fold_f1
    truth, predicted = task.targets, decide(task, probabilities)
    classes = list(range(len(task.labels)))
    precision, recall, f1, support = precision_recall_fscore_support(
        truth, predicted, labels=None if task.multilabel else classes, zero_division=0
    )
    result: dict = {
        "f1_macro": rounded(f1_score(truth, predicted, average="macro", zero_division=0)),
        "f1_micro": rounded(f1_score(truth, predicted, average="micro", zero_division=0)),
        "f1_macro_dobras": {
            "media": rounded(np.mean(fold_f1)),
            "desvio": rounded(np.std(fold_f1)),
            "valores": [rounded(value) for value in fold_f1],
        },
        "c_escolhido": validation.chosen_c,
        "por_genero": {
            name: {"precisao": rounded(p), "revocacao": rounded(r), "f1": rounded(f), "suporte": int(s)}
            for name, p, r, f, s in zip(task.label_names, precision, recall, f1, support, strict=True)
        },
    }
    if task.multilabel:
        return result | {
            "acuracia_exata": rounded(accuracy_score(truth, predicted)),
            "hamming": rounded(hamming_loss(truth, predicted)),
            "rotulos_por_filme": {"real": rounded(truth.sum(axis=1).mean()), "previsto": rounded(predicted.sum(axis=1).mean())},
        }
    confidence = probabilities.max(axis=1)
    correct = predicted == truth
    return result | {
        "acuracia": rounded(accuracy_score(truth, predicted)),
        **agreement(truth, predicted),
        "log_loss": rounded(log_loss(truth, probabilities, labels=classes)),
        "confianca_media": {
            "acertos": rounded(confidence[correct].mean()) if correct.any() else None,
            "erros": rounded(confidence[~correct].mean()) if (~correct).any() else None,
        },
        "matriz_confusao": confusion_matrix(truth, predicted, labels=classes).tolist(),
    }


def prediction_rows(task: Task, probabilities: np.ndarray, titles: dict[int, str], fold: list[int]) -> list[dict]:
    """Uma linha por sinopse: dobra de teste, gêneros reais e previstos e a probabilidade de cada gênero."""
    predicted = decide(task, probabilities)
    rows = []
    for position, movie_id in enumerate(task.ids):
        if task.multilabel:
            real = [task.label_names[i] for i in np.flatnonzero(task.targets[position])]
            guess = [task.label_names[i] for i in np.flatnonzero(predicted[position])]
        else:
            real, guess = [task.label_names[task.targets[position]]], [task.label_names[predicted[position]]]
        rows.append(
            {
                "id": movie_id,
                "title": titles[movie_id],
                "dobra": fold[position],
                "real": real,
                "previsto": guess,
                "acertou": real == guess,
                "probabilidades": {name: rounded(p, 4) for name, p in zip(task.label_names, probabilities[position], strict=True)},
            }
        )
    return rows


def confident_errors(rows: list[dict], limit: int) -> list[dict]:
    """Erros com maior probabilidade atribuída ao gênero previsto: onde o modelo errou com mais convicção."""
    wrong = [row for row in rows if not row["acertou"]]
    wrong.sort(key=lambda row: (-max(row["probabilidades"].values()), row["id"]))
    return wrong[:limit]


def top_terms(task: Task, source: Features, config: ClassificationConfig) -> dict[str, list[list]]:
    """Termos de maior coeficiente por gênero, num modelo ajustado com todas as sinopses da tarefa multiclasse.

    Serve para interpretar o modelo, não para avaliá-lo: as métricas vêm da validação cruzada.
    """
    fitted = estimator(LOGISTIC, task, source, config).fit(source.take(task.rows), task.targets)
    terms = fitted.named_steps["preparacao"].get_feature_names_out()
    coefficients = fitted.named_steps["classificador"].coef_
    if len(coefficients) == 1:
        coefficients = np.vstack([-coefficients[0], coefficients[0]])
    result = {}
    for name, weights in zip(task.label_names, coefficients, strict=True):
        order = np.lexsort((terms, -weights))[: config.top_features]
        result[name] = [[str(terms[column]), rounded(weights[column], 4)] for column in order]
    return result


def f1_macro_score(model: BaseEstimator, x: np.ndarray, y: np.ndarray) -> float:
    """F1 macro das dobras internas, como função e não como nome: com o nome, o scikit-learn 1.9 falha em problemas binários."""
    return float(f1_score(y, model.predict(x), average="macro", zero_division=0))


def neg_log_loss_score(model: BaseEstimator, x: np.ndarray, y: np.ndarray) -> float:
    """Log loss negativa (maior = melhor) das dobras internas, como função pelo mesmo motivo de `f1_macro_score`."""
    return -float(log_loss(y, model.predict_proba(x), labels=model.classes_))


def _take(data: list | np.ndarray, positions: np.ndarray) -> list | np.ndarray:
    if isinstance(data, np.ndarray):
        return data[positions]
    return [data[position] for position in positions]
