"""Casos controlados: não representam filmes ou medições do corpus real."""

import json
import tempfile
import unittest
from pathlib import Path

from app.corpus.collect import collect
from app.corpus.config import parse_collection_config
from app.corpus.process import process
from app.corpus.transform import representations
from app.corpus.verification import verify_processed as verify
from app.corpus.verification import verify_raw
from app.shared.artifacts import read_jsonl, write_json, write_jsonl


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / "config.json"
        write_json(
            self.config,
            {
                "language": "pt-BR",
                "pages_per_slice": 3,
                "genres": [18],
                "periods": [[2000, 2010]],
                "vote_count_gte": 50,
                "sort_by": "popularity.desc",
                "include_adult": False,
                "request_interval_seconds": 0,
                "seed_movie_ids": [],
            },
        )
        self.stop = self.root / "stopwords.txt"
        self.stop.write_text("# exemplo\no\nde\nnão\nsem\n", encoding="utf-8")

    @staticmethod
    def fetch(endpoint, **params):
        if endpoint == "/genre/movie/list":
            return {"genres": [{"id": 18, "name": "Drama"}]}
        movie = {"id": 1, "title": "Caso de teste", "overview": "O Neo não teme a simulação.", "genre_ids": [18]}
        return {"page": params["page"], "total_pages": 2, "results": [movie, {"id": 2, "title": "Ausente", "overview": None}]}

    def test_preserves_accents_negation_numbers_and_original(self):
        text = "<p>O Neo não vive <b>sem</b> ação em 1999.</p> https://example.test <script>ruído</script>"
        result = representations(text, {"o", "não", "sem"})
        self.assertEqual(result["clean"], "O Neo não vive sem ação em 1999.")
        self.assertIn("não", result["filtered"])
        self.assertIn("sem", result["filtered"])
        self.assertIn("1999", result["filtered"])
        self.assertIn("ação", result["filtered"])
        self.assertIn(".", result["tokens"])
        self.assertNotIn(".", result["words"])
        self.assertNotIn("o", result["filtered"])
        self.assertTrue(text.startswith("<p>"))

    def test_missing_empty_and_entity_spacing(self):
        self.assertIsNone(representations(None, set())["clean"])
        self.assertEqual(representations(" \n ", set())["tokens"], [])
        self.assertEqual(representations("A&nbsp;B", set())["clean"], "A B")
        with self.assertRaises(ValueError):
            representations(123, set())

    def test_collection_pagination_dedup_and_no_overwrite(self):
        raw = self.root / "raw"
        manifest = collect(self.config, raw, self.fetch)
        self.assertEqual(manifest["records_received"], 4)
        self.assertEqual(manifest["unique_movies"], 2)
        self.assertEqual(manifest["duplicates_removed"], 2)
        self.assertEqual(len(manifest["requests"]), 3)
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(verify_raw(raw)["status"], "complete")
        with self.assertRaises(FileExistsError):
            collect(self.config, raw, self.fetch)

    def test_error_is_partial_and_does_not_record_credentials(self):
        def failing(endpoint, **params):
            if endpoint == "/genre/movie/list":
                return {"genres": []}
            raise RuntimeError("secret-key-must-not-be-logged")

        raw = self.root / "raw"
        result = collect(self.config, raw, failing)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["unique_movies"], 0)
        self.assertNotIn("secret-key", (raw / "manifest.json").read_text())
        with self.assertRaises(ValueError):
            process(raw, self.root / "processed", self.stop)

    def test_collection_config_rejects_unsafe_or_invalid_values(self):
        base = json.loads(self.config.read_text(encoding="utf-8"))
        invalid = [
            {**base, "seed_movie_ids": ["603/../../account"]},
            {**base, "pages_per_slice": True},
            {**base, "periods": [[2010, 2000]]},
            {**base, "language": "pt-BR&api_key=x"},
            {**base, "sort_by": "popularity"},
            {**base, "request_interval_seconds": -1},
            {**base, "campo_desconhecido": 1},
            {key: value for key, value in base.items() if key != "genres"},
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_collection_config(value)
        self.assertEqual(parse_collection_config(base).genres, (18,))

    def test_all_six_stages_keep_same_ids_and_missing_rows(self):
        raw, output = self.root / "raw", self.root / "processed"
        collect(self.config, raw, self.fetch)
        process(raw, output, self.stop)
        self.assertEqual(verify(output)["movies"], 2)
        self.assertEqual(verify(output)["stages"], 6)
        self.assertEqual(read_jsonl(output / "01_original.jsonl")[1], {"id": 2, "text": None})
        self.assertEqual(read_jsonl(output / "06_without_stopwords.jsonl")[1], {"id": 2, "tokens": []})
        stats = json.loads((output / "statistics.json").read_text())
        self.assertEqual(stats["missing_overviews_percent"], 50)
        self.assertEqual(stats["valid_overviews"], 1)
        self.assertEqual(stats["filtered"]["tokens"], 5)
        with self.assertRaises(FileExistsError):
            process(raw, output, self.stop)
        write_jsonl(output / "04_tokens.jsonl", [{"id": 999, "tokens": []}])
        with self.assertRaisesRegex(ValueError, "Hash divergente"):
            verify(output)

    def test_reprocessing_is_deterministic_and_raw_tampering_is_rejected(self):
        raw = self.root / "raw"
        collect(self.config, raw, self.fetch)
        first, second = self.root / "first", self.root / "second"
        process(raw, first, self.stop)
        process(raw, second, self.stop)
        for path in first.iterdir():
            if path.name != "manifest.json":
                self.assertEqual(path.read_bytes(), (second / path.name).read_bytes(), path.name)
        (raw / "movies.jsonl").write_text("{}\n")
        with self.assertRaisesRegex(ValueError, "hash"):
            process(raw, self.root / "third", self.stop)


if __name__ == "__main__":
    unittest.main()
