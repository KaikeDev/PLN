"""Testes para o vetorizador e representação numérica Bag of Words."""
import json
import tempfile
import unittest
from pathlib import Path

from app.corpus.bow import (
    BagOfWordsVectorizer,
    cosine_similarity,
    generate_bow_dataset,
)


class TestBagOfWords(unittest.TestCase):
    def test_vectorizer_fit_transform(self):
        docs = [
            ["matrix", "ficção", "científica", "matrix"],
            ["matrix", "ação", "futuro"],
            ["comédia", "romântica"],
        ]
        vec = BagOfWordsVectorizer()
        vectors = vec.fit_transform(docs)

        self.assertIn("matrix", vec.vocabulary_)
        matrix_idx = vec.vocabulary_["matrix"]
        self.assertEqual(vectors[0][matrix_idx], 2)
        self.assertEqual(vectors[1][matrix_idx], 1)
        self.assertNotIn(matrix_idx, vectors[2])

        dense_0 = vec.to_dense(vectors[0])
        self.assertEqual(len(dense_0), len(vec.feature_names_))
        self.assertEqual(dense_0[matrix_idx], 2)

    def test_binary_and_normalized_modes(self):
        docs = [["matrix", "matrix", "neo"]]
        vec_bin = BagOfWordsVectorizer(binary=True)
        vec_norm = BagOfWordsVectorizer(normalize=True)

        v_bin = vec_bin.fit_transform(docs)[0]
        v_norm = vec_norm.fit_transform(docs)[0]

        matrix_idx_b = vec_bin.vocabulary_["matrix"]
        matrix_idx_n = vec_norm.vocabulary_["matrix"]

        self.assertEqual(v_bin[matrix_idx_b], 1)
        self.assertAlmostEqual(v_norm[matrix_idx_n], 2 / 3, places=4)

    def test_cosine_similarity(self):
        v1 = {0: 1, 1: 2, 2: 0}
        v2 = {0: 1, 1: 2, 3: 5}
        v3 = {4: 1}

        sim12 = cosine_similarity(v1, v2)
        sim13 = cosine_similarity(v1, v3)

        self.assertGreater(sim12, 0.0)
        self.assertEqual(sim13, 0.0)
        self.assertAlmostEqual(cosine_similarity(v1, v1), 1.0)

    def test_generate_bow_dataset_from_processed_dir(self):
        processed_dir = Path("../data/processed/tmdb_2026-09-12")
        if not processed_dir.exists():
            self.skipTest("Diretório processado não encontrado no caminho relativo.")

        result = generate_bow_dataset(processed_dir)
        self.assertEqual(result["total_documents"], 430)
        self.assertGreater(result["vocabulary_size"], 5000)
        self.assertIn("top_20_terms", result)
        self.assertGreater(result["sparsity_percent"], 90.0)


if __name__ == "__main__":
    unittest.main()
