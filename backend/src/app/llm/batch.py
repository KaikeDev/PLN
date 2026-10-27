"""Modelos para as avaliações em lote: criação adiada e intervalo mínimo entre chamadas.

- `LazyModel` só cria o modelo real na primeira chamada. Uma avaliação que reaproveita todas as respostas
  gravadas roda sem chaves.
- `PacedModel` espera `request_interval_seconds` entre o início de duas chamadas, para respeitar o limite
  por minuto da cota gratuita (ADR 0029). Não vale para o site, que usa cache e orçamento diário.
"""

import time
from collections.abc import Callable

from app.llm.ports import LanguageModel, LLMRequest, LLMResponse


class LazyModel:
    """Cria o modelo com `factory` na primeira chamada e o reaproveita nas seguintes."""

    def __init__(self, factory: Callable[[], LanguageModel]) -> None:
        self._factory = factory
        self._model: LanguageModel | None = None

    def generate(self, request: LLMRequest) -> LLMResponse:
        if self._model is None:
            self._model = self._factory()
        return self._model.generate(request)


class PacedModel:
    """Repassa ao modelo interno, com pelo menos `interval` segundos entre o início de duas chamadas."""

    def __init__(
        self,
        inner: LanguageModel,
        interval: float,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner = inner
        self._interval = interval
        self._sleep = sleep
        self._clock = clock
        self._last: float | None = None

    def generate(self, request: LLMRequest) -> LLMResponse:
        if self._last is not None and (wait := self._interval - (self._clock() - self._last)) > 0:
            self._sleep(wait)
        self._last = self._clock()
        return self._inner.generate(request)
