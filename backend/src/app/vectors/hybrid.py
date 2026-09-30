"""Busca híbrida: soma ponderada dos cossenos de várias representações das mesmas sinopses (ADR 0018).

Para cada consulta, o cosseno de cada representação é dividido pelo maior cosseno positivo dela, de
modo que representações com escalas diferentes (TF-IDF esparso e embedding denso) fiquem comparáveis.
Um filme sem cosseno positivo numa representação recebe zero dela. A pontuação final é a soma ponderada.

`evaluate` mede cada representação sozinha e a combinação nas consultas anotadas, com as mesmas
métricas da análise `retrieval`.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import numpy as np

from app.shared.validation import read_config_json, require_name, require_number, require_object, require_unique
from app.vectors.config import QuerySpec
from app.vectors.corpus import ProcessedCorpus
from app.vectors.methods import METHODS, Method
from app.vectors.metrics import average_precision, precision_at_k, reciprocal_rank, rounded
from app.vectors.pipeline import prepare
from app.vectors.retrieval import search
from app.vectors.space import Representation

MAX_MEMBERS = 8
WEIGHT_TOLERANCE = 1e-6


@dataclass(frozen=True)
class WeightedRepresentation:
    """Representação de `vetorizacao*.json` e o seu peso na combinação."""

    name: str
    weight: float


@dataclass(frozen=True)
class SearchConfig:
    """Representações combinadas na busca; os pesos somam 1."""

    representations: tuple[WeightedRepresentation, ...]


def load_search_config(path: Path) -> SearchConfig:
    """Lê e valida a configuração da busca híbrida."""
    data = require_object(read_config_json(path), "configuração da busca", required={"representations"}, optional={"description"})
    items = data["representations"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_MEMBERS:
        raise ValueError(f"representations deve listar de 1 a {MAX_MEMBERS} representações")
    members = tuple(_member(item) for item in items)
    require_unique([member.name for member in members], "Representações repetidas na busca")
    if abs(sum(member.weight for member in members) - 1) > WEIGHT_TOLERANCE:
        raise ValueError("Os pesos da busca devem somar 1")
    return SearchConfig(members)


class HybridIndex:
    """Ordena as sinopses de um corpus pela soma ponderada dos cossenos normalizados."""

    def __init__(self, corpus: ProcessedCorpus, members: Sequence[tuple[Representation, float]]) -> None:
        self.corpus = corpus
        self.members = tuple(members)
        self._rows = {movie_id: row for row, movie_id in enumerate(corpus.ids)}

    @classmethod
    def build(
        cls, processed: Path, vectors_config: Path, search_config: SearchConfig, methods: Mapping[str, Method] = METHODS
    ) -> HybridIndex:
        """Constrói só as representações usadas pela busca, com as especificações da configuração vetorial."""
        corpus, config, _ = prepare(processed, vectors_config, methods=methods)
        specs = {spec.name: spec for spec in config.representations}
        if missing := sorted(member.name for member in search_config.representations if member.name not in specs):
            raise ValueError(f"Representações da busca ausentes de {vectors_config.name}: {missing}")
        members = [
            (methods[specs[member.name].method].build(specs[member.name], corpus, config), member.weight)
            for member in search_config.representations
        ]
        return cls(corpus, members)

    def only(self, name: str) -> HybridIndex:
        """Índice com uma única representação, para comparar com a combinação."""
        return HybridIndex(self.corpus, [(representation, 1.0) for representation, _ in self.members if representation.spec.name == name])

    def rank(self, text: str) -> list[tuple[int, float]]:
        """Pares (id, pontuação) com pontuação positiva, em ordem decrescente e, no empate, por id."""
        combined = np.zeros(len(self.corpus.ids))
        for representation, weight in self.members:
            ranked = search(representation, self.corpus, text).ranked
            if not ranked:
                continue
            top = ranked[0][1]
            for movie_id, score in ranked:
                combined[self._rows[movie_id]] += weight * score / top
        order = sorted((row for row in range(len(combined)) if combined[row] > 0), key=lambda row: (-combined[row], self.corpus.ids[row]))
        return [(self.corpus.ids[row], float(combined[row])) for row in order]


def evaluate(index: HybridIndex, queries: Sequence[QuerySpec], k: int = 5) -> dict:
    """MRR, acerto @k, MAP e precisão @k de cada representação sozinha e da combinação."""
    rankers: dict[str, Callable[[str], list[tuple[int, float]]]] = {
        representation.spec.name: index.only(representation.spec.name).rank for representation, _ in index.members
    }
    rankers["combinacao"] = index.rank
    return {
        "k": k,
        "weights": {representation.spec.name: weight for representation, weight in index.members},
        "results": {name: _metrics(rank, queries, k) for name, rank in rankers.items()},
    }


def _metrics(rank: Callable[[str], list[tuple[int, float]]], queries: Sequence[QuerySpec], k: int) -> dict:
    per_query = {}
    for query in queries:
        positions = {movie_id: position for position, (movie_id, _) in enumerate(rank(query.text), 1)}
        ranks = [positions.get(movie_id) for movie_id in query.relevant_ids]
        first = min((rank for rank in ranks if rank is not None), default=None)
        per_query[query.id] = {
            "reciprocal_rank": rounded(reciprocal_rank(first)),
            "hit_at_k": first is not None and first <= k,
            "average_precision": rounded(average_precision(ranks)),
            "precision_at_k": rounded(precision_at_k(ranks, k)),
        }
    rows = list(per_query.values())
    return {
        "mean_reciprocal_rank": rounded(mean(row["reciprocal_rank"] for row in rows)),
        "hit_rate_at_k": rounded(mean(row["hit_at_k"] for row in rows)),
        "mean_average_precision": rounded(mean(row["average_precision"] for row in rows)),
        "mean_precision_at_k": rounded(mean(row["precision_at_k"] for row in rows)),
        "queries": per_query,
    }


def _member(item: object) -> WeightedRepresentation:
    data = require_object(item, "representação da busca", required={"name", "weight"})
    return WeightedRepresentation(require_name(data["name"], "name"), require_number(data["weight"], "weight", 0.001, 1))
