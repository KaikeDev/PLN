"""Porta do analisador de sentimento: o que a API precisa de um modelo treinado."""

from typing import Protocol

from app.sentiment.live import SentimentResult


class SentimentAnalyzer(Protocol):
    """Modelo que atribui polaridade e nota a um texto livre, como uma crítica."""

    representation_name: str
    training_size: int

    def analyze(self, text: str) -> SentimentResult:
        """Polaridade, probabilidade, nota prevista e palavras de maior peso; `ValueError` para texto inválido."""
        ...
