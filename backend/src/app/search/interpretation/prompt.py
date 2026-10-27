"""Prompt versionado da interpretação (`config/busca/interpretacao_prompt.json`) e as suas duas variantes.

- `zero_shot`: só as instruções.
- `few_shot`: as instruções e os exemplos resolvidos, nenhum deles entre as frases de avaliação.

As instruções usam as mesmas convenções de período das regras (ADR 0005), calculadas a partir da data
de hoje informada; a avaliação passa a data de referência das frases anotadas, para que as respostas
gravadas continuem valendo em outros dias.
"""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from app.search.rules.period import OLD_YEARS, RECENT_YEARS
from app.shared.validation import read_config_json, require_bool, require_object

Variant = Literal["zero_shot", "few_shot"]
VARIANTS: tuple[Variant, ...] = ("zero_shot", "few_shot")
PLACEHOLDERS = ("hoje", "generos", "inicio_recente", "fim_antigo")
OUTPUT_FIELDS = ("generos", "generos_excluidos", "lancado_depois", "lancado_antes", "bem_avaliado", "tema")
MAX_INSTRUCTIONS = 30
MAX_EXAMPLES = 12
MAX_TEXT_CHARS = 2000


@dataclass(frozen=True)
class Example:
    """Frase resolvida para o few-shot."""

    text: str
    output: dict


@dataclass(frozen=True)
class InterpretationPrompt:
    """Instruções, exemplos e as escolhas do site, já validados."""

    instructions: tuple[str, ...]
    examples: tuple[Example, ...]
    site_variant: Variant
    use_theme: bool

    def system(self, variant: Variant, today: date, genre_names: list[str]) -> str:
        """Instruções do sistema para a variante, com a data e os gêneros preenchidos."""
        values = {
            "hoje": today.isoformat(),
            "generos": ", ".join(genre_names),
            "inicio_recente": f"{today.year - RECENT_YEARS}-01-01",
            "fim_antigo": f"{today.year - OLD_YEARS - 1}-12-31",
        }
        lines = [instruction.format(**values) for instruction in self.instructions]
        if variant == "few_shot":
            lines += ["", "Exemplos:"]
            lines += [
                f"Frase: {quoted(example.text)}\nResposta: {json.dumps(example.output, ensure_ascii=False)}" for example in self.examples
            ]
        return "\n".join(lines)


def quoted(text: str) -> str:
    """Texto entre aspas, com escape de JSON: a frase do usuário não consegue fechar as aspas."""
    return json.dumps(text, ensure_ascii=False)


def user_prompt(text: str) -> str:
    """Pedido ao LLM com a frase do usuário."""
    return f"Frase: {quoted(text)}"


def load_prompt(path: Path) -> InterpretationPrompt:
    """Lê e valida o prompt; marcadores desconhecidos e exemplos sem todos os campos são recusados."""
    data = require_object(
        read_config_json(path),
        "prompt da interpretação",
        required={"variante_do_site", "usar_tema_na_busca", "instrucoes", "exemplos"},
        optional={"description"},
    )
    if data["variante_do_site"] not in VARIANTS:
        raise ValueError(f"variante_do_site deve ser uma de {list(VARIANTS)}")
    instructions = data["instrucoes"]
    if not isinstance(instructions, list) or not 1 <= len(instructions) <= MAX_INSTRUCTIONS:
        raise ValueError(f"instrucoes deve listar de 1 a {MAX_INSTRUCTIONS} textos")
    examples = data["exemplos"]
    if not isinstance(examples, list) or not 1 <= len(examples) <= MAX_EXAMPLES:
        raise ValueError(f"exemplos deve listar de 1 a {MAX_EXAMPLES} frases")
    prompt = InterpretationPrompt(
        instructions=tuple(_text(item, "instrucoes") for item in instructions),
        examples=tuple(_example(item, position) for position, item in enumerate(examples)),
        site_variant=data["variante_do_site"],
        use_theme=require_bool(data["usar_tema_na_busca"], "usar_tema_na_busca"),
    )
    try:
        prompt.system("few_shot", date(2000, 1, 1), [])
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError(f"Marcador inválido nas instruções; use só {list(PLACEHOLDERS)}") from exc
    return prompt


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT_CHARS:
        raise ValueError(f"{where} deve conter textos de 1 a {MAX_TEXT_CHARS} caracteres")
    return value


def _example(value: object, position: int) -> Example:
    where = f"exemplo {position}"
    item = require_object(value, where, required={"texto", "saida"})
    output = require_object(item["saida"], f"{where}: saida", required=OUTPUT_FIELDS)
    return Example(_text(item["texto"], where), {name: output[name] for name in OUTPUT_FIELDS})
