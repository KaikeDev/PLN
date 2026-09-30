"""Estratégias de pesquisa sobre um catálogo e um índice de sinopses falsos."""

import unittest

from app.domain.search.extractor import ExtractedFilters
from app.domain.search.ports import DiscoverQuery
from app.domain.search.service import PAGE_SIZE, FilterInterpretation, Notice, SearchMode, SearchService
from tests.fakes import FakeCatalog, FakeSynopsisIndex

MOVIES = {
    1: {
        "id": 1,
        "title": "Máquinas do Futuro",
        "genre_ids": [28, 878],
        "release_date": "1984-10-26",
        "vote_average": 7.7,
        "vote_count": 900,
    },
    2: {"id": 2, "title": "Robô Solitário", "genre_ids": [18, 878], "release_date": "2010-05-01", "vote_average": 6.1, "vote_count": 80},
    3: {"id": 3, "title": "Riso Fácil", "genre_ids": [35], "release_date": "2000-01-01", "vote_average": None, "vote_count": None},
}
RANKED = [(2, 0.9), (1, 0.8), (3, 0.1)]


def synopsis_service(catalog: FakeCatalog | None = None) -> tuple[SearchService, FakeSynopsisIndex]:
    index = FakeSynopsisIndex(RANKED, MOVIES)
    return SearchService(catalog or FakeCatalog(), index), index


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

    def test_synopsis_ranks_by_theme_and_filters_by_recognized_genre(self) -> None:
        service, index = synopsis_service()
        result = service.search("quero um filme de ação sobre máquinas", mode=SearchMode.SYNOPSIS)
        self.assertEqual(result.mode, SearchMode.SYNOPSIS)
        self.assertEqual([movie["id"] for movie in result.results], [1])
        self.assertEqual(result.results[0]["pontuacao"], 0.8)
        self.assertEqual(index.texts, ["quero um filme de ação sobre máquinas"])
        assert isinstance(result.interpretation, FilterInterpretation)
        self.assertEqual(result.interpretation.included_genres, ["Ação"])

    def test_synopsis_applies_exclusions_and_period(self) -> None:
        service, _ = synopsis_service()
        without_comedy = service.search("robôs sem comédia", mode=SearchMode.SYNOPSIS)
        self.assertEqual([movie["id"] for movie in without_comedy.results], [2, 1])
        eighties = service.search("robôs dos anos 80", mode=SearchMode.SYNOPSIS)
        self.assertEqual([movie["id"] for movie in eighties.results], [1])
        by_year = service.search("robôs", year=2010, mode=SearchMode.SYNOPSIS)
        self.assertEqual([movie["id"] for movie in by_year.results], [2])

    def test_synopsis_paginates_the_filtered_ranking(self) -> None:
        movies = {i: {"id": i, "genre_ids": []} for i in range(1, PAGE_SIZE + 6)}
        service = SearchService(FakeCatalog(), FakeSynopsisIndex([(i, 1 - i / 100) for i in movies], movies))
        self.assertEqual(len(service.search("tema", mode=SearchMode.SYNOPSIS).results), PAGE_SIZE)
        self.assertEqual(
            [m["id"] for m in service.search("tema", page=2, mode=SearchMode.SYNOPSIS).results], list(range(PAGE_SIZE + 1, PAGE_SIZE + 6))
        )
        self.assertEqual(service.search("tema", page=3, mode=SearchMode.SYNOPSIS).results, [])

    def test_synopsis_without_index_returns_notice(self) -> None:
        result = SearchService(FakeCatalog()).search("máquinas", mode=SearchMode.SYNOPSIS)
        self.assertEqual(result.interpretation, Notice("Busca por sinopse indisponível"))

    def test_auto_prefers_exact_title_then_synopsis_then_discovery(self) -> None:
        titled, index = synopsis_service(FakeCatalog(titles=[{"id": 9, "title": "Máquinas"}]))
        self.assertEqual(titled.search("máquinas").mode, SearchMode.TITLE)
        self.assertEqual(index.texts, [])
        by_theme, _ = synopsis_service()
        self.assertEqual(by_theme.search("filme sobre robôs").mode, SearchMode.SYNOPSIS)
        catalog = FakeCatalog(discovered=[{"id": 50}])
        fallback, _ = synopsis_service(catalog)
        result = fallback.search("terror sobre robôs")
        self.assertEqual((result.mode, result.results), (SearchMode.DISCOVERY, [{"id": 50}]))

    def test_filters_accept_only_matching_movies(self) -> None:
        self.assertTrue(ExtractedFilters(min_rating=7.0, min_votes=500).accepts(MOVIES[1]))
        self.assertFalse(ExtractedFilters(min_rating=7.0).accepts(MOVIES[2]))
        self.assertFalse(ExtractedFilters(min_rating=5.0).accepts(MOVIES[3]))
        self.assertFalse(ExtractedFilters(released_after="1990-01-01").accepts({"id": 4, "genre_ids": []}))
        self.assertTrue(ExtractedFilters(genres=(35, 878)).accepts(MOVIES[2]))


if __name__ == "__main__":
    unittest.main()
