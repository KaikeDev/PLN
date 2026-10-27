"""Cache em memória das respostas do site, pela identidade do pedido (`LLMRequest.key`).

Fica por fora do orçamento: uma pergunta repetida, como os exemplos clicáveis do site, não gasta cota.
É por processo e se perde ao reiniciar; a reprodutibilidade das avaliações é papel de `app.llm.replay`.
"""

import threading
from collections import OrderedDict

from app.llm.ports import LanguageModel, LLMRequest, LLMResponse

DEFAULT_MAXSIZE = 256


class CachedModel:
    """LRU com até `maxsize` respostas; falhas não são guardadas."""

    def __init__(self, inner: LanguageModel, maxsize: int = DEFAULT_MAXSIZE) -> None:
        self._inner = inner
        self._maxsize = maxsize
        self._entries: OrderedDict[str, LLMResponse] = OrderedDict()
        self._lock = threading.Lock()

    def generate(self, request: LLMRequest) -> LLMResponse:
        key = request.key()
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
                return self._entries[key]
        response = self._inner.generate(request)
        with self._lock:
            self._entries[key] = response
            self._entries.move_to_end(key)
            while len(self._entries) > self._maxsize:
                self._entries.popitem(last=False)
        return response
