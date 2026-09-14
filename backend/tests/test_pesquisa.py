import unittest
from unittest.mock import patch

from app.services.pln import generos_cache
from app.services.pln.extrator import extrair_filtros
from app.services.pln.pesquisa import pesquisar
from app.services.tmdb.filmes import descobrir_filmes


class PesquisaTests(unittest.TestCase):
    def setUp(self):
        generos_cache.definir_cache_para_teste({10752: "Guerra", 18: "Drama", 35: "Comédia", 27: "Terror"})
        self.addCleanup(generos_cache.invalidar_cache)

    def test_exact_title_precedes_genre_and_original_text_is_forwarded(self):
        movie = {"id": 11, "title": "Guerra nas Estrelas"}
        with patch("app.services.pln.pesquisa.tmdb_filmes.buscar_filmes", return_value=[movie]) as search, patch("app.services.pln.pesquisa.tmdb_filmes.descobrir_filmes") as discover:
            result = pesquisar("Guerra nas Estrelas")
            self.assertEqual(result.modo, "titulo")
            self.assertEqual(result.resultados, [movie])
            search.assert_called_once_with("Guerra nas Estrelas", pagina=1, ano=None)
            discover.assert_not_called()

    def test_discovery_routes_to_tmdb_with_both_bounds_and_exclusions(self):
        with patch("app.services.pln.pesquisa.tmdb_filmes.descobrir_filmes", return_value=[]) as discover:
            result = pesquisar("drama depois de 2015 e antes de 2020 sem terror", modo="descoberta")
            self.assertEqual(result.modo, "descoberta")
            kwargs = discover.call_args.kwargs
            self.assertEqual(kwargs["generos"], "18")
            self.assertEqual(kwargs["sem_generos"], "27")
            self.assertEqual(kwargs["lancado_apos"], "2015-01-01")
            self.assertEqual(kwargs["lancado_antes"], "2019-12-31")

    def test_negative_quality_is_not_treated_as_positive_or_award(self):
        self.assertIsNone(extrair_filtros("Não quero filme com boa avaliação").nota_minima)
        self.assertIsNone(extrair_filtros("filme premiado").nota_minima)

    def test_discover_parameter_mapping(self):
        with patch("app.services.tmdb.filmes.get", return_value={"results": [{"id": 1}]}) as fetch:
            self.assertEqual(descobrir_filmes(sem_generos="27,10749", nota_minima=7), [{"id": 1}])
            self.assertEqual(fetch.call_args.args, ("/discover/movie",))
            self.assertEqual(fetch.call_args.kwargs["without_genres"], "27,10749")
            self.assertEqual(fetch.call_args.kwargs["vote_average.gte"], 7)

    def test_explicit_year_does_not_silently_ignore_other_bounds(self):
        with patch("app.services.pln.pesquisa.tmdb_filmes.descobrir_filmes") as discover:
            result = pesquisar("drama antes de 2000", ano=2020, modo="descoberta")
            self.assertEqual(result.resultados, [])
            discover.assert_not_called()
