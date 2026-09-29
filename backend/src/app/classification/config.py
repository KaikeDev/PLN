"""Configuração validada do experimento de classificação. Arquivos de entrada são dados, nunca código.

As representações usam o mesmo esquema e a mesma validação da Etapa 2 (`app.vectors.config`), de modo
que um nome de representação significa a mesma coisa nos dois experimentos.
"""

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from pathlib import Path

from app.shared.validation import read_config_json, require_ids, require_int, require_number, require_object, require_unique
from app.vectors.config import MAX_REPRESENTATIONS, ExperimentConfig, MethodInfo, RepresentationSpec, parse_representation

DEFAULTS = {
    "folds": 5,
    "inner_folds": 3,
    "random_state": 42,
    "regularization_grid": [1e-6, 1e-5, 1e-4, 1e-3, 0.01, 0.1, 1, 10, 100, 1000, 10000],
    "min_df": 1,
    "top_features": 10,
    "error_examples": 5,
    "alternatives": [],
}


@dataclass(frozen=True)
class ClassificationConfig:
    """Rótulos, representações e parâmetros da validação cruzada.

    `labels` são IDs de gênero do TMDB; `folds` é o número de dobras externas, as mesmas para todas as
    representações. `regularization_grid` lista os valores de `C` da regressão logística (maior = menos
    regularização), escolhidos em `inner_folds` dobras internas feitas só com as sinopses de treino.
    `alternatives` lista outros classificadores avaliados na tarefa multiclasse, para comparação.
    """

    representations: tuple[RepresentationSpec, ...]
    labels: tuple[int, ...]
    folds: int
    inner_folds: int
    random_state: int
    regularization_grid: tuple[float, ...]
    min_df: int
    top_features: int
    error_examples: int
    alternatives: tuple[str, ...] = ()

    def vector_config(self) -> ExperimentConfig:
        """Parâmetros que os métodos de representação da Etapa 2 esperam; os de análise não são usados aqui."""
        return ExperimentConfig(
            representations=self.representations,
            min_df=self.min_df,
            neighbors_k=1,
            example_ids=(),
            clusters=2,
            top_terms=self.top_features,
            random_state=self.random_state,
            probe_words=(),
        )


def load_config(path: Path, methods: Mapping[str, MethodInfo], alternatives: Collection[str] = ()) -> ClassificationConfig:
    """Lê e valida a configuração contra os métodos de representação e os classificadores alternativos disponíveis."""
    data = require_object(read_config_json(path), "configuração", required={"representations", "labels"}, optional=set(DEFAULTS))
    items = data["representations"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_REPRESENTATIONS:
        raise ValueError(f"representations deve listar de 1 a {MAX_REPRESENTATIONS} representações")
    specs = tuple(parse_representation(item, methods) for item in items)
    require_unique([spec.name for spec in specs], "Nomes de representação repetidos")
    labels = require_ids(data["labels"], "labels")
    if not 2 <= len(labels) <= 20:
        raise ValueError("labels deve listar de 2 a 20 gêneros")
    values = {**DEFAULTS, **data}
    grid = values["regularization_grid"]
    if not isinstance(grid, list) or not 1 <= len(grid) <= 20:
        raise ValueError("regularization_grid deve listar de 1 a 20 valores de C")
    chosen = values["alternatives"]
    if not isinstance(chosen, list) or any(name not in alternatives for name in chosen):
        raise ValueError(f"alternatives deve listar classificadores entre {sorted(alternatives)}")
    require_unique(chosen, "Classificadores alternativos repetidos")
    return ClassificationConfig(
        representations=specs,
        labels=labels,
        folds=require_int(values["folds"], "folds", 2, 20),
        inner_folds=require_int(values["inner_folds"], "inner_folds", 2, 10),
        random_state=require_int(values["random_state"], "random_state", 0, 2**32 - 1),
        regularization_grid=tuple(sorted({require_number(c, "regularization_grid", 1e-8, 1e4) for c in grid})),
        min_df=require_int(values["min_df"], "min_df", 1, 1000),
        top_features=require_int(values["top_features"], "top_features", 1, 50),
        error_examples=require_int(values["error_examples"], "error_examples", 0, 50),
        alternatives=tuple(chosen),
    )
