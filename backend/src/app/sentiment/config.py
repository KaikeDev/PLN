"""Configuração validada do experimento de sentimentos. Arquivos de entrada são dados, nunca código.

As representações usam o esquema da Etapa 2, e os parâmetros da regressão logística são os da classificação
(`ClassificationConfig`), para que a validação cruzada da classificação seja reaproveitada sem cópia.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.classification.config import ClassificationConfig
from app.representations.config import MAX_REPRESENTATIONS, MethodInfo, parse_representation
from app.shared.validation import read_config_json, require_int, require_number, require_object, require_unique

NEGATIVE, POSITIVE = 0, 1
LABEL_NAMES = ("negativo", "positivo")
MAX_RATING = 10


@dataclass(frozen=True)
class SentimentConfig:
    """Faixas de nota de cada polaridade, grade do Ridge para a nota e parâmetros comuns da classificação.

    Críticas com nota entre `negative_max` e `positive_min` (exclusive) ficam fora da polaridade, mas entram na
    previsão da nota.
    """

    classification: ClassificationConfig
    negative_max: float
    positive_min: float
    ridge_alphas: tuple[float, ...]

    def polarity(self, rating: float) -> int | None:
        """Polaridade da nota: negativa, positiva ou None (faixa do meio)."""
        if rating <= self.negative_max:
            return NEGATIVE
        if rating >= self.positive_min:
            return POSITIVE
        return None


def load_config(path: Path, methods: Mapping[str, MethodInfo]) -> SentimentConfig:
    """Lê e valida a configuração contra os métodos de representação disponíveis."""
    data = require_object(
        read_config_json(path),
        "configuração de sentimentos",
        required={
            "representations",
            "negative_max",
            "positive_min",
            "folds",
            "inner_folds",
            "random_state",
            "regularization_grid",
            "ridge_alphas",
            "min_df",
            "top_features",
            "error_examples",
        },
        optional={"description"},
    )
    items = data["representations"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_REPRESENTATIONS:
        raise ValueError(f"representations deve listar de 1 a {MAX_REPRESENTATIONS} representações")
    specs = tuple(parse_representation(item, methods) for item in items)
    require_unique([spec.name for spec in specs], "Nomes de representação repetidos")
    negative_max = require_number(data["negative_max"], "negative_max", 0, MAX_RATING)
    positive_min = require_number(data["positive_min"], "positive_min", 0, MAX_RATING)
    if negative_max >= positive_min:
        raise ValueError("negative_max deve ser menor que positive_min")
    grid, alphas = data["regularization_grid"], data["ridge_alphas"]
    if not isinstance(grid, list) or not 1 <= len(grid) <= 20:
        raise ValueError("regularization_grid deve listar de 1 a 20 valores de C")
    if not isinstance(alphas, list) or not 1 <= len(alphas) <= 20:
        raise ValueError("ridge_alphas deve listar de 1 a 20 valores de alfa")
    classification = ClassificationConfig(
        representations=specs,
        labels=(NEGATIVE, POSITIVE),
        folds=require_int(data["folds"], "folds", 2, 20),
        inner_folds=require_int(data["inner_folds"], "inner_folds", 2, 10),
        random_state=require_int(data["random_state"], "random_state", 0, 2**32 - 1),
        regularization_grid=tuple(sorted({require_number(c, "regularization_grid", 1e-8, 1e4) for c in grid})),
        min_df=require_int(data["min_df"], "min_df", 1, 1000),
        top_features=require_int(data["top_features"], "top_features", 1, 50),
        error_examples=require_int(data["error_examples"], "error_examples", 0, 50),
    )
    return SentimentConfig(
        classification=classification,
        negative_max=negative_max,
        positive_min=positive_min,
        ridge_alphas=tuple(sorted({require_number(a, "ridge_alphas", 1e-6, 1e6) for a in alphas})),
    )
