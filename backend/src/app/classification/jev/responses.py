"""Validação das respostas do Jev: dado externo, conferido antes de entrar em métricas ou arquivos.

Uma resposta só é aceita com todas as perguntas respondidas, a opção da Choice entre as enviadas e
probabilidades, Nouls e confiança entre 0 e 1. Os valores são arredondados para que a mesma resposta
produza sempre os mesmos bytes.
"""

from collections.abc import Mapping

from app.classification.jev.ports import Question
from app.representations.metrics import rounded

MAX_MODEL_CHARS = 100


def validate_response(raw: object, questions: Mapping[str, Question]) -> dict:
    """Resposta normalizada `{"model", "usage", "answers"}` ou `ValueError` com o campo inválido."""
    if not isinstance(raw, dict):
        raise ValueError("A resposta do Jev deve ser um objeto")
    answers = raw.get("answers")
    if not isinstance(answers, dict):
        raise ValueError("A resposta do Jev não tem answers")
    if missing := sorted(questions.keys() - answers.keys()):
        raise ValueError(f"Perguntas sem resposta: {missing}")
    return {
        "model": _model(raw.get("model")),
        "usage": _usage(raw.get("usage")),
        "answers": {name: _answer(answers[name], question, name) for name, question in questions.items()},
    }


def _answer(value: object, question: Question, name: str) -> dict:
    if not isinstance(value, dict) or value.get("type") != question.kind:
        raise ValueError(f"{name}: resposta do tipo errado; esperado {question.kind}")
    if question.kind == "noul":
        return {"type": "noul", "noul": _probability(value.get("noul"), f"{name}.noul")}
    choice = value.get("choice")
    if choice not in question.option_keys:
        raise ValueError(f"{name}: opção fora das enviadas: {choice!r}")
    probabilities = value.get("probabilities") or {}
    if not isinstance(probabilities, dict) or not probabilities.keys() <= set(question.option_keys):
        raise ValueError(f"{name}: probabilidades com opções desconhecidas")
    confidence = value.get("confidence")
    return {
        "type": "choice",
        "choice": choice,
        "probabilities": {
            key: _probability(probabilities[key], f"{name}.probabilities") for key in question.option_keys if key in probabilities
        },
        "confidence": None if confidence is None else _probability(confidence, f"{name}.confidence"),
    }


def _probability(value: object, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value <= 1:
        raise ValueError(f"{where} deve ser número entre 0 e 1")
    return rounded(value)


def _model(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > MAX_MODEL_CHARS:
        raise ValueError("model deve ser texto curto")
    return value


def _usage(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("usage deve ser um objeto")
    usage: dict[str, int | None] = {}
    for field in ("input_tokens", "output_tokens"):
        count = value.get(field)
        if count is not None and (type(count) is not int or count < 0):
            raise ValueError(f"usage.{field} deve ser inteiro não negativo")
        usage[field] = count
    return usage
