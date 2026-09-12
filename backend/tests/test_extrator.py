import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from app.services.pln import generos_cache  # noqa: E402
from app.services.pln.extrator import extrair_filtros  # noqa: E402

# Mapa fixo id->nome, igual ao que /genre/movie/list devolveria em pt-BR -
# evita bater na API real do TMDB durante os testes.
GENEROS_TESTE = {
    28: "Ação",
    12: "Aventura",
    16: "Animação",
    35: "Comédia",
    80: "Crime",
    99: "Documentário",
    18: "Drama",
    10751: "Família",
    14: "Fantasia",
    36: "História",
    27: "Terror",
    10402: "Música",
    9648: "Mistério",
    10749: "Romance",
    878: "Ficção científica",
    53: "Thriller",
    10752: "Guerra",
}

ID_COMEDIA = 35
ID_FAMILIA = 10751
ID_TERROR = 27
ID_DRAMA = 18
ID_ROMANCE = 10749


class TestExtrairFiltros(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        generos_cache.definir_cache_para_teste(GENEROS_TESTE)

    @classmethod
    def tearDownClass(cls) -> None:
        generos_cache.invalidar_cache()

    def test_humor_qualidade_e_periodo_relativo(self) -> None:
        """Frase de exemplo do usuario: humor + qualidade + 'nao muito antigo'."""
        filtros = extrair_filtros(
            "queria um filme descontraido com boa avaliacao que nao seja muito antigo"
        )

        self.assertIn(ID_COMEDIA, filtros.generos)
        self.assertIn(ID_FAMILIA, filtros.generos)
        self.assertEqual(filtros.sem_generos, [])
        self.assertEqual(filtros.nota_minima, 7.0)
        self.assertEqual(filtros.votos_minimos, 100)
        self.assertIsNotNone(filtros.lancado_apos)
        self.assertEqual(filtros.ordenar_por, "vote_average.desc")
        self.assertTrue(filtros.tem_filtro())

    def test_titulo_puro_nao_gera_filtro(self) -> None:
        """Titulo comum deve continuar caindo no fallback de busca por titulo."""
        filtros = extrair_filtros("matrix")

        self.assertFalse(filtros.tem_filtro())
        self.assertEqual(filtros.generos, [])
        self.assertIsNone(filtros.nota_minima)
        self.assertIsNone(filtros.lancado_apos)

    def test_negacao_de_genero_e_decada_explicita(self) -> None:
        """'Nao quero terror' deve excluir Terror; 'dos anos 90' deve virar 1990-1999."""
        filtros = extrair_filtros("nao quero terror, algo emocionante dos anos 90")

        self.assertIn(ID_TERROR, filtros.sem_generos)
        self.assertNotIn(ID_TERROR, filtros.generos)
        self.assertIn(ID_DRAMA, filtros.generos)
        self.assertIn(ID_ROMANCE, filtros.generos)
        self.assertEqual(filtros.lancado_apos, "1990-01-01")
        self.assertEqual(filtros.lancado_antes, "1999-12-31")

    def test_ano_explicito_depois_de(self) -> None:
        filtros = extrair_filtros("acao depois de 2015")

        self.assertEqual(filtros.lancado_apos, "2015-01-01")
        self.assertIsNone(filtros.lancado_antes)


class TestAcuraciaPorSlot(unittest.TestCase):
    """Mede acuracia agregada por 'slot' nos casos anotados - numero pra citar no relatorio."""

    CASOS = [
        (
            "queria um filme descontraido com boa avaliacao que nao seja muito antigo",
            {"genero_incluido": ID_COMEDIA, "nota_minima": 7.0, "tem_periodo": True},
        ),
        ("matrix", {"fallback_titulo": True}),
        (
            "nao quero terror, algo emocionante dos anos 90",
            {
                "genero_excluido": ID_TERROR,
                "genero_incluido": ID_DRAMA,
                "lancado_apos": "1990-01-01",
                "lancado_antes": "1999-12-31",
            },
        ),
        ("acao depois de 2015", {"genero_incluido": 28, "lancado_apos": "2015-01-01"}),
        ("sem romance, algo de acao", {"genero_excluido": ID_ROMANCE, "genero_incluido": 28}),
    ]

    @classmethod
    def setUpClass(cls) -> None:
        generos_cache.definir_cache_para_teste(GENEROS_TESTE)

    @classmethod
    def tearDownClass(cls) -> None:
        generos_cache.invalidar_cache()

    def test_acuracia_agregada(self) -> None:
        acertos = 0
        total = 0

        for texto, esperado in self.CASOS:
            filtros = extrair_filtros(texto)

            if "fallback_titulo" in esperado:
                total += 1
                acertos += int(not filtros.tem_filtro())
                continue

            if "genero_incluido" in esperado:
                total += 1
                acertos += int(esperado["genero_incluido"] in filtros.generos)
            if "genero_excluido" in esperado:
                total += 1
                acertos += int(esperado["genero_excluido"] in filtros.sem_generos)
            if "nota_minima" in esperado:
                total += 1
                acertos += int(filtros.nota_minima == esperado["nota_minima"])
            if "tem_periodo" in esperado:
                total += 1
                acertos += int(filtros.lancado_apos is not None)
            if "lancado_apos" in esperado:
                total += 1
                acertos += int(filtros.lancado_apos == esperado["lancado_apos"])
            if "lancado_antes" in esperado:
                total += 1
                acertos += int(filtros.lancado_antes == esperado["lancado_antes"])

        acuracia = acertos / total
        print(f"\nAcuracia por slot: {acuracia:.0%} ({acertos}/{total})")
        self.assertGreaterEqual(acuracia, 0.9)


if __name__ == "__main__":
    unittest.main()
