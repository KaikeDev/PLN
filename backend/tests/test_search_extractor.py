"""Extração de preferências com frases escritas para o teste e mapa de gêneros fixo."""

import unittest
from typing import ClassVar

from app.domain.search.extractor import FilterExtractor
from app.domain.search.negation import is_negated
from app.domain.search.period import extract_period
from tests.fakes import FakeCatalog

COMEDY, FAMILY, HORROR, DRAMA, ROMANCE, ACTION = 35, 10751, 27, 18, 10749, 28


class FilterExtractorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = FakeCatalog()
        self.extractor = FilterExtractor(self.catalog)

    def test_mood_quality_and_relative_period(self) -> None:
        filters = self.extractor.extract("queria um filme descontraido com boa avaliacao que nao seja muito antigo")
        self.assertIn(COMEDY, filters.genres)
        self.assertIn(FAMILY, filters.genres)
        self.assertEqual(filters.excluded_genres, ())
        self.assertEqual((filters.min_rating, filters.min_votes), (7.0, 100))
        self.assertIsNotNone(filters.released_after)
        self.assertEqual(filters.sort_by, "vote_average.desc")
        self.assertTrue(filters.has_filters())

    def test_plain_title_has_no_filter_and_skips_genre_lookup(self) -> None:
        filters = self.extractor.extract("matrix")
        self.assertFalse(filters.has_filters())
        self.assertEqual(self.catalog.genre_calls, 0)

    def test_genre_negation_and_decade(self) -> None:
        filters = self.extractor.extract("nao quero terror, algo emocionante dos anos 90")
        self.assertIn(HORROR, filters.excluded_genres)
        self.assertNotIn(HORROR, filters.genres)
        self.assertIn(DRAMA, filters.genres)
        self.assertIn(ROMANCE, filters.genres)
        self.assertEqual((filters.released_after, filters.released_before), ("1990-01-01", "1999-12-31"))

    def test_accents_are_ignored_and_nem_negates_genre(self) -> None:
        filters = self.extractor.extract("Ação, nem terror")
        self.assertEqual(filters.genres, (ACTION,))
        self.assertEqual(filters.excluded_genres, (HORROR,))

    def test_explicit_years(self) -> None:
        self.assertEqual(extract_period("acao depois de 2015"), extract_period("apos 2015"))
        period = extract_period("drama depois de 2015 e antes de 2020")
        self.assertEqual((period.released_after, period.released_before), ("2015-01-01", "2019-12-31"))
        self.assertEqual(extract_period("antes de 1500").released_before, None)

    def test_relative_periods_use_current_year(self) -> None:
        self.assertEqual(extract_period("algo recente", current_year=2026).released_after, "2016-01-01")
        self.assertEqual(extract_period("um classico", current_year=2026).released_before, "2001-01-01")

    def test_negated_quality_is_not_a_preference(self) -> None:
        self.assertIsNone(self.extractor.extract("Não quero filme com boa avaliação").min_rating)
        self.assertIsNone(self.extractor.extract("filme premiado").min_rating)
        self.assertEqual(self.extractor.extract("uma obra-prima").min_rating, 8.0)

    def test_negation_window(self) -> None:
        self.assertTrue(is_negated(["nao", "quero"], 3))
        self.assertFalse(is_negated(["nao", "a", "b", "c"], 3))


class SlotAccuracyTests(unittest.TestCase):
    """Acurácia por campo em cinco frases anotadas; não é medida geral de linguagem natural."""

    CASES: ClassVar[list[tuple[str, dict]]] = [
        (
            "queria um filme descontraido com boa avaliacao que nao seja muito antigo",
            {"included": COMEDY, "min_rating": 7.0, "has_period": True},
        ),
        ("matrix", {"title_fallback": True}),
        (
            "nao quero terror, algo emocionante dos anos 90",
            {"excluded": HORROR, "included": DRAMA, "after": "1990-01-01", "before": "1999-12-31"},
        ),
        ("acao depois de 2015", {"included": ACTION, "after": "2015-01-01"}),
        ("sem romance, algo de acao", {"excluded": ROMANCE, "included": ACTION}),
    ]

    def test_aggregate_accuracy(self) -> None:
        extractor = FilterExtractor(FakeCatalog())
        checks = []
        for text, expected in self.CASES:
            filters = extractor.extract(text)
            if expected.get("title_fallback"):
                checks.append(not filters.has_filters())
                continue
            actual = {
                "included": expected.get("included") in filters.genres,
                "excluded": expected.get("excluded") in filters.excluded_genres,
                "min_rating": filters.min_rating == expected.get("min_rating"),
                "has_period": filters.released_after is not None,
                "after": filters.released_after == expected.get("after"),
                "before": filters.released_before == expected.get("before"),
            }
            checks.extend(actual[key] for key in expected)
        accuracy = sum(checks) / len(checks)
        print(f"\nAcuracia por slot: {accuracy:.0%} ({sum(checks)}/{len(checks)})")
        self.assertGreaterEqual(accuracy, 0.9)


if __name__ == "__main__":
    unittest.main()
