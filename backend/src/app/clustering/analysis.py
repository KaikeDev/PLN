"""Agrupamento (K-Means) e visualização (projeção 2D colorida pelo gênero e pelo cluster) sobre cada representação."""

from collections import Counter

from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score

from app.clustering.kmeans import descriptive_terms, fit_kmeans, project_2d
from app.clustering.svg import render_projection
from app.representations.analyses import Analysis
from app.representations.context import AnalysisContext
from app.representations.metrics import purity, rounded
from app.representations.report import number
from app.representations.space import Representation


class Clustering(Analysis):
    """K-Means sobre linhas com norma L2 (`app.clustering.kmeans`, o mesmo usado pela Etapa 3).

    ARI, NMI e pureza usam só filmes com exatamente um gênero da coleta, os únicos com rótulo inequívoco.
    Os termos descritivos vêm do TF-IDF de referência do contexto. `assignments` traz o cluster de cada
    sinopse na ordem de `documents.json`; o gráfico colore por ele a mesma projeção 2D da análise `projection`.
    """

    name = "clustering"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return clustering_section(results, context)

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
        return projection_section(results, context)

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


def clustering_section(results: dict, context: AnalysisContext) -> list[str]:
    names = context.representation_names
    lines = [
        "## Agrupamento (K-Means)",
        "",
        f"K-Means com k = {context.config.clusters}, sem rótulos. ARI, NMI e pureza comparam os clusters com o gênero dos filmes que têm exatamente um "
        "gênero da coleta; a silhueta usa distância do cosseno e não depende de rótulos. Os termos descritivos vêm da média TF-IDF (sem stopwords) "
        "dos membros de cada cluster, o mesmo vocabulário para todas as representações. "
        "O gráfico de cada representação é a projeção da seção seguinte colorida pelo cluster encontrado.",
        "",
        "| Representação | ARI | NMI | Pureza | Silhueta | Filmes rotulados | Tamanhos | Gráfico |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for name in names:
        row = results[name]
        sizes = ", ".join(str(cluster["size"]) for cluster in row["clusters"])
        lines.append(
            f"| {name} | {number(row['adjusted_rand_index'])} | {number(row['normalized_mutual_information'])} | {number(row['purity'])} | "
            f"{number(row['silhouette_cosine'])} | {row['labeled_documents']} | {sizes} | [{name}.clusters.svg]({name}.clusters.svg) |"
        )
    for name in names:
        lines += ["", f"### {name}", ""]
        for cluster in results[name]["clusters"]:
            genres = ", ".join(f"{genre} {count}" for genre, count in list(cluster["genres"].items())[:4]) or "sem gênero"
            lines.append(f"- Cluster {cluster['cluster']} ({cluster['size']} filmes; {genres}): {', '.join(cluster['descriptive_terms'])}")
    return [*lines, ""]


def projection_section(results: dict, context: AnalysisContext) -> list[str]:
    names = context.representation_names
    lines = [
        "## Visualização: projeção em duas dimensões",
        "",
        "TruncatedSVD reduz as dimensões a dois componentes para inspeção visual (nas matrizes lexicais, é a LSA). "
        "Variância explicada baixa indica que o plano mostra só parte da estrutura; distâncias no gráfico não substituem o cosseno original. "
        "Sem centralização, o primeiro componente tende a seguir a direção média das sinopses e pode explicar menos variância que o segundo. "
        "Cada representação tem dois gráficos com as mesmas coordenadas: um colorido pelo gênero e outro pelo cluster do K-Means. "
        "Comparar os dois mostra se os grupos encontrados sem rótulos seguem os gêneros.",
        "",
        "| Representação | Variância componente 1 | Variância componente 2 | Por gênero | Por cluster |",
        "|---|---:|---:|---|---|",
    ]
    for name in names:
        first, second = results[name]["explained_variance_ratio"]
        lines.append(
            f"| {name} | {first:.2%} | {second:.2%} | [{name}.projection.svg]({name}.projection.svg) | [{name}.clusters.svg]({name}.clusters.svg) |"
        )
    return [*lines, ""]
