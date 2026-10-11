"""Varredura do número de clusters com sinopses escritas para o teste e só representações lexicais; sem rede."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app.clustering.sweep import load_sweep_config, sweep, verify
from app.corpus.collect import collect
from app.corpus.process import process
from app.shared.artifacts import read_json_object, write_json

SYNOPSES = {
    27: [
        (1, "Casa", "Um fantasma assombra a casa da família durante a noite."),
        (2, "Espírito", "Um espírito maligno assombra uma família numa casa antiga."),
        (3, "Porão", "A família ouve o fantasma no porão da casa assombrada."),
        (4, "Possessão", "Um demônio possui a filha e assombra a casa da família."),
    ],
    878: [
        (5, "Nave", "Astronautas viajam numa nave espacial até um planeta distante."),
        (6, "Marte", "Um astronauta sobrevive sozinho num planeta depois da missão espacial."),
        (7, "Estação", "A tripulação da estação espacial enfrenta uma falha na nave."),
        (8, "Órbita", "Uma missão espacial leva astronautas para a órbita de um planeta."),
    ],
}


def fetch(endpoint, **params):
    if endpoint == "/genre/movie/list":
        return {"genres": [{"id": 27, "name": "Terror"}, {"id": 878, "name": "Ficção científica"}]}
    genre = int(params["with_genres"])
    return {
        "page": 1,
        "total_pages": 1,
        "results": [{"id": i, "title": t, "overview": o, "genre_ids": [genre]} for i, t, o in SYNOPSES[genre]],
    }


class SweepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        write_json(
            root / "coleta.json",
            {
                "language": "pt-BR",
                "pages_per_slice": 1,
                "genres": [27, 878],
                "periods": [[2000, 2010]],
                "vote_count_gte": 50,
                "sort_by": "popularity.desc",
                "include_adult": False,
                "request_interval_seconds": 0,
                "seed_movie_ids": [],
            },
        )
        stopwords = root / "stopwords.txt"
        stopwords.write_text("a\no\num\numa\nda\nde\nno\nna\nnuma\nnum\naté\npara\n", encoding="utf-8")
        collect(root / "coleta.json", root / "raw", fetch)
        process(root / "raw", root / "processed", stopwords)
        write_json(
            root / "vetorizacao.json",
            {
                "representations": [{"name": "tfidf_sem_stopwords", "method": "tfidf", "stage": "06_without_stopwords.jsonl"}],
                "min_df": 1,
                "neighbors_k": 2,
                "example_ids": [1],
                "clusters": 2,
                "top_terms": 3,
                "random_state": 42,
                "probe_words": [],
            },
        )
        write_json(root / "varredura.json", {"k_min": 2, "k_max": 3, "random_state": 42, "top_terms": 3})
        cls.output = root / "varredura"
        cls.result = sweep(root / "processed", root / "vetorizacao.json", cls.output, root / "varredura.json")
        cls.root = root

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_each_k_has_internal_and_external_metrics(self) -> None:
        rows = json.loads((self.output / "sweep.json").read_text(encoding="utf-8"))["tfidf_sem_stopwords"]
        self.assertEqual([row["k"] for row in rows], [2, 3])
        for row in rows:
            self.assertEqual(sum(row["tamanhos"]), 8)
            for key in (
                "silhueta_cosseno",
                "davies_bouldin",
                "calinski_harabasz",
                "distancia_ao_centroide",
                "distancia_entre_centroides",
                "ari",
                "nmi",
                "pureza",
            ):
                self.assertIn(key, row)
        two = rows[0]
        self.assertEqual(two["ari"], 1.0)
        self.assertGreater(two["silhueta_cosseno"], 0)

    def test_summary_report_and_verify(self) -> None:
        summary = read_json_object(self.output / "summary.json")
        self.assertEqual(summary["tfidf_sem_stopwords"]["maior_ari"], 2)
        self.assertIn("Melhor k por métrica", (self.output / "report.md").read_text(encoding="utf-8"))
        self.assertEqual(verify(self.output)["status"], "ok")
        copy = self.root / "adulterada"
        shutil.copytree(self.output, copy)
        (copy / "sweep.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            verify(copy)

    def test_config_rejects_inverted_range(self) -> None:
        write_json(self.root / "invalida.json", {"k_min": 5, "k_max": 3, "random_state": 1, "top_terms": 3})
        with self.assertRaises(ValueError):
            load_sweep_config(self.root / "invalida.json")


if __name__ == "__main__":
    unittest.main()
