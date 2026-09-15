"""Negação local por janela de tokens anteriores ao gatilho.

Os marcadores são os mesmos do corpus (`app.shared.language`), sem acento. A janela de gêneros é
curta porque o gatilho é uma palavra; a de qualidade é maior porque as expressões têm várias palavras
("não quero nada com boa avaliação"). A regra não interpreta toda a semântica da negação (ADR 0005).
"""

from collections.abc import Mapping, Sequence

from app.domain.search.normalization import normalize
from app.shared.language import NEGATION_MARKERS

MARKERS = frozenset(normalize(marker) for marker in NEGATION_MARKERS)
GENRE_WINDOW = 3
QUALITY_WINDOW = 5


def is_negated(preceding_tokens: Sequence[str], window: int) -> bool:
    """Verdadeiro quando há marcador de negação entre os últimos `window` tokens."""
    return any(token in MARKERS for token in preceding_tokens[-window:]) if window else False


def split_negated_genres(tokens: list[str], genre_matches: Mapping[str, Sequence[str]]) -> tuple[list[str], list[str]]:
    """Separa os nomes de gênero em (incluídos, excluídos), sem repetição e na ordem do texto."""
    included: list[str] = []
    excluded: list[str] = []
    for index, token in enumerate(tokens):
        names = genre_matches.get(token)
        if not names:
            continue
        target = excluded if is_negated(tokens[:index], GENRE_WINDOW) else included
        for name in names:
            if name not in target:
                target.append(name)
    return included, excluded
