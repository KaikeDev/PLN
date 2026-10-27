"""Montagem da pilha de LLM do site: cache → orçamento → reserva → (saída estruturada sobre cada provedor).

O cache fica por fora do orçamento, para que respostas repetidas não gastem cota. Só entram os provedores com
chave configurada; sem nenhuma, `build_llm` devolve None e as funções com LLM respondem 503 (ADR 0029).

As avaliações em lote usam `batch_model`: a mesma reserva entre provedores, sem cache nem orçamento, que
servem ao site; o intervalo entre chamadas fica com `app.llm.batch.PacedModel`.
"""

from dataclasses import dataclass

from app.llm.budget import DailyBudget
from app.llm.cache import CachedModel
from app.llm.config import LLMConfig, ProviderConfig, load_config
from app.llm.fallback import FallbackModel
from app.llm.gemini import GeminiProvider
from app.llm.groq import GroqProvider
from app.llm.ports import LanguageModel, Provider
from app.llm.structured import StructuredModel
from app.settings import Settings


@dataclass(frozen=True)
class LLMStack:
    """Modelo pronto para as rotas e os dados que `/saude` informa."""

    model: LanguageModel
    budget: DailyBudget
    config: LLMConfig
    providers: tuple[str, ...]

    def status(self) -> dict:
        """Provedores, temperatura e orçamento restante, sem chaves."""
        return {"provedores": list(self.providers), "temperatura": self.config.temperature, "orcamento_restante": self.budget.remaining()}


def make_provider(config: ProviderConfig, api_key: str) -> Provider:
    """Adaptador do provedor configurado."""
    if config.name == "gemini":
        return GeminiProvider(config, api_key)
    return GroqProvider(config, api_key)


def available_providers(config: LLMConfig, settings: Settings) -> list[Provider]:
    """Provedores da configuração, na ordem, que têm chave."""
    return [make_provider(item, key) for item in config.providers if (key := settings.llm_api_key(item.name))]


def stack_for(providers: list[Provider], config: LLMConfig) -> LLMStack:
    """Pilha completa sobre provedores já criados; os testes passam provedores falsos."""
    budget = DailyBudget(FallbackModel([StructuredModel(provider, config) for provider in providers]), config.daily_budget)
    return LLMStack(CachedModel(budget), budget, config, tuple(f"{provider.name}:{provider.model}" for provider in providers))


def build_llm(settings: Settings) -> LLMStack | None:
    """Pilha do site, ou None quando nenhum provedor tem chave."""
    config = load_config(settings.llm_config)
    providers = available_providers(config, settings)
    return stack_for(providers, config) if providers else None


def batch_model(settings: Settings) -> tuple[LanguageModel, LLMConfig]:
    """Reserva entre os provedores com chave, sem cache nem orçamento, e a configuração lida; falha sem nenhuma chave."""
    config = load_config(settings.llm_config)
    providers = available_providers(config, settings)
    if not providers:
        raise ValueError("Defina GEMINI_API_KEY ou GROQ_API_KEY em backend/.env")
    return FallbackModel([StructuredModel(provider, config) for provider in providers]), config
