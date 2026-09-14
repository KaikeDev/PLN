"""Representações comparáveis sem sobrescrever o texto original."""
import html
import re
import unicodedata
from html.parser import HTMLParser

TOKEN_PATTERN = r"\w+(?:['’\-]\w+)*|[^\w\s]"
TOKEN_RE = re.compile(TOKEN_PATTERN, re.UNICODE)
URL_RE = re.compile(r"https?://[^\s<>]+|www\.[^\s<>]+", re.IGNORECASE)
PRESERVED_NEGATIONS = {"não", "nem", "nunca", "sem"}


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "div", "br", "li"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1
        if tag in {"p", "div", "li"}:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def clean(text: str | None) -> str | None:
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
    return any(ch.isalnum() for ch in token)


def representations(text: str | None, stopwords: set[str]) -> dict:
    cleaned = clean(text)
    normalized = cleaned.casefold() if cleaned is not None else None
    tokens = TOKEN_RE.findall(normalized or "")
    words = [token for token in tokens if word_token(token)]
    filtered = [token for token in words if token not in stopwords or token in PRESERVED_NEGATIONS]
    return {"clean": cleaned, "normalized": normalized, "tokens": tokens, "words": words, "filtered": filtered}
