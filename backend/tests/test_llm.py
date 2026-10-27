"""Camada de LLM sem rede: configuração, adaptadores Gemini e Groq, transporte, saída estruturada, reserva, cache, orçamento e replay."""

import json
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

import requests
from pydantic import BaseModel, Field

from app.llm.batch import LazyModel, PacedModel
from app.llm.budget import DailyBudget
from app.llm.cache import CachedModel
from app.llm.compose import available_providers, build_llm, stack_for
from app.llm.config import LLMConfig, ProviderConfig, load_config
from app.llm.fallback import FallbackModel
from app.llm.gemini import GeminiProvider, gemini_schema
from app.llm.groq import GroqProvider
from app.llm.ports import Completion, LLMRequest, LLMUnavailable, RawReply
from app.llm.replay import RecordingModel, ReplayModel, ReuseModel, to_record
from app.llm.structured import StructuredModel, parse
from app.llm.transport import JsonPoster
from app.settings import REPOSITORY_DIR, Settings
from tests.fakes import FakeLanguageModel

SECRET = "CHAVE-SECRETA-NAO-PODE-VAZAR"
GEMINI = ProviderConfig("gemini", "gemini-flash-lite-latest", "https://gemini.example/v1beta", 5.0)
GROQ = ProviderConfig("groq", "openai/gpt-oss-20b", "https://groq.example/openai/v1", 5.0, "low")
CONFIG = LLMConfig(
    providers=(GEMINI, GROQ),
    temperature=0.0,
    max_output_tokens={"interpretacao": 100, "sentimento": 200, "rag": 300},
    daily_budget={"interpretacao": 2, "sentimento": 1, "rag": 0},
    request_interval_seconds=0.0,
)


class Genre(BaseModel):
    genero: Literal["Drama", "Terror"]
    confianca: float = Field(ge=0, le=1)


class Cited(BaseModel):
    id: int
    motivo: str | None = None


class Answer(BaseModel):
    resposta: str
    filmes: list[Cited]


def request(prompt: str = "casa assombrada", purpose: Literal["interpretacao", "sentimento", "rag"] = "interpretacao") -> LLMRequest:
    return LLMRequest(purpose=purpose, system="sistema", prompt=prompt, output=Genre)


class FakeResponse:
    def __init__(self, status: int = 200, payload: object = None, text: str | None = None) -> None:
        self.status_code = status
        self._payload = payload
        self.text = text if text is not None else json.dumps(payload)

    def json(self) -> object:
        if self._payload is None:
            raise ValueError("sem JSON")
        return self._payload


class FakeSession:
    def __init__(self, *outcomes: FakeResponse | Exception) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict] = []
        self.closed = False

    def post(self, url: str, json: dict, headers: dict, timeout: float) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self) -> None:
        self.closed = True


def poster(session: FakeSession, name: str = "Gemini") -> JsonPoster:
    return JsonPoster(name, 5.0, session_factory=lambda: session)  # type: ignore[arg-type,return-value]


class FakeProvider:
    def __init__(self, *texts: str, name: str = "falso", model: str = "falso-1") -> None:
        self.name = name
        self.model = model
        self.texts = list(texts)
        self.completions: list[Completion] = []

    def complete(self, completion: Completion) -> RawReply:
        self.completions.append(completion)
        return RawReply(self.texts.pop(0), f"{self.model}-exato", 7, 3)


def gemini_payload(text: str) -> dict:
    return {
        "candidates": [{"content": {"parts": [{"text": "pensando...", "thought": True}, {"text": text}]}, "finishReason": "STOP"}],
        "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 4},
        "modelVersion": "gemini-2.9-flash-lite-001",
    }


class ConfigTests(unittest.TestCase):
    def test_repository_config_is_valid(self) -> None:
        config = load_config(REPOSITORY_DIR / "config" / "llm" / "llm.json")
        self.assertEqual([provider.name for provider in config.providers], ["gemini", "groq"])
        self.assertEqual(config.temperature, 0.0)

    def test_rejects_unsafe_or_incomplete_config(self) -> None:
        base = json.loads((REPOSITORY_DIR / "config" / "llm" / "llm.json").read_text(encoding="utf-8"))
        cases = {
            "campo desconhecido": {**base, "extra": 1},
            "http": {**base, "providers": [{**base["providers"][0], "base_url": "http://inseguro"}]},
            "repetido": {**base, "providers": [base["providers"][0], base["providers"][0]]},
            "sem propósito": {**base, "daily_budget": {"interpretacao": 1, "sentimento": 1}},
            "booleano": {**base, "daily_budget": {**base["daily_budget"], "rag": True}},
            "provedor desconhecido": {**base, "providers": [{**base["providers"][0], "name": "outro"}]},
        }
        with TemporaryDirectory() as folder:
            for label, content in cases.items():
                with self.subTest(label):
                    path = Path(folder) / "llm.json"
                    path.write_text(json.dumps(content), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_config(path)


class GeminiTests(unittest.TestCase):
    def test_schema_conversion_resolves_refs_enums_and_nullable(self) -> None:
        converted = gemini_schema(Answer.model_json_schema())
        self.assertEqual(converted["type"], "OBJECT")
        self.assertEqual(converted["propertyOrdering"], ["resposta", "filmes"])
        item = converted["properties"]["filmes"]["items"]
        self.assertEqual(item["properties"]["id"], {"type": "INTEGER"})
        self.assertEqual(item["properties"]["motivo"], {"type": "STRING", "nullable": True})
        self.assertNotIn("title", json.dumps(converted))
        genre = gemini_schema(Genre.model_json_schema())["properties"]
        self.assertEqual(genre["genero"]["enum"], ["Drama", "Terror"])
        self.assertEqual((genre["confianca"]["minimum"], genre["confianca"]["maximum"]), (0, 1))

    def test_request_puts_key_in_header_and_reads_answer_without_thoughts(self) -> None:
        session = FakeSession(FakeResponse(payload=gemini_payload('{"genero": "Terror", "confianca": 0.9}')))
        provider = GeminiProvider(GEMINI, SECRET, poster(session))
        reply = provider.complete(Completion("sistema", "pergunta", Genre.model_json_schema(), 0.0, 100))
        call = session.calls[0]
        self.assertEqual(call["url"], "https://gemini.example/v1beta/models/gemini-flash-lite-latest:generateContent")
        self.assertNotIn(SECRET, call["url"])
        self.assertEqual(call["headers"]["x-goog-api-key"], SECRET)
        config = call["json"]["generationConfig"]
        self.assertEqual((config["responseMimeType"], config["maxOutputTokens"], config["temperature"]), ("application/json", 100, 0.0))
        self.assertEqual(config["responseSchema"]["type"], "OBJECT")
        self.assertEqual(reply, RawReply('{"genero": "Terror", "confianca": 0.9}', "gemini-2.9-flash-lite-001", 11, 4))

    def test_blocked_or_empty_answers_fail(self) -> None:
        blocked = FakeSession(FakeResponse(payload={"promptFeedback": {"blockReason": "SAFETY"}}))
        with self.assertRaises(LLMUnavailable) as caught:
            GeminiProvider(GEMINI, SECRET, poster(blocked)).complete(Completion("s", "p", {}, 0.0, 10))
        self.assertEqual(caught.exception.reason, "indisponivel")
        empty = FakeSession(FakeResponse(payload={"candidates": [{"content": {"parts": []}, "finishReason": "MAX_TOKENS"}]}))
        with self.assertRaises(LLMUnavailable) as caught:
            GeminiProvider(GEMINI, SECRET, poster(empty)).complete(Completion("s", "p", {}, 0.0, 10))
        self.assertEqual(caught.exception.reason, "json_invalido")

    def test_rejects_missing_key_and_model_that_changes_the_path(self) -> None:
        with self.assertRaises(ValueError):
            GeminiProvider(GEMINI, "")
        with self.assertRaises(ValueError):
            GeminiProvider(replace(GEMINI, model="../outro"), SECRET)


class GroqTests(unittest.TestCase):
    def test_request_uses_bearer_json_mode_and_schema_in_system(self) -> None:
        payload = {
            "choices": [{"message": {"content": '{"genero": "Drama", "confianca": 0.5}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 6},
            "model": "openai/gpt-oss-20b",
        }
        session = FakeSession(FakeResponse(payload=payload))
        reply = GroqProvider(GROQ, SECRET, poster(session, "Groq")).complete(
            Completion("sistema", "pergunta", Genre.model_json_schema(), 0.0, 100)
        )
        call = session.calls[0]
        self.assertEqual(call["url"], "https://groq.example/openai/v1/chat/completions")
        self.assertEqual(call["headers"]["Authorization"], f"Bearer {SECRET}")
        body = call["json"]
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual((body["model"], body["max_completion_tokens"], body["reasoning_effort"]), ("openai/gpt-oss-20b", 100, "low"))
        self.assertIn('"genero"', body["messages"][0]["content"])
        self.assertEqual(body["messages"][1], {"role": "user", "content": "pergunta"})
        self.assertEqual(reply, RawReply('{"genero": "Drama", "confianca": 0.5}', "openai/gpt-oss-20b", 20, 6))

    def test_reasoning_effort_is_optional(self) -> None:
        payload = {"choices": [{"message": {"content": "{}"}}]}
        session = FakeSession(FakeResponse(payload=payload))
        GroqProvider(replace(GROQ, reasoning_effort=None), SECRET, poster(session, "Groq")).complete(Completion("s", "p", {}, 0.0, 10))
        self.assertNotIn("reasoning_effort", session.calls[0]["json"])


class TransportTests(unittest.TestCase):
    def test_errors_are_translated_without_leaking_url_or_key(self) -> None:
        cases = [
            (FakeResponse(429, {"error": {"message": "quota"}}), "cota"),
            (FakeResponse(401, {"error": {}}), "sem_chave"),
            (FakeResponse(403, {"error": {}}), "sem_chave"),
            (FakeResponse(400, {"error": {"code": "json_validate_failed"}}), "json_invalido"),
            (FakeResponse(400, {"error": {"message": "Invalid schema"}}), "indisponivel"),
            (FakeResponse(503, {"error": {}}), "indisponivel"),
            (FakeResponse(200, None, text="<html>"), "indisponivel"),
            (FakeResponse(200, ["lista"]), "indisponivel"),
            (requests.Timeout(f"https://x?key={SECRET}"), "timeout"),
            (requests.ConnectionError(f"https://x?key={SECRET}"), "indisponivel"),
        ]
        for outcome, reason in cases:
            with self.subTest(reason=reason, outcome=type(outcome).__name__):
                with self.assertRaises(LLMUnavailable) as caught:
                    poster(FakeSession(outcome)).post(f"https://x/{SECRET}", {"Authorization": SECRET}, {})
                self.assertEqual(caught.exception.reason, reason)
                self.assertNotIn(SECRET, str(caught.exception))

    def test_bad_request_shows_provider_message(self) -> None:
        with self.assertRaises(LLMUnavailable) as caught:
            poster(FakeSession(FakeResponse(400, {"error": {"message": "Invalid schema"}}))).post("https://x", {}, {})
        self.assertIn("Invalid schema", str(caught.exception))

    def test_close_closes_sessions(self) -> None:
        session = FakeSession(FakeResponse(payload={}))
        transport = poster(session)
        transport.post("https://x", {}, {})
        transport.close()
        self.assertTrue(session.closed)


class StructuredTests(unittest.TestCase):
    def test_valid_answer_uses_purpose_settings(self) -> None:
        provider = FakeProvider('{"genero": "Terror", "confianca": 0.9}')
        response = StructuredModel(provider, CONFIG).generate(request(purpose="sentimento"))
        self.assertEqual(response.data, {"genero": "Terror", "confianca": 0.9})
        self.assertEqual(
            (response.provider, response.model, response.input_tokens, response.output_tokens), ("falso", "falso-1-exato", 7, 3)
        )
        self.assertEqual((provider.completions[0].max_output_tokens, provider.completions[0].temperature), (200, 0.0))

    def test_fenced_json_is_accepted(self) -> None:
        self.assertEqual(parse('```json\n{"genero": "Drama", "confianca": 1}\n```', Genre), {"genero": "Drama", "confianca": 1.0})

    def test_invalid_answer_gets_one_repair_attempt(self) -> None:
        provider = FakeProvider('{"genero": "Comédia", "confianca": 2}', '{"genero": "Terror", "confianca": 0.8}')
        response = StructuredModel(provider, CONFIG).generate(request())
        self.assertEqual(response.data["genero"], "Terror")
        self.assertEqual((response.input_tokens, response.output_tokens), (14, 6))
        self.assertIn("genero", provider.completions[1].prompt)
        self.assertTrue(provider.completions[1].prompt.startswith("casa assombrada"))

    def test_invalid_twice_fails_as_invalid_json(self) -> None:
        provider = FakeProvider("não é JSON", '{"genero": "Comédia"}')
        with self.assertRaises(LLMUnavailable) as caught:
            StructuredModel(provider, CONFIG).generate(request())
        self.assertEqual(caught.exception.reason, "json_invalido")


class FallbackTests(unittest.TestCase):
    def test_availability_failures_go_to_the_next_model(self) -> None:
        reserve = FakeLanguageModel({"genero": "Drama", "confianca": 0.4}, provider="reserva")
        model = FallbackModel([FakeLanguageModel(LLMUnavailable("cota", "429")), reserve])
        self.assertEqual(model.generate(request()).provider, "reserva")

    def test_format_errors_do_not_fall_back(self) -> None:
        reserve = FakeLanguageModel({"genero": "Drama", "confianca": 0.4})
        model = FallbackModel([FakeLanguageModel(LLMUnavailable("json_invalido", "formato")), reserve])
        with self.assertRaises(LLMUnavailable) as caught:
            model.generate(request())
        self.assertEqual(caught.exception.reason, "json_invalido")
        self.assertEqual(reserve.requests, [])

    def test_all_failing_reports_every_failure(self) -> None:
        model = FallbackModel(
            [FakeLanguageModel(LLMUnavailable("cota", "primeiro")), FakeLanguageModel(LLMUnavailable("timeout", "segundo"))]
        )
        with self.assertRaises(LLMUnavailable) as caught:
            model.generate(request())
        self.assertEqual(caught.exception.reason, "timeout")
        self.assertIn("primeiro", str(caught.exception))


class CacheAndBudgetTests(unittest.TestCase):
    def test_repeated_request_is_served_from_cache(self) -> None:
        inner = FakeLanguageModel({"genero": "Terror", "confianca": 0.9})
        cached = CachedModel(inner, maxsize=1)
        cached.generate(request())
        cached.generate(request())
        self.assertEqual(len(inner.requests), 1)
        cached.generate(request("outro"))
        cached.generate(request())
        self.assertEqual(len(inner.requests), 3)

    def test_failures_are_not_cached(self) -> None:
        inner = FakeLanguageModel(LLMUnavailable("cota", "429"))
        cached = CachedModel(inner)
        for _ in range(2):
            with self.assertRaises(LLMUnavailable):
                cached.generate(request())
        self.assertEqual(len(inner.requests), 2)

    def test_budget_limits_each_purpose_and_resets_next_day(self) -> None:
        day = [date(2026, 10, 26)]
        inner = FakeLanguageModel({"genero": "Terror", "confianca": 0.9})
        budget = DailyBudget(inner, CONFIG.daily_budget, today=lambda: day[0])
        budget.generate(request("a"))
        budget.generate(request("b"))
        with self.assertRaises(LLMUnavailable) as caught:
            budget.generate(request("c"))
        self.assertEqual(caught.exception.reason, "orcamento")
        self.assertEqual(budget.remaining(), {"interpretacao": 0, "sentimento": 1, "rag": 0})
        day[0] = date(2026, 10, 27)
        self.assertEqual(budget.remaining()["interpretacao"], 2)
        budget.generate(request("c"))
        self.assertEqual(len(inner.requests), 3)

    def test_cache_hits_do_not_spend_budget(self) -> None:
        stack = stack_for([FakeProvider('{"genero": "Terror", "confianca": 0.9}')], CONFIG)  # type: ignore[list-item]
        for _ in range(3):
            stack.model.generate(request())
        self.assertEqual(stack.budget.remaining()["interpretacao"], 1)


class ReplayTests(unittest.TestCase):
    def test_recorded_answers_replay_without_calls(self) -> None:
        recording = RecordingModel(FakeLanguageModel({"genero": "Terror", "confianca": 0.9}))
        original = recording.generate(request())
        self.assertNotIn("latency_ms", recording.records[0])
        with TemporaryDirectory() as folder:
            path = Path(folder) / "responses.jsonl"
            path.write_text("".join(json.dumps(record) + "\n" for record in recording.records), encoding="utf-8")
            replayed = ReplayModel.from_file(path).generate(request())
        self.assertEqual((replayed.data, replayed.provider, replayed.model), (original.data, original.provider, original.model))
        self.assertEqual(to_record(request(), replayed), recording.records[0])

    def test_missing_request_resumes_with_the_real_model(self) -> None:
        recording = RecordingModel(FakeLanguageModel({"genero": "Terror", "confianca": 0.9}))
        recording.generate(request("gravado"))
        real = FakeLanguageModel({"genero": "Drama", "confianca": 0.1})
        resumed = FallbackModel([ReplayModel(recording.records), real])
        resumed.generate(request("gravado"))
        resumed.generate(request("novo"))
        self.assertEqual([item.prompt for item in real.requests], ["novo"])

    def test_record_that_no_longer_matches_the_schema_fails(self) -> None:
        recording = RecordingModel(FakeLanguageModel({"genero": "Terror", "confianca": 0.9}))
        recording.generate(request())
        record = {**recording.records[0], "raw_text": '{"genero": "Comédia", "confianca": 0.9}'}
        with self.assertRaises(LLMUnavailable) as caught:
            ReplayModel([record]).generate(request())
        self.assertEqual(caught.exception.reason, "json_invalido")

    def test_records_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            ReplayModel([{"key": "x"}])


class ComposeTests(unittest.TestCase):
    def test_only_providers_with_keys_are_used(self) -> None:
        settings = Settings(_env_file=None, groq_api_key=SECRET)
        providers = available_providers(CONFIG, settings)
        self.assertEqual([provider.name for provider in providers], ["groq"])

    def test_without_keys_there_is_no_llm(self) -> None:
        self.assertIsNone(build_llm(Settings(_env_file=None, gemini_api_key="  ")))

    def test_status_never_shows_keys(self) -> None:
        settings = Settings(_env_file=None, gemini_api_key=SECRET, groq_api_key=SECRET)
        stack = build_llm(settings)
        assert stack is not None
        self.assertEqual(stack.providers, ("gemini:gemini-flash-lite-latest", "groq:openai/gpt-oss-20b"))
        self.assertNotIn(SECRET, json.dumps(stack.status()))
        self.assertNotIn(SECRET, repr(settings))


class BatchTests(unittest.TestCase):
    def test_lazy_model_is_created_on_first_call(self) -> None:
        created: list[FakeLanguageModel] = []

        def factory() -> FakeLanguageModel:
            created.append(FakeLanguageModel({"genero": "Terror", "confianca": 0.5}))
            return created[-1]

        lazy = LazyModel(factory)
        self.assertEqual(created, [])
        lazy.generate(request())
        lazy.generate(request())
        self.assertEqual((len(created), len(created[0].requests)), (1, 2))

    def test_paced_model_waits_only_what_is_missing(self) -> None:
        now = [100.0]
        waits: list[float] = []

        def sleep(seconds: float) -> None:
            waits.append(seconds)
            now[0] += seconds

        paced = PacedModel(FakeLanguageModel({"genero": "Terror", "confianca": 0.5}), 4.0, sleep, lambda: now[0])
        paced.generate(request())
        now[0] += 1.5
        paced.generate(request())
        now[0] += 10
        paced.generate(request())
        self.assertEqual(waits, [2.5])

    def test_reuse_model_answers_recorded_requests_without_calling(self) -> None:
        recorder = RecordingModel(FakeLanguageModel({"genero": "Terror", "confianca": 0.5}))
        recorder.generate(request())
        inner = FakeLanguageModel({"genero": "Drama", "confianca": 0.5})
        reuse = ReuseModel(ReplayModel(recorder.records), inner)
        self.assertTrue(reuse.is_recorded(request()))
        self.assertFalse(reuse.is_recorded(request("outra sinopse")))
        self.assertEqual(reuse.generate(request()).data["genero"], "Terror")
        self.assertEqual(reuse.generate(request("outra sinopse")).data["genero"], "Drama")
        self.assertEqual((reuse.reused, reuse.calls, len(inner.requests)), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
