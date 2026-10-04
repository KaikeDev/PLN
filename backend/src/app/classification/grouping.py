"""Clusterização × classificação: o mesmo K-Means da Etapa 2 (`app.clustering.kmeans`) sobre as sinopses da tarefa multiclasse.

O K-Means não vê rótulos: agrupa pela proximidade no espaço da representação, e os gêneros só entram
depois, para medir quanto os grupos coincidem com as classes. ARI, NMI e pureza não dependem do nome
de cada grupo, então medem da mesma forma os grupos e as previsões do classificador. A acurácia com o
melhor mapeamento associa cada grupo a um gênero diferente usando os próprios rótulos: é um teto
otimista para quem quisesse usar os grupos como classes.
"""

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import accuracy_score, adjusted_rand_score, f1_score, normalized_mutual_info_score

from app.classification.dataset import Task
from app.clustering.kmeans import descriptive_terms, fit_kmeans
from app.representations.corpus import ProcessedCorpus
from app.representations.metrics import purity, rounded
from app.representations.space import LexicalSpace, Representation


def agreement(truth: np.ndarray, groups: np.ndarray) -> dict:
    """ARI (perto de 0 ao acaso, 1 = coincidência perfeita), NMI (0 = independentes, 1 = coincidência) e pureza entre gêneros e grupos ou previsões."""
    return {
        "ari": rounded(adjusted_rand_score(truth, groups)),
        "nmi": rounded(normalized_mutual_info_score(truth, groups)),
        "pureza": rounded(purity(truth.tolist(), groups.tolist())),
    }


def contingency(truth: np.ndarray, groups: np.ndarray, size: int) -> np.ndarray:
    """Contagem de sinopses por grupo (linhas) e gênero real (colunas)."""
    table = np.zeros((size, size), dtype=np.int64)
    np.add.at(table, (groups, truth), 1)
    return table


def best_mapping(table: np.ndarray) -> list[int]:
    """Gênero associado a cada grupo, um gênero por grupo, maximizando as sinopses coincidentes (algoritmo húngaro)."""
    groups, genres = linear_sum_assignment(-table)
    mapping = dict(zip(groups.tolist(), genres.tolist(), strict=True))
    return [mapping[group] for group in range(len(table))]


def cluster(
    task: Task, representation: Representation, descriptor: LexicalSpace, corpus: ProcessedCorpus, random_state: int, top_terms: int
) -> dict:
    """K-Means com k = número de gêneros e o mesmo algoritmo da Etapa 2 (k-means++, n_init=10, linhas com norma L2).

    Cada grupo é descrito pelos termos de maior peso médio no TF-IDF de referência e pelas sinopses mais
    próximas do centroide, como na Etapa 2, para que a interpretação não dependa da representação.
    """
    size = len(task.labels)
    grouping = fit_kmeans(representation.unit[task.rows], size, random_state)
    groups = grouping.labels
    table = contingency(task.targets, groups, size)
    mapping = best_mapping(table)
    mapped = np.array([mapping[group] for group in groups], dtype=np.int64)
    details = []
    for group in range(size):
        members = grouping.members(group)
        details.append(
            {
                "grupo": group,
                "tamanho": len(members),
                "genero_associado": task.label_names[mapping[group]],
                "generos": {name: int(count) for name, count in zip(task.label_names, table[group], strict=True)},
                "termos": descriptive_terms(descriptor, task.rows[members], top_terms),
                "mais_proximos_do_centroide": [corpus.documents[task.rows[member]].title for member in grouping.closest(group)],
            }
        )
    return {
        **agreement(task.targets, groups),
        "acuracia_melhor_mapeamento": rounded(accuracy_score(task.targets, mapped)),
        "f1_macro_melhor_mapeamento": rounded(f1_score(task.targets, mapped, average="macro", zero_division=0)),
        "grupos": details,
    }
