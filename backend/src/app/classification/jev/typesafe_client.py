"""Adaptador do SDK `typesafe-sdk` para a porta `DecisionClient` de `app.classification.jev`.

O SDK é o extra opcional `jev` e só é importado ao abrir o cliente, portanto os testes e o CI não
dependem dele. A chave vem de `Settings` (variável `TYPESAFE_API_KEY` ou `backend/.env`) e é passada
ao construtor do SDK; nunca é gravada em arquivos, saídas ou mensagens.
As respostas são convertidas para dicionários e validadas depois, em `app.classification.jev.responses`.
"""

from collections.abc import Mapping
from types import TracebackType
from typing import Any, Self

from app.classification.jev.ports import Question


class TypeSafeDecisionClient:
    """Cliente síncrono do Jev; use como gerenciador de contexto para abrir e fechar a conexão."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._sdk: Any = None
        self._client: Any = None

    def __enter__(self) -> Self:
        try:
            import typesafe_sdk
        except ImportError as exc:
            raise ValueError("SDK do Jev não instalado; em backend, rode: uv sync --frozen --extra jev") from exc
        self._sdk = typesafe_sdk
        self._client = typesafe_sdk.TypeSafeClient(api_key=self._api_key)
        self._client.__enter__()
        return self

    def __exit__(self, kind: type[BaseException] | None, error: BaseException | None, trace: TracebackType | None) -> None:
        if self._client is not None:
            self._client.__exit__(kind, error, trace)
            self._client = None

    def decide(self, state: str, questions: Mapping[str, Question]) -> dict:
        if self._client is None:
            raise RuntimeError("Abra o cliente com `with` antes de chamar o Jev")
        response = self._client.system_one(state=state, questions={name: self._question(q) for name, q in questions.items()})
        return normalize_response(response, questions)

    def _question(self, question: Question) -> Any:
        if question.kind == "choice":
            return self._sdk.Choice(instructions=question.instructions, criteria=dict(question.options))
        return self._sdk.Noul(instructions=question.instructions)


def normalize_response(response: Any, questions: Mapping[str, Question]) -> dict:
    """Converte a resposta do SDK para o dicionário da porta, sem validar valores.

    O SDK expõe as respostas em `answers`; a documentação também cita `choices` e `nouls` por tipo,
    então as duas formas são aceitas.
    """
    answers = getattr(response, "answers", None)
    if answers is None:
        answers = {**(getattr(response, "choices", None) or {}), **(getattr(response, "nouls", None) or {})}
    converted = {name: _answer(answers[name], question.kind) for name, question in questions.items() if name in answers}
    model = getattr(response, "model", None)
    return {"model": None if model is None else str(model), "usage": _usage(getattr(response, "usage", None)), "answers": converted}


def _answer(answer: Any, kind: str) -> dict:
    if kind == "noul":
        return {"type": "noul", "noul": _number(getattr(answer, "noul", None))}
    probabilities = getattr(answer, "probabilities", None) or {}
    return {
        "type": "choice",
        "choice": getattr(answer, "choice", None),
        "probabilities": {str(key): _number(value) for key, value in dict(probabilities).items()},
        "confidence": _number(getattr(answer, "confidence", None)),
    }


def _usage(usage: Any) -> dict | None:
    if usage is None:
        return None
    read = usage.get if isinstance(usage, dict) else lambda field: getattr(usage, field, None)
    return {field: read(field) for field in ("input_tokens", "output_tokens")}


def _number(value: Any) -> Any:
    """Números viram float; valores de outro tipo seguem como estão e a validação os recusa."""
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else value
