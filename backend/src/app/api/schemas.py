"""Modelos de resposta da API. Os nomes dos campos em português são o contrato público (ADR 0008).

Os modelos de filme declaram os campos usados pela interface e aceitam os demais campos do TMDB,
repassados sem alteração.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.search.service import FilterInterpretation, Notice, SearchResult


class SearchCatalog(BaseModel):
    """Onde a busca por tema e os filmes parecidos procuram: o catálogo do site ou, sem ele, a amostra avaliada."""

    model_config = ConfigDict(extra="forbid")

    origem: Literal["catalogo_do_site", "amostra_avaliada"]
    filmes: int


class Health(BaseModel):
    """Estado do servidor e, quando carregado, o catálogo da busca por tema (`null` sem busca por tema)."""

    status: Literal["ok"] = "ok"
    catalogo: SearchCatalog | None = None


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


class GenreScore(BaseModel):
    """Probabilidade de um gênero."""

    model_config = ConfigDict(extra="forbid")

    genero: str
    probabilidade: float


class ClassificationResponse(BaseModel):
    """Resultado de `/classificacao`: gêneros do mais ao menos provável e o modelo usado."""

    model_config = ConfigDict(extra="forbid")

    genero_previsto: str
    generos: list[GenreScore]
    representacao: str
    sinopses_de_treino: int


class TermWeight(BaseModel):
    """Palavra do texto e a sua contribuição para a polaridade."""

    model_config = ConfigDict(extra="forbid")

    palavra: str
    peso: float


class SentimentResponse(BaseModel):
    """Resultado de `/sentimento`: polaridade, probabilidade de ser positiva, nota prevista e o modelo usado.

    As listas de palavras vêm vazias quando a representação não é lexical.
    """

    model_config = ConfigDict(extra="forbid")

    polaridade: Literal["positivo", "negativo"]
    probabilidade_positiva: float
    nota_prevista: float
    palavras_positivas: list[TermWeight]
    palavras_negativas: list[TermWeight]
    representacao: str
    criticas_de_treino: int


class EntityMention(BaseModel):
    """Menção reconhecida pelo NER, com as posições de caractere no texto (`fim` exclusivo)."""

    model_config = ConfigDict(extra="forbid")

    texto: str
    categoria: str
    inicio: int
    fim: int


class RelationTriple(BaseModel):
    """Tripla sujeito — relação → objeto, a sentença de origem (a partir de 1) e a regra que a gerou."""

    model_config = ConfigDict(extra="forbid")

    sujeito: str
    relacao: str
    objeto: str
    sentenca: int
    regra: Literal["svo", "obl", "coordenacao"]


class EntitiesResponse(BaseModel):
    """Resultado de `/entidades`: menções na ordem do texto, triplas e o modelo usado."""

    model_config = ConfigDict(extra="forbid")

    entidades: list[EntityMention]
    relacoes: list[RelationTriple]
    modelo: str


class SimilarMoviesResponse(BaseModel):
    """Resultado de `/filmes/{id}/parecidos`: os filmes mais parecidos, do mais ao menos próximo."""

    model_config = ConfigDict(extra="forbid")

    filme_id: int
    na_amostra: bool
    representacao: str
    parecidos: list[MovieSummary]


class SearchResponse(BaseModel):
    """Resultado de `/pesquisa`."""

    modo: Literal["titulo", "descoberta", "sinopse"]
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
