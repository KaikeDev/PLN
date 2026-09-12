from dataclasses import dataclass
from typing import Any

from app.services.pln.extrator import FiltrosExtraidos, extrair_filtros
from app.services.pln.generos_cache import mapa_id_para_nome
from app.services.tmdb import filmes as tmdb_filmes


@dataclass
class ResultadoPesquisa:
    modo: str  # "titulo" ou "descoberta"
    resultados: list[dict[str, Any]]
    interpretacao: dict[str, Any]


def pesquisar(texto: str, pagina: int = 1, ano: int | None = None) -> ResultadoPesquisa:
    """Extrai filtros do texto; sem nenhum sinal descritivo, cai para busca por titulo."""
    filtros = extrair_filtros(texto)

    if not filtros.tem_filtro():
        resultados = tmdb_filmes.buscar_filmes(texto, pagina=pagina, ano=ano)
        return ResultadoPesquisa(modo="titulo", resultados=resultados, interpretacao=_interpretacao(filtros))

    resultados = tmdb_filmes.descobrir_filmes(**_parametros_discover(filtros), pagina=pagina)
    return ResultadoPesquisa(modo="descoberta", resultados=resultados, interpretacao=_interpretacao(filtros))


def _parametros_discover(f: FiltrosExtraidos) -> dict[str, Any]:
    # "|" = OR no TMDB (qualquer um dos generos serve); "," seria AND (precisa ter todos).
    return dict(
        generos="|".join(str(g) for g in f.generos) or None,
        sem_generos="|".join(str(g) for g in f.sem_generos) or None,
        nota_minima=f.nota_minima,
        votos_minimos=f.votos_minimos,
        lancado_apos=f.lancado_apos,
        lancado_antes=f.lancado_antes,
        ordenar_por=f.ordenar_por,
    )


def _interpretacao(f: FiltrosExtraidos) -> dict[str, Any]:
    """Filtros detectados, para depuracao/relatorio - a UI nao precisa exibir isso."""
    nomes = mapa_id_para_nome() if (f.generos or f.sem_generos) else {}
    return {
        "generos_incluidos": [nomes.get(g, str(g)) for g in f.generos],
        "generos_excluidos": [nomes.get(g, str(g)) for g in f.sem_generos],
        "nota_minima": f.nota_minima,
        "votos_minimos": f.votos_minimos,
        "lancado_apos": f.lancado_apos,
        "lancado_antes": f.lancado_antes,
    }
