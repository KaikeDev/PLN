"""CLI: python -m app.llm ping faz uma chamada real a cada provedor com chave, para conferir chave, modelo e formato.

Não passa pelo orçamento nem pelo cache, e não grava nada. Cada provedor gasta uma chamada da cota gratuita.
Devolve 0 quando todos responderam no formato pedido e 1 quando algum falhou.
"""

import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

PING_SYSTEM = "Você classifica temas de filmes. Responda em JSON."
PING_PROMPT = "Qual destes gêneros combina mais com um filme sobre uma família numa casa assombrada? Dê também sua confiança de 0 a 1."


class PingAnswer(BaseModel):
    """Saída do teste: um gênero de uma lista fechada e uma confiança, para exercitar `enum` e limites no esquema."""

    genero: Literal["Drama", "Comédia", "Terror", "Ficção científica"]
    confianca: float = Field(ge=0, le=1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Conferir os provedores de LLM configurados (ADR 0029)")
    commands = parser.add_subparsers(dest="command", required=True)
    ping = commands.add_parser("ping", help="Uma chamada real a cada provedor com chave")
    ping.add_argument("--config", type=Path, help="Padrão: config/llm/llm.json")
    args = parser.parse_args()

    from app.llm.compose import available_providers
    from app.llm.config import load_config
    from app.llm.ports import LLMRequest, LLMUnavailable
    from app.llm.structured import StructuredModel
    from app.settings import get_settings

    settings = get_settings()
    try:
        config = load_config(args.config or settings.llm_config)
        providers = available_providers(config, settings)
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")
    if not providers:
        parser.exit(2, "Erro: defina GEMINI_API_KEY ou GROQ_API_KEY em backend/.env\n")
    request = LLMRequest(purpose="interpretacao", system=PING_SYSTEM, prompt=PING_PROMPT, output=PingAnswer)
    failed = False
    for provider in providers:
        try:
            response = StructuredModel(provider, config).generate(request)
        except LLMUnavailable as exc:
            failed = True
            print(
                json.dumps(
                    {"provedor": provider.name, "modelo": provider.model, "erro": exc.reason, "mensagem": str(exc)}, ensure_ascii=False
                )
            )
            continue
        print(
            json.dumps(
                {
                    "provedor": response.provider,
                    "modelo": response.model,
                    "latencia_ms": response.latency_ms,
                    "tokens_entrada": response.input_tokens,
                    "tokens_saida": response.output_tokens,
                    "resposta": response.data,
                },
                ensure_ascii=False,
            )
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
