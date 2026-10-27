"""Contexto e pedido do RAG: blocos numerados `[F<id>]` com sinopse e trechos de crítica.

O texto de terceiros (títulos, sinopses e críticas) passa por `neutralize`: uma marca `[F123]` escrita numa
sinopse viraria uma citação falsa, então os colchetes de qualquer `[F…]` vindo dali são trocados por
parênteses. A pergunta vai entre aspas, com escape de JSON. O mesmo contexto gera sempre o mesmo texto.
"""

import json
import re
from collections.abc import Mapping

from app.rag.config import RagConfig
from app.rag.retrieval import Retrieval, RetrievedMovie

CITATION_LIKE = re.compile(r"\[(\s*F\s*\d*[^\]]*)\]", re.IGNORECASE)


def neutralize(text: str) -> str:
    """Texto de terceiros sem marcas que pareçam citações; espaços e quebras de linha colapsados."""
    return CITATION_LIKE.sub(r"(\1)", " ".join(str(text).split()))


def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def movie_block(item: RetrievedMovie, genre_names: Mapping[int, str], config: RagConfig) -> str:
    movie = item.movie
    year = (movie.get("release_date") or "")[:4] or "s/d"
    genres = ", ".join(genre_names.get(genre, str(genre)) for genre in movie.get("genre_ids") or []) or "sem gênero"
    rating = movie.get("vote_average")
    rating_text = f"nota TMDB {rating:.1f}".replace(".", ",") if isinstance(rating, int | float) else "sem nota TMDB"
    lines = [
        f"[F{item.id}] {neutralize(movie.get('title') or 'Sem título')} ({year}) — {genres} — {rating_text}",
        f"Sinopse: {truncate(neutralize(movie.get('overview') or 'sem sinopse'), config.overview_chars)}",
    ]
    if item.excerpts:
        lines.append("Críticas:")
        lines += [f'- "{neutralize(excerpt.text)}" (nota do autor: {_rating(excerpt.rating)})' for excerpt in item.excerpts]
    elif config.excerpts_per_movie:
        lines.append("Críticas: nenhuma coletada.")
    return "\n".join(lines)


def context_text(retrieval: Retrieval, genre_names: Mapping[int, str], config: RagConfig) -> str:
    if not retrieval.movies:
        return "CONTEXTO: nenhum filme encontrado."
    return "CONTEXTO:\n\n" + "\n\n".join(movie_block(item, genre_names, config) for item in retrieval.movies)


def user_prompt(question: str, retrieval: Retrieval, genre_names: Mapping[int, str], config: RagConfig) -> str:
    return f"{context_text(retrieval, genre_names, config)}\n\nPERGUNTA: {json.dumps(question, ensure_ascii=False)}"


def _rating(value: float | None) -> str:
    return "sem nota" if value is None else f"{value:g}/10".replace(".", ",")
