"""Porta do extrator de entidades e relações: o que a API precisa de um modelo carregado."""

from typing import Protocol

from app.entities.live import Extraction


class EntityExtractor(Protocol):
    """Modelo que reconhece entidades e extrai triplas de um texto livre, como uma sinopse."""

    model_name: str

    def extract(self, text: str) -> Extraction:
        """Entidades e triplas do texto; `ValueError` para texto inválido."""
        ...
