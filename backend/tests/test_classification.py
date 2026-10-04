"""Casos controlados: sinopses e modelos falsos escritos para o teste, não filmes, medições ou modelos reais."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from app.classification.alternatives import ALTERNATIVES
from app.classification.config import load_config
from app.classification.dataset import MULTICLASS, MULTILABEL, make_tasks
from app.classification.evaluation import BASELINE, decide
from app.classification.grouping import best_mapping, contingency
from app.classification.live import GenreClassifier
from app.classification.pipeline import build, verify
from app.corpus.collect import collect
from app.corpus.process import process
from app.representations.corpus import ProcessedCorpus
from app.representations.pipeline import build as build_vectors
from app.shared.artifacts import read_json_array, read_json_object, read_jsonl, write_json
from tests.test_representations import FAKE_METHODS, REVISION

DRAMA, SCIFI = 18, 878
SYNOPSES = {
    DRAMA: [
        (1, "Família em crise", "Uma família enfrenta o luto e reconstrói a vida depois da perda do pai."),
        (2, "Luto na cidade", "Depois da perda da mãe, uma família em luto tenta reconstruir a vida."),
        (3, "Amor e perda", "Um casal enfrenta a perda do filho e o luto da família."),
        (4, "Recomeço", "Uma mulher reconstrói a vida em outra cidade depois do divórcio e do luto."),
        (5, "Despedida", "A família se despede da avó e aprende a viver com a perda."),
        (6, "Herança", "Irmãos brigam pela herança depois da perda do pai e do luto da família."),
    ],
    SCIFI: [
        (11, "Programador preso", "Um programador descobre que vive conectado a um sistema artificial de computadores."),
        (12, "Rede artificial", "Um sistema artificial de computadores controla a mente das pessoas."),
        (13, "Robôs do futuro", "No futuro, robôs dominam o planeta e o sistema artificial das pessoas."),
        (14, "Nave perdida", "A tripulação de uma nave espacial perdida enfrenta um sistema artificial."),
        (15, "Colônia", "Colonos de uma nave chegam a um planeta controlado por robôs e computadores."),
        (16, "Código", "Um programador cria um sistema artificial que aprende a controlar computadores."),
    ],
}
BOTH = (21, "Luto artificial", "Depois da perda do pai, a família conversa com um sistema artificial que imita a voz dele.")
REPRESENTATIONS = [
    {"name": "tfidf_sem_stopwords", "method": "tfidf", "stage": "06_without_stopwords.jsonl"},
    {"name": "contextual_teste", "method": "contextual", "stage": "02_clean.jsonl", "model": "teste/contextual", "revision": REVISION},
]
CONFIG = {
    "representations": REPRESENTATIONS,
    "labels": [DRAMA, SCIFI],
    "folds": 2,
    "inner_folds": 2,
    "regularization_grid": [0.1, 1, 10],
    "top_features": 3,
    "error_examples": 2,
    "alternatives": ["naive_bayes", "svm_linear", "floresta_aleatoria"],
}


def fetch(endpoint, **params):
    if endpoint == "/genre/movie/list":
        return {"genres": [{"id": DRAMA, "name": "Drama"}, {"id": SCIFI, "name": "Ficção científica"}]}
    genre = int(params["with_genres"])
    results = [{"id": i, "title": title, "overview": text, "genre_ids": [genre]} for i, title, text in SYNOPSES[genre]]
    results.append({"id": BOTH[0], "title": BOTH[1], "overview": BOTH[2], "genre_ids": [DRAMA, SCIFI]})
    return {"page": 1, "total_pages": 1, "results": results}


class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        write_json(
            cls.root / "coleta.json",
            {
                "language": "pt-BR",
                "pages_per_slice": 1,
                "genres": [DRAMA, SCIFI],
                "periods": [[2000, 2010]],
                "vote_count_gte": 50,
                "sort_by": "popularity.desc",
                "include_adult": False,
                "request_interval_seconds": 0,
                "seed_movie_ids": [],
            },
        )
        stopwords = cls.root / "stopwords.txt"
        stopwords.write_text("a\no\nde\nda\ndo\ndas\num\numa\ne\nem\nas\nque\nno\n", encoding="utf-8")
        collect(cls.root / "coleta.json", cls.root / "raw", fetch)
        cls.processed = cls.root / "processed"
        process(cls.root / "raw", cls.processed, stopwords)
        cls.config = cls.write_config("classificacao.json", CONFIG)
        cls.output = cls.root / "classificacao"
        build(cls.processed, cls.output, cls.config, methods=FAKE_METHODS)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def write_config(cls, name, value):
        path = cls.root / name
        write_json(path, value)
        return path

    def live_classifier(self, name="contextual_teste"):
        config = load_config(self.config, FAKE_METHODS, ALTERNATIVES)
        corpus = ProcessedCorpus.load(self.processed)
        spec = next(spec for spec in config.representations if spec.name == name)
        representation = FAKE_METHODS[spec.method].build(spec, corpus, config.vector_config())
        return GenreClassifier(corpus, representation, config)

    def test_live_classifier_uses_trained_model_on_free_text(self):
        classifier = self.live_classifier()
        self.assertEqual((classifier.representation_name, classifier.training_size), ("contextual_teste", 12))
        scifi = classifier.classify("Um sistema artificial de computadores e robôs controla a nave.")
        drama = classifier.classify("Uma família vive o luto depois da perda da mãe.")
        self.assertEqual(scifi[0][0], "Ficção científica")
        self.assertEqual(drama[0][0], "Drama")
        self.assertAlmostEqual(sum(probability for _, probability in scifi), 1.0, places=3)
        self.assertEqual([probability for _, probability in scifi], sorted((p for _, p in scifi), reverse=True))

    def test_live_classifier_rejects_lexical_representation_and_truncates_long_text(self):
        with self.assertRaisesRegex(ValueError, "densa"):
            self.live_classifier("tfidf_sem_stopwords")
        long_text = "Um sistema artificial de computadores controla a nave. " * 20
        self.assertGreater(len(long_text), 500)
        self.assertEqual(self.live_classifier().classify(long_text)[0][0], "Ficção científica")

    def test_tasks_use_tmdb_genres(self):
        corpus = ProcessedCorpus.load(self.processed)
        multiclass, multilabel = make_tasks(corpus, (DRAMA, SCIFI), 2)
        self.assertNotIn(BOTH[0], multiclass.ids)
        self.assertEqual(len(multiclass.ids), 12)
        self.assertEqual(len(multilabel.ids), 13)
        self.assertEqual(multilabel.targets[multilabel.ids.index(BOTH[0])].tolist(), [1, 1])

    def test_rejects_genre_with_fewer_examples_than_folds(self):
        corpus = ProcessedCorpus.load(self.processed)
        with self.assertRaisesRegex(ValueError, "menos exemplos que dobras"):
            make_tasks(corpus, (DRAMA, SCIFI), 7)

    def test_build_writes_verified_results(self):
        self.assertEqual(verify(self.output)["status"], "ok")
        results = read_json_object(self.output / "results.json")
        for task in (MULTICLASS, MULTILABEL):
            self.assertEqual(set(results[task]), {BASELINE, "tfidf_sem_stopwords", "contextual_teste"})
        self.assertGreater(results[MULTICLASS]["tfidf_sem_stopwords"]["f1_macro"], results[MULTICLASS][BASELINE]["f1_macro"])
        self.assertEqual(len(results[MULTICLASS]["contextual_teste"]["c_escolhido"]), 2)
        self.assertEqual(results[MULTICLASS][BASELINE]["c_escolhido"], [])
        documents = {row["id"]: row for row in read_json_array(self.output / "documents.json")}
        self.assertIsNone(documents[BOTH[0]]["fold_multiclasse"])
        self.assertIn(documents[BOTH[0]]["fold_multirrotulo"], (0, 1))
        rows = read_jsonl(self.output / "tfidf_sem_stopwords.multiclasse.predictions.jsonl")
        self.assertEqual(len(rows), 12)
        self.assertAlmostEqual(sum(rows[0]["probabilidades"].values()), 1, places=3)

    def test_only_lexical_representations_have_terms(self):
        terms = read_json_object(self.output / "top_terms.json")
        self.assertEqual(list(terms), ["tfidf_sem_stopwords"])
        self.assertEqual(len(terms["tfidf_sem_stopwords"]["Drama"]), 3)
        report = (self.output / "report.md").read_text(encoding="utf-8")
        self.assertIn("## Multirrótulo", report)
        self.assertIn("Melhor F1 macro", report)

    def test_build_is_deterministic(self):
        other = self.root / "classificacao_2"
        build(self.processed, other, self.config, methods=FAKE_METHODS)
        manifest = read_json_object(self.output / "manifest.json")["files"]
        self.assertEqual(manifest, read_json_object(other / "manifest.json")["files"])

    def test_verify_detects_changes(self):
        copy = self.root / "adulterada"
        build(self.processed, copy, self.config, methods=FAKE_METHODS)
        path = copy / "contextual_teste.multirrotulo.predictions.jsonl"
        path.write_text(path.read_text(encoding="utf-8").replace('"acertou": true', '"acertou": false', 1), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Hash divergente"):
            verify(copy)

    def test_reuses_dense_vectors_from_stage_two(self):
        vectors = self.root / "vetores"
        build_vectors(
            self.processed,
            vectors,
            self.write_config("vetorizacao.json", {"representations": REPRESENTATIONS, "clusters": 2}),
            methods=FAKE_METHODS,
        )
        output = self.root / "classificacao_reuso"
        build(self.processed, output, self.config, methods=FAKE_METHODS, vectors=vectors)
        manifest = read_json_object(output / "manifest.json")
        self.assertEqual(manifest["reused_representations"], ["contextual_teste"])
        self.assertIsNotNone(manifest["source_vectors_manifest_sha256"])
        reused = read_json_object(output / "results.json")[MULTICLASS]["contextual_teste"]["f1_macro"]
        original = read_json_object(self.output / "results.json")[MULTICLASS]["contextual_teste"]["f1_macro"]
        self.assertAlmostEqual(reused, original, places=3)
        representations = read_json_object(output / "representations.json")
        self.assertEqual(representations["contextual_teste"]["vectors"], "lidos da Etapa 2")
        self.assertEqual(representations["tfidf_sem_stopwords"]["vectors"], "calculados nesta execução")
        other_revision = [REPRESENTATIONS[0], {**REPRESENTATIONS[1], "revision": "1" * 40}]
        config = self.write_config("outra_revisao.json", {**CONFIG, "representations": other_revision})
        output = self.root / "classificacao_outra_revisao"
        build(self.processed, output, config, methods=FAKE_METHODS, vectors=vectors)
        self.assertEqual(read_json_object(output / "manifest.json")["reused_representations"], [])

    def test_refuses_existing_output(self):
        with self.assertRaises(FileExistsError):
            build(self.processed, self.output, self.config, methods=FAKE_METHODS)

    def test_config_validation(self):
        cases = [
            ({**CONFIG, "desconhecido": 1}, "Campos desconhecidos"),
            ({**CONFIG, "labels": [DRAMA]}, "de 2 a 20"),
            ({**CONFIG, "regularization_grid": []}, "regularization_grid"),
            ({**CONFIG, "regularization_grid": [0]}, "regularization_grid"),
            ({**CONFIG, "folds": True}, "folds"),
            ({**CONFIG, "alternatives": ["arvore_magica"]}, "alternatives"),
            ({**CONFIG, "alternatives": ["knn", "knn"]}, "repetidos"),
        ]
        for value, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                load_config(self.write_config("invalida.json", value), FAKE_METHODS, ALTERNATIVES)

    def test_alternatives_require_registry(self):
        with self.assertRaisesRegex(ValueError, "alternatives"):
            load_config(self.write_config("sem_registro.json", CONFIG), FAKE_METHODS)

    def test_clustering_compares_groups_with_genres(self):
        clusters = read_json_object(self.output / "clustering.json")
        self.assertEqual(list(clusters), ["tfidf_sem_stopwords", "contextual_teste"])
        for grouping in clusters.values():
            self.assertTrue(-1 <= grouping["ari"] <= 1)
            self.assertLessEqual(grouping["acuracia_melhor_mapeamento"], grouping["pureza"])
            self.assertEqual(sum(group["tamanho"] for group in grouping["grupos"]), 12)
            self.assertEqual(sorted(group["genero_associado"] for group in grouping["grupos"]), ["Drama", "Ficção científica"])
        results = read_json_object(self.output / "results.json")
        self.assertIn("ari", results[MULTICLASS]["contextual_teste"])
        self.assertEqual(results[MULTICLASS][BASELINE]["ari"], 0)

    def test_best_mapping_undoes_group_permutation(self):
        truth = np.array([0, 0, 1, 1, 2, 2])
        groups = np.array([2, 2, 0, 0, 1, 1])
        table = contingency(truth, groups, 3)
        self.assertEqual(best_mapping(table), [1, 2, 0])

    def test_alternatives_use_same_folds_and_skip_inapplicable(self):
        alternatives = read_json_object(self.output / "alternatives.json")
        self.assertIsNone(alternatives["contextual_teste"]["naive_bayes"])
        self.assertIsNotNone(alternatives["tfidf_sem_stopwords"]["naive_bayes"])
        for name in ("svm_linear", "floresta_aleatoria"):
            for representation in alternatives.values():
                self.assertTrue(0 <= representation[name]["f1_macro"] <= 1)
        self.assertEqual(len(alternatives["tfidf_sem_stopwords"]["svm_linear"]["parametro_escolhido"]), 2)
        self.assertIsNone(alternatives["contextual_teste"]["floresta_aleatoria"]["parametro_escolhido"][0])
        report = (self.output / "report.md").read_text(encoding="utf-8")
        self.assertIn("## Outros classificadores (multiclasse)", report)
        self.assertIn("## Descobrir grupos ou reconhecer classes?", report)

    def test_multilabel_decision_assigns_at_least_one_genre(self):
        corpus = ProcessedCorpus.load(self.processed)
        _, multilabel = make_tasks(corpus, (DRAMA, SCIFI), 2)
        chosen = decide(multilabel, np.array([[0.2, 0.3], [0.6, 0.7], [0.9, 0.1]]))
        self.assertEqual(chosen.tolist(), [[0, 1], [1, 1], [1, 0]])


if __name__ == "__main__":
    unittest.main()
