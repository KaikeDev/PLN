"""Polaridade e nota de uma crítica por LLM, sem treino, com a variante de prompt configurada (ADR 0031)."""

from dataclasses import dataclass
from typing import Literal

from app.llm.ports import LanguageModel, LLMRequest, LLMResponse
from app.sentiment.llm.prompt import SentimentLLMConfig, Variant, excerpt, user_prompt


@dataclass(frozen=True)
class LLMSentimentResult:
    """Polaridade, nota (0–10), justificativa quando a variante pede, e quem respondeu."""

    polarity: Literal["positivo", "negativo"]
    rating: float
    reason: str | None
    provider: str
    model: str


class LLMSentiment:
    """Pergunta ao LLM o que o autor da crítica achou do filme; críticas longas são cortadas no meio."""

    def __init__(self, model: LanguageModel, config: SentimentLLMConfig, variant: Variant | None = None) -> None:
        self._model = model
        self._config = config
        self.variant: Variant = variant or config.chosen_variant

    def request(self, text: str) -> LLMRequest:
        prepared = excerpt(text, self._config.sample.max_chars)
        return LLMRequest("sentimento", self._config.system(self.variant), user_prompt(prepared), self._config.output(self.variant))

    def ask(self, text: str) -> LLMResponse:
        """Resposta validada, com provedor, modelo e tokens."""
        return self._model.generate(self.request(text))

    def analyze(self, text: str) -> LLMSentimentResult:
        response = self.ask(text)
        return result_of(response)


def result_of(response: LLMResponse) -> LLMSentimentResult:
    data = response.data
    return LLMSentimentResult(
        data["polaridade"], round(float(data["nota"]), 1), data.get("justificativa"), response.provider, response.model
    )
