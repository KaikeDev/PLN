"""Representações comparáveis de uma sinopse, sem sobrescrever o texto original.

A limpeza remove marcação HTML, URLs e caracteres de controle e aplica Unicode NFC. A normalização usa
`casefold` e preserva acentos. A tokenização separa palavras (com apóstrofos e hífens internos) de
pontuação. O filtro de stopwords nunca remove marcadores de negação.
"""

import html
import re
import unicodedata
from html.parser import HTMLParser

from app.corpus.contracts import Representations
from app.shared.language import NEGATION_MARKERS

TOKEN_PATTERN = r"\w+(?:['’\-]\w+)*|[^\w\s]"
TOKEN_RE = re.compile(TOKEN_PATTERN, re.UNICODE)
URL_RE = re.compile(r"https?://[^\s<>]+|www\.[^\s<>]+", re.IGNORECASE)
PRESERVED_NEGATIONS = NEGATION_MARKERS

HIDDEN_TAGS = frozenset({"script", "style"})
BLOCK_START_TAGS = frozenset({"p", "div", "br", "li"})
BLOCK_END_TAGS = frozenset({"p", "div", "li"})


class VisibleText(HTMLParser):
    """Extrai o texto visível de um fragmento HTML, separando blocos por espaço."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in HIDDEN_TAGS:
            self.hidden += 1
        if tag in BLOCK_START_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in HIDDEN_TAGS and self.hidden:
            self.hidden -= 1
        if tag in BLOCK_END_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def clean(text: str | None) -> str | None:
    """Texto visível, sem URLs nem caracteres de controle, em NFC e com espaços uniformizados."""
    if text is None:
        return None
    if not isinstance(text, str):
        raise ValueError("overview deve ser texto ou null")
    parser = VisibleText()
    parser.feed(text)
    value = unicodedata.normalize("NFC", html.unescape("".join(parser.parts)))
    value = URL_RE.sub(" ", value)
    value = "".join(ch if not unicodedata.category(ch).startswith("C") or ch.isspace() else " " for ch in value)
    return re.sub(r"\s+", " ", value).strip()


def word_token(token: str) -> bool:
    """Verdadeiro quando o token contém ao menos uma letra ou dígito."""
    return any(ch.isalnum() for ch in token)


def representations(text: str | None, stopwords: set[str]) -> Representations:
    """Aplica limpeza, normalização, tokenização, remoção de pontuação e filtro de stopwords."""
    cleaned = clean(text)
    normalized = cleaned.casefold() if cleaned is not None else None
    tokens = TOKEN_RE.findall(normalized or "")
    words = [token for token in tokens if word_token(token)]
    filtered = [token for token in words if token not in stopwords or token in PRESERVED_NEGATIONS]
    return {"clean": cleaned, "normalized": normalized, "tokens": tokens, "words": words, "filtered": filtered}
