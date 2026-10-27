"""Interpretação do site: o LLM primeiro e, se ele falhar ou demorar, as regras (ADR 0030).

O LLM roda numa thread com prazo (`timeout_seconds`). Passado o prazo, ou com `LLMUnavailable` (cota,
orçamento do dia, JSON inválido, sem chave), a frase é interpretada pelas regras e o resultado sai com
`origin = "regras"`, o que o site mostra no selo. A chamada atrasada continua e, se terminar, entra no
cache do LLM. O log registra só o motivo, nunca a frase digitada.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

from app.llm.ports import LLMUnavailable
from app.search.filters import ExtractedFilters
from app.search.ports import PreferenceExtractor

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 4.0
MAX_WORKERS = 4


class FallbackExtractor:
    """`PreferenceExtractor` que tenta `primary` dentro do prazo e recorre a `fallback`."""

    def __init__(
        self,
        primary: PreferenceExtractor,
        fallback: PreferenceExtractor,
        timeout_seconds: float = TIMEOUT_SECONDS,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._timeout = timeout_seconds
        self._executor = executor or ThreadPoolExecutor(MAX_WORKERS, thread_name_prefix="interpretacao")

    def extract(self, text: str) -> ExtractedFilters:
        future = self._executor.submit(self._primary.extract, text)
        try:
            return future.result(timeout=self._timeout)
        except TimeoutError:
            logger.warning("Interpretação por LLM passou de %g s; usando as regras", self._timeout)
        except LLMUnavailable as exc:
            logger.warning("Interpretação por LLM indisponível (%s); usando as regras", exc.reason)
        return self._fallback.extract(text)
