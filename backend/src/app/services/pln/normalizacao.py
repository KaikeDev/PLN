import re
import unicodedata

_RE_TOKEN = re.compile(r"\w+", re.UNICODE)


def normalizar(texto: str) -> str:
    """minusculas + remove acentos (NFKD) + colapsa espacos."""
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento).strip()


def tokenizar(texto_normalizado: str) -> list[str]:
    """Tokens alfanumericos extraidos de um texto ja normalizado."""
    return _RE_TOKEN.findall(texto_normalizado)
