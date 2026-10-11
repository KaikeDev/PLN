"""Reúne os números do Trabalho da Unidade 3 que ainda não estavam num único arquivo.

Rode em `backend`, depois de gerar o catálogo do site (docs/tecnico/rodar-o-site.md):

    uv run --frozen --extra semantico python ../docs/entregas/unidade-3/coletar_resultados.py

Gera `resultados.json` nesta pasta, com:

- **busca:** os 5 primeiros filmes de cada representação e da combinação do site em cada uma das 20 consultas
  anotadas, e a precisão @3 e @5 média de cada uma (a amostra de 428 sinopses);
- **dados novos:** o classificador de gênero da Etapa 3, treinado nas sinopses de um gênero da amostra, aplicado
  às sinopses do catálogo do site que não estão na amostra e têm exatamente um dos quatro gêneros.
"""

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from app.classification.alternatives import ALTERNATIVES
from app.classification.config import load_config as load_classification_config
from app.classification.dataset import make_tasks
from app.classification.evaluation import LOGISTIC, estimator, features
from app.representations.methods import METHODS
from app.representations.pipeline import build_one
from app.search.hybrid import HybridIndex, load_search_config

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data"
SAMPLE = DATA / "preparacao" / "tmdb_2026-09-12"
SAMPLE_VECTORS = DATA / "representacoes" / "tmdb_2026-09-12"
CATALOG = DATA / "preparacao" / "site_2026-10-05"
CATALOG_VECTORS = DATA / "representacoes" / "site_2026-10-05"
VECTORS_CONFIG = REPO / "config" / "representacoes" / "vetorizacao_semantica.json"
SITE_CONFIG = REPO / "config" / "representacoes" / "vetorizacao_site.json"
CLASSIFICATION_CONFIG = REPO / "config" / "classificacao" / "classificacao_semantica.json"
OUTPUT = Path(__file__).resolve().parent / "resultados.json"


def search() -> dict:
    queries = json.loads((REPO / "config" / "busca" / "consultas.json").read_text(encoding="utf-8"))["queries"]
    retrieval = json.loads((SAMPLE_VECTORS / "retrieval.json").read_text(encoding="utf-8"))
    rankings: dict[str, dict[str, list[dict]]] = {}
    for name, result in retrieval.items():
        rankings[name] = {q["id"]: [{"id": t["id"], "title": t["title"]} for t in q["top"][:5]] for q in result["queries"]}
    index = HybridIndex.build(SAMPLE, VECTORS_CONFIG, load_search_config(REPO / "config" / "busca" / "busca.json"), vectors=SAMPLE_VECTORS)
    titles = {document.id: document.title for document in index.corpus.documents}
    rankings["combinacao"] = {q["id"]: [{"id": i, "title": titles[i]} for i, _ in index.rank(q["text"])[:5]] for q in queries}
    relevant = {q["id"]: set(q["relevant_ids"]) for q in queries}
    precision = {
        name: {
            f"p@{k}": round(float(np.mean([sum(t["id"] in relevant[q] for t in ranked[q][:k]) / k for q in relevant])), 4)
            for k in (3, 5)
        }
        for name, ranked in rankings.items()
    }
    return {
        "consultas": [{"id": q["id"], "texto": q["text"], "relevantes": q["relevant_ids"]} for q in queries],
        "top5": rankings,
        "precisao": precision,
    }


def new_data() -> dict:
    config = load_classification_config(CLASSIFICATION_CONFIG, METHODS, ALTERNATIVES)
    labels = config.labels
    result = {}
    for name in ("tfidf_sem_stopwords", "sentenca_minilm"):
        corpus, representation = build_one(SAMPLE, VECTORS_CONFIG, name, vectors=SAMPLE_VECTORS)
        task, _ = make_tasks(corpus, labels, config.inner_folds)
        source = features(representation)
        model = estimator(LOGISTIC, task, source, config).fit(source.take(task.rows), task.targets)
        catalog, catalog_representation = build_one(CATALOG, SITE_CONFIG, name, vectors=CATALOG_VECTORS if name != "tfidf_sem_stopwords" else None)
        sample_ids = set(corpus.ids)
        position = {label: index for index, label in enumerate(labels)}
        rows, truth = [], []
        for row, document in enumerate(catalog.documents):
            genres = document.tmdb_genres & set(labels)
            if document.id not in sample_ids and len(genres) == 1:
                rows.append(row)
                truth.append(position[next(iter(genres))])
        catalog_source = features(catalog_representation)
        predicted = model.predict(catalog_source.take(np.asarray(rows)))
        truth_array = np.asarray(truth)
        result[name] = {
            "treino": len(task.rows),
            "teste": len(rows),
            "f1_macro": round(float(f1_score(truth_array, predicted, average="macro")), 4),
            "acuracia": round(float(accuracy_score(truth_array, predicted)), 4),
            "f1_por_genero": dict(
                zip(task.label_names, [round(float(v), 4) for v in f1_score(truth_array, predicted, average=None, labels=list(range(len(labels))))], strict=True)
            ),
            "suporte": dict(zip(task.label_names, np.bincount(truth_array, minlength=len(labels)).tolist(), strict=True)),
            "matriz_confusao": confusion_matrix(truth_array, predicted, labels=list(range(len(labels)))).tolist(),
            "generos": list(task.label_names),
        }
    return result


def main() -> None:
    results = {"busca": search(), "dados_novos": new_data()}
    OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"precisao": results["busca"]["precisao"], "dados_novos": {k: {x: v[x] for x in ("treino", "teste", "f1_macro", "acuracia")} for k, v in results["dados_novos"].items()}}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
