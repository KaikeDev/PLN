"""K-Means e projeção 2D compartilhados pelas Etapas 2 e 3, para que “agrupar” signifique o mesmo nas duas.

Os dois operam sobre linhas com norma L2. O K-Means usa k-means++ com dez inicializações e semente fixa
(ADR 0012); a projeção é a TruncatedSVD com dois componentes, que nas matrizes lexicais é a LSA.
"""

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD

from app.representations.space import LexicalSpace

CLOSEST = 3


@dataclass(frozen=True)
class Grouping:
    """Grupo de cada linha e distância de cada linha a cada centroide."""

    labels: np.ndarray
    distances: np.ndarray

    def members(self, cluster: int) -> np.ndarray:
        """Posições das linhas do grupo `cluster`."""
        return np.flatnonzero(self.labels == cluster)

    def closest(self, cluster: int, limit: int = CLOSEST) -> np.ndarray:
        """Posições dos membros mais próximos do centroide, em ordem estável."""
        members = self.members(cluster)
        return members[np.argsort(self.distances[members, cluster], kind="stable")][:limit]


def fit_kmeans(unit: np.ndarray | csr_matrix, k: int, random_state: int) -> Grouping:
    """K-Means (k-means++, `n_init=10`) sobre linhas com norma L2."""
    model = KMeans(n_clusters=k, n_init=10, random_state=random_state)
    labels = model.fit_predict(unit)
    return Grouping(labels, model.transform(unit))


def project_2d(unit: np.ndarray | csr_matrix, random_state: int) -> tuple[np.ndarray, list[float]]:
    """Coordenadas 2D por TruncatedSVD e a fração da variância explicada por componente."""
    svd = TruncatedSVD(n_components=2, random_state=random_state)
    coordinates = svd.fit_transform(unit)
    return coordinates, [float(value) for value in svd.explained_variance_ratio_]


def descriptive_terms(descriptor: LexicalSpace, rows: np.ndarray, limit: int) -> list[str]:
    """Termos de maior peso médio no TF-IDF de referência entre as linhas `rows`: o mesmo vocabulário para qualquer representação."""
    profile = np.asarray(descriptor.unit[rows].mean(axis=0)).ravel() if len(rows) else np.zeros(descriptor.dimensions)
    top = np.lexsort((np.arange(len(profile)), -profile))[:limit]
    return [descriptor.terms[column] for column in top]
