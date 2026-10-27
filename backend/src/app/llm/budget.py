"""Orçamento diário de chamadas por propósito, para que o site público não esgote a cota gratuita (ADR 0029).

Conta cada pedido encaminhado ao provedor, inclusive os que falham, e zera na virada do dia em UTC. O estado
fica na memória do processo, o que basta com um único processo do uvicorn.
"""

import threading
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime

from app.llm.ports import PURPOSES, LanguageModel, LLMRequest, LLMResponse, LLMUnavailable, Purpose


def utc_today() -> date:
    return datetime.now(UTC).date()


class DailyBudget:
    """Recusa com `LLMUnavailable("orcamento")` quando o propósito atingiu o limite do dia."""

    def __init__(self, inner: LanguageModel, limits: Mapping[Purpose, int], today: Callable[[], date] = utc_today) -> None:
        self._inner = inner
        self._limits = dict(limits)
        self._today = today
        self._day = today()
        self._used: dict[Purpose, int] = dict.fromkeys(PURPOSES, 0)
        self._lock = threading.Lock()

    def generate(self, request: LLMRequest) -> LLMResponse:
        with self._lock:
            self._roll_over()
            if self._used[request.purpose] >= self._limits.get(request.purpose, 0):
                raise LLMUnavailable("orcamento", "Limite diário de uso de IA atingido; tente novamente amanhã")
            self._used[request.purpose] += 1
        return self._inner.generate(request)

    def remaining(self) -> dict[Purpose, int]:
        """Chamadas que ainda cabem hoje em cada propósito."""
        with self._lock:
            self._roll_over()
            return {purpose: max(0, self._limits.get(purpose, 0) - self._used[purpose]) for purpose in PURPOSES}

    def _roll_over(self) -> None:
        today = self._today()
        if today != self._day:
            self._day = today
            self._used = dict.fromkeys(PURPOSES, 0)
