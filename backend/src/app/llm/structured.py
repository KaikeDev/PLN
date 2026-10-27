"""Saída estruturada: o texto do provedor só chega ao chamador depois de validado contra o modelo Pydantic do pedido.

Uma resposta fora do formato ganha uma única nova tentativa, com o erro anexado ao pedido. Se falhar de
novo, vira `LLMUnavailable("json_invalido")`, que não passa para o provedor reserva: o problema é do
prompt ou do esquema, não da disponibilidade (ADR 0029). Cercas de código Markdown em volta do JSON são
toleradas, porque alguns modelos as acrescentam mesmo no modo JSON.
"""

import re
import time
from collections.abc import Callable
from dataclasses import replace

from pydantic import BaseModel, ValidationError

from app.llm.config import LLMConfig
from app.llm.ports import Completion, LLMRequest, LLMResponse, LLMUnavailable, Provider

FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)
REPAIR = "Sua resposta anterior não seguiu o formato pedido ({error}). Responda de novo, somente com o objeto JSON."
MAX_ERRORS = 3
MAX_ERROR_CHARS = 300


class StructuredModel:
    """`LanguageModel` sobre um provedor: monta a chamada pela configuração do propósito e valida a resposta."""

    def __init__(self, provider: Provider, config: LLMConfig, clock: Callable[[], float] = time.perf_counter) -> None:
        self._provider = provider
        self._config = config
        self._clock = clock

    def generate(self, request: LLMRequest) -> LLMResponse:
        start = self._clock()
        completion = Completion(
            system=request.system,
            prompt=request.prompt,
            schema=request.schema(),
            temperature=self._config.temperature,
            max_output_tokens=self._config.max_output_tokens[request.purpose],
        )
        reply = self._provider.complete(completion)
        input_tokens, output_tokens = reply.input_tokens, reply.output_tokens
        try:
            data = parse(reply.text, request.output)
        except ValueError as error:
            reply = self._provider.complete(replace(completion, prompt=f"{completion.prompt}\n\n{REPAIR.format(error=error)}"))
            input_tokens += reply.input_tokens
            output_tokens += reply.output_tokens
            try:
                data = parse(reply.text, request.output)
            except ValueError as again:
                raise LLMUnavailable("json_invalido", f"{self._provider.name} não seguiu o formato pedido: {again}") from again
        return LLMResponse(
            data=data,
            raw_text=reply.text,
            provider=self._provider.name,
            model=reply.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round((self._clock() - start) * 1000),
        )


def parse(text: str, output: type[BaseModel]) -> dict:
    """Objeto validado por `output`, como dicionário JSON; `ValueError` com os primeiros erros quando inválido."""
    match = FENCE_RE.match(text)
    try:
        return output.model_validate_json(match.group(1) if match else text).model_dump(mode="json")
    except ValidationError as exc:
        errors = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or 'raiz'}: {error['msg']}" for error in exc.errors()[:MAX_ERRORS]
        )
        raise ValueError(errors[:MAX_ERROR_CHARS]) from exc
