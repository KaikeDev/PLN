"""Adaptador da API REST do Gemini (`generateContent`) para a porta `Provider`.

A saída estruturada usa `responseMimeType = application/json` e `responseSchema`, que aceita um subconjunto
do OpenAPI: `gemini_schema` converte o JSON Schema do Pydantic para ele (resolve `$ref`, troca `anyOf` com
`null` por `nullable` e descarta `title` e `additionalProperties`). A chave vai no cabeçalho `x-goog-api-key`.
O modelo devolvido é o `modelVersion` da resposta, mais exato que um alias como `gemini-flash-lite-latest`.
"""

import re

from app.llm.config import ProviderConfig
from app.llm.ports import Completion, LLMUnavailable, RawReply
from app.llm.transport import JsonPoster

MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
COPIED_KEYS = ("description", "enum", "minimum", "maximum", "minItems", "maxItems")


class GeminiProvider:
    """Gemini por API REST."""

    name = "gemini"

    def __init__(self, config: ProviderConfig, api_key: str, poster: JsonPoster | None = None) -> None:
        if not api_key:
            raise ValueError("Defina GEMINI_API_KEY no ambiente ou em backend/.env")
        if not MODEL_RE.fullmatch(config.model):
            raise ValueError("O modelo do Gemini deve usar apenas letras, números, ponto, hífen e sublinhado")
        self.model = config.model
        self._url = f"{config.base_url}/models/{config.model}:generateContent"
        self._api_key = api_key
        self._poster = poster or JsonPoster("Gemini", config.timeout_seconds)

    def complete(self, completion: Completion) -> RawReply:
        body = {
            "systemInstruction": {"parts": [{"text": completion.system}]},
            "contents": [{"role": "user", "parts": [{"text": completion.prompt}]}],
            "generationConfig": {
                "temperature": completion.temperature,
                "maxOutputTokens": completion.max_output_tokens,
                "responseMimeType": "application/json",
                "responseSchema": gemini_schema(completion.schema),
            },
        }
        data = self._poster.post(self._url, {"x-goog-api-key": self._api_key}, body)
        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
            reason = (data.get("promptFeedback") or {}).get("blockReason", "sem candidatos")
            raise LLMUnavailable("indisponivel", f"Gemini não gerou resposta ({reason})")
        candidate = candidates[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict) and not part.get("thought"))
        if not text.strip():
            raise LLMUnavailable("json_invalido", f"Gemini não devolveu texto (finishReason={candidate.get('finishReason')})")
        usage = data.get("usageMetadata") or {}
        return RawReply(
            text=text,
            model=str(data.get("modelVersion") or self.model),
            input_tokens=int(usage.get("promptTokenCount") or 0),
            output_tokens=int(usage.get("candidatesTokenCount") or 0),
        )


def gemini_schema(schema: dict) -> dict:
    """JSON Schema do Pydantic convertido para o `responseSchema` do Gemini."""
    definitions = schema.get("$defs", {})

    def convert(node: dict) -> dict:
        if "$ref" in node:
            return convert(definitions[node["$ref"].rsplit("/", 1)[-1]])
        if "anyOf" in node:
            options = [option for option in node["anyOf"] if option.get("type") != "null"]
            if len(options) != 1:
                raise ValueError("O Gemini só aceita anyOf de um tipo com null")
            single = convert(options[0])
            if len(options) < len(node["anyOf"]):
                single["nullable"] = True
            if "description" in node:
                single["description"] = node["description"]
            return single
        if "const" in node:
            node = {**node, "enum": [node["const"]]}
        kind = node.get("type", "string")
        result: dict = {"type": str(kind).upper()}
        result.update({key: node[key] for key in COPIED_KEYS if key in node})
        if kind == "object":
            properties = {name: convert(value) for name, value in node.get("properties", {}).items()}
            result["properties"] = properties
            result["propertyOrdering"] = list(properties)
            if node.get("required"):
                result["required"] = list(node["required"])
        elif kind == "array":
            result["items"] = convert(node.get("items", {}))
        return result

    return convert(schema)
