"""Preparação das críticas: filtro, as seis etapas de texto da Etapa 1 e evidências (ADR 0026).

A pasta gerada tem o mesmo formato da pasta processada da Etapa 1 (etapas, `metadata.jsonl`, manifesto),
então `ProcessedCorpus` e as oito representações funcionam sem mudança. Cada crítica recebe um ID inteiro
sequencial, na ordem (filme, crítica); `metadata.jsonl` guarda o ID da crítica no TMDB, o filme e a nota.

Parte das críticas é bilíngue, com seções sob cabeçalhos como "**Português**", "**Portuguese**" e "**English**": só o texto
fora das seções em inglês é usado (`portuguese_part`). Ficam de fora, com o motivo em `excluded.json`:
críticas sem nota, com menos de `MIN_CHARS` caracteres depois da limpeza ou que não parecem estar em
português (mais palavras funcionais do inglês que do português). A limpeza é a da Etapa 1, que preserva os
marcadores de negação, importantes para o sentimento.
"""

import platform
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

from app.corpus.contracts import STAGES
from app.corpus.process import load_stopwords, transform_movies
from app.corpus.transform import PRESERVED_NEGATIONS, TOKEN_PATTERN, clean
from app.corpus.verification import verify_processed
from app.sentiment.collect import verify_collection
from app.shared.artifacts import create_output, json_text, read_jsonl, sha256, source_identity, write_json, write_jsonl, write_text
from app.shared.manifest import hash_files

MIN_CHARS = 30
WORD_RE = re.compile(r"\w+", re.UNICODE)
SECTION_RE = re.compile(r"^[\W_]*(english|portugu[eê]s|portuguese)[\W_]*$", re.IGNORECASE)
PORTUGUESE = frozenset(
    {"o", "a", "os", "as", "de", "do", "da", "que", "e", "é", "um", "uma", "em", "no", "na", "não", "para", "com", "se", "mais"}
)
ENGLISH = frozenset({"the", "and", "of", "to", "is", "this", "that", "it", "was", "with", "for", "but", "are", "be"})


def portuguese_part(content: str) -> str:
    """Texto sem as seções em inglês de críticas bilíngues; críticas sem cabeçalho de idioma ficam inteiras."""
    kept, english = [], False
    for line in content.splitlines():
        if match := SECTION_RE.fullmatch(line.strip()):
            english = match.group(1).casefold() == "english"
            continue
        if not english:
            kept.append(line)
    return "\n".join(kept).strip()


def has_english_section(content: str) -> bool:
    """Verdadeiro quando a crítica tem uma seção sob o cabeçalho "English"."""
    return any((match := SECTION_RE.fullmatch(line.strip())) and match.group(1).casefold() == "english" for line in content.splitlines())


def exclusion(review: dict) -> str | None:
    """Motivo para deixar a crítica de fora, ou None se ela entra no corpus."""
    if review["rating"] is None:
        return "sem_nota"
    text = clean(portuguese_part(review["content"])) or ""
    if len(text) < MIN_CHARS:
        return "curta_demais"
    words = Counter(WORD_RE.findall(text.casefold()))
    if sum(words[word] for word in ENGLISH) >= sum(words[word] for word in PORTUGUESE):
        return "outro_idioma"
    return None


def process(collection: Path, output: Path, stopwords_path: Path) -> dict:
    """Filtra as críticas de `collection` e grava as etapas de texto numa pasta nova."""
    if output.exists():
        raise FileExistsError(f"A pasta de saída já existe: {output}")
    verify_collection(collection)
    reviews = read_jsonl(collection / "reviews.jsonl")
    kept, excluded = [], []
    for review in reviews:
        reason = exclusion(review)
        if reason is None:
            kept.append(review)
        else:
            excluded.append({"review_id": review["review_id"], "movie_id": review["movie_id"], "reason": reason})
    if not kept:
        raise ValueError("Nenhuma crítica utilizável na coleta")
    stopwords = load_stopwords(stopwords_path)
    documents = [
        {"id": number, "title": review["title"], "overview": portuguese_part(review["content"])} for number, review in enumerate(kept, 1)
    ]
    corpus = transform_movies(documents, stopwords)
    metadata = [
        {
            "id": number,
            "review_id": review["review_id"],
            "movie_id": review["movie_id"],
            "title": review["title"],
            "rating": review["rating"],
            "author_key": review["author_key"],
            "created_at": review["created_at"],
            "genre_ids": [],
            "overview_missing": False,
        }
        for number, review in enumerate(kept, 1)
    ]
    statistics = _statistics(reviews, kept, excluded, corpus.by_id)

    create_output(output)
    for filename, rows in corpus.stage_rows.items():
        write_jsonl(output / filename, rows)
    write_jsonl(output / "metadata.jsonl", metadata)
    write_json(output / "excluded.json", excluded)
    write_json(output / "stopwords_used.json", sorted(stopwords))
    write_json(output / "memberships.json", {})
    write_json(output / "genres.json", {"genres": []})
    write_json(output / "statistics.json", statistics)
    write_text(output / "report.md", _report(statistics))
    write_json(
        output / "manifest.json",
        {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "collection_manifest_sha256": sha256(collection / "manifest.json"),
            "source_reviews_sha256": sha256(collection / "reviews.jsonl"),
            "source_identity": source_identity(),
            "python": platform.python_version(),
            "token_pattern": TOKEN_PATTERN,
            "preserved_negations": sorted(PRESERVED_NEGATIONS),
            "stopwords_source_sha256": sha256(stopwords_path),
            "min_chars": MIN_CHARS,
            "stages": STAGES,
            "files": hash_files(output),
        },
    )
    verify_processed(output)
    return {
        "collected": len(reviews),
        "kept": len(kept),
        "excluded": dict(Counter(row["reason"] for row in excluded)),
        "output": str(output),
    }


def _statistics(reviews: list[dict], kept: list[dict], excluded: list[dict], by_id: dict) -> dict:
    ratings = Counter(review["rating"] for review in kept)
    words = [len(stages["words"]) for stages in by_id.values()]
    authors = Counter(review["author_key"] for review in kept)
    return {
        "collected": len(reviews),
        "kept": len(kept),
        "english_sections_removed": sum(has_english_section(review["content"]) for review in kept),
        "excluded": dict(sorted(Counter(row["reason"] for row in excluded).items())),
        "movies": len({review["movie_id"] for review in kept}),
        "authors": len(authors),
        "largest_author_share": round(max(authors.values()) / len(kept), 4),
        "reviews_per_author_top5": sorted(authors.values(), reverse=True)[:5],
        "ratings": {str(rating): count for rating, count in sorted(ratings.items())},
        "words": {"min": min(words), "median": median(words), "max": max(words)},
    }


def _report(statistics: dict) -> str:
    lines = [
        "# Preparação das críticas",
        "",
        f"- Críticas coletadas: {statistics['collected']}",
        f"- Críticas mantidas: {statistics['kept']}, de {statistics['movies']} filmes e {statistics['authors']} autores",
        f"- Críticas bilíngues em que a seção em inglês foi removida: {statistics['english_sections_removed']}",
        f"- Excluídas por motivo: {json_text(statistics['excluded']).strip()}",
        f"- Maior parcela de um único autor: {statistics['largest_author_share']:.1%}",
        f"- Palavras por crítica: mínimo {statistics['words']['min']}, mediana {statistics['words']['median']}, máximo {statistics['words']['max']}",
        "",
        "| Nota | Críticas |",
        "|---:|---:|",
        *(f"| {rating} | {count} |" for rating, count in statistics["ratings"].items()),
        "",
    ]
    return "\n".join(lines)
