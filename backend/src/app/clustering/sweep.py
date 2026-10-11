"""Varredura do número de clusters com métricas internas e externas, para cada representação (ADR 0028).

O agrupamento da Etapa 2 usa k = 4, o número de gêneros da coleta. Aqui o mesmo K-Means (`fit_kmeans`, sobre
linhas com norma L2) roda para cada k de `k_min` a `k_max`, e cada resultado recebe:

- **intracluster:** inércia (soma das distâncias quadradas ao centroide; menor = grupos mais compactos) e distância
  de cosseno média de cada sinopse ao centroide do próprio grupo;
- **intercluster:** distância de cosseno média entre os centroides (maior = grupos mais separados);
- **intra × inter:** silhueta de cosseno (−1 a 1; maior = melhor), Davies-Bouldin (menor = melhor) e
  Calinski-Harabasz (maior = melhor);
- **contra os gêneros:** ARI, NMI e pureza, só com os filmes de um único gênero, como na Etapa 2.

As métricas internas medem a forma dos grupos, não se eles fazem sentido: por isso a leitura dos termos e
títulos de cada grupo continua sendo necessária.
"""

import platform
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    normalized_mutual_info_score,
    silhouette_score,
)
from sklearn.metrics.pairwise import cosine_distances

from app.clustering.kmeans import descriptive_terms, fit_kmeans
from app.representations.methods import METHODS, Method
from app.representations.metrics import purity, rounded
from app.representations.pipeline import DESCRIPTOR, library_versions, prepare
from app.representations.space import TFIDF
from app.representations.stored import StoredVectors, build_representation
from app.shared.artifacts import create_output, json_text, sha256, source_identity, write_json, write_text
from app.shared.manifest import MANIFEST_NAME, hash_files, read_manifest, verify_hashes
from app.shared.validation import read_config_json, require_int, require_object


@dataclass(frozen=True)
class SweepConfig:
    """Faixa de k, semente e quantos termos descrevem cada grupo."""

    k_min: int
    k_max: int
    random_state: int
    top_terms: int


def load_sweep_config(path: Path) -> SweepConfig:
    """Lê e valida a configuração da varredura."""
    data = require_object(
        read_config_json(path),
        "configuração da varredura",
        required={"k_min", "k_max", "random_state", "top_terms"},
        optional={"description"},
    )
    k_min, k_max = require_int(data["k_min"], "k_min", 2, 30), require_int(data["k_max"], "k_max", 2, 30)
    if k_min > k_max:
        raise ValueError("k_min deve ser menor ou igual a k_max")
    return SweepConfig(
        k_min, k_max, require_int(data["random_state"], "random_state", 0, 2**32 - 1), require_int(data["top_terms"], "top_terms", 1, 30)
    )


def sweep(
    processed: Path,
    vectors_config: Path,
    output: Path,
    config_path: Path,
    vectors: Path | None = None,
    methods: Mapping[str, Method] = METHODS,
) -> dict:
    """Métricas de cada k para cada representação, numa pasta nova, com relatório e manifesto."""
    if output.exists():
        raise FileExistsError(f"A pasta de saída já existe: {output}")
    config = load_sweep_config(config_path)
    corpus, vector_config, _ = prepare(processed, vectors_config, methods=methods)
    stored = StoredVectors(vectors, corpus) if vectors is not None else None
    descriptor = TFIDF.build(DESCRIPTOR, corpus, vector_config)
    labeled = [(row, next(iter(document.genres))) for row, document in enumerate(corpus.documents) if len(document.genres) == 1]
    genres = [genre for _, genre in labeled]
    results: dict[str, list[dict]] = {}
    for spec in vector_config.representations:
        representation = build_representation(spec, corpus, vector_config, methods, stored)
        unit = representation.unit
        dense = csr_matrix(unit).toarray()
        rows = []
        for k in range(config.k_min, config.k_max + 1):
            grouping = fit_kmeans(unit, k, config.random_state)
            labels = grouping.labels
            centroids = np.vstack([dense[labels == cluster].mean(axis=0) for cluster in range(k)])
            own = cosine_distances(dense, centroids)[np.arange(len(labels)), labels]
            between = cosine_distances(centroids)[np.triu_indices(k, 1)]
            predicted = labels[[row for row, _ in labeled]].tolist()
            rows.append(
                {
                    "k": k,
                    "tamanhos": sorted(np.bincount(labels, minlength=k).tolist(), reverse=True),
                    "inercia": rounded(float((grouping.distances[np.arange(len(labels)), labels] ** 2).sum())),
                    "distancia_ao_centroide": rounded(float(own.mean())),
                    "distancia_entre_centroides": rounded(float(between.mean())),
                    "silhueta_cosseno": rounded(silhouette_score(dense, labels, metric="cosine")),
                    "davies_bouldin": rounded(davies_bouldin_score(dense, labels)),
                    "calinski_harabasz": rounded(calinski_harabasz_score(dense, labels)),
                    "ari": rounded(adjusted_rand_score(genres, predicted)),
                    "nmi": rounded(normalized_mutual_info_score(genres, predicted)),
                    "pureza": rounded(purity(genres, predicted)),
                    "grupos": [
                        {
                            "tamanho": len(grouping.members(cluster)),
                            "termos": descriptive_terms(descriptor, grouping.members(cluster), config.top_terms),
                            "mais_proximos": [corpus.documents[row].title for row in grouping.closest(cluster)],
                        }
                        for cluster in range(k)
                    ],
                }
            )
        results[spec.name] = rows

    summary = {name: _best(rows) for name, rows in results.items()}
    files = {
        "config.json": json_text(asdict(config)),
        "sweep.json": json_text(results),
        "summary.json": json_text(summary),
        "report.md": _report(results, summary, config, len(labeled)),
    }
    create_output(output)
    for filename, content in files.items():
        write_text(output / filename, content)
    write_json(
        output / MANIFEST_NAME,
        {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "source_processed_manifest_sha256": corpus.manifest_sha256,
            "source_vectors_manifest_sha256": stored.manifest_sha256 if stored else None,
            "vectors_config_sha256": sha256(vectors_config),
            "config_sha256": sha256(config_path),
            "source_identity": source_identity(),
            "python": platform.python_version(),
            "libraries": library_versions(),
            "files": hash_files(output),
        },
    )
    verify(output)
    return {"representations": list(results), "k": [config.k_min, config.k_max], "output": str(output)}


def verify(output: Path) -> dict:
    """Confere os hashes do manifesto."""
    manifest = read_manifest(output)
    verify_hashes(output, manifest["files"])
    return {"status": "ok", "files_verified": len(manifest["files"])}


def _best(rows: list[dict]) -> dict:
    return {
        "maior_silhueta": max(rows, key=lambda row: row["silhueta_cosseno"])["k"],
        "menor_davies_bouldin": min(rows, key=lambda row: row["davies_bouldin"])["k"],
        "maior_calinski_harabasz": max(rows, key=lambda row: row["calinski_harabasz"])["k"],
        "maior_ari": max(rows, key=lambda row: row["ari"])["k"],
        "maior_nmi": max(rows, key=lambda row: row["nmi"])["k"],
    }


def _report(results: dict, summary: dict, config: SweepConfig, labeled: int) -> str:
    lines = [
        "# Varredura do número de clusters",
        "",
        f"K-Means (k-means++, 10 inicializações, semente {config.random_state}) sobre as linhas com norma L2 de cada representação, "
        f"para k de {config.k_min} a {config.k_max}. ARI, NMI e pureza usam os {labeled} filmes de um único gênero.",
        "",
        "## Melhor k por métrica",
        "",
        "| Representação | Silhueta | Davies-Bouldin | Calinski-Harabasz | ARI | NMI |",
        "|---|---:|---:|---:|---:|---:|",
        *(
            f"| `{name}` | {best['maior_silhueta']} | {best['menor_davies_bouldin']} | {best['maior_calinski_harabasz']} | {best['maior_ari']} | {best['maior_nmi']} |"
            for name, best in summary.items()
        ),
        "",
    ]
    for name, rows in results.items():
        lines += [
            f"## `{name}`",
            "",
            "| k | Silhueta | Davies-Bouldin | Calinski-Harabasz | Dist. ao centroide | Dist. entre centroides | ARI | NMI | Pureza | Tamanhos |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
            *(
                f"| {r['k']} | {r['silhueta_cosseno']:.3f} | {r['davies_bouldin']:.3f} | {r['calinski_harabasz']:.1f} | {r['distancia_ao_centroide']:.3f} | "
                f"{r['distancia_entre_centroides']:.3f} | {r['ari']:.3f} | {r['nmi']:.3f} | {r['pureza']:.3f} | {', '.join(map(str, r['tamanhos']))} |"
                for r in rows
            ),
            "",
        ]
    return "\n".join(lines)
