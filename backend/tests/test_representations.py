"""Casos controlados: sinopses e modelos falsos escritos para o teste, não filmes, medições ou modelos reais."""

import json
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

import numpy as np
from sklearn.preprocessing import normalize

from app.clustering.svg import render_projection
from app.corpus.collect import collect
from app.corpus.process import process
from app.recommendation.similar import SimilarMovies
from app.representations.config import load_config, load_queries
from app.representations.corpus import ProcessedCorpus
from app.representations.embeddings import ContextualMethod, Word2VecMethod
from app.representations.methods import METHODS
from app.representations.metrics import average_precision, genre_agreement, precision_at_k, purity, reciprocal_rank
from app.representations.pipeline import build, verify
from app.representations.probes import contains_word, load_probes
from app.representations.space import TFIDF
from app.search.hybrid import HybridIndex, SearchConfig, WeightedRepresentation, evaluate, load_search_config
from app.search.retrieval import search
from app.search.synopsis_index import CorpusSynopsisIndex
from app.shared.artifacts import read_json_object, read_jsonl, write_json

SYNOPSES = {
    18: [
        (1, "Família em crise", "Uma família enfrenta o luto e reconstrói a vida depois da perda do pai."),
        (2, "Luto na cidade", "Depois da perda da mãe, uma família em luto tenta reconstruir a vida."),
        (3, "Amor e perda", "Um casal enfrenta a perda do filho e o luto da família."),
        (4, "Recomeço", "Uma mulher reconstrói a vida em outra cidade depois do divórcio."),
    ],
    878: [
        (5, "Programador preso", "Um programador descobre que vive conectado a um sistema artificial de computadores."),
        (6, "Rede artificial", "Um sistema artificial de computadores controla a mente das pessoas."),
        (7, "Robôs do futuro", "No futuro, robôs dominam o planeta e as pessoas."),
        (8, "Nave perdida", "A tripulação de uma nave espacial perdida enfrenta um sistema artificial."),
    ],
}
GENRE_IDS = {4: [18, 878]}
REVISION = "0" * 40
REPRESENTATIONS = [
    {"name": "bow_sem_pontuacao", "method": "bow", "stage": "05_without_punctuation.jsonl"},
    {"name": "tfidf_sem_stopwords", "method": "tfidf", "stage": "06_without_stopwords.jsonl"},
    {"name": "word2vec_teste", "method": "word2vec", "stage": "06_without_stopwords.jsonl", "model": "teste/vetores", "revision": REVISION},
    {"name": "contextual_teste", "method": "contextual", "stage": "02_clean.jsonl", "model": "teste/contextual", "revision": REVISION},
]


class FakeWordVectors:
    """Vetores escolhidos à mão: eixo 0 ≈ tecnologia, eixo 1 ≈ luto. “realidade” fica fora do vocabulário."""

    dimension = 4
    parameters = 60
    TABLE: ClassVar[dict[str, list[float]]] = {
        "simulação": [1, 0.1, 0, 0],
        "artificial": [1, 0, 0, 0.1],
        "sistema": [0.9, 0, 0.1, 0],
        "computadores": [0.8, 0.2, 0, 0],
        "programador": [0.7, 0, 0.3, 0],
        "robôs": [0.6, 0, 0, 0.4],
        "nave": [0.5, 0, 0.5, 0],
        "luto": [0, 1, 0, 0.1],
        "perda": [0, 0.9, 0.1, 0],
        "família": [0.1, 0.8, 0, 0],
        "vida": [0, 0.6, 0.4, 0],
        "cachorro": [0.1, 0, 0.9, 0.2],
        "cão": [0.1, 0, 0.85, 0.25],
        "banco": [0.4, 0.4, 0.2, 0],
        "xícara": [0, 0, 0, 1],
    }

    def vector(self, word):
        values = self.TABLE.get(word)
        return None if values is None else np.array(values, dtype=np.float64)


class FakeEncoder:
    """Codificador contextual falso: conta grupos de palavras temáticas; não depende de palavras idênticas à consulta.

    O vetor de uma palavra dentro de uma frase é o vetor da própria frase, então muda com o contexto.
    """

    max_tokens = 12
    parameters = 1000
    GROUPS = (
        ("sistema", "artificial", "computador", "robô", "nave", "simulação", "realidade"),
        ("luto", "perda", "família", "vida"),
        ("cidade", "divórcio", "casal"),
    )

    def encode(self, texts):
        rows = [[sum(text.lower().count(word) for word in group) for group in self.GROUPS] + [0.1] for text in texts]
        return normalize(np.array(rows, dtype=np.float64))

    def count_tokens(self, text):
        return len(text.split())

    def word_vectors(self, text, word):
        return [self.encode([text])[0]] if contains_word(text, word) else []


FAKE_METHODS = {
    **METHODS,
    "word2vec": Word2VecMethod(lambda spec: FakeWordVectors()),
    "contextual": ContextualMethod(lambda spec: FakeEncoder()),
}


PROBES = {
    "sentence_pairs": [
        {
            "id": "parafrase",
            "left": "O programador usa computadores.",
            "right": "Um sistema artificial controla robôs.",
            "expected": "proximas",
        },
        {"id": "distantes", "left": "O luto da família.", "right": "Um sistema artificial.", "expected": "distantes"},
    ],
    "word_pairs": [["cachorro", "cão"], ["cachorro", "xícara"], ["cachorro", "inexistente"]],
    "word_senses": [
        {
            "id": "banco",
            "word": "banco",
            "contexts": [
                {"sense": "finanças", "text": "O banco da família sofreu uma perda."},
                {"sense": "finanças", "text": "O banco cobrou a família pela perda da vida."},
                {"sense": "assento", "text": "O casal sentou no banco da cidade."},
                {"sense": "assento", "text": "O banco de madeira da cidade quebrou no divórcio."},
            ],
        }
    ],
}


def fetch(endpoint, **params):
    if endpoint == "/genre/movie/list":
        return {"genres": [{"id": 18, "name": "Drama"}, {"id": 878, "name": "Ficção científica"}]}
    genre = int(params["with_genres"])
    results = [{"id": i, "title": title, "overview": text, "genre_ids": GENRE_IDS.get(i, [genre])} for i, title, text in SYNOPSES[genre]]
    return {"page": 1, "total_pages": 1, "results": results}


class VectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        write_json(
            cls.root / "coleta.json",
            {
                "language": "pt-BR",
                "pages_per_slice": 1,
                "genres": [18, 878],
                "periods": [[2000, 2010]],
                "vote_count_gte": 50,
                "sort_by": "popularity.desc",
                "include_adult": False,
                "request_interval_seconds": 0,
                "seed_movie_ids": [],
            },
        )
        stopwords = cls.root / "stopwords.txt"
        stopwords.write_text("a\no\nde\nda\ndo\ndas\num\numa\ne\nem\nas\nque\nno\nsobre\n", encoding="utf-8")
        collect(cls.root / "coleta.json", cls.root / "raw", fetch)
        cls.processed = cls.root / "processed"
        process(cls.root / "raw", cls.processed, stopwords)
        cls.config = cls.write_config(
            "vetorizacao.json",
            {
                "representations": REPRESENTATIONS,
                "neighbors_k": 3,
                "example_ids": [5],
                "clusters": 2,
                "top_terms": 5,
                "probe_words": ["simulação", "inexistente"],
                "profiles": [{"id": "ficcao", "movie_ids": [5, 6], "note": "Gostou de filmes sobre sistemas artificiais."}],
            },
        )
        cls.queries = cls.root / "consultas.json"
        write_json(
            cls.queries,
            {
                "queries": [
                    {"id": "literal", "text": "programador conectado a um sistema de computadores", "relevant_ids": [5]},
                    {"id": "tematica", "text": "simulação da realidade", "relevant_ids": [5]},
                ]
            },
        )
        cls.probes = cls.write_config("sondas.json", PROBES)
        cls.output = cls.root / "vectors"
        build(cls.processed, cls.output, cls.config, cls.queries, cls.probes, methods=FAKE_METHODS)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def write_config(cls, name, value):
        path = cls.root / name
        write_json(path, value)
        return path

    def read(self, filename):
        return json.loads((self.output / filename).read_text(encoding="utf-8"))

    def query(self, representation, index):
        return self.read("retrieval.json")[representation]["queries"][index]

    def test_build_writes_aligned_verified_outputs_without_overwrite(self):
        self.assertEqual(verify(self.output), {"status": "ok", "documents": 8, "representations": 4, "files_verified": 32})
        for filename in [
            "bow_sem_pontuacao.matrix.jsonl",
            "tfidf_sem_stopwords.matrix.jsonl",
            "word2vec_teste.embeddings.jsonl",
            "contextual_teste.embeddings.jsonl",
            "contextual_teste.recommendations.jsonl",
        ]:
            self.assertEqual([row["id"] for row in read_jsonl(self.output / filename)], list(range(1, 9)))
        self.assertTrue((self.output / "contextual_teste.projection.svg").read_text(encoding="utf-8").startswith("<svg"))
        self.assertIn("contextual_teste.recommendations.jsonl", read_json_object(self.output / "manifest.json")["row_files"])
        with self.assertRaises(FileExistsError):
            build(self.processed, self.output, self.config, self.queries, self.probes, methods=FAKE_METHODS)

    def test_bow_counts_and_tfidf_downweights_common_terms(self):
        bow = {row["id"]: row["weights"] for row in read_jsonl(self.output / "bow_sem_pontuacao.matrix.jsonl")}
        tfidf = {row["id"]: row["weights"] for row in read_jsonl(self.output / "tfidf_sem_stopwords.matrix.jsonl")}
        self.assertEqual(bow[2]["da"], 2)
        self.assertNotIn("da", tfidf[2])
        idf = {item["term"]: item["idf"] for item in self.read("tfidf_sem_stopwords.vocabulary.json")["terms"]}
        self.assertLess(idf["família"], idf["programador"])
        self.assertAlmostEqual(sum(value**2 for value in tfidf[5].values()), 1.0, places=4)

    def test_dimensions_distinguish_sparse_and_dense(self):
        dimensions = self.read("dimensions.json")
        self.assertTrue(dimensions["tfidf_sem_stopwords"]["sparse"])
        self.assertFalse(dimensions["word2vec_teste"]["sparse"])
        self.assertEqual(dimensions["word2vec_teste"]["dimensions"], 4)
        self.assertLess(dimensions["word2vec_teste"]["token_coverage"], 1)
        self.assertEqual(dimensions["contextual_teste"]["max_tokens"], 12)
        self.assertGreater(dimensions["contextual_teste"]["truncated_documents"], 0)

    def test_labels_are_tmdb_genres_restricted_to_collection(self):
        corpus = ProcessedCorpus.load(self.processed)
        self.assertEqual(corpus.collection_genres, {18, 878})
        self.assertEqual(corpus.by_id[4].genres, {18, 878})
        self.assertEqual(corpus.by_id[1].genres, {18})
        self.assertIsNone(corpus.genre_name(corpus.by_id[4]))
        self.assertEqual(self.read("documents.json")[3]["genres"], ["Drama", "Ficção científica"])

    def test_item_recommendations_use_cosine_and_explain_similarity(self):
        recommendation = self.read("recommendation.json")
        lexical = recommendation["tfidf_sem_stopwords"]["examples"][0]["recommendations"]
        self.assertEqual(lexical[0]["id"], 6)
        self.assertIn("computadores", lexical[0]["explanation"])
        self.assertEqual(lexical[0]["shared_genres"], ["Ficção científica"])
        self.assertNotIn(5, [item["id"] for item in lexical])
        contextual = recommendation["contextual_teste"]["examples"][0]["recommendations"]
        self.assertEqual(contextual[0]["explanation"], [])
        self.assertGreater(recommendation["tfidf_sem_stopwords"]["precision_at_k"], recommendation["tfidf_sem_stopwords"]["baseline"])
        self.assertEqual(recommendation["tfidf_sem_stopwords"]["documents_evaluated"], 8)

    def test_site_recommender_matches_offline_recommendations(self):
        corpus = ProcessedCorpus.load(self.processed)
        config = load_config(self.config, FAKE_METHODS)
        spec = next(spec for spec in config.representations if spec.name == "tfidf_sem_stopwords")
        recommender = SimilarMovies(FAKE_METHODS[spec.method].build(spec, corpus, config))
        offline = {
            row["id"]: [item["id"] for item in row["recommendations"]]
            for row in read_jsonl(self.output / "tfidf_sem_stopwords.recommendations.jsonl")
        }
        for movie_id, expected in offline.items():
            ranked = recommender.similar(movie_id, len(expected))
            self.assertEqual([other for other, _ in ranked], expected)
            self.assertNotIn(movie_id, [other for other, _ in ranked])
        self.assertIsNone(recommender.similar(999999, 3))
        self.assertEqual(recommender.representation_name, "tfidf_sem_stopwords")

    def test_every_movie_gets_k_recommendations_without_itself(self):
        for row in read_jsonl(self.output / "tfidf_sem_stopwords.recommendations.jsonl"):
            ids = [item["id"] for item in row["recommendations"]]
            self.assertEqual(len(ids), 3)
            self.assertNotIn(row["id"], ids)

    def test_profile_recommendations_exclude_liked_movies(self):
        profile = self.read("recommendation.json")["tfidf_sem_stopwords"]["profiles"][0]
        ids = [item["id"] for item in profile["recommendations"]]
        self.assertEqual(profile["id"], "ficcao")
        self.assertEqual(ids[0], 8)
        self.assertFalse({5, 6} & set(ids))
        self.assertEqual(profile["genres"], ["Ficção científica"])
        word2vec = self.read("recommendation.json")["word2vec_teste"]["profiles"][0]["recommendations"][0]
        self.assertTrue(word2vec["explanation"])

    def test_clustering_and_projection_cover_every_document(self):
        for name in ["tfidf_sem_stopwords", "word2vec_teste", "contextual_teste"]:
            clustering = self.read("clustering.json")[name]
            self.assertEqual(sum(cluster["size"] for cluster in clustering["clusters"]), 8)
            self.assertEqual(len(clustering["assignments"]), 8)
            self.assertTrue(-1 <= clustering["adjusted_rand_index"] <= 1)
            self.assertEqual(clustering["labeled_documents"], 7)
            self.assertEqual(len(clustering["clusters"][0]["descriptive_terms"]), 5)
            self.assertEqual(len(self.read("projection.json")[name]["points"]), 8)
            svg = (self.output / f"{name}.clusters.svg").read_text(encoding="utf-8")
            self.assertIn("Cluster 0", svg)
            self.assertNotIn("Nenhum ou mais de um gênero", svg)

    def test_lexical_query_needs_identical_words(self):
        literal, thematic = self.query("tfidf_sem_stopwords", 0), self.query("tfidf_sem_stopwords", 1)
        self.assertEqual(literal["relevant"][0]["rank"], 1)
        self.assertEqual(literal["reciprocal_rank"], 1.0)
        self.assertTrue(thematic["null_vector"])
        self.assertEqual(thematic["out_of_vocabulary"], ["realidade", "simulação"])
        self.assertIsNone(thematic["relevant"][0]["rank"])

    def test_embeddings_reach_thematic_query_without_shared_words(self):
        word2vec = self.query("word2vec_teste", 1)
        self.assertEqual(word2vec["out_of_vocabulary"], ["realidade"])
        self.assertIsNotNone(word2vec["relevant"][0]["rank"])
        self.assertEqual(word2vec["relevant"][0]["explanation"][0], "simulação ≈ artificial")
        self.assertIsNotNone(self.query("contextual_teste", 1)["relevant"][0]["rank"])

    def test_word_neighbors_only_for_word_vectors(self):
        words = self.read("word_neighbors.json")
        self.assertEqual(words["tfidf_sem_stopwords"], {"supported": False})
        self.assertIn("artificial", [word for word, _ in words["word2vec_teste"]["words"]["simulação"][:3]])
        self.assertIsNone(words["word2vec_teste"]["words"]["inexistente"])

    def test_static_embeddings_ignore_context(self):
        senses = self.read("word_senses.json")
        self.assertEqual(senses["tfidf_sem_stopwords"], {"supported": False})
        word2vec = senses["word2vec_teste"]
        self.assertEqual(word2vec["family"], "static")
        banco = word2vec["words"][0]
        self.assertTrue(all(value == 1.0 for row in banco["similarity"] for value in row))
        self.assertEqual(banco["gap"], 0.0)

    def test_contextual_embeddings_separate_senses(self):
        banco = self.read("word_senses.json")["contextual_teste"]["words"][0]
        self.assertEqual(banco["senses"], ["finanças", "finanças", "assento", "assento"])
        self.assertGreater(banco["same_sense_mean"], banco["different_sense_mean"])
        self.assertGreater(banco["gap"], 0.5)

    def test_sentence_pairs_contrast_lexical_and_semantic_similarity(self):
        pairs = self.read("sentence_pairs.json")
        lexical, word2vec, contextual = (pairs[name]["pairs"][0] for name in ("tfidf_sem_stopwords", "word2vec_teste", "contextual_teste"))
        self.assertEqual(lexical["cosine"], 0.0)
        self.assertEqual(lexical["explanation"], [])
        self.assertGreater(word2vec["cosine"], 0.8)
        self.assertTrue(any("≈" in pair for pair in word2vec["explanation"]))
        self.assertGreater(contextual["cosine"], 0.9)
        self.assertLess(pairs["contextual_teste"]["pairs"][1]["cosine"], contextual["cosine"])

    def test_word_pairs_follow_distributional_vectors(self):
        pairs = self.read("word_neighbors.json")["word2vec_teste"]["pairs"]
        self.assertEqual([left for left, _, _ in pairs], ["cachorro", "cachorro", "cachorro"])
        self.assertGreater(pairs[0][2], 0.95)
        self.assertLess(pairs[1][2], pairs[0][2])
        self.assertIsNone(pairs[2][2])

    def test_synthesis_describes_families_and_cost(self):
        synthesis = self.read("synthesis.json")
        self.assertEqual(synthesis["bow_sem_pontuacao"]["family"], "lexical")
        self.assertTrue(synthesis["bow_sem_pontuacao"]["dimensions_are_vocabulary"])
        self.assertIsNone(synthesis["bow_sem_pontuacao"]["parameters"])
        self.assertTrue(synthesis["word2vec_teste"]["learned"])
        self.assertFalse(synthesis["word2vec_teste"]["word_depends_on_context"])
        self.assertTrue(synthesis["contextual_teste"]["word_depends_on_context"])
        self.assertFalse(synthesis["contextual_teste"]["interpretable_by_words"])
        self.assertEqual(synthesis["contextual_teste"]["parameters"], 1000)
        manifest = read_json_object(self.output / "manifest.json")
        self.assertEqual(set(manifest["build_seconds"]), {spec["name"] for spec in REPRESENTATIONS})

    def test_probes_reject_invalid_examples(self):
        sense = PROBES["word_senses"][0]
        invalid = [
            {},
            {"word_pairs": [["cachorro", "cachorro"]]},
            {"word_pairs": [["cachorro", "c4o"]]},
            {"sentence_pairs": [{**PROBES["sentence_pairs"][0], "expected": "talvez"}]},
            {"word_senses": [{**sense, "contexts": [{"sense": "finanças", "text": "Sem a palavra aqui."}, *sense["contexts"][1:]]}]},
            {"word_senses": [{**sense, "contexts": sense["contexts"][:2]}]},
            {"sentence_pairs": [{**PROBES["sentence_pairs"][0], "left": "x" * 501}]},
            {"campo_desconhecido": []},
        ]
        for index, value in enumerate(invalid):
            with self.subTest(value=value), self.assertRaises(ValueError):
                load_probes(self.write_config(f"invalid_probes_{index}.json", value))
        self.assertEqual(len(load_probes(self.probes).word_senses[0].contexts), 4)

    def test_build_is_deterministic(self):
        second = self.root / "vectors_second"
        build(self.processed, second, self.config, self.queries, self.probes, methods=FAKE_METHODS)
        for path in self.output.iterdir():
            if path.name != "manifest.json":
                self.assertEqual(path.read_bytes(), (second / path.name).read_bytes(), path.name)

    def test_tampering_is_rejected(self):
        tampered = self.root / "vectors_tampered"
        build(self.processed, tampered, self.config, methods=FAKE_METHODS)
        (tampered / "documents.json").write_text("[]\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Hash divergente"):
            verify(tampered)
        manifest = json.loads((tampered / "manifest.json").read_text(encoding="utf-8"))
        manifest["files"] = {"../manifest.json": "0"}
        write_json(tampered / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "inválido"):
            verify(tampered)

    def test_config_rejects_unsafe_or_invalid_values(self):
        lexical, word2vec, contextual = REPRESENTATIONS[0], REPRESENTATIONS[2], REPRESENTATIONS[3]
        base = {"representations": [lexical]}
        invalid = [
            {"representations": [{**lexical, "stage": "../../raw/movies.jsonl"}]},
            {"representations": [{**lexical, "name": "../fora"}]},
            {"representations": [{**lexical, "method": "desconhecido"}]},
            {"representations": [{**lexical, "stage": "02_clean.jsonl"}]},
            {"representations": [{**lexical, "model": "teste/vetores"}]},
            {"representations": [{**contextual, "stage": "06_without_stopwords.jsonl"}]},
            {"representations": [{key: value for key, value in word2vec.items() if key != "revision"}]},
            {"representations": [{**word2vec, "revision": "main"}]},
            {"representations": [{**word2vec, "model": "../../segredo"}]},
            {"representations": [lexical, lexical]},
            {**base, "clusters": True},
            {**base, "neighbors_k": 0},
            {**base, "probe_words": "simulação"},
            {**base, "campo_desconhecido": 1},
            {**base, "profiles": [{"id": "um_filme", "movie_ids": [1]}]},
            {**base, "profiles": [{"id": "../fora", "movie_ids": [1, 2]}]},
            {**base, "profiles": [{"id": "p", "movie_ids": [1, 2]}, {"id": "p", "movie_ids": [3, 4]}]},
            {**base, "profiles": {"id": "p", "movie_ids": [1, 2]}},
        ]
        for index, value in enumerate(invalid):
            with self.subTest(value=value), self.assertRaises(ValueError):
                load_config(self.write_config(f"invalid_{index}.json", value), METHODS)
        with self.assertRaises(ValueError):
            load_queries(self.write_config("long_query.json", {"queries": [{"id": "q", "text": "x" * 501, "relevant_ids": [1]}]}))

    def test_invalid_reference_leaves_no_partial_output(self):
        output = self.root / "never_created"
        for index, extra in enumerate([{"example_ids": [999]}, {"profiles": [{"id": "p", "movie_ids": [1, 999]}]}]):
            config = self.write_config(f"missing_id_{index}.json", {"representations": REPRESENTATIONS[:2], "clusters": 2, **extra})
            with self.subTest(extra=extra), self.assertRaisesRegex(ValueError, "999"):
                build(self.processed, output, config)
        self.assertFalse(output.exists())

    def test_processed_input_is_verified_before_use(self):
        copy = self.root / "processed_copy"
        copy.mkdir()
        for path in self.processed.iterdir():
            (copy / path.name).write_bytes(path.read_bytes())
        (copy / "06_without_stopwords.jsonl").write_text('{"id": 1, "tokens": []}\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Hash divergente"):
            ProcessedCorpus.load(copy)

    def test_search_applies_same_preparation_as_documents(self):
        corpus = ProcessedCorpus.load(self.processed)
        config = load_config(self.config, METHODS)
        representation = TFIDF.build(config.representations[1], corpus, config)
        result = search(representation, corpus, "<b>Sistema</b> ARTIFICIAL")
        self.assertEqual(result.query.tokens, ("sistema", "artificial"))
        self.assertEqual({movie_id for movie_id, _ in result.ranked}, {5, 6, 8})

    def test_svg_escapes_text_from_data(self):
        points = [
            {"id": 1, "title": "<script>alert(1)</script>", "label": "Drama", "x": 0.0, "y": 1.0},
            {"id": 2, "title": "B & C", "label": None, "x": 1.0, "y": 0.0},
        ]
        svg = render_projection("Título <teste>", points, [0.5, 0.25], {1, 2})
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)
        self.assertIn("B &amp; C", svg)

    def hybrid(self, lexical=0.3, semantic=0.7):
        config = SearchConfig(
            (WeightedRepresentation("tfidf_sem_stopwords", lexical), WeightedRepresentation("contextual_teste", semantic))
        )
        return HybridIndex.build(self.processed, self.config, config, FAKE_METHODS)

    def test_hybrid_combines_literal_and_thematic_matches(self):
        index = self.hybrid()
        self.assertEqual(index.rank("programador conectado a um sistema de computadores")[0][0], 5)
        thematic = index.rank("simulação da realidade")
        self.assertIn(thematic[0][0], {5, 6, 7, 8})
        self.assertNotIn(1, [movie_id for movie_id, _ in thematic[:4]])
        scores = [score for _, score in thematic]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertLessEqual(scores[0], 1.0)

    def test_hybrid_normalizes_each_representation_by_its_best_cosine(self):
        index = self.hybrid()
        for name in ("tfidf_sem_stopwords", "contextual_teste"):
            self.assertAlmostEqual(index.only(name).rank("sistema artificial de computadores")[0][1], 1.0)
        self.assertEqual(
            self.hybrid(1.0, 0.0001).rank("sistema artificial")[0][0], index.only("tfidf_sem_stopwords").rank("sistema artificial")[0][0]
        )

    def test_hybrid_evaluation_compares_members_and_combination(self):
        report = evaluate(self.hybrid(), load_queries(self.queries), k=3)
        self.assertEqual(set(report["results"]), {"tfidf_sem_stopwords", "contextual_teste", "combinacao"})
        self.assertEqual(report["weights"], {"tfidf_sem_stopwords": 0.3, "contextual_teste": 0.7})
        literal = report["results"]["combinacao"]["queries"]["literal"]
        self.assertEqual(literal["reciprocal_rank"], 1.0)
        self.assertIn("mean_average_precision", report["results"]["contextual_teste"])

    def test_search_config_is_validated(self):
        valid = {"representations": [{"name": "tfidf_sem_stopwords", "weight": 0.3}, {"name": "contextual_teste", "weight": 0.7}]}
        self.assertEqual(len(load_search_config(self.write_config("busca.json", valid)).representations), 2)
        invalid = {
            "soma": {"representations": [{"name": "tfidf_sem_stopwords", "weight": 0.5}]},
            "repetida": {"representations": [{"name": "a", "weight": 0.5}, {"name": "a", "weight": 0.5}]},
            "campo": {**valid, "extra": 1},
            "nome": {"representations": [{"name": "../x", "weight": 1}]},
        }
        for name, value in invalid.items():
            with self.subTest(name), self.assertRaises(ValueError):
                load_search_config(self.write_config(f"busca_{name}.json", value))
        missing = SearchConfig((WeightedRepresentation("inexistente", 1.0),))
        with self.assertRaisesRegex(ValueError, "ausentes"):
            HybridIndex.build(self.processed, self.config, missing, FAKE_METHODS)

    def test_synopsis_index_serves_display_fields_of_verified_sample(self):
        search_config = self.write_config("busca_site.json", {"representations": [{"name": "contextual_teste", "weight": 1}]})
        index = CorpusSynopsisIndex.load(self.processed, self.root / "raw", self.config, search_config, FAKE_METHODS)
        movie_id = index.rank("robôs dominam o planeta")[0][0]
        self.assertEqual(index.movie(movie_id)["id"], movie_id)
        self.assertEqual(
            set(index.movie(movie_id)),
            {"id", "title", "original_title", "overview", "poster_path", "release_date", "vote_average", "vote_count", "genre_ids"},
        )
        with self.assertRaisesRegex(ValueError, "sem dados de exibição"):
            CorpusSynopsisIndex(self.hybrid(), {})

    def test_pure_metrics(self):
        self.assertEqual(purity([1, 1, 2, 2], [0, 0, 0, 1]), 0.75)
        self.assertEqual(genre_agreement(frozenset({18}), [frozenset({18, 35}), frozenset({878})]), 0.5)
        self.assertEqual(reciprocal_rank(4), 0.25)
        self.assertEqual(reciprocal_rank(None), 0.0)
        self.assertAlmostEqual(average_precision([1, 3, None]), (1 / 1 + 2 / 3) / 3)
        self.assertEqual(average_precision([None, None]), 0.0)
        self.assertEqual(precision_at_k([1, 4, 6, None], 5), 0.4)


if __name__ == "__main__":
    unittest.main()
