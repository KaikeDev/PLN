"""Análises sobre cada representação: as tarefas busca, recomendação, agrupamento e visualização, e as sondas da Aula 7."""

from abc import ABC, abstractmethod
from collections import Counter
from itertools import combinations
from statistics import mean
from typing import Any

import numpy as np
from scipy.sparse import issparse
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score
from sklearn.preprocessing import normalize

from app.shared.artifacts import jsonl_text
from app.vectors import report
from app.vectors.clusters import descriptive_terms, fit_kmeans, project_2d
from app.vectors.config import ProfileSpec
from app.vectors.context import AnalysisContext
from app.vectors.metrics import average_precision, genre_agreement, precision_at_k, purity, reciprocal_rank, rounded
from app.vectors.retrieval import search
from app.vectors.space import Encoded, Representation, count_nonzero, encoded_cosine
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


class Recommendation(Analysis):
    """Recomendação por conteúdo: os k filmes de maior cosseno com um filme (item → item) ou com um perfil.

    O perfil é a média, com norma L2, dos vetores dos filmes de que a pessoa gostou. Sem avaliações de
    usuários, a avaliação offline usa os gêneros como aproximação de relevância: a precisão @k é a fração
    dos recomendados que compartilham ao menos um gênero com o filme (ou com os filmes do perfil), e a
    referência é essa fração sobre todos os demais filmes, o esperado de uma recomendação que ignora o texto.
    """

    name = "recommendation"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.recommendation_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        k, corpus = context.config.neighbors_k, context.corpus
        documents = corpus.documents
        scores, rankings = _item_rankings(representation, k)
        precision, baseline = [], []
        for row, document in enumerate(documents):
            if document.genres:
                precision.append(genre_agreement(document.genres, [documents[other].genres for other in rankings[row]]))
                baseline.append(genre_agreement(document.genres, [other.genres for other in documents if other.id != document.id]))
        examples = []
        for movie_id in context.config.example_ids:
            row = corpus.ids.index(movie_id)
            document = documents[row]
            examples.append(
                {
                    "id": movie_id,
                    "title": document.title,
                    "genres": corpus.genre_labels(document.genres),
                    "recommendations": _described(
                        representation, context, representation.document(row), document.genres, rankings[row], scores[row]
                    ),
                }
            )
        return {
            "k": k,
            "documents_evaluated": len(precision),
            "precision_at_k": rounded(mean(precision)) if precision else None,
            "baseline": rounded(mean(baseline)) if baseline else None,
            "examples": examples,
            "profiles": [_profile_recommendations(representation, context, profile, k) for profile in context.config.profiles],
        }

    def artifacts(self, representation: Representation, result: dict, context: AnalysisContext) -> dict[str, str]:
        """Recomendações de todos os filmes, uma linha por filme na ordem de `documents.json`."""
        scores, rankings = _item_rankings(representation, result["k"])
        ids = representation.ids
        rows = [
            {"id": movie_id, "recommendations": [{"id": ids[other], "score": rounded(scores[row, other])} for other in rankings[row]]}
            for row, movie_id in enumerate(ids)
        ]
        return {f"{representation.spec.name}.recommendations.jsonl": jsonl_text(rows)}


def _item_rankings(representation: Representation, k: int) -> tuple[np.ndarray, list[np.ndarray]]:
    """Cosseno entre todas as sinopses, sem a própria, e as k linhas de maior cosseno de cada uma."""
    scores = representation.cosine(representation.unit)
    np.fill_diagonal(scores, -np.inf)
    return scores, [representation.ranking(scores[row])[:k] for row in range(len(representation.ids))]


def _described(
    representation: Representation, context: AnalysisContext, source: Encoded, genres: frozenset[int], rows: np.ndarray, scores: np.ndarray
) -> list[dict]:
    """Recomendações com título, cosseno, gêneros em comum e a explicação da proximidade."""
    corpus = context.corpus
    return [
        {
            "id": corpus.documents[other].id,
            "title": corpus.documents[other].title,
            "score": rounded(scores[other]),
            "shared_genres": corpus.genre_labels(genres & corpus.documents[other].genres),
            "explanation": representation.explain(source, representation.document(other), 5),
        }
        for other in rows
    ]


def _profile_recommendations(representation: Representation, context: AnalysisContext, profile: ProfileSpec, k: int) -> dict:
    """Média, com norma L2, dos vetores do perfil; recomenda os k filmes de maior cosseno fora do perfil."""
    corpus = context.corpus
    rows = [corpus.ids.index(movie_id) for movie_id in profile.movie_ids]
    vector = normalize(np.asarray(representation.unit[rows].mean(axis=0), dtype=np.float64).reshape(1, -1))
    tokens = tuple(token for row in rows for token in representation.document(row).tokens)
    scores = representation.cosine(vector)[0]
    scores[rows] = -np.inf
    ranked = representation.ranking(scores)[:k]
    genres = frozenset().union(*(corpus.documents[row].genres for row in rows))
    return {
        "id": profile.id,
        "movies": [{"id": corpus.documents[row].id, "title": corpus.documents[row].title} for row in rows],
        "genres": corpus.genre_labels(genres),
        "precision_at_k": rounded(genre_agreement(genres, [corpus.documents[row].genres for row in ranked])) if genres else None,
        "recommendations": _described(representation, context, Encoded(vector, tokens), genres, ranked, scores),
    }


class Clustering(Analysis):
    """K-Means sobre linhas com norma L2 (`app.vectors.clusters`, o mesmo usado pela Etapa 3).

    ARI, NMI e pureza usam só filmes com exatamente um gênero da coleta, os únicos com rótulo inequívoco.
    Os termos descritivos vêm do TF-IDF de referência do contexto. `assignments` traz o cluster de cada
    sinopse na ordem de `documents.json`; o gráfico colore por ele a mesma projeção 2D da análise `projection`.
    """

    name = "clustering"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.clustering_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        config, corpus, descriptor = context.config, context.corpus, context.descriptor
        grouping = fit_kmeans(representation.unit, config.clusters, config.random_state)
        labels = grouping.labels
        labeled = [(row, next(iter(document.genres))) for row, document in enumerate(corpus.documents) if len(document.genres) == 1]
        genres = [genre for _, genre in labeled]
        predicted = labels[[row for row, _ in labeled]].tolist()
        clusters = []
        for cluster in range(config.clusters):
            members = grouping.members(cluster)
            counts = Counter(corpus.genre_label(genre) for row in members for genre in corpus.documents[row].genres)
            clusters.append(
                {
                    "cluster": cluster,
                    "size": len(members),
                    "descriptive_terms": descriptive_terms(descriptor, members, config.top_terms),
                    "genres": dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))),
                    "closest_to_centroid": [
                        {"id": corpus.documents[row].id, "title": corpus.documents[row].title} for row in grouping.closest(cluster)
                    ],
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
            "assignments": labels.tolist(),
            "clusters": clusters,
        }

    def artifacts(self, representation: Representation, result: dict, context: AnalysisContext) -> dict[str, str]:
        """Mesma projeção 2D da análise `projection`, colorida pelo cluster encontrado."""
        coordinates, variance = project_2d(representation.unit, context.config.random_state)
        points = [
            {"id": document.id, "title": document.title, "label": f"Cluster {cluster}", "x": rounded(x, 5), "y": rounded(y, 5)}
            for document, cluster, (x, y) in zip(context.corpus.documents, result["assignments"], coordinates, strict=True)
        ]
        heading = f"{representation.spec.name}: sinopses coloridas pelo cluster do K-Means"
        svg = render_projection(heading, points, variance, set(context.config.example_ids))
        return {f"{representation.spec.name}.clusters.svg": svg}


class Projection(Analysis):
    """Projeção 2D por TruncatedSVD (LSA nas matrizes lexicais) e gráfico SVG colorido pelo gênero."""

    name = "projection"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.projection_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        if representation.dimensions <= 2:
            raise ValueError(f"{representation.spec.name}: a projeção 2D exige mais de duas dimensões")
        coordinates, variance = project_2d(representation.unit, context.config.random_state)
        corpus = context.corpus
        return {
            "method": "TruncatedSVD com 2 componentes sobre linhas com norma L2 (LSA nas matrizes lexicais)",
            "explained_variance_ratio": [rounded(value) for value in variance],
            "points": [
                {"id": document.id, "title": document.title, "genre": corpus.genre_name(document), "x": rounded(x, 5), "y": rounded(y, 5)}
                for document, (x, y) in zip(corpus.documents, coordinates, strict=True)
            ],
        }

    def artifacts(self, representation: Representation, result: dict, context: AnalysisContext) -> dict[str, str]:
        heading = f"{representation.spec.name}: sinopses coloridas pelo gênero"
        points = [{**point, "label": point["genre"]} for point in result["points"]]
        svg = render_projection(heading, points, result["explained_variance_ratio"], set(context.config.example_ids))
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
        pairs = [[left, right, _optional_round(representation.word_similarity(left, right))] for left, right in context.probes.word_pairs]
        return {
            "supported": True,
            "words": {word: representation.nearest_words(word, limit) for word in context.config.probe_words},
            "pairs": pairs,
        }


class SentencePairs(Analysis):
    """Cosseno entre pares de frases da aula: paráfrases sem palavras em comum e frases que só compartilham uma palavra polissêmica.

    Cada frase passa pelas mesmas regras de preparação da entrada da representação. A explicação usa
    `Representation.explain` (termos idênticos, pares de palavras próximas ou nada, conforme a família).
    """

    name = "sentence_pairs"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.sentence_pairs_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        pairs = []
        for pair in context.probes.sentence_pairs:
            left, right = representation.encode(pair.left, context.corpus), representation.encode(pair.right, context.corpus)
            pairs.append(
                {
                    "id": pair.id,
                    "expected": pair.expected,
                    "cosine": rounded(encoded_cosine(left, right)),
                    "null_vector": left.null or right.null,
                    "out_of_vocabulary": sorted(set(left.out_of_vocabulary) | set(right.out_of_vocabulary)),
                    "explanation": representation.explain(left, right, 5),
                }
            )
        return {"pairs": pairs}


class WordSenses(Analysis):
    """Polissemia: cosseno entre os vetores de uma mesma palavra em frases com sentidos iguais e diferentes.

    Em representações estáticas o vetor não muda com a frase, então a diferença entre os dois grupos é
    zero; em representações contextuais espera-se cosseno maior dentro do mesmo sentido.
    """

    name = "word_senses"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.word_senses_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        if not representation.supports_word_in_context:
            return {"supported": False}
        words = []
        for item in context.probes.word_senses:
            vectors = [representation.word_in_context(entry.text, item.word) for entry in item.contexts]
            if any(vector is None for vector in vectors):
                words.append({"id": item.id, "word": item.word, "found": False})
                continue
            matrix = np.vstack([vector for vector in vectors if vector is not None])
            similarity = matrix @ matrix.T
            same: list[float] = []
            different: list[float] = []
            for i, j in combinations(range(len(item.contexts)), 2):
                (same if item.contexts[i].sense == item.contexts[j].sense else different).append(float(similarity[i, j]))
            same_mean, different_mean = mean(same) if same else None, mean(different)
            words.append(
                {
                    "id": item.id,
                    "word": item.word,
                    "found": True,
                    "senses": [entry.sense for entry in item.contexts],
                    "similarity": [[rounded(value, 4) for value in row] for row in similarity.tolist()],
                    "same_sense_mean": _optional_round(same_mean),
                    "different_sense_mean": rounded(different_mean),
                    "gap": _optional_round(same_mean - different_mean if same_mean is not None else None),
                }
            )
        return {"supported": True, "family": representation.family, "words": words}


class Synthesis(Analysis):
    """Propriedades de cada representação para a síntese comparativa da aula: informação, custo e interpretabilidade."""

    name = "synthesis"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return report.synthesis_section(results, context)

    def run(self, representation: Representation, context: AnalysisContext) -> dict:
        return {
            "family": representation.family,
            "sparse": issparse(representation.matrix),
            "dimensions": representation.dimensions,
            "dimensions_are_vocabulary": representation.family == "lexical",
            "learned": representation.learned,
            "word_depends_on_context": representation.family == "contextual",
            "interpretable_by_words": representation.family != "contextual",
            "parameters": representation.parameters(),
            "model": representation.spec.model,
        }


def _optional_round(value: float | None) -> float | None:
    return None if value is None else rounded(value)


class Retrieval(Analysis):
    """Busca (recuperação de informação): posição dos filmes relevantes, MRR e acerto @k das consultas anotadas."""

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
            ranks = [item["rank"] for item in relevant]
            first = min((rank for rank in ranks if rank is not None), default=None)
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
                    "average_precision": rounded(average_precision(ranks)),
                    "precision_at_k": rounded(precision_at_k(ranks, k)),
                    "top": result.top(corpus, k),
                }
            )
        return {
            "k": k,
            "mean_reciprocal_rank": rounded(mean(item["reciprocal_rank"] for item in items)) if items else None,
            "hit_rate_at_k": rounded(mean(item["hit_at_k"] for item in items)) if items else None,
            "mean_average_precision": rounded(mean(item["average_precision"] for item in items)) if items else None,
            "mean_precision_at_k": rounded(mean(item["precision_at_k"] for item in items)) if items else None,
            "queries": items,
        }


DEFAULT_ANALYSES: tuple[Analysis, ...] = (
    Dimensions(),
    Retrieval(),
    Recommendation(),
    Clustering(),
    Projection(),
    WordNeighbors(),
    SentencePairs(),
    WordSenses(),
    Synthesis(),
)
