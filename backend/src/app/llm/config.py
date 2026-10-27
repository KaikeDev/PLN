"""Configuração dos LLMs (`config/llm/llm.json`), validada como dado e nunca como código (ADR 0011).

A ordem de `providers` é a ordem de tentativa: o primeiro é o principal e os seguintes são reservas.
`max_output_tokens` e `daily_budget` têm um valor por propósito; o orçamento fica abaixo da cota
gratuita de cada provedor, para que o site público não a esgote (ADR 0029).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.llm.ports import PURPOSES, Purpose
from app.shared.validation import read_config_json, require_int, require_number, require_object

ProviderName = Literal["gemini", "groq"]
PROVIDER_NAMES: tuple[ProviderName, ...] = ("gemini", "groq")
REASONING_EFFORTS = ("low", "medium", "high")
MAX_MODEL_CHARS = 100


@dataclass(frozen=True)
class ProviderConfig:
    """Um provedor: nome, modelo (ou alias), URL base HTTPS, timeout e, para modelos com raciocínio, o esforço pedido."""

    name: ProviderName
    model: str
    base_url: str
    timeout_seconds: float
    reasoning_effort: str | None = None


@dataclass(frozen=True)
class LLMConfig:
    """Provedores em ordem de tentativa e parâmetros de geração por propósito."""

    providers: tuple[ProviderConfig, ...]
    temperature: float
    max_output_tokens: dict[Purpose, int]
    daily_budget: dict[Purpose, int]
    request_interval_seconds: float


def load_config(path: Path) -> LLMConfig:
    """Lê e valida `config/llm/llm.json`."""
    raw = require_object(
        read_config_json(path),
        path.name,
        ("providers", "temperature", "max_output_tokens", "daily_budget", "request_interval_seconds"),
        ("description",),
    )
    providers = raw["providers"]
    if not isinstance(providers, list) or not providers:
        raise ValueError("providers deve ser uma lista não vazia")
    parsed = tuple(_provider(item, f"providers[{position}]") for position, item in enumerate(providers))
    if len({provider.name for provider in parsed}) != len(parsed):
        raise ValueError("providers não pode repetir o mesmo provedor")
    return LLMConfig(
        providers=parsed,
        temperature=require_number(raw["temperature"], "temperature", 0.0, 2.0),
        max_output_tokens=_per_purpose(raw["max_output_tokens"], "max_output_tokens", 16, 8192),
        daily_budget=_per_purpose(raw["daily_budget"], "daily_budget", 0, 100_000),
        request_interval_seconds=require_number(raw["request_interval_seconds"], "request_interval_seconds", 0.0, 120.0),
    )


def _provider(value: object, where: str) -> ProviderConfig:
    item = require_object(value, where, ("name", "model", "base_url", "timeout_seconds"), ("reasoning_effort",))
    name = item["name"]
    if name not in PROVIDER_NAMES:
        raise ValueError(f"{where}.name deve ser um de {list(PROVIDER_NAMES)}")
    model = item["model"]
    if not isinstance(model, str) or not model.strip() or len(model) > MAX_MODEL_CHARS:
        raise ValueError(f"{where}.model deve ser um texto com até {MAX_MODEL_CHARS} caracteres")
    base_url = item["base_url"]
    if not isinstance(base_url, str) or not base_url.startswith("https://"):
        raise ValueError(f"{where}.base_url deve começar com https://")
    effort = item.get("reasoning_effort")
    if effort is not None and effort not in REASONING_EFFORTS:
        raise ValueError(f"{where}.reasoning_effort deve ser um de {list(REASONING_EFFORTS)}")
    return ProviderConfig(
        name=name,
        model=model.strip(),
        base_url=base_url.rstrip("/"),
        timeout_seconds=require_number(item["timeout_seconds"], f"{where}.timeout_seconds", 1.0, 120.0),
        reasoning_effort=effort,
    )


def _per_purpose(value: object, where: str, low: int, high: int) -> dict[Purpose, int]:
    item = require_object(value, where, PURPOSES)
    return {purpose: require_int(item[purpose], f"{where}.{purpose}", low, high) for purpose in PURPOSES}
