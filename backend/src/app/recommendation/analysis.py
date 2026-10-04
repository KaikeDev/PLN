"""Recomendação por conteúdo sobre cada representação: item → item, por perfil e avaliação por gênero compartilhado."""

from statistics import mean

import numpy as np
from sklearn.preprocessing import normalize

from app.representations.analyses import Analysis
from app.representations.config import ProfileSpec
from app.representations.context import AnalysisContext
from app.representations.metrics import genre_agreement, rounded
from app.representations.report import number, titled
from app.representations.space import Encoded, Representation
from app.shared.artifacts import jsonl_text


class Recommendation(Analysis):
    """Recomendação por conteúdo: os k filmes de maior cosseno com um filme (item → item) ou com um perfil.

    O perfil é a média, com norma L2, dos vetores dos filmes de que a pessoa gostou. Sem avaliações de
    usuários, a avaliação offline usa os gêneros como aproximação de relevância: a precisão @k é a fração
    dos recomendados que compartilham ao menos um gênero com o filme (ou com os filmes do perfil), e a
    referência é essa fração sobre todos os demais filmes, o esperado de uma recomendação que ignora o texto.
    """

    name = "recommendation"

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]:
        return recommendation_section(results, context)

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


def recommendation_section(results: dict, context: AnalysisContext) -> list[str]:
    names = context.representation_names
    k = context.config.neighbors_k
    lines = [
        "## Recomendação: filmes parecidos",
        "",
        f"Recomendação por conteúdo: para cada filme, os {k} filmes de maior cosseno com a sinopse dele (item → item); para um perfil, "
        "os de maior cosseno com a média dos filmes de que a pessoa gostou. Sem avaliações de usuários, a relevância é aproximada pelos gêneros: "
        "a precisão @k é a fração dos recomendados com ao menos um gênero em comum, e a referência é essa fração sobre todos os demais filmes, "
        "o esperado de uma recomendação que ignora o texto. As recomendações de todos os filmes estão em `<representação>.recommendations.jsonl`. "
        "Nas representações lexicais a explicação lista termos idênticos; no word2vec, pares de palavras próximas (≈); "
        "o modelo contextual não é explicável por palavras.",
        "",
        f"| Representação | Precisão @{k} | Referência | Ganho sobre a referência | Filmes avaliados |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in names:
        row = results[name]
        precision, baseline = row["precision_at_k"], row["baseline"]
        gain = precision - baseline if precision is not None and baseline is not None else None
        lines.append(f"| {name} | {number(precision)} | {number(baseline)} | {number(gain)} | {row['documents_evaluated']} |")
    lines.append("")
    for index, movie_id in enumerate(context.config.example_ids):
        example = results[names[0]]["examples"][index]
        genres = ", ".join(example["genres"]) or "nenhum da coleta"
        lines += [f"### Quem gostou de {example['title']} ({movie_id})", "", f"Gêneros: {genres}.", ""]
        for name in names:
            items = results[name]["examples"][index]["recommendations"][:3]
            lines.append(f"- **{name}**: {'; '.join(titled(item) for item in items) or 'nenhuma recomendação'}")
        lines.append("")
    for index, profile in enumerate(context.config.profiles):
        first = results[names[0]]["profiles"][index]
        lines += [f"### Perfil `{profile.id}`: gostou de {', '.join(movie['title'] for movie in first['movies'])}", ""]
        if profile.note:
            lines += [profile.note, ""]
        lines += [
            f"Gêneros do perfil: {', '.join(first['genres']) or 'nenhum da coleta'}.",
            "",
            f"| Representação | Precisão @{k} | Primeiras recomendações |",
            "|---|---:|---|",
        ]
        for name in names:
            item = results[name]["profiles"][index]
            top = "; ".join(f"{rec['title']} ({rec['score']:.3f})" for rec in item["recommendations"][:3]) or "nenhuma recomendação"
            lines.append(f"| {name} | {number(item['precision_at_k'])} | {top} |")
        lines.append("")
    return lines
