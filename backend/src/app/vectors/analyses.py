"""Análises sobre cada representação: dimensões, similaridade, clustering, projeção, palavras e consultas."""

from abc import ABC, abstractmethod
from collections import Counter
from statistics import mean
from typing import Any

import numpy as np
from scipy.sparse import issparse
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score

from app.vectors import report
from app.vectors.context import AnalysisContext
from app.vectors.metrics import genre_agreement, purity, reciprocal_rank, rounded
from app.vectors.retrieval import search
from app.vectors.space import Representation, count_nonzero
from app.vectors.svg import render_projection


class Analysis(ABC):
    """Estratégia de análise: incluir uma nova análise não exige alterar o pipeline nem o relatório."""

    name: str

    @abstractmethod
    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        """Resultado serializável em JSON da análise sobre uma representação."""

    @abstractmethod
    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        """Linhas Markdown da seção do relatório, a partir dos resultados de todas as representações."""

    def artifacts(self, representation: Representation, result: dict, context: AnalysisContext) -> dict[str, str]:
        """Arquivos textuais extras. Os nomes derivam de nomes de representação já validados."""
        return {}


class Dimensions(Analysis):
    """Tamanho, esparsidade e resumo específico de cada representação."""

    name = "dimensions"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.dimensions_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        matrix, spec = representation.matrix, representation.spec
        documents, dimensions = matrix.shape
        nonzero = count_nonzero(matrix)
        return {
            "method": spec.method,
            "stage": spec.stage,
            "documents": documents,
            "dimensions": dimensions,
            "sparse": issparse(matrix),
            "nonzero": nonzero,
            "density": rounded(nonzero / (documents * dimensions)),
            "mean_nonzero_per_document": rounded(nonzero / documents),
            **representation.summary(context.config),
        }


class Neighbors(Analysis):
    """Vizinhos de maior cosseno de cada sinopse (excluída ela mesma) e concordância de gênero @k.

    A referência de concordância é calculada sobre todos os demais filmes, ou seja, sem usar o texto.
    """

    name = "neighbors"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.neighbors_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        k, documents = context.config.neighbors_k, context.corpus.documents
        scores = representation.cosine(representation.unit)
        np.fill_diagonal(scores, -np.inf)
        rankings = [representation.ranking(scores[row])[:k] for row in range(len(documents))]
        agreement, baseline = [], []
        for row, document in enumerate(documents):
            if document.genres:
                agreement.append(genre_agreement(document.genres, [documents[other].genres for other in rankings[row]]))
                baseline.append(genre_agreement(document.genres, [other.genres for other in documents if other.id != document.id]))
        examples = []
        for movie_id in context.config.example_ids:
            row = context.corpus.ids.index(movie_id)
            examples.append(
                {
                    "id": movie_id,
                    "title": documents[row].title,
                    "neighbors": [
                        {
                            "id": documents[other].id,
                            "title": documents[other].title,
                            "score": rounded(scores[row, other]),
                            "explanation": representation.explain(representation.document(row), representation.document(other), 5),
                        }
                        for other in rankings[row]
                        if scores[row, other] > 0
                    ],
                }
            )
        return {
            "k": k,
            "documents_evaluated": len(agreement),
            "genre_agreement_at_k": rounded(mean(agreement)) if agreement else None,
            "genre_agreement_baseline": rounded(mean(baseline)) if baseline else None,
            "examples": examples,
        }


class Clustering(Analysis):
    """K-Means sobre linhas com norma L2.

    ARI, NMI e pureza usam só filmes de um único gênero de coleta, os únicos com rótulo inequívoco. Os
    termos descritivos vêm do TF-IDF de referência do contexto.
    """

    name = "clustering"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.clustering_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        config, corpus, descriptor = context.config, context.corpus, context.descriptor
        model = KMeans(n_clusters=config.clusters, n_init=10, random_state=config.random_state)
        labels = model.fit_predict(representation.unit)
        distances = model.transform(representation.unit)
        labeled = [(row, next(iter(document.genres))) for row, document in enumerate(corpus.documents) if len(document.genres) == 1]
        genres = [genre for _, genre in labeled]
        predicted = labels[[row for row, _ in labeled]].tolist()
        clusters = []
        for cluster in range(config.clusters):
            members = np.flatnonzero(labels == cluster)
            profile = np.asarray(descriptor.unit[members].mean(axis=0)).ravel() if len(members) else np.zeros(descriptor.dimensions)
            top = np.lexsort((np.arange(len(profile)), -profile))[: config.top_terms]
            closest = members[np.argsort(distances[members, cluster], kind="stable")][:3]
            counts = Counter(corpus.genre_names.get(genre, str(genre)) for row in members for genre in corpus.documents[row].genres)
            clusters.append(
                {
                    "cluster": cluster,
                    "size": len(members),
                    "descriptive_terms": [descriptor.terms[column] for column in top],
                    "genres": dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))),
                    "closest_to_centroid": [{"id": corpus.documents[row].id, "title": corpus.documents[row].title} for row in closest],
                }
            )
        distinct = len(set(labels.tolist()))
        return {
            "algorithm": "KMeans (k-means++, n_init=10) sobre linhas com norma L2",
            "k": config.clusters,
            "labeled_documents": len(labeled),
            "adjusted_rand_index": rounded(adjusted_rand_score(genres, predicted)) if labeled else None,
            "normalized_mutual_information": rounded(normalized_mutual_info_score(genres, predicted)) if labeled else None,
            "purity": rounded(purity(genres, predicted)) if labeled else None,
            "silhouette_cosine": rounded(silhouette_score(representation.unit, labels, metric="cosine"))
            if 1 < distinct < len(labels)
            else None,
            "clusters": clusters,
        }


class Projection(Analysis):
    """Projeção 2D por TruncatedSVD (LSA nas matrizes lexicais) e gráfico SVG por representação."""

    name = "projection"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.projection_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        if representation.dimensions <= 2:
            raise ValueError(f"{representation.spec.name}: a projeção 2D exige mais de duas dimensões")
        svd = TruncatedSVD(n_components=2, random_state=context.config.random_state)
        coordinates = svd.fit_transform(representation.unit)
        corpus = context.corpus
        return {
            "method": "TruncatedSVD com 2 componentes sobre linhas com norma L2 (LSA nas matrizes lexicais)",
            "explained_variance_ratio": [rounded(value) for value in svd.explained_variance_ratio_],
            "points": [
                {"id": document.id, "title": document.title, "genre": corpus.genre_name(document), "x": rounded(x, 5), "y": rounded(y, 5)}
                for document, (x, y) in zip(corpus.documents, coordinates, strict=True)
            ],
        }

    def artifacts(self, representation: Representation, result: dict, context: AnalysisContext) -> dict[str, str]:
        heading = f"{representation.spec.name}: projeção 2D das sinopses"
        svg = render_projection(heading, result["points"], result["explained_variance_ratio"], set(context.config.example_ids))
        return {f"{representation.spec.name}.projection.svg": svg}


class WordNeighbors(Analysis):
    """Palavras do corpus mais próximas de cada palavra de sondagem, quando há vetores por palavra."""

    name = "word_neighbors"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.word_neighbors_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        if not representation.supports_words:
            return {"supported": False}
        limit = context.config.top_terms
        return {"supported": True, "words": {word: representation.nearest_words(word, limit) for word in context.config.probe_words}}


class Retrieval(Analysis):
    """Posição dos filmes relevantes, MRR e acerto @k das consultas anotadas."""

    name = "retrieval"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.retrieval_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        k, corpus = context.config.neighbors_k, context.corpus
        items: list[dict[str, Any]] = []
        for query in context.queries:
            result = search(representation, corpus, query.text)
            relevant: list[dict[str, Any]] = [
                {
                    "id": movie_id,
                    "title": corpus.by_id[movie_id].title,
                    "rank": result.rank_of(movie_id),
                    "explanation": representation.explain(result.query, representation.document(corpus.ids.index(movie_id)), 5),
                }
                for movie_id in query.relevant_ids
            ]
            first = min((item["rank"] for item in relevant if item["rank"] is not None), default=None)
            items.append(
                {
                    "id": query.id,
                    "text": query.text,
                    "note": query.note,
                    "tokens": list(result.query.tokens),
                    "out_of_vocabulary": list(result.query.out_of_vocabulary),
                    "null_vector": result.query.null,
                    "retrieved": len(result.ranked),
                    "relevant": relevant,
                    "reciprocal_rank": rounded(reciprocal_rank(first)),
                    "hit_at_k": first is not None and first <= k,
                    "top": result.top(corpus, k),
                }
            )
        return {
            "k": k,
            "mean_reciprocal_rank": rounded(mean(item["reciprocal_rank"] for item in items)) if items else None,
            "hit_rate_at_k": rounded(mean(item["hit_at_k"] for item in items)) if items else None,
            "queries": items,
        }


DEFAULT_ANALYSES: tuple[Analysis, ...] = (Dimensions(), Neighbors(), Clustering(), Projection(), WordNeighbors(), Retrieval())
