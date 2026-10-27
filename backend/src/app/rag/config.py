"""Configuração do RAG (`config/rag/rag.json`): tamanho do contexto, trechos de crítica e prompt versionado."""

from dataclasses import dataclass, replace
from pathlib import Path

from app.shared.validation import read_config_json, require_int, require_object

MAX_INSTRUCTIONS = 20
MAX_TEXT_CHARS = 2000


@dataclass(frozen=True)
class RagConfig:
    """Parâmetros da recuperação e da geração, já validados."""

    k: int
    excerpts_per_movie: int
    excerpt_chars: int
    overview_chars: int
    max_cited: int
    instructions: tuple[str, ...]
    no_context_answer: str

    def with_k(self, k: int) -> RagConfig:
        """Mesma configuração com outro tamanho de contexto (usado na avaliação)."""
        return replace(self, k=k)

    def without_reviews(self) -> RagConfig:
        """Mesma configuração sem trechos de crítica (ablação da avaliação)."""
        return replace(self, excerpts_per_movie=0)

    def system(self) -> str:
        return "\n".join(instruction.format(max_filmes=self.max_cited) for instruction in self.instructions)


def load_config(path: Path) -> RagConfig:
    data = require_object(
        read_config_json(path),
        "configuração do RAG",
        required={
            "k",
            "trechos_por_filme",
            "caracteres_por_trecho",
            "caracteres_da_sinopse",
            "max_filmes_citados",
            "instrucoes",
            "resposta_sem_contexto",
        },
        optional={"description"},
    )
    instructions = data["instrucoes"]
    if not isinstance(instructions, list) or not 1 <= len(instructions) <= MAX_INSTRUCTIONS:
        raise ValueError(f"instrucoes deve listar de 1 a {MAX_INSTRUCTIONS} textos")
    config = RagConfig(
        k=require_int(data["k"], "k", 1, 50),
        excerpts_per_movie=require_int(data["trechos_por_filme"], "trechos_por_filme", 0, 5),
        excerpt_chars=require_int(data["caracteres_por_trecho"], "caracteres_por_trecho", 100, 2000),
        overview_chars=require_int(data["caracteres_da_sinopse"], "caracteres_da_sinopse", 100, 3000),
        max_cited=require_int(data["max_filmes_citados"], "max_filmes_citados", 1, 10),
        instructions=tuple(_text(item, "instrucoes") for item in instructions),
        no_context_answer=_text(data["resposta_sem_contexto"], "resposta_sem_contexto"),
    )
    try:
        config.system()
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError("Marcador inválido nas instruções; use só {max_filmes}") from exc
    return config


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT_CHARS:
        raise ValueError(f"{where} deve conter textos de 1 a {MAX_TEXT_CHARS} caracteres")
    return value
