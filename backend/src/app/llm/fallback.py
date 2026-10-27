"""Reserva entre provedores: quando o principal falha por disponibilidade, o pedido vai para o seguinte.

Só passam adiante as falhas de disponibilidade (`cota`, `timeout`, `indisponivel`, `sem_chave`). Erro de
formato e orçamento esgotado são devolvidos na hora: outro provedor não resolveria (ADR 0029).
"""

import logging
from collections.abc import Sequence

from app.llm.ports import PROVIDER_FAILURES, LanguageModel, LLMRequest, LLMResponse, LLMUnavailable

logger = logging.getLogger(__name__)


class FallbackModel:
    """Tenta os modelos em ordem e devolve a primeira resposta."""

    def __init__(self, models: Sequence[LanguageModel]) -> None:
        if not models:
            raise ValueError("FallbackModel precisa de ao menos um modelo")
        self._models = tuple(models)

    def generate(self, request: LLMRequest) -> LLMResponse:
        failures: list[LLMUnavailable] = []
        for model in self._models:
            try:
                return model.generate(request)
            except LLMUnavailable as exc:
                if exc.reason not in PROVIDER_FAILURES:
                    raise
                logger.warning("LLM indisponível (%s): %s", exc.reason, exc)
                failures.append(exc)
        raise LLMUnavailable(failures[-1].reason, "; ".join(str(failure) for failure in failures))
