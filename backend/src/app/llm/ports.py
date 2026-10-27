"""Portas da camada de LLM: o pedido, a resposta validada e as falhas que o chamador precisa tratar.

O pedido descreve a saída como um modelo Pydantic; quem chama recebe `data` já validado contra ele e
nunca vê JSON solto. Os provedores só conhecem `Completion` e devolvem texto bruto, que a camada
estruturada (`app.llm.structured`) valida.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel

Purpose = Literal["interpretacao", "sentimento", "rag"]
PURPOSES: tuple[Purpose, ...] = ("interpretacao", "sentimento", "rag")
Reason = Literal["cota", "timeout", "indisponivel", "json_invalido", "sem_chave", "orcamento"]
PROVIDER_FAILURES: frozenset[Reason] = frozenset({"cota", "timeout", "indisponivel", "sem_chave"})


class LLMUnavailable(RuntimeError):
    """O LLM não respondeu algo utilizável; `reason` diz por quê. A mensagem nunca inclui URL, cabeçalhos ou chave."""

    def __init__(self, reason: Reason, message: str) -> None:
        super().__init__(message)
        self.reason: Reason = reason


@dataclass(frozen=True)
class LLMRequest:
    """Pedido ao LLM. `output` é o modelo Pydantic da resposta; temperatura e limite de tokens vêm da configuração pelo `purpose`."""

    purpose: Purpose
    system: str
    prompt: str
    output: type[BaseModel]

    def schema(self) -> dict:
        """JSON Schema da saída esperada."""
        return self.output.model_json_schema()

    def key(self) -> str:
        """Identidade do pedido para cache e replay: propósito, instruções, texto e esquema."""
        payload = json.dumps([self.purpose, self.system, self.prompt, self.schema()], ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LLMResponse:
    """Resposta validada. `model` é a versão informada pelo provedor, que pode ser mais exata que o alias configurado."""

    data: dict
    raw_text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class LanguageModel(Protocol):
    """Gera uma resposta estruturada ou levanta `LLMUnavailable`."""

    def generate(self, request: LLMRequest) -> LLMResponse: ...


@dataclass(frozen=True)
class Completion:
    """Chamada a um provedor: instruções, texto, esquema da saída e parâmetros de geração."""

    system: str
    prompt: str
    schema: dict
    temperature: float
    max_output_tokens: int


@dataclass(frozen=True)
class RawReply:
    """Texto devolvido por um provedor, ainda não validado, com o consumo de tokens."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int


class Provider(Protocol):
    """Adaptador de um provedor de LLM."""

    name: str
    model: str

    def complete(self, completion: Completion) -> RawReply: ...
