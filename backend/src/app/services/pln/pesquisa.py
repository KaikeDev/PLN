from dataclasses import dataclass
from typing import Any, Literal

from app.services.pln.normalizacao import normalizar

from app.services.pln.extrator import FiltrosExtraidos, extrair_filtros
from app.services.pln.generos_cache import mapa_id_para_nome
from app.services.tmdb import filmes as tmdb_filmes


@dataclass
class ResultadoPesquisa:
    modo: str  # "titulo" ou "descoberta"
    resultados: list[dict[str, Any]]
    interpretacao: dict[str, Any]


def pesquisar(
    texto: str, pagina: int = 1, ano: int | None = None,
    modo: Literal["auto", "titulo", "descoberta"] = "auto",
) -> ResultadoPesquisa:
    """Prioriza título exato no modo automático; permite escolha explícita."""
    if modo not in {"auto", "titulo", "descoberta"}:
        raise ValueError("Modo de pesquisa inválido")
    candidates = None
    if modo != "descoberta":
        candidates = tmdb_filmes.buscar_filmes(texto, pagina=pagina, ano=ano)
        # A proteção do título consulta a primeira página mesmo ao paginar resultados.
        first_page = candidates if pagina == 1 else tmdb_filmes.buscar_filmes(texto, pagina=1, ano=ano)
        exact = any(normalizar(texto) in {
            normalizar(movie.get("title") or ""), normalizar(movie.get("original_title") or "")
        } for movie in first_page)
        if modo == "titulo" or exact:
            return ResultadoPesquisa("titulo", candidates, {})
    filtros = extrair_filtros(texto)
    if not filtros.tem_filtro():
        if modo == "descoberta":
            return ResultadoPesquisa("descoberta", [], {"aviso": "Nenhuma preferência reconhecida"})
        return ResultadoPesquisa("titulo", candidates or [], _interpretacao(filtros))
    if ano is not None:
        filtros.lancado_apos = max(filtros.lancado_apos or f"{ano}-01-01", f"{ano}-01-01")
        filtros.lancado_antes = min(filtros.lancado_antes or f"{ano}-12-31", f"{ano}-12-31")
    if filtros.lancado_apos and filtros.lancado_antes and filtros.lancado_apos > filtros.lancado_antes:
        return ResultadoPesquisa("descoberta", [], {"aviso": "Período sem interseção"})
    results = tmdb_filmes.descobrir_filmes(**_parametros_discover(filtros), pagina=pagina)
    return ResultadoPesquisa("descoberta", results, _interpretacao(filtros))


def _parametros_discover(f: FiltrosExtraidos) -> dict[str, Any]:
    # "|" = OR no TMDB (qualquer um dos generos serve); "," seria AND (precisa ter todos).
    return dict(
        generos="|".join(str(g) for g in f.generos) or None,
        sem_generos=",".join(str(g) for g in f.sem_generos) or None,
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

