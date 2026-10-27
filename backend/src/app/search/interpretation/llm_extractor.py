"""Interpretação da frase por LLM: o mesmo `ExtractedFilters` das regras, a partir de uma saída estruturada.

O esquema da saída é montado com os nomes de gênero do catálogo como `enum`, então o LLM não consegue
devolver um gênero que não existe; datas fora do formato AAAA-MM-DD ou impossíveis também são recusadas
pela validação (e, depois de uma nova tentativa, viram `LLMUnavailable("json_invalido")`). Os nomes viram
IDs pelo mesmo caminho das regras, e "bem avaliado" usa o limiar das regras (nota ≥ 7 e ≥ 100 votos,
ordenado por nota). Um gênero pedido e rejeitado ao mesmo tempo fica só nos excluídos.
"""

from collections.abc import Callable, Sequence
from datetime import date
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

from app.llm.ports import LanguageModel, LLMRequest, LLMResponse
from app.search.filters import ExtractedFilters
from app.search.interpretation.prompt import InterpretationPrompt, Variant, user_prompt
from app.search.ports import POPULARITY_DESC, RATING_DESC, GenreSource
from app.search.rules.extractor import genre_ids_by_name, resolve_genres
from app.search.rules.lexicon import HIGH_QUALITY

MAX_GENRES = 5
MAX_THEME_CHARS = 200
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class InterpretationOutput(BaseModel):
    """Campos comuns da saída; `generos` e `generos_excluidos` ganham o `enum` do catálogo em `output_model`."""

    model_config = ConfigDict(extra="forbid")

    generos: list[str]
    generos_excluidos: list[str]
    lancado_depois: str | None = Field(pattern=DATE_PATTERN, description="Data AAAA-MM-DD ou null")
    lancado_antes: str | None = Field(pattern=DATE_PATTERN, description="Data AAAA-MM-DD ou null")
    bem_avaliado: bool
    tema: str = Field(max_length=MAX_THEME_CHARS, description="Assunto da frase sem os filtros, ou vazio")

    @field_validator("lancado_depois", "lancado_antes")
    @classmethod
    def _real_date(cls, value: str | None) -> str | None:
        if value is not None:
            date.fromisoformat(value)
        return value


def output_model(genre_names: Sequence[str]) -> type[InterpretationOutput]:
    """Modelo da saída com os gêneros restritos aos nomes do catálogo."""
    genre = cast(Any, Literal).__getitem__(tuple(genre_names))
    genres_field = (cast(Any, list)[genre], Field(max_length=MAX_GENRES))
    return create_model(
        "FiltrosDaConsulta",
        __base__=InterpretationOutput,
        generos=genres_field,
        generos_excluidos=genres_field,
    )


class LLMFilterExtractor:
    """`PreferenceExtractor` por LLM; `use_theme` decide se o tema substitui a frase na busca por sinopse."""

    def __init__(
        self,
        model: LanguageModel,
        genres: GenreSource,
        prompt: InterpretationPrompt,
        variant: Variant | None = None,
        today: Callable[[], date] = date.today,
        use_theme: bool | None = None,
    ) -> None:
        self._model = model
        self._genres = genres
        self._prompt = prompt
        self._variant: Variant = variant or prompt.site_variant
        self._today = today
        self._use_theme = prompt.use_theme if use_theme is None else use_theme
        self._output: type[InterpretationOutput] | None = None

    def extract(self, text: str) -> ExtractedFilters:
        return self.to_filters(self.ask(text).data)

    def ask(self, text: str) -> LLMResponse:
        """Resposta validada do LLM, com provedor, modelo e tokens (a avaliação os registra)."""
        return self._model.generate(self.request(text))

    def request(self, text: str) -> LLMRequest:
        """Pedido ao LLM para `text`; o gênero de cada nome vem do catálogo."""
        names = list(self._genres.genres().values())
        if self._output is None:
            self._output = output_model(names)
        return LLMRequest("interpretacao", self._prompt.system(self._variant, self._today(), names), user_prompt(text), self._output)

    def to_filters(self, data: dict) -> ExtractedFilters:
        """Converte a saída validada nos filtros da busca."""
        ids_by_name = genre_ids_by_name(self._genres.genres())
        excluded = resolve_genres(data["generos_excluidos"], ids_by_name)
        included = tuple(genre for genre in resolve_genres(data["generos"], ids_by_name) if genre not in excluded)
        quality = data["bem_avaliado"]
        theme = data["tema"].strip()
        return ExtractedFilters(
            genres=included,
            excluded_genres=excluded,
            min_rating=HIGH_QUALITY.min_rating if quality else None,
            min_votes=HIGH_QUALITY.min_votes if quality else None,
            released_after=data["lancado_depois"],
            released_before=data["lancado_antes"],
            sort_by=RATING_DESC if quality else POPULARITY_DESC,
            origin="llm",
            theme=theme if self._use_theme and theme else None,
        )
