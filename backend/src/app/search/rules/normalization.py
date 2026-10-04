"""Normalização da pesquisa: minúsculas, sem acentos e com espaços uniformizados.

Difere da normalização do corpus, que preserva acentos (ADR 0003): aqui o objetivo é casar o que a
pessoa digitou, com ou sem acento, com um léxico fixo.
"""

import re
import unicodedata

TOKEN_RE = re.compile(r"\w+", re.UNICODE)
SPACES_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Minúsculas, remoção de acentos por decomposição NFKD e espaços colapsados."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return SPACES_RE.sub(" ", without_accents).strip()


def tokenize(normalized_text: str) -> list[str]:
    """Tokens alfanuméricos de um texto já normalizado."""
    return TOKEN_RE.findall(normalized_text)
