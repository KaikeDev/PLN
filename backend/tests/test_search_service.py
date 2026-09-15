"""Estratégias de pesquisa sobre um catálogo falso."""

import unittest

from app.domain.search.ports import DiscoverQuery
from app.domain.search.service import FilterInterpretation, Notice, SearchMode, SearchService
from tests.fakes import FakeCatalog


class SearchServiceTests(unittest.TestCase):
    def test_exact_title_wins_over_genre_trigger_with_single_request(self) -> None:
        movie = {"id": 11, "title": "Guerra nas Estrelas"}
        catalog = FakeCatalog(titles=[movie])
        result = SearchService(catalog).search("Guerra nas Estrelas")
        self.assertEqual(result.mode, SearchMode.TITLE)
        self.assertEqual(result.results, [movie])
        self.assertEqual(catalog.search_calls, [("Guerra nas Estrelas", 1, None)])
        self.assertEqual(catalog.discover_calls, [])

    def test_exact_title_check_uses_first_page_when_paginating(self) -> None:
        catalog = FakeCatalog(titles=[{"id": 603, "title": "Matrix"}])
        SearchService(catalog).search("matrix", page=2)
        self.assertEqual(catalog.search_calls, [("matrix", 2, None), ("matrix", 1, None)])

    def test_discovery_forwards_bounds_and_exclusions(self) -> None:
        catalog = FakeCatalog(discovered=[{"id": 1}])
        result = SearchService(catalog).search("drama depois de 2015 e antes de 2020 sem terror", mode=SearchMode.DISCOVERY)
        self.assertEqual(result.mode, SearchMode.DISCOVERY)
        query, page = catalog.discover_calls[0]
        self.assertEqual(query, DiscoverQuery((18,), (27,), None, None, "2015-01-01", "2019-12-31", "popularity.desc"))
        self.assertEqual(page, 1)
        self.assertIsInstance(result.interpretation, FilterInterpretation)
        self.assertEqual(result.interpretation.excluded_genres, ["Terror"])

    def test_auto_without_title_or_preferences_falls_back_to_title(self) -> None:
        catalog = FakeCatalog(titles=[{"id": 2, "title": "Outro"}])
        result = SearchService(catalog).search("xyz")
        self.assertEqual(result.mode, SearchMode.TITLE)
        self.assertEqual(result.results, [{"id": 2, "title": "Outro"}])

    def test_discovery_without_preferences_returns_notice(self) -> None:
        result = SearchService(FakeCatalog()).search("xyz", mode=SearchMode.DISCOVERY)
        self.assertEqual(result.interpretation, Notice("Nenhuma preferência reconhecida"))

    def test_year_is_intersected_and_empty_period_skips_request(self) -> None:
        catalog = FakeCatalog()
        result = SearchService(catalog).search("drama antes de 2000", year=2020, mode=SearchMode.DISCOVERY)
        self.assertEqual(result.interpretation, Notice("Período sem interseção"))
        self.assertEqual(catalog.discover_calls, [])


if __name__ == "__main__":
    unittest.main()
