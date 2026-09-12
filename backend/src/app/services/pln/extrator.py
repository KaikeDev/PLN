"""Orquestra normalizacao + lexico + negacao + periodo -> FiltrosExtraidos.

Modulo puro: nao fala com o TMDB diretamente, so consome o cache ja carregado
por generos_cache (e so toca o cache quando o lexico realmente encontrou algum
nome de genero no texto, para nao forcar uma chamada de rede em buscas por
titulo comum, ex. "matrix").
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.pln import generos_cache, lexico, negacao, periodo
from app.services.pln.normalizacao import normalizar, tokenizar


@dataclass
class FiltrosExtraidos:
    generos: list[int] = field(default_factory=list)
    sem_generos: list[int] = field(default_factory=list)
    nota_minima: float | None = None
    votos_minimos: int | None = None
    lancado_apos: str | None = None
    lancado_antes: str | None = None
    ordenar_por: str = "popularity.desc"

    def tem_filtro(self) -> bool:
        """True se algum sinal descritivo (genero/qualidade/periodo) foi detectado."""
        return bool(
            self.generos
            or self.sem_generos
            or self.nota_minima is not None
            or self.lancado_apos is not None
            or self.lancado_antes is not None
        )


def extrair_filtros(texto: str) -> FiltrosExtraidos:
    """Pipeline: normalizar -> tokenizar -> lexico -> negacao -> periodo -> resolve IDs de genero."""
    texto_normalizado = normalizar(texto)
    tokens = tokenizar(texto_normalizado)

    generos_no_texto = lexico.buscar_generos_no_texto(tokens)
    nomes_incluir, nomes_excluir = negacao.separar_generos_negados(tokens, generos_no_texto)

    nota_minima, votos_minimos = lexico.buscar_qualidade_no_texto(texto_normalizado)
    periodo_extraido = periodo.extrair_periodo(texto_normalizado)

    ids_incluir: list[int] = []
    ids_excluir: list[int] = []
    if nomes_incluir or nomes_excluir:
        mapa_nomes = generos_cache.mapa_nome_para_id()
        ids_incluir = _resolver_ids(nomes_incluir, mapa_nomes)
        ids_excluir = _resolver_ids(nomes_excluir, mapa_nomes)

    return FiltrosExtraidos(
        generos=ids_incluir,
        sem_generos=ids_excluir,
        nota_minima=nota_minima,
        votos_minimos=votos_minimos,
        lancado_apos=periodo_extraido.lancado_apos,
        lancado_antes=periodo_extraido.lancado_antes,
        ordenar_por="vote_average.desc" if nota_minima is not None else "popularity.desc",
    )


def _resolver_ids(nomes_genero: list[str], mapa_nomes: dict[str, int]) -> list[int]:
    ids: list[int] = []
    for nome in nomes_genero:
        id_genero = mapa_nomes.get(normalizar(nome))
        if id_genero is not None and id_genero not in ids:
            ids.append(id_genero)
    return ids
