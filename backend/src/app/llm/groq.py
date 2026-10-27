"""Adaptador da API do Groq (compatível com a da OpenAI, `chat/completions`) para a porta `Provider`.

Usa o modo JSON (`response_format = json_object`), aceito por todos os modelos do Groq; o JSON Schema vai
nas instruções do sistema, e a validação de verdade é a de `app.llm.structured`. Quando o modelo gera JSON
inválido, o Groq responde 400 `json_validate_failed`, traduzido para `json_invalido` em `app.llm.transport`.
A chave vai no cabeçalho `Authorization`.
"""

import json

from app.llm.config import ProviderConfig
from app.llm.ports import Completion, LLMUnavailable, RawReply
from app.llm.transport import JsonPoster

SCHEMA_INSTRUCTION = "Responda somente com um objeto JSON válido, sem texto antes ou depois, que siga este JSON Schema:\n"


class GroqProvider:
    """Groq por API REST."""

    name = "groq"

    def __init__(self, config: ProviderConfig, api_key: str, poster: JsonPoster | None = None) -> None:
        if not api_key:
            raise ValueError("Defina GROQ_API_KEY no ambiente ou em backend/.env")
        self.model = config.model
        self._url = f"{config.base_url}/chat/completions"
        self._api_key = api_key
        self._reasoning_effort = config.reasoning_effort
        self._poster = poster or JsonPoster("Groq", config.timeout_seconds)

    def complete(self, completion: Completion) -> RawReply:
        system = f"{completion.system}\n\n{SCHEMA_INSTRUCTION}{json.dumps(completion.schema, ensure_ascii=False)}"
        body: dict = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": completion.prompt}],
            "temperature": completion.temperature,
            "max_completion_tokens": completion.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        if self._reasoning_effort:
            body["reasoning_effort"] = self._reasoning_effort
        data = self._poster.post(self._url, {"Authorization": f"Bearer {self._api_key}"}, body)
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise LLMUnavailable("indisponivel", "Groq não gerou resposta")
        text = (choices[0].get("message") or {}).get("content") or ""
        if not text.strip():
            raise LLMUnavailable("json_invalido", f"Groq não devolveu texto (finish_reason={choices[0].get('finish_reason')})")
        usage = data.get("usage") or {}
        return RawReply(
            text=text,
            model=str(data.get("model") or self.model),
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
        )
