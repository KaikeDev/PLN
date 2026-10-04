"""Porta do modelo de decisões estruturadas: o pipeline depende deste contrato, não do SDK da TypeSafe.

Uma chamada recebe o texto (`state`) e um conjunto de perguntas tipadas e devolve um dicionário já
convertido para tipos do Python:

    {"model": "jev-1.13.0" | None,
     "usage": {"input_tokens": int | None, "output_tokens": int | None} | None,
     "answers": {nome: {"type": "choice", "choice": str, "probabilities": {opção: float}, "confidence": float | None}
                    | {"type": "noul", "noul": float}}}

A resposta é dado externo, não confiável: `app.classification.jev.responses` a valida antes de qualquer uso.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

QuestionKind = Literal["choice", "noul"]


@dataclass(frozen=True)
class Question:
    """Pergunta tipada. Em `choice`, `options` associa cada opção à descrição usada como critério."""

    kind: QuestionKind
    instructions: str
    options: tuple[tuple[str, str], ...] = ()

    @property
    def option_keys(self) -> tuple[str, ...]:
        return tuple(key for key, _ in self.options)


class DecisionClient(Protocol):
    """Modelo que responde a perguntas tipadas sobre um texto."""

    def decide(self, state: str, questions: Mapping[str, Question]) -> dict: ...
