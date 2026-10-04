"""Métricas iguais para o Jev e para o classificador de referência, sobre os mesmos filmes.

Cada linha de previsão tem `gold` (gêneros do TMDB entre os avaliados) e, por método, `choice` (gênero principal) e
`labels` (probabilidade de cada gênero). Filmes em que o Jev falhou ficam fora de todas as métricas,
inclusive das do classificador de referência, para que os dois sejam medidos no mesmo conjunto.

- Choice: taxa de acerto (a opção está entre os gêneros do filme) em toda a amostra; acurácia,
  F1 macro e matriz de confusão só nos filmes de um gênero, que têm rótulo inequívoco.
- Rótulos (Noul ou regressão binária): ROC AUC por gênero, que não depende de limiar; precisão,
  revocação e F1 com o limiar configurado; e a fração de filmes com o conjunto de gêneros exato.
"""

from collections.abc import Sequence
from statistics import fmean

from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support, roc_auc_score

from app.representations.metrics import rounded

METHODS = ("jev", "tfidf_logreg")
LOW_CONFIDENCE_CASES = 5


def evaluate(rows: Sequence[dict], keys: Sequence[str], threshold: float) -> dict:
    """Métricas por método, confiança e coerência do Jev e concordância entre os métodos."""
    evaluated = [row for row in rows if row["jev"] is not None]
    if not evaluated:
        raise ValueError("Nenhum filme foi avaliado pelo Jev")
    gold = [set(row["gold"]) for row in evaluated]
    return {
        "films": len(rows),
        "evaluated": len(evaluated),
        "failed": len(rows) - len(evaluated),
        "single_genre": sum(len(labels) == 1 for labels in gold),
        "threshold": threshold,
        "methods": {
            method: {
                "choice": choice_metrics(gold, [row[method]["choice"] for row in evaluated], keys),
                "labels": label_metrics(gold, [row[method]["labels"] for row in evaluated], keys, threshold),
            }
            for method in METHODS
        },
        "choice_agreement": rounded(fmean(row["jev"]["choice"] == row["tfidf_logreg"]["choice"] for row in evaluated)),
        "jev_confidence": confidence_metrics(evaluated),
        "jev_consistency": consistency(evaluated, threshold),
    }


def choice_metrics(gold: Sequence[set[str]], predicted: Sequence[str], keys: Sequence[str]) -> dict:
    """Acerto em toda a amostra e métricas multiclasse nos filmes de um único gênero."""
    single = [(next(iter(labels)), choice) for labels, choice in zip(gold, predicted, strict=True) if len(labels) == 1]
    result: dict = {"hit_rate": rounded(fmean(choice in labels for labels, choice in zip(gold, predicted, strict=True)))}
    if not single:
        return result | {"accuracy": None, "macro_f1": None, "per_genre": {}, "confusion": None}
    y_true, y_pred = [label for label, _ in single], [choice for _, choice in single]
    precision, recall, f1, support = precision_recall_fscore_support(y_true, y_pred, labels=list(keys), zero_division=0)
    return result | {
        "accuracy": rounded(fmean(true == pred for true, pred in single)),
        "macro_f1": rounded(f1_score(y_true, y_pred, labels=list(keys), average="macro", zero_division=0)),
        "per_genre": {
            key: {"precision": rounded(p), "recall": rounded(r), "f1": rounded(f), "support": int(s)}
            for key, p, r, f, s in zip(keys, precision, recall, f1, support, strict=True)
        },
        "confusion": {"labels": list(keys), "matrix": confusion_matrix(y_true, y_pred, labels=list(keys)).tolist()},
    }


def label_metrics(gold: Sequence[set[str]], scores: Sequence[dict[str, float]], keys: Sequence[str], threshold: float) -> dict:
    """Métricas de uma decisão binária por gênero, como numa classificação com vários rótulos."""
    per_genre: dict[str, dict] = {}
    for key in keys:
        truth = [int(key in labels) for labels in gold]
        values = [score[key] for score in scores]
        decided = [int(value >= threshold) for value in values]
        precision, recall, f1, _ = precision_recall_fscore_support(truth, decided, average="binary", zero_division=0)
        per_genre[key] = {
            "auc": rounded(roc_auc_score(truth, values)) if 0 < sum(truth) < len(truth) else None,
            "precision": rounded(precision),
            "recall": rounded(recall),
            "f1": rounded(f1),
            "positives": sum(truth),
        }
    aucs = [row["auc"] for row in per_genre.values() if row["auc"] is not None]
    exact = [labels == {key for key in keys if score[key] >= threshold} for labels, score in zip(gold, scores, strict=True)]
    return {
        "per_genre": per_genre,
        "macro_auc": rounded(fmean(aucs)) if aucs else None,
        "macro_f1": rounded(fmean(row["f1"] for row in per_genre.values())),
        "exact_match": rounded(fmean(exact)),
    }


def confidence_metrics(rows: Sequence[dict]) -> dict:
    """Confiança média da Choice quando ela acerta e quando erra, e os casos mais ambíguos."""
    hits = [row["jev"]["confidence"] for row in rows if row["jev"]["choice"] in row["gold"] and row["jev"]["confidence"] is not None]
    misses = [row["jev"]["confidence"] for row in rows if row["jev"]["choice"] not in row["gold"] and row["jev"]["confidence"] is not None]
    known = [row for row in rows if row["jev"]["confidence"] is not None]
    lowest = sorted(known, key=lambda row: (row["jev"]["confidence"], row["id"]))[:LOW_CONFIDENCE_CASES]
    return {
        "mean_when_hit": rounded(fmean(hits)) if hits else None,
        "mean_when_miss": rounded(fmean(misses)) if misses else None,
        "lowest": [
            {
                "id": row["id"],
                "title": row["title"],
                "gold": row["gold"],
                "choice": row["jev"]["choice"],
                "confidence": row["jev"]["confidence"],
                "choice_probabilities": row["jev"]["choice_probabilities"],
            }
            for row in lowest
        ],
    }


def consistency(rows: Sequence[dict], threshold: float) -> dict:
    """Coerência entre as perguntas da mesma chamada: a Choice é o Noul mais alto e passa do limiar?"""
    return {
        "choice_is_top_noul": rounded(
            fmean(row["jev"]["choice"] == max(row["jev"]["labels"], key=row["jev"]["labels"].get) for row in rows)
        ),
        "choice_noul_above_threshold": rounded(fmean(row["jev"]["labels"][row["jev"]["choice"]] >= threshold for row in rows)),
    }
