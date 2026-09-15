"""Período de lançamento pedido em linguagem natural.

A ordem de prioridade é década ("dos anos 90") > ano explícito ("depois de 2015", "antes de 2020") >
termos relativos ("recente", "antigo"). "Depois de X" é inclusivo (a partir de 1º/1/X) e "antes de X"
termina em 31/12/(X-1). Décadas até 29 são do século XXI. Frases de recência com negação ("não muito
antigo") são testadas antes de "antigo" isolado (ADR 0005).
"""

import re
from dataclasses import dataclass
from datetime import date

from app.shared.language import MAX_RELEASE_YEAR, MIN_RELEASE_YEAR

DECADE_RE = re.compile(r"\bdos anos (\d{2})\b")
EXPLICIT_YEAR_RE = re.compile(r"\b(depois de|apos|a partir de|antes de)\s+(\d{4})\b")
LAST_21ST_CENTURY_DECADE = 29
RECENT_YEARS = 10
OLD_YEARS = 25

RECENT_TERMS = (
    "nao seja muito antigo",
    "nao muito antigo",
    "nao seja muito antiga",
    "nao muito antiga",
    "recente",
    "recentes",
    "novo",
    "nova",
    "atual",
    "atuais",
)
OLD_TERMS = ("antigo", "antiga", "classico", "classica", "cult")


@dataclass(frozen=True)
class Period:
    """Limites de data de lançamento no formato AAAA-MM-DD; None quando o limite não foi pedido."""

    released_after: str | None = None
    released_before: str | None = None


def extract_period(normalized_text: str, current_year: int | None = None) -> Period:
    """Período pedido em `normalized_text`, relativo a `current_year` (padrão: ano atual)."""
    year = current_year if current_year is not None else date.today().year
    decade = DECADE_RE.search(normalized_text)
    if decade:
        value = int(decade.group(1))
        start = (2000 if value <= LAST_21ST_CENTURY_DECADE else 1900) + value
        return Period(f"{start}-01-01", f"{start + 9}-12-31")

    explicit = list(EXPLICIT_YEAR_RE.finditer(normalized_text))
    if explicit:
        return _explicit_period(explicit)

    if _contains_any(normalized_text, RECENT_TERMS):
        return Period(released_after=f"{year - RECENT_YEARS}-01-01")
    if _contains_any(normalized_text, OLD_TERMS):
        return Period(released_before=f"{year - OLD_YEARS}-01-01")
    return Period()


def _explicit_period(matches: list[re.Match[str]]) -> Period:
    lower, upper = [], []
    for match in matches:
        direction, year = match.group(1), int(match.group(2))
        if not MIN_RELEASE_YEAR <= year <= MAX_RELEASE_YEAR:
            continue
        if direction == "antes de":
            upper.append(f"{year - 1}-12-31")
        else:
            lower.append(f"{year}-01-01")
    return Period(max(lower) if lower else None, min(upper) if upper else None)


def _contains_any(normalized_text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(r"\b" + re.escape(term) + r"\b", normalized_text) for term in terms)
