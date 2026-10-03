"""Porta do classificador de gênero: o que a API precisa de um modelo treinado."""

from typing import Protocol


class GenreClassifier(Protocol):
    """Modelo que atribui probabilidades de gênero a um texto livre, como uma sinopse."""

    representation_name: str
    training_size: int

    def classify(self, text: str) -> list[tuple[str, float]]:
        """Pares (gênero, probabilidade) do mais ao menos provável; `ValueError` para texto inválido."""
        ...
