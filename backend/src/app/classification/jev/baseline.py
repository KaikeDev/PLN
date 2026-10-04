"""Classificador de referência: TF-IDF + regressão logística, treinado com os filmes fora da amostra.

É o pipeline clássico da Aula 8 (textos rotulados → TF-IDF → treino → previsão). Produz as mesmas
duas saídas que o Jev, para que as métricas sejam idênticas:

- `choice`: regressão logística multinomial treinada só com filmes de um gênero avaliado;
- `labels`: uma regressão logística binária por gênero (um contra os demais), com classes
  balanceadas, treinada com todos os filmes fora da amostra — equivale aos Nouls.

Nenhum filme da amostra entra no treino nem no vocabulário do TF-IDF.
"""

from collections.abc import Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from app.classification.jev.config import JevConfig
from app.representations.corpus import Document, ProcessedCorpus
from app.representations.metrics import rounded
from app.representations.space import pretokenized

MAX_ITERATIONS = 1000


def baseline_predictions(corpus: ProcessedCorpus, config: JevConfig, sample: Sequence[Document]) -> dict[int, dict]:
    """Previsão de cada filme da amostra, por ID: `{"choice", "choice_probabilities", "confidence", "labels"}`."""
    sample_ids = {document.id for document in sample}
    tokens = dict(zip(corpus.ids, corpus.tokens(config.baseline_stage), strict=True))
    train = [document for document in corpus.documents if document.id not in sample_ids and config.gold(document)]
    vectorizer = TfidfVectorizer(analyzer=pretokenized, min_df=config.baseline_min_df)
    x_train = vectorizer.fit_transform([tokens[document.id] for document in train])
    x_test = vectorizer.transform([tokens[document.id] for document in sample])

    single = [index for index, document in enumerate(train) if len(config.gold(document)) == 1]
    choice_model = LogisticRegression(C=config.baseline_c, max_iter=MAX_ITERATIONS)
    choice_model.fit(x_train[single], [config.gold(train[index])[0] for index in single])
    classes = [str(label) for label in choice_model.classes_]
    choice_probabilities = choice_model.predict_proba(x_test)

    labels: dict[str, np.ndarray] = {}
    for key in config.keys:
        target = [key in config.gold(document) for document in train]
        model = LogisticRegression(C=config.baseline_c, max_iter=MAX_ITERATIONS, class_weight="balanced").fit(x_train, target)
        labels[key] = model.predict_proba(x_test)[:, list(model.classes_).index(True)]

    predictions: dict[int, dict] = {}
    for row, document in enumerate(sample):
        probabilities = dict(zip(classes, choice_probabilities[row], strict=True))
        predictions[document.id] = {
            "choice": classes[int(np.argmax(choice_probabilities[row]))],
            "choice_probabilities": {key: rounded(probabilities.get(key, 0.0)) for key in config.keys},
            "confidence": None,
            "labels": {key: rounded(labels[key][row]) for key in config.keys},
        }
    return predictions
