"""Limite de requisições por cliente em janela deslizante de 60 segundos.

A API repassa chamadas ao TMDB com a credencial do servidor; o limite impede que um cliente local
esgote a cota. O estado fica em memória do processo e o cliente é identificado pelo IP da conexão
(ADR 0002). Excedido o limite, a resposta é 429 com `Retry-After`.
"""

import math
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

WINDOW_SECONDS = 60.0


class RateLimiter:
    """Dependência FastAPI que aceita até `limit` requisições por cliente a cada `window` segundos."""

    def __init__(self, limit: int, window: float = WINDOW_SECONDS, clock: Callable[[], float] = time.monotonic) -> None:
        self._limit = limit
        self._window = window
        self._clock = clock
        self._hits: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def __call__(self, request: Request) -> None:
        client = request.client.host if request.client else "desconhecido"
        now = self._clock()
        with self._lock:
            hits = self._hits[client]
            while hits and hits[0] <= now - self._window:
                hits.popleft()
            if len(hits) >= self._limit:
                retry_after = max(1, math.ceil(hits[0] + self._window - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Limite de requisições excedido; tente novamente em instantes.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)
