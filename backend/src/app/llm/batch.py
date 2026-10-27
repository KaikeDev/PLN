"""Modelos para as avaliações em lote: criação adiada, intervalo mínimo entre chamadas e nova tentativa na cota por minuto.

- `LazyModel` só cria o modelo real na primeira chamada. Uma avaliação que reaproveita todas as respostas
  gravadas roda sem chaves.
- `PacedModel` espera `request_interval_seconds` entre o início de duas chamadas, para respeitar o limite
  por minuto da cota gratuita (ADR 0029). Não vale para o site, que usa cache e orçamento diário.
- `QuotaRetryModel` espera e tenta de novo quando a cota **por minuto** estoura. A cota do dia não volta em
  minutos: a falha passa direto, e a avaliação continua no dia seguinte com `--reuse`.
"""

import logging
import re
import time
from collections.abc import Callable, Sequence

from app.llm.ports import LanguageModel, LLMRequest, LLMResponse, LLMUnavailable

logger = logging.getLogger(__name__)

QUOTA_WAITS = (20.0, 40.0, 60.0)
DAILY_QUOTA_RE = re.compile(r"per\s*day|PerDay|\bTPD\b|\bRPD\b", re.IGNORECASE)


def is_daily_quota(error: LLMUnavailable) -> bool:
    """Verdadeiro quando a mensagem do provedor diz que a cota do dia acabou."""
    return error.reason == "cota" and bool(DAILY_QUOTA_RE.search(str(error)))


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


class QuotaRetryModel:
    """Repassa ao modelo interno; na cota por minuto, espera cada intervalo de `waits` e tenta de novo."""

    def __init__(self, inner: LanguageModel, waits: Sequence[float] = QUOTA_WAITS, sleep: Callable[[float], None] = time.sleep) -> None:
        self._inner = inner
        self._waits = tuple(waits)
        self._sleep = sleep

    def generate(self, request: LLMRequest) -> LLMResponse:
        for wait in self._waits:
            try:
                return self._inner.generate(request)
            except LLMUnavailable as exc:
                if exc.reason != "cota" or is_daily_quota(exc):
                    raise
                logger.warning("Cota por minuto esgotada; nova tentativa em %g s", wait)
                self._sleep(wait)
        return self._inner.generate(request)
