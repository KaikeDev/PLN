"""Preparação da consulta antes da busca por tema (ADR 0025).

- **Palavras de pedido:** "quero", "me indica", "um filme sobre"… descrevem o pedido, não o tema. Elas
  puxavam para o topo sinopses que falam de cinema ("O Guia Pervertido do Cinema" em "filmes sobre saúde
  mental"), pelo TF-IDF e pelo embedding. São removidas; se nada sobrar, a consulta original é mantida.
- **Acentos que faltam:** o vocabulário guarda as palavras acentuadas ("saúde"), e uma consulta sem acento
  ("saude") não casava no TF-IDF. Uma palavra digitada sem acento, com pelo menos 4 letras e fora do
  vocabulário é trocada pela forma do vocabulário com as mesmas letras sem acento, se houver uma só. Palavras
  curtas ficam como estão: "a" e "que" virariam "á" e "quê".
"""

import re
import unicodedata
from collections.abc import Iterable

REQUEST_PREFIX = re.compile(
    r"^\s*(?:eu\s+)?(?:"
    r"quero|queria|gostaria(?:\s+de)?|preciso(?:\s+de)?|procuro|estou\s+procurando|busco|"
    r"(?:me\s+)?(?:indica|indique|recomenda|recomende|sugere|sugira|mostra|mostre)(?:\s+me)?"
    r")\b\s*(?:(?:ver|assistir)\b\s*)?",
    re.IGNORECASE,
)
FILM_PHRASE = re.compile(
    r"\b(?:(?:um|uma|uns|umas|algum|alguma|alguns|algumas|o|a|os|as)\s+)?(?:(?:bom|bons|boa|boas|ótimo|ótimos)\s+)?"
    r"(?:filmes?|longas?(?:-metragens?)?)\b"
    r"(?:\s+(?:que\s+(?:fal|trat|mostr)[ae]m?\s+)?(?:sobre|de|do|da|dos|das|com)\b)?",
    re.IGNORECASE,
)
SPACES = re.compile(r"\s+")
WORD = re.compile(r"\w+", re.UNICODE)
MIN_RESTORED_CHARS = 4


def strip_request(text: str) -> str:
    """Tira o pedido e as menções a "filme"; devolve o texto original quando sobraria vazio."""
    cleaned = SPACES.sub(" ", FILM_PHRASE.sub(" ", REQUEST_PREFIX.sub("", text))).strip(" ,.;:!?")
    return cleaned or text


def fold(word: str) -> str:
    """Minúsculas e sem acentos."""
    return "".join(char for char in unicodedata.normalize("NFD", word.casefold()) if unicodedata.category(char) != "Mn")


class AccentRestorer:
    """Troca palavras sem acento pela forma acentuada do vocabulário, quando ela é única."""

    def __init__(self, vocabulary: Iterable[str]) -> None:
        words = set(vocabulary)
        by_fold: dict[str, set[str]] = {}
        for word in words:
            by_fold.setdefault(fold(word), set()).add(word)
        self._known = words
        self._forms = {key: next(iter(forms)) for key, forms in by_fold.items() if len(forms) == 1}

    def restore(self, text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            word = match.group(0)
            folded = fold(word)
            if len(word) < MIN_RESTORED_CHARS or folded != word.casefold() or folded in self._known:
                return word
            return self._forms.get(folded, word)

        return WORD.sub(replace, text)


def prepare_query(text: str, restorer: AccentRestorer | None = None) -> str:
    """Consulta pronta para a busca por tema: sem as palavras de pedido e com os acentos do vocabulário."""
    cleaned = strip_request(text)
    return restorer.restore(cleaned) if restorer is not None else cleaned
