"""Modelos de resposta da API. Os nomes dos campos em português são o contrato público (ADR 0008).

Os modelos de filme declaram os campos usados pela interface e aceitam os demais campos do TMDB,
repassados sem alteração.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.search.service import FilterInterpretation, Notice, SearchResult


class Health(BaseModel):
    """Estado do servidor."""

    status: Literal["ok"] = "ok"


class Genre(BaseModel):
    """Gênero de um filme."""

    model_config = ConfigDict(extra="allow")

    id: int
    name: str


class MovieSummary(BaseModel):
    """Filme em uma lista de resultados."""

    model_config = ConfigDict(extra="allow")

    id: int
    title: str | None = None
    original_title: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    release_date: str | None = None
    vote_average: float | None = None


class MovieDetails(MovieSummary):
    """Ficha completa de um filme, com gêneros, elenco (`credits`) e vídeos."""

    genres: list[Genre] = []
    credits: dict | None = None
    videos: dict | None = None


class InterpretedFilters(BaseModel):
    """Preferências reconhecidas na pesquisa."""

    model_config = ConfigDict(extra="forbid")

    generos_incluidos: list[str]
    generos_excluidos: list[str]
    nota_minima: float | None
    votos_minimos: int | None
    lancado_apos: str | None
    lancado_antes: str | None


class SearchNotice(BaseModel):
    """Aviso quando a descoberta não gerou consulta."""

    model_config = ConfigDict(extra="forbid")

    aviso: str


class NoInterpretation(BaseModel):
    """Busca por título exato: não há preferências a interpretar."""

    model_config = ConfigDict(extra="forbid")


class SearchResponse(BaseModel):
    """Resultado de `/pesquisa`."""

    modo: Literal["titulo", "descoberta"]
    resultados: list[MovieSummary]
    interpretacao: InterpretedFilters | SearchNotice | NoInterpretation

    @classmethod
    def from_result(cls, result: SearchResult) -> SearchResponse:
        """Converte o resultado do domínio no contrato da API."""
        return cls.model_validate(
            {"modo": result.mode.value, "resultados": result.results, "interpretacao": _interpretation(result.interpretation)}
        )


def _interpretation(value: FilterInterpretation | Notice | None) -> InterpretedFilters | SearchNotice | NoInterpretation:
    if isinstance(value, Notice):
        return SearchNotice(aviso=value.message)
    if isinstance(value, FilterInterpretation):
        return InterpretedFilters(
            generos_incluidos=value.included_genres,
            generos_excluidos=value.excluded_genres,
            nota_minima=value.min_rating,
            votos_minimos=value.min_votes,
            lancado_apos=value.released_after,
            lancado_antes=value.released_before,
        )
    return NoInterpretation()
