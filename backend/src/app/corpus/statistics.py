"""Medidas lexicais e de composição da amostra processada.

As medidas de extensão e vocabulário usam apenas sinopses preenchidas; as contagens de filmes e de
ausência usam toda a base. Tokens de pontuação não entram nas medidas do texto original.
"""

import statistics
from collections import Counter

from app.corpus.contracts import Representations
from app.corpus.transform import TOKEN_RE, word_token


def lexical_metrics(documents: list[list[str]]) -> dict:
    """Tokens, tipos, TTR, extensão média e mediana e os 20 termos mais frequentes."""
    counts = Counter(token for document in documents for token in document)
    total = sum(counts.values())
    lengths = [len(document) for document in documents]
    return {
        "documents": len(documents),
        "tokens": total,
        "types": len(counts),
        "type_token_ratio": len(counts) / total if total else 0,
        "mean_tokens": statistics.mean(lengths) if lengths else 0,
        "median_tokens": statistics.median(lengths) if lengths else 0,
        "most_frequent": counts.most_common(20),
    }


def has_overview(movie: dict) -> bool:
    """Verdadeiro quando a sinopse original existe e não é só espaço."""
    return bool(movie.get("overview") and movie["overview"].strip())


def release_decade(movie: dict) -> str:
    """Década de lançamento como `AAA0`, ou `unknown` quando a data está ausente ou malformada."""
    release_date = movie.get("release_date") or ""
    return release_date[:3] + "0" if release_date[:4].isdigit() else "unknown"


def compute_statistics(
    movies: list[dict],
    metadata: list[dict],
    transformed: dict[int, Representations],
    memberships: dict[str, list[str]],
) -> dict:
    """Estatísticas globais e por recorte de coleta, na ordem de chaves gravada em `statistics.json`."""
    valid = [movie for movie in movies if has_overview(movie)]
    missing = len(movies) - len(valid)
    original_documents = [[token for token in TOKEN_RE.findall(movie["overview"]) if word_token(token)] for movie in valid]
    stats = {
        "unique_movies": len(movies),
        "valid_overviews": len(valid),
        "missing_overviews": missing,
        "missing_overviews_percent": missing / len(movies) * 100,
        "mean_characters_original": statistics.mean(len(movie["overview"]) for movie in valid) if valid else 0,
        "median_characters_original": statistics.median(len(movie["overview"]) for movie in valid) if valid else 0,
        "original": lexical_metrics(original_documents),
        "normalized_without_punctuation": lexical_metrics([transformed[movie["id"]]["words"] for movie in valid]),
        "filtered": lexical_metrics([transformed[movie["id"]]["filtered"] for movie in valid]),
        "original_languages": dict(Counter(movie.get("original_language") or "unknown" for movie in movies)),
        "release_decades": dict(Counter(release_decade(movie) for movie in movies)),
        "genre_memberships": dict(Counter(str(genre) for row in metadata for genre in row["genre_ids"])),
        "changed_by_cleaning": sum(movie.get("overview") != transformed[movie["id"]]["clean"] for movie in movies),
        "slices": {},
    }
    for label in sorted({label for labels in memberships.values() for label in labels}):
        members = [movie for movie in movies if label in memberships.get(str(movie["id"]), [])]
        documents = [transformed[movie["id"]]["filtered"] for movie in members if has_overview(movie)]
        stats["slices"][label] = {"movies": len(members), "valid_overviews": len(documents), "filtered": lexical_metrics(documents)}
    return stats
