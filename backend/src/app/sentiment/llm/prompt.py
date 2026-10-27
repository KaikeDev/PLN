"""Configuração do sentimento com LLM (`config/sentimento/sentimento_llm.json`) e as variantes do prompt.

| Variante | Prompt | Saída |
|---|---|---|
| `zero_shot` | instruções | polaridade, nota e justificativa |
| `few_shot` | instruções e exemplos escritos pela equipe | polaridade, nota e justificativa |
| `zero_shot_sem_justificativa` | instruções, sem pedir justificativa | polaridade e nota |
| `reserva` | a `variante_escolhida`, no provedor reserva | a da variante escolhida |

O texto da crítica vai entre aspas, com escape de JSON, e as críticas longas são cortadas no meio
(`excerpt`), da mesma forma para todas as variantes.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.validation import read_config_json, require_int, require_object

Variant = Literal["zero_shot", "few_shot", "zero_shot_sem_justificativa", "reserva"]
PROMPT_VARIANTS: tuple[Variant, ...] = ("zero_shot", "few_shot", "zero_shot_sem_justificativa")
VARIANTS: tuple[Variant, ...] = (*PROMPT_VARIANTS, "reserva")
PROVIDERS = ("gemini", "groq")
REFERENCES = ("tfidf", "bertimbau")
CUT_MARK = " [...] "
MAX_INSTRUCTIONS = 20
MAX_EXAMPLES = 8
MAX_CASES = 10
MAX_TEXT_CHARS = 2000
MAX_REASON_CHARS = 200


class SentimentOutput(BaseModel):
    """Saída sem justificativa."""

    model_config = ConfigDict(extra="forbid")

    polaridade: Literal["positivo", "negativo"]
    nota: float = Field(ge=0, le=10, description="Nota de 0 a 10 que o autor provavelmente deu")


class ReasonedSentimentOutput(SentimentOutput):
    """Saída com a justificativa curta."""

    justificativa: str = Field(max_length=MAX_REASON_CHARS, description="Motivo principal, em uma frase curta")


@dataclass(frozen=True)
class SampleSettings:
    """Tamanho e estratos da amostra, repetições de estabilidade e corte das críticas longas."""

    seed: int
    per_polarity: int
    main_author_per_polarity: int
    stability: int
    max_chars: int


@dataclass(frozen=True)
class Example:
    text: str
    output: dict


@dataclass(frozen=True)
class TeamCase:
    kind: str
    text: str


@dataclass(frozen=True)
class SentimentLLMConfig:
    """Configuração validada do experimento e do uso no site."""

    sample: SampleSettings
    references: dict[str, str]
    main_provider: str
    reserve_provider: str
    chosen_variant: Variant
    instructions: tuple[str, ...]
    reason_instruction: str
    examples: tuple[Example, ...]
    team_cases: tuple[TeamCase, ...]

    def resolved(self, variant: Variant) -> Variant:
        """Variante de prompt usada: `reserva` repete a escolhida em outro provedor."""
        return self.chosen_variant if variant == "reserva" else variant

    def provider(self, variant: Variant) -> str:
        return self.reserve_provider if variant == "reserva" else self.main_provider

    def output(self, variant: Variant) -> type[SentimentOutput]:
        return SentimentOutput if self.resolved(variant) == "zero_shot_sem_justificativa" else ReasonedSentimentOutput

    def system(self, variant: Variant) -> str:
        """Instruções do sistema da variante."""
        prompt_variant = self.resolved(variant)
        lines = list(self.instructions)
        if prompt_variant != "zero_shot_sem_justificativa":
            lines.insert(len(lines) - 2, self.reason_instruction)
        if prompt_variant == "few_shot":
            lines += ["", "Exemplos:"]
            lines += [
                f"Crítica: {quoted(example.text)}\nResposta: {json.dumps(example.output, ensure_ascii=False)}" for example in self.examples
            ]
        return "\n".join(lines)


def quoted(text: str) -> str:
    """Texto entre aspas com escape de JSON: a crítica não consegue fechar as aspas."""
    return json.dumps(text, ensure_ascii=False)


def user_prompt(text: str) -> str:
    return f"Crítica: {quoted(text)}"


def excerpt(text: str, max_chars: int) -> str:
    """O texto inteiro, ou o começo e o fim com o meio trocado por `CUT_MARK`, somando até `max_chars` caracteres."""
    if len(text) <= max_chars:
        return text
    half = (max_chars - len(CUT_MARK)) // 2
    return f"{text[:half].rstrip()}{CUT_MARK}{text[-half:].lstrip()}"


def load_config(path: Path) -> SentimentLLMConfig:
    """Lê e valida a configuração; os exemplos são conferidos contra o esquema da saída."""
    data = require_object(
        read_config_json(path),
        "configuração do sentimento com LLM",
        required={
            "amostra",
            "referencias",
            "provedor_principal",
            "provedor_reserva",
            "variante_escolhida",
            "instrucoes",
            "instrucao_justificativa",
            "exemplos",
            "casos_da_equipe",
        },
        optional={"description"},
    )
    sample = require_object(
        data["amostra"],
        "amostra",
        required={"semente", "por_polaridade", "do_autor_principal_por_polaridade", "repeticoes_de_estabilidade", "max_caracteres"},
    )
    per_polarity = require_int(sample["por_polaridade"], "por_polaridade", 1, 1000)
    settings = SampleSettings(
        seed=require_int(sample["semente"], "semente", 0, 2**31 - 1),
        per_polarity=per_polarity,
        main_author_per_polarity=require_int(
            sample["do_autor_principal_por_polaridade"], "do_autor_principal_por_polaridade", 0, per_polarity
        ),
        stability=require_int(sample["repeticoes_de_estabilidade"], "repeticoes_de_estabilidade", 0, 2 * per_polarity),
        max_chars=require_int(sample["max_caracteres"], "max_caracteres", 200, 20000),
    )
    references = require_object(data["referencias"], "referencias", required=REFERENCES)
    if not all(isinstance(name, str) and name for name in references.values()):
        raise ValueError("referencias deve nomear as representações do experimento")
    providers = (data["provedor_principal"], data["provedor_reserva"])
    if any(provider not in PROVIDERS for provider in providers) or providers[0] == providers[1]:
        raise ValueError(f"provedor_principal e provedor_reserva devem ser diferentes, entre {list(PROVIDERS)}")
    if data["variante_escolhida"] not in PROMPT_VARIANTS:
        raise ValueError(f"variante_escolhida deve ser uma de {list(PROMPT_VARIANTS)}")
    config = SentimentLLMConfig(
        sample=settings,
        references=dict(references),
        main_provider=providers[0],
        reserve_provider=providers[1],
        chosen_variant=data["variante_escolhida"],
        instructions=_texts(data["instrucoes"], "instrucoes", MAX_INSTRUCTIONS),
        reason_instruction=_text(data["instrucao_justificativa"], "instrucao_justificativa"),
        examples=tuple(_example(item, position) for position, item in enumerate(_items(data["exemplos"], "exemplos", MAX_EXAMPLES))),
        team_cases=tuple(
            _case(item, position) for position, item in enumerate(_items(data["casos_da_equipe"], "casos_da_equipe", MAX_CASES))
        ),
    )
    if len(config.instructions) < 2:
        raise ValueError("instrucoes deve ter ao menos duas linhas")
    return config


def _items(value: object, where: str, maximum: int) -> list:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise ValueError(f"{where} deve listar de 1 a {maximum} itens")
    return value


def _texts(value: object, where: str, maximum: int) -> tuple[str, ...]:
    return tuple(_text(item, where) for item in _items(value, where, maximum))


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT_CHARS:
        raise ValueError(f"{where} deve conter textos de 1 a {MAX_TEXT_CHARS} caracteres")
    return value


def _example(value: object, position: int) -> Example:
    item = require_object(value, f"exemplo {position}", required={"texto", "saida"})
    output = ReasonedSentimentOutput.model_validate(item["saida"]).model_dump(mode="json")
    return Example(_text(item["texto"], f"exemplo {position}"), output)


def _case(value: object, position: int) -> TeamCase:
    item = require_object(value, f"caso {position}", required={"tipo", "texto"})
    return TeamCase(_text(item["tipo"], f"caso {position}"), _text(item["texto"], f"caso {position}"))
