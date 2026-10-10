"""Entidades e relações de um texto avulso, usadas pela ficha do filme no site (ADR 0027).

Carrega o mesmo modelo spaCy e aplica as mesmas regras do experimento (`app.entities.extraction`), com a regra
de coordenação ligada.
"""

from dataclasses import dataclass

from app.entities.extraction import Triple, entities, load_model, relations

MAX_TEXT_CHARS = 2000


@dataclass(frozen=True)
class Extraction:
    """Menções reconhecidas e triplas sujeito — relação → objeto de um texto."""

    entities: list[dict]
    triples: list[Triple]


class EntityExtractor:
    """NER e relações com o spaCy `pt_core_news_sm`."""

    def __init__(self, model: str = "pt_core_news_sm") -> None:
        self._nlp = load_model(model)
        self.model_name = model

    def extract(self, text: str) -> Extraction:
        """Entidades e triplas do texto; `ValueError` para texto vazio ou longo demais."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Digite um texto")
        if len(text) > MAX_TEXT_CHARS:
            raise ValueError(f"O texto excede {MAX_TEXT_CHARS} caracteres")
        doc = self._nlp(text.strip())
        return Extraction(entities(doc), relations(doc))
