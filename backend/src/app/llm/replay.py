"""Gravação e replay de respostas: reavaliar sem gastar cota, como o `--reuse` do Jev (ADR 0019, 0029).

`RecordingModel` guarda cada resposta como um registro JSON sem a latência, que vai só para o manifesto
(ADR 0009). `ReplayModel` responde a partir desses registros, sem rede, e revalida cada um contra o modelo
do pedido. Um pedido não gravado vira `LLMUnavailable("indisponivel")`; assim,
`FallbackModel([ReplayModel(...), modelo_real])` continua uma avaliação interrompida de onde parou; `ReuseModel` faz o
mesmo sem registrar aviso a cada pedido novo e conta as chamadas feitas.

O mesmo pedido pode ter sido feito mais de uma vez (o teste de estabilidade repete pedidos): cada registro
responde uma vez, na ordem em que foi gravado, e o pedido que passar do número de registros vira uma chamada
nova. Com `provider`, só os registros desse provedor contam, para separar o mesmo prompt em provedores diferentes.
"""

from collections import deque
from collections.abc import Iterable
from pathlib import Path

from app.llm.ports import LanguageModel, LLMRequest, LLMResponse, LLMUnavailable
from app.llm.structured import parse
from app.shared.artifacts import read_jsonl
from app.shared.validation import require_object

RECORD_FIELDS = ("key", "purpose", "provider", "model", "input_tokens", "output_tokens", "raw_text", "data")


def to_record(request: LLMRequest, response: LLMResponse) -> dict:
    """Registro determinístico de uma resposta: mesma resposta, mesmos bytes."""
    return {
        "key": request.key(),
        "purpose": request.purpose,
        "provider": response.provider,
        "model": response.model,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "raw_text": response.raw_text,
        "data": response.data,
    }


class RecordingModel:
    """Repassa ao modelo interno e acumula os registros das respostas em `records`, que pode ser compartilhada."""

    def __init__(self, inner: LanguageModel, records: list[dict] | None = None) -> None:
        self._inner = inner
        self.records: list[dict] = records if records is not None else []

    def generate(self, request: LLMRequest) -> LLMResponse:
        response = self._inner.generate(request)
        self.records.append(to_record(request, response))
        return response


class ReplayModel:
    """Responde com os registros gravados, cada um uma vez e na ordem; não acessa a rede."""

    def __init__(self, records: Iterable[dict], provider: str | None = None) -> None:
        self._records: dict[str, deque[dict]] = {}
        for position, record in enumerate(records):
            item = require_object(record, f"registro {position}", RECORD_FIELDS)
            if provider is None or item["provider"] == provider:
                self._records.setdefault(str(item["key"]), deque()).append(item)

    @classmethod
    def from_file(cls, path: Path, provider: str | None = None) -> ReplayModel:
        """Registros de um `responses.jsonl` gravado por uma execução anterior."""
        return cls(read_jsonl(path), provider)

    def __len__(self) -> int:
        return sum(len(queue) for queue in self._records.values())

    def __contains__(self, request: object) -> bool:
        return isinstance(request, LLMRequest) and bool(self._records.get(request.key()))

    def generate(self, request: LLMRequest) -> LLMResponse:
        queue = self._records.get(request.key())
        if not queue:
            raise LLMUnavailable("indisponivel", "Pedido não gravado na execução reaproveitada")
        record = queue.popleft()
        try:
            data = parse(str(record["raw_text"]), request.output)
        except ValueError as exc:
            raise LLMUnavailable("json_invalido", f"Resposta gravada não segue o formato atual: {exc}") from exc
        return LLMResponse(
            data=data,
            raw_text=str(record["raw_text"]),
            provider=str(record["provider"]),
            model=str(record["model"]),
            input_tokens=int(record["input_tokens"]),
            output_tokens=int(record["output_tokens"]),
            latency_ms=0,
        )


class ReuseModel:
    """Responde com a resposta gravada quando há uma e, senão, chama `inner`; conta as reaproveitadas e as chamadas novas.

    Diferente de `FallbackModel([ReplayModel, real])`, não registra aviso a cada pedido não gravado.
    """

    def __init__(self, replay: ReplayModel, inner: LanguageModel) -> None:
        self._replay = replay
        self._inner = inner
        self.reused = 0
        self.calls = 0

    def is_recorded(self, request: LLMRequest) -> bool:
        """Verdadeiro quando o pedido será respondido sem rede."""
        return request in self._replay

    def generate(self, request: LLMRequest) -> LLMResponse:
        if request in self._replay:
            self.reused += 1
            return self._replay.generate(request)
        self.calls += 1
        return self._inner.generate(request)
