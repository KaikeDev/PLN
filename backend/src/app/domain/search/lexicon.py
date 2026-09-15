"""Léxico de gêneros e de qualidade reconhecido na pesquisa por preferências.

Os gatilhos estão normalizados (sem acento). Os nomes de gênero são comparados, também normalizados,
com os nomes devolvidos pelo catálogo. Os limiares de qualidade combinam nota mínima e quantidade
mínima de votos, para que poucos votos não bastem para atingir a nota (ADR 0005).
"""

import re
from dataclasses import dataclass
from typing import Final

from app.domain.search.negation import QUALITY_WINDOW, is_negated
from app.domain.search.normalization import tokenize

GENRE_TRIGGERS: Final[dict[str, tuple[str, ...]]] = {
    "descontraido": ("Comedia", "Familia"),
    "descontraida": ("Comedia", "Familia"),
    "leve": ("Comedia", "Familia"),
    "divertido": ("Comedia",),
    "divertida": ("Comedia",),
    "engracado": ("Comedia",),
    "engracada": ("Comedia",),
    "comedia": ("Comedia",),
    "familia": ("Familia",),
    "infantil": ("Familia", "Animacao"),
    "animacao": ("Animacao",),
    "tenso": ("Terror", "Thriller"),
    "tensa": ("Terror", "Thriller"),
    "assustador": ("Terror",),
    "assustadora": ("Terror",),
    "medo": ("Terror",),
    "terror": ("Terror",),
    "suspense": ("Thriller", "Misterio"),
    "misterio": ("Misterio",),
    "emocionante": ("Drama", "Romance"),
    "drama": ("Drama",),
    "thriller": ("Thriller",),
    "dramatico": ("Drama",),
    "dramatica": ("Drama",),
    "romantico": ("Romance",),
    "romantica": ("Romance",),
    "romance": ("Romance",),
    "acao": ("Acao",),
    "aventura": ("Aventura",),
    "fantasia": ("Fantasia",),
    "ficcao": ("Ficcao cientifica",),
    "guerra": ("Guerra",),
    "policial": ("Crime",),
    "crime": ("Crime",),
    "investigacao": ("Crime", "Misterio"),
    "documentario": ("Documentario",),
    "musical": ("Musica",),
    "historico": ("Historia",),
    "historica": ("Historia",),
}


@dataclass(frozen=True)
class QualityThreshold:
    """Nota média mínima e quantidade mínima de votos."""

    min_rating: float
    min_votes: int


HIGH_QUALITY = QualityThreshold(7.0, 100)
VERY_HIGH_QUALITY = QualityThreshold(8.0, 200)

HIGH_QUALITY_EXPRESSIONS: Final = (
    "bem avaliado",
    "bem avaliada",
    "bem avaliados",
    "boa avaliacao",
    "boas avaliacoes",
    "aclamado",
    "aclamada",
)

VERY_HIGH_QUALITY_EXPRESSIONS: Final = (
    "muito bem avaliado",
    "muito bem avaliada",
    "excelente",
    "nota alta",
    "aclamadissimo",
    "aclamadissima",
    "obra-prima",
    "obra prima",
)


def find_genres(tokens: list[str]) -> dict[str, list[str]]:
    """Gatilhos encontrados e os nomes de gênero associados, indexados pelo token que os disparou."""
    return {token: list(GENRE_TRIGGERS[token]) for token in tokens if token in GENRE_TRIGGERS}


def find_quality(normalized_text: str) -> QualityThreshold | None:
    """Limiar de qualidade da expressão afirmada mais forte; None quando não há expressão afirmada."""
    if any(_affirmed(expression, normalized_text) for expression in VERY_HIGH_QUALITY_EXPRESSIONS):
        return VERY_HIGH_QUALITY
    if any(_affirmed(expression, normalized_text) for expression in HIGH_QUALITY_EXPRESSIONS):
        return HIGH_QUALITY
    return None


def _affirmed(expression: str, normalized_text: str) -> bool:
    pattern = re.compile(r"\b" + re.escape(expression) + r"\b")
    return any(not is_negated(tokenize(normalized_text[: match.start()]), QUALITY_WINDOW) for match in pattern.finditer(normalized_text))
