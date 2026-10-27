"""Pergunta → contexto recuperado → resposta do LLM em JSON validado → citações conferidas (ADR 0032)."""

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from app.llm.ports import LanguageModel, LLMRequest, LLMResponse
from app.rag.config import RagConfig
from app.rag.grounding import Grounded, ground
from app.rag.prompt import user_prompt
from app.rag.retrieval import Retrieval, Retriever

MAX_ANSWER_CHARS = 2000
MAX_REASON_CHARS = 300
MAX_CITED_ITEMS = 10


class CitedMovie(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=1, description="Número do filme no contexto, o mesmo de [F<id>]")
    motivo: str = Field(max_length=MAX_REASON_CHARS, description="Por que o filme responde à pergunta, em uma frase")


class RagOutput(BaseModel):
    """Saída pedida ao LLM."""

    model_config = ConfigDict(extra="forbid")

    resposta: str = Field(max_length=MAX_ANSWER_CHARS, description="Resposta em português, com [F<id>] depois de cada filme citado")
    filmes: list[CitedMovie] = Field(max_length=MAX_CITED_ITEMS)
    contexto_suficiente: bool = Field(description="false quando o contexto não basta para responder")


@dataclass(frozen=True)
class Answer:
    """Resposta conferida, o contexto usado e quem respondeu; `raw` é a saída do LLM antes da conferência."""

    question: str
    grounded: Grounded
    retrieval: Retrieval
    raw: dict
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class QuestionAnswering:
    """Responde perguntas sobre os filmes do catálogo com o contexto recuperado."""

    def __init__(
        self,
        retriever: Retriever,
        model: LanguageModel,
        genre_names: Callable[[], Mapping[int, str]],
        config: RagConfig,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._retriever = retriever
        self._model = model
        self._genre_names = genre_names
        self._config = config
        self._clock = clock

    @property
    def config(self) -> RagConfig:
        return self._config

    def request(self, question: str, retrieval: Retrieval, config: RagConfig | None = None) -> LLMRequest:
        config = config or self._config
        return LLMRequest("rag", config.system(), user_prompt(question, retrieval, self._genre_names(), config), RagOutput)

    def answer(self, question: str, config: RagConfig | None = None) -> Answer:
        """Levanta `LLMUnavailable` quando o LLM não responde; quem chama decide o que mostrar."""
        config = config or self._config
        start = self._clock()
        retrieval = self._retriever.retrieve(question, config)
        response: LLMResponse = self._model.generate(self.request(question, retrieval, config))
        grounded = ground(response.data, [movie.id for movie in retrieval.movies], config.max_cited, config.no_context_answer)
        return Answer(
            question,
            grounded,
            retrieval,
            response.data,
            response.provider,
            response.model,
            response.input_tokens,
            response.output_tokens,
            round((self._clock() - start) * 1000),
        )
