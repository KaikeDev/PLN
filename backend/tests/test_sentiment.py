"""Casos controlados: filmes e críticas escritos para o teste, com um TMDB falso; não são críticas reais."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from app.corpus.collect import collect as collect_movies
from app.corpus.process import process as process_movies
from app.representations.methods import METHODS
from app.sentiment.collect import author_key, collect, review_row
from app.sentiment.config import NEGATIVE, POSITIVE, load_config
from app.sentiment.encoders import ChunkedEncoder
from app.sentiment.pipeline import build, verify, verify_any
from app.sentiment.process import exclusion, portuguese_part, process
from app.shared.artifacts import read_json_object, read_jsonl, write_json

POSITIVE_TEXTS = [
    "Excelente filme, adorei a atuação e a história emocionante.",
    "Ótimo roteiro, gostei muito, uma obra excelente e bonita.",
    "Filme maravilhoso, recomendo, atuação brilhante e trilha excelente.",
]
NEGATIVE_TEXTS = [
    "Péssimo filme, roteiro fraco e atuação ruim, não gostei.",
    "Muito chato e entediante, não recomendo, uma perda de tempo.",
    "Horrível, história ruim e sem graça, não vale a pena.",
]
MIDDLE_TEXT = "Um filme mediano, tem bons momentos e alguns problemas na história."
MOVIES = [(index, f"Filme {index}", f"Sinopse do filme número {index} com uma família e uma viagem.") for index in range(1, 21)]
REVIEW_CONFIG = {"language": "pt-BR", "max_pages_per_movie": 2, "request_interval_seconds": 0, "workers": 2}


def tmdb(endpoint, **params):
    """TMDB falso: lista de gêneros, uma página de descoberta e duas críticas por filme, a segunda em outra página."""
    if endpoint == "/genre/movie/list":
        return {"genres": [{"id": 18, "name": "Drama"}]}
    if endpoint == "/discover/movie":
        return {"page": 1, "total_pages": 1, "results": [{"id": i, "title": t, "overview": o, "genre_ids": [18]} for i, t, o in MOVIES]}
    movie_id = int(endpoint.split("/")[2])
    page = params["page"]
    good = movie_id % 2 == 0
    texts = POSITIVE_TEXTS if good else NEGATIVE_TEXTS
    text = texts[(movie_id + page) % len(texts)] if movie_id % 5 else MIDDLE_TEXT
    rating = (9 if good else 2) if movie_id % 5 else 6
    review = {
        "id": f"r{movie_id:03d}{page}",
        "author": f"autor {movie_id % 3}",
        "author_details": {"username": f"usuario{movie_id % 3}", "name": "Nome Real", "avatar_path": "/a.jpg", "rating": rating},
        "content": text,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    return {"page": page, "total_pages": 2, "results": [review]}


class ReviewTextTests(unittest.TestCase):
    def test_bilingual_review_keeps_only_portuguese_sections(self) -> None:
        content = "**Português**\r\n\r\nGostei muito.\r\n\r\n**English**\r\n\r\nI liked it.\r\n\r\n**Portuguese**\r\n\r\nRecomendo."
        self.assertEqual(portuguese_part(content), "Gostei muito.\n\n\nRecomendo.")
        self.assertEqual(portuguese_part("Sem cabeçalho de idioma."), "Sem cabeçalho de idioma.")

    def test_exclusion_reasons(self) -> None:
        base = {"rating": 8.0, "content": "Um filme muito bom, que eu recomendo para a família toda assistir."}
        self.assertIsNone(exclusion(base))
        self.assertEqual(exclusion(base | {"rating": None}), "sem_nota")
        self.assertEqual(exclusion(base | {"content": "Bom."}), "curta_demais")
        self.assertEqual(exclusion(base | {"content": "This is a great movie and the cast was good with it."}), "outro_idioma")
        self.assertEqual(exclusion(base | {"content": "**English**\n\nThis is a great movie and the cast was good."}), "curta_demais")

    def test_jsonl_keeps_unicode_line_separators_inside_text(self) -> None:
        from app.shared.artifacts import write_jsonl

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "linhas.jsonl"
            rows = [{"content": "primeira segunda\x85terceira"}, {"content": "outra"}]
            write_jsonl(path, rows)
            self.assertEqual(read_jsonl(path), rows)

    def test_review_row_keeps_no_personal_data(self) -> None:
        review = tmdb("/movie/2/reviews", page=1)["results"][0]
        row = review_row({"id": 2, "title": "Filme 2"}, review)
        self.assertEqual(row["author_key"], author_key("usuario2"))
        self.assertEqual(len(row["author_key"]), 16)
        self.assertNotIn("usuario2", json.dumps(row))
        self.assertNotIn("Nome Real", json.dumps(row))
        self.assertEqual(row["rating"], 9.0)


class FakeTokenizer:
    """Um token por palavra, com as posições de caractere, como os tokenizadores rápidos."""

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False, verbose=False):
        import re

        return {"offset_mapping": [match.span() for match in re.finditer(r"\S+", text)]}


class ChunkedEncoderTests(unittest.TestCase):
    def test_long_text_is_split_and_averaged(self) -> None:
        inner = SimpleNamespace(
            model=SimpleNamespace(tokenizer=FakeTokenizer()),
            max_tokens=5,
            parameters=10,
            encode=lambda texts: np.array([[1.0, 0.0] if "bom" in text else [0.0, 1.0] for text in texts]),
            count_tokens=lambda text: len(text.split()),
            word_vectors=lambda text, word: [],
        )
        encoder = ChunkedEncoder(inner)  # type: ignore[arg-type]
        self.assertEqual(encoder.chunks("um dois três"), ["um dois três"])
        self.assertEqual(encoder.chunks("a b c d e f g"), ["a b c", "d e f", "g"])
        vectors = encoder.encode(["bom bom bom ruim ruim ruim", "curto"])
        self.assertEqual(encoder.chunks_per_text, [2, 1])
        np.testing.assert_allclose(vectors[0], [np.sqrt(0.5), np.sqrt(0.5)])
        np.testing.assert_allclose(vectors[1], [0.0, 1.0])


class SentimentPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        write_json(
            root / "coleta.json",
            {
                "language": "pt-BR",
                "pages_per_slice": 1,
                "genres": [18],
                "periods": [[2000, 2010]],
                "vote_count_gte": 50,
                "sort_by": "popularity.desc",
                "include_adult": False,
                "request_interval_seconds": 0,
                "seed_movie_ids": [],
            },
        )
        stopwords = root / "stopwords.txt"
        stopwords.write_text("a\no\nde\ne\num\numa\ncom\n", encoding="utf-8")
        collect_movies(root / "coleta.json", root / "raw", tmdb)
        process_movies(root / "raw", root / "movies", stopwords)
        write_json(root / "criticas.json", REVIEW_CONFIG)
        cls.collected = collect(root / "movies", root / "criticas.json", root / "reviews", tmdb, sleep=lambda _: None)
        cls.processed = process(root / "reviews", root / "processed", stopwords)
        config = {
            "representations": [
                {"name": "bow_sem_stopwords", "method": "bow", "stage": "06_without_stopwords.jsonl"},
                {"name": "tfidf_sem_stopwords", "method": "tfidf", "stage": "06_without_stopwords.jsonl"},
            ],
            "negative_max": 4,
            "positive_min": 7,
            "folds": 2,
            "inner_folds": 2,
            "random_state": 42,
            "regularization_grid": [0.1, 1, 10],
            "ridge_alphas": [0.1, 1, 10],
            "min_df": 1,
            "top_features": 3,
            "error_examples": 2,
        }
        write_json(root / "sentimento.json", config)
        cls.config_path = root / "sentimento.json"
        cls.output = root / "experimento"
        cls.result = build(root / "processed", cls.output, cls.config_path, methods=METHODS)
        cls.root = root

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_collection_follows_pages_and_records_counts(self) -> None:
        self.assertEqual(self.collected["status"], "complete")
        self.assertEqual((self.collected["movies"], self.collected["reviews"], self.collected["requests"]), (20, 40, 40))
        rows = read_jsonl(self.root / "reviews" / "reviews.jsonl")
        self.assertEqual([row["review_id"] for row in rows[:2]], ["r0011", "r0012"])
        self.assertEqual(verify_any(self.root / "reviews")["status"], "ok")

    def test_processed_reviews_load_as_corpus(self) -> None:
        self.assertEqual(self.processed["kept"], 40)
        metadata = read_jsonl(self.root / "processed" / "metadata.jsonl")
        self.assertEqual([row["id"] for row in metadata], list(range(1, 41)))
        self.assertEqual(metadata[0]["review_id"], "r0011")
        self.assertEqual(verify_any(self.root / "processed")["status"], "ok")

    def test_polarity_thresholds(self) -> None:
        config = load_config(self.config_path, METHODS)
        self.assertEqual([config.polarity(r) for r in (2, 4, 5, 6.5, 7, 10)], [NEGATIVE, NEGATIVE, None, None, POSITIVE, POSITIVE])

    def test_build_learns_polarity_and_rating(self) -> None:
        results = read_json_object(self.output / "results.json")
        dataset = read_json_object(self.output / "dataset.json")
        self.assertEqual(dataset["polarity"], {"negativo": 16, "positivo": 16})
        self.assertEqual(dataset["middle_excluded_from_polarity"], 8)
        tfidf = results["polaridade"]["tfidf_sem_stopwords"]
        self.assertGreater(tfidf["f1_macro"], results["polaridade"]["maioria"]["f1_macro"])
        self.assertIn("entre_autores", tfidf)
        rating = results["nota"]
        self.assertLess(rating["tfidf_sem_stopwords"]["erro_absoluto_medio"], rating["media_do_treino"]["erro_absoluto_medio"])
        self.assertEqual(verify(self.output)["status"], "ok")

    def test_reviews_of_one_movie_share_a_fold(self) -> None:
        documents = json.loads((self.output / "documents.json").read_text(encoding="utf-8"))
        folds: dict[int, set] = {}
        for document in documents:
            folds.setdefault(document["movie_id"], set()).add(document["fold_nota"])
        self.assertTrue(all(len(found) == 1 for found in folds.values()))

    def test_live_analyzer_reads_long_text_and_explains(self) -> None:
        from app.sentiment.live import SentimentAnalyzer

        analyzer = SentimentAnalyzer.load(self.root / "processed", self.config_path, "tfidf_sem_stopwords")
        good = analyzer.analyze("Excelente filme, adorei a atuação brilhante. " * 20)
        bad = analyzer.analyze("Péssimo e chato, roteiro ruim, não recomendo.")
        self.assertEqual((good.polarity, bad.polarity), ("positivo", "negativo"))
        self.assertGreater(good.rating, bad.rating)
        self.assertIn("excelente", [term for term, _ in good.positive_terms])
        self.assertIn("ruim", [term for term, _ in bad.negative_terms])
        self.assertEqual(analyzer.training_size, 32)
        with self.assertRaises(ValueError):
            analyzer.analyze("xyzw qwerty")

    def test_verify_detects_tampering(self) -> None:
        copy = self.root / "adulterado"
        import shutil

        shutil.copytree(self.output, copy)
        (copy / "results.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            verify(copy)


if __name__ == "__main__":
    unittest.main()
