"""Conferência do NER com os créditos do TMDB, sem anotação manual (ADR 0027).

O notebook da aula avalia o NER à mão, numa frase. Aqui os créditos dão uma referência parcial para as pessoas:

- **Menção de pessoa creditada:** uma sequência de palavras com maiúscula da sinopse em que cada palavra faz parte do
  nome de um personagem ou ator do filme ("Forrest Gump", "Andy Dufresne", "Neo"). Palavras genéricas dos créditos
  ("Young", "Agent", "Mrs.") não contam, e apelidos entre aspas ("Dr. William 'Bill' Harford") contam sem as aspas.
- **Revocação de pessoas:** parcela dessas menções que o NER marcou como PER (e, à parte, com qualquer categoria).
- **Precisão estimada:** parcela das entidades PER que contêm ao menos uma palavra dos créditos. É um piso: uma pessoa
  real fora do elenco principal (um diretor, um personagem não creditado) conta como erro.

A referência só cobre pessoas do elenco; lugares e organizações não têm referência automática.
"""

import re
from collections import Counter

from app.representations.metrics import rounded

GENERIC = frozenset(
    {
        "the",
        "young",
        "old",
        "little",
        "big",
        "mr",
        "mrs",
        "ms",
        "miss",
        "dr",
        "agent",
        "officer",
        "detective",
        "captain",
        "sergeant",
        "lieutenant",
        "general",
        "doctor",
        "professor",
        "uncle",
        "aunt",
        "mother",
        "father",
        "man",
        "woman",
        "boy",
        "girl",
        "kid",
        "self",
        "himself",
        "herself",
        "voice",
        "narrator",
        "uncredited",
        "and",
    }
)
NAME_WORD = re.compile(r"[A-ZÀ-Ý][\w'’\-]+")
MIN_NAME_CHARS = 3
QUOTES = "'’\"."


def name_words(cast: list[dict]) -> frozenset[str]:
    """Palavras com maiúscula dos nomes de atores e personagens, sem as genéricas e as muito curtas."""
    words = set()
    for person in cast:
        for value in (person.get("name"), person.get("character")):
            for found in NAME_WORD.findall(value or ""):
                word = found.strip(QUOTES)
                if len(word) >= MIN_NAME_CHARS and word.casefold().strip(".") not in GENERIC:
                    words.add(word)
    return frozenset(words)


def credited_mentions(doc: object, words: frozenset[str]) -> list[tuple[int, int, str]]:
    """Sequências máximas de tokens consecutivos que são palavras dos créditos: (início, fim exclusivo, texto), em tokens."""
    mentions, start = [], None
    tokens = list(doc)  # type: ignore[call-overload]
    for index, token in enumerate([*tokens, None]):
        inside = token is not None and token.text in words
        if inside and start is None:
            start = index
        elif not inside and start is not None:
            mentions.append((start, index, " ".join(t.text for t in tokens[start:index])))
            start = None
    return mentions


def check_film(doc: object, words: frozenset[str]) -> dict:
    """Menções creditadas de uma sinopse com a categoria que o NER deu, e as entidades PER confirmadas ou não."""
    ents = list(doc.ents)  # type: ignore[attr-defined]
    mentions = []
    for start, end, text in credited_mentions(doc, words):
        found = next((ent for ent in ents if ent.start < end and start < ent.end), None)
        mentions.append(
            {
                "mencao": text,
                "categoria": found.label_ if found is not None else None,
                "entidade": found.text if found is not None else None,
            }
        )
    people = [{"entidade": ent.text, "confirmada": any(token.text in words for token in ent)} for ent in ents if ent.label_ == "PER"]
    return {"mencoes_creditadas": mentions, "pessoas_previstas": people}


def summarize(checks: list[dict]) -> dict:
    """Revocação de pessoas creditadas, categorias dadas a elas e precisão estimada das entidades PER."""
    mentions = [mention for check in checks for mention in check["mencoes_creditadas"]]
    people = [person for check in checks for person in check["pessoas_previstas"]]
    labels = Counter(mention["categoria"] or "nao_reconhecida" for mention in mentions)
    return {
        "mencoes_creditadas": len(mentions),
        "filmes_com_mencao": sum(bool(check["mencoes_creditadas"]) for check in checks),
        "revocacao_per": rounded(labels["PER"] / len(mentions)) if mentions else None,
        "revocacao_qualquer_categoria": rounded(1 - labels["nao_reconhecida"] / len(mentions)) if mentions else None,
        "categorias_das_mencoes": dict(sorted(labels.items())),
        "pessoas_previstas": len(people),
        "precisao_estimada_per": rounded(sum(person["confirmada"] for person in people) / len(people)) if people else None,
    }
