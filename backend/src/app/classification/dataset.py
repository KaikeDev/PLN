"""Tarefas de classificação derivadas do corpus: multiclasse e multirrótulo sobre os mesmos gêneros.

Os rótulos são os `genre_ids` do TMDB restritos aos gêneros configurados. O recorte de coleta que
retornou o filme não é usado como rótulo: ele depende do ranking e do limite de páginas.
"""

from dataclasses import dataclass

import numpy as np

from app.vectors.corpus import ProcessedCorpus

MULTICLASS = "multiclasse"
MULTILABEL = "multirrotulo"


@dataclass(frozen=True)
class Task:
    """Uma tarefa sobre um subconjunto das sinopses.

    `rows` indexa `corpus.documents` (e as linhas das representações). Em multiclasse, `targets` tem uma
    posição de `labels` por linha; em multirrótulo, é a matriz binária linhas × rótulos.
    """

    name: str
    labels: tuple[int, ...]
    label_names: tuple[str, ...]
    rows: np.ndarray
    ids: tuple[int, ...]
    targets: np.ndarray

    @property
    def multilabel(self) -> bool:
        return self.targets.ndim == 2


def label_sets(corpus: ProcessedCorpus, labels: tuple[int, ...]) -> list[frozenset[int]]:
    """Gêneros configurados de cada sinopse, na ordem de `corpus.documents`."""
    wanted = frozenset(labels)
    return [document.tmdb_genres & wanted for document in corpus.documents]


def make_tasks(corpus: ProcessedCorpus, labels: tuple[int, ...], folds: int) -> tuple[Task, Task]:
    """Multiclasse: só filmes com exatamente um dos gêneros. Multirrótulo: filmes com ao menos um.

    Falha se algum gênero tiver menos exemplos que dobras, pois a validação estratificada exige
    ao menos um exemplo de cada classe em cada dobra.
    """
    sets = label_sets(corpus, labels)
    names = tuple(corpus.genre_names.get(label, str(label)) for label in labels)
    position = {label: index for index, label in enumerate(labels)}
    single = np.array([row for row, genres in enumerate(sets) if len(genres) == 1], dtype=np.int64)
    many = np.array([row for row, genres in enumerate(sets) if genres], dtype=np.int64)
    multiclass = Task(
        MULTICLASS,
        labels,
        names,
        single,
        tuple(corpus.ids[row] for row in single),
        np.array([position[next(iter(sets[row]))] for row in single], dtype=np.int64),
    )
    matrix = np.zeros((len(many), len(labels)), dtype=np.int64)
    for line, row in enumerate(many):
        for genre in sets[row]:
            matrix[line, position[genre]] = 1
    multilabel = Task(MULTILABEL, labels, names, many, tuple(corpus.ids[row] for row in many), matrix)
    counts = np.bincount(multiclass.targets, minlength=len(labels))
    if (scarce := [names[i] for i, count in enumerate(counts) if count < folds]) or matrix.sum(axis=0).min() < folds:
        raise ValueError(f"Gêneros com menos exemplos que dobras ({folds}): {scarce or 'multirrótulo'}")
    return multiclass, multilabel
