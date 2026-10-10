"""Dependências, entidades e relações de um texto, com as regras do notebook da Aula 9 (ADR 0027).

As funções seguem `PLN_2026_Aula_9_parsing,_NER_e_extração_de_relações.ipynb`:

- `dependencies` é `analisar_dependencias`: token, lema, classe, dependência e núcleo;
- `entities` é `extrair_entidades`: menção, categoria e posições de caractere (`fim` exclusivo);
- `phrase`, `argument` e `normalize_preposition` são `obter_sintagma`, `obter_argumento` e `normalizar_preposicao`;
- `relations` é `extrair_relacoes`: sujeito (`nsubj`, `nsubj:pass`) de um verbo com cada complemento
  (`obj`, `iobj`, `obl`); no `obl`, a preposição normalizada entra na relação (`trabalhar_em`).

Uma regra vai além do notebook, que a aponta como limite ("nasceu … e estudou …"): com `coordination`, um verbo
coordenado (`conj`) sem sujeito próprio herda o sujeito do verbo ao qual se coordena. Cada tripla registra a regra
que a produziu (`svo`, `obl` ou `coordenacao`), para medir o efeito separadamente.
"""

from dataclasses import dataclass
from typing import Any

SUBJECTS = frozenset({"nsubj", "nsubj:pass"})
COMPLEMENTS = frozenset({"obj", "iobj", "obl"})
LEADING = frozenset({"det", "case"})
PREPOSITIONS = {
    **dict.fromkeys(["no", "na", "nos", "nas"], "em"),
    **dict.fromkeys(["do", "da", "dos", "das"], "de"),
    **dict.fromkeys(["ao", "aos", "à", "às"], "a"),
    **dict.fromkeys(["pelo", "pela", "pelos", "pelas"], "por"),
}
PRONOUNS = frozenset({"ele", "ela", "eles", "elas", "que", "quem", "o qual", "a qual"})


@dataclass(frozen=True)
class Triple:
    """Sujeito — relação → objeto, com a sentença de origem e a regra que gerou a tripla."""

    subject: str
    relation: str
    object: str
    sentence: int
    rule: str
    subject_is_entity: bool
    object_is_entity: bool


def dependencies(doc: Any) -> list[dict]:
    """Uma linha por token: forma, lema, classe gramatical, dependência e núcleo."""
    return [{"token": t.text, "lema": t.lemma_, "classe": t.pos_, "dependencia": t.dep_, "nucleo": t.head.text} for t in doc]


def entities(doc: Any) -> list[dict]:
    """Menções reconhecidas, com categoria e posições de caractere (`fim` exclusivo)."""
    return [{"entidade": ent.text, "categoria": ent.label_, "inicio": ent.start_char, "fim": ent.end_char} for ent in doc.ents]


def phrase(token: Any) -> str:
    """Trecho contínuo da subárvore do núcleo: a primeira aproximação do sintagma."""
    tokens = list(token.subtree)
    return token.doc[min(t.i for t in tokens) : max(t.i for t in tokens) + 1].text


def entity_of(token: Any) -> Any | None:
    """Entidade que contém o núcleo do argumento, ou None."""
    return next((ent for ent in token.doc.ents if ent.start <= token.i < ent.end), None)


def argument(token: Any) -> str:
    """A entidade que contém o núcleo; sem entidade, o sintagma sem artigos e preposições iniciais nem pontuação."""
    if (entity := entity_of(token)) is not None:
        return entity.text
    tokens = sorted((t for t in token.subtree if not t.is_punct), key=lambda t: t.i)
    while tokens and tokens[0].dep_ in LEADING:
        tokens.pop(0)
    return " ".join(t.text for t in tokens)


def normalize_preposition(token: Any) -> str:
    """Contração da preposição com o artigo reduzida à preposição: "na" → "em", "pela" → "por"."""
    return PREPOSITIONS.get(token.text.lower(), token.lemma_.lower())


def relations(doc: Any, normalize: bool = True, coordination: bool = True) -> list[Triple]:
    """Triplas de todas as sentenças do texto, na ordem dos verbos."""
    make = argument if normalize else phrase
    sentence_of = {token.i: number for number, sentence in enumerate(doc.sents, 1) for token in sentence}
    triples = []
    for verb in doc:
        if verb.pos_ != "VERB":
            continue
        subjects = [t for t in verb.children if t.dep_ in SUBJECTS]
        rule_for_subject = None
        if not subjects and coordination and verb.dep_ == "conj" and verb.head.pos_ in {"VERB", "AUX"}:
            subjects = [t for t in verb.head.children if t.dep_ in SUBJECTS]
            rule_for_subject = "coordenacao"
        for complement in (t for t in verb.children if t.dep_ in COMPLEMENTS):
            preposition = next((t for t in complement.children if t.dep_ == "case"), None)
            relation = verb.lemma_
            if complement.dep_ == "obl" and preposition is not None:
                relation += "_" + normalize_preposition(preposition)
            rule = rule_for_subject or ("obl" if complement.dep_ == "obl" else "svo")
            for subject in subjects:
                triples.append(
                    Triple(
                        make(subject),
                        relation,
                        make(complement),
                        sentence_of[verb.i],
                        rule,
                        entity_of(subject) is not None,
                        entity_of(complement) is not None,
                    )
                )
    return triples


def is_pronoun(text: str) -> bool:
    """Sujeito que é só um pronome pessoal ou relativo ("Ela", "que"): sem correferência, não é ligado ao antecedente."""
    return text.casefold() in PRONOUNS


def load_model(name: str) -> Any:
    """Carrega o modelo spaCy instalado pelo extra `entidades`; falha com mensagem orientativa sem ele."""
    try:
        import spacy
    except ImportError as exc:
        raise ValueError("NER e relações exigem o extra opcional: uv sync --frozen --extra entidades") from exc
    try:
        return spacy.load(name)
    except OSError as exc:
        raise ValueError(f"Modelo spaCy {name!r} não instalado; use uv sync --frozen --extra entidades") from exc
