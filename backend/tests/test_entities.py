"""Frases do notebook da Aula 9 e sinopses escritas para o teste, com créditos falsos; sem rede."""

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app.corpus.collect import collect as collect_movies
from app.corpus.process import process as process_movies
from app.entities.evaluation import name_words, summarize
from app.shared.artifacts import read_json_object, write_json, write_jsonl

HAS_SPACY = importlib.util.find_spec("spacy") is not None and importlib.util.find_spec("pt_core_news_sm") is not None
SYNOPSES = [
    (1, "Curie", "Marie Curie nasceu em Varsóvia e estudou em Paris. Ela trabalhou na Universidade de Paris."),
    (2, "Fusão", "A Microsoft adquiriu a Activision Blizzard. Pierre Curie colaborou com Marie Curie em diversos experimentos."),
    (3, "Prisão", "Andy Dufresne é condenado por um crime que nunca cometeu. Na prisão, Andy conhece Red."),
]
CREDITS = {
    1: [{"name": "Atriz Um", "character": "Marie Curie"}],
    2: [{"name": "Ator Dois", "character": "Pierre Curie"}, {"name": "Atriz Três", "character": "Marie Curie"}],
    3: [{"name": "Ator Quatro", "character": "Andy Dufresne"}, {"name": "Ator Cinco", "character": "Ellis 'Red' Redding"}],
}


def tmdb(endpoint, **params):
    if endpoint == "/genre/movie/list":
        return {"genres": [{"id": 18, "name": "Drama"}]}
    return {"page": 1, "total_pages": 1, "results": [{"id": i, "title": t, "overview": o, "genre_ids": [18]} for i, t, o in SYNOPSES]}


class CreditsMatchTests(unittest.TestCase):
    def test_name_words_drop_generic_and_short_words(self) -> None:
        words = name_words([{"name": "Tom Hanks", "character": "Young Forrest Gump"}, {"name": "Al Li", "character": "Mrs. Gump"}])
        self.assertEqual(words, frozenset({"Tom", "Hanks", "Forrest", "Gump"}))
        self.assertIn("Bill", name_words([{"name": "Tom Cruise", "character": "Dr. William 'Bill' Harford"}]))

    def test_summary_counts_recall_and_estimated_precision(self) -> None:
        checks = [
            {
                "mencoes_creditadas": [{"categoria": "PER"}, {"categoria": "LOC"}, {"categoria": None}, {"categoria": "PER"}],
                "pessoas_previstas": [{"confirmada": True}, {"confirmada": False}],
            },
            {"mencoes_creditadas": [], "pessoas_previstas": []},
        ]
        summary = summarize(checks)
        self.assertEqual((summary["mencoes_creditadas"], summary["filmes_com_mencao"]), (4, 1))
        self.assertEqual((summary["revocacao_per"], summary["revocacao_qualquer_categoria"]), (0.5, 0.75))
        self.assertEqual(summary["precisao_estimada_per"], 0.5)
        self.assertEqual(summary["categorias_das_mencoes"], {"LOC": 1, "PER": 2, "nao_reconhecida": 1})


@unittest.skipUnless(HAS_SPACY, "exige o extra entidades (spaCy e pt_core_news_sm)")
class NotebookRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from app.entities.extraction import load_model

        cls.nlp = load_model("pt_core_news_sm")

    def triples(self, text: str, **options) -> list[tuple[str, str, str]]:
        from app.entities.extraction import relations

        return [(t.subject, t.relation, t.object) for t in relations(self.nlp(text), **options)]

    def test_notebook_examples(self) -> None:
        self.assertEqual(
            self.triples("Marie Curie trabalhou na Universidade de Paris."), [("Marie Curie", "trabalhar_em", "Universidade de Paris")]
        )
        self.assertEqual(self.triples("A Microsoft adquiriu a Activision Blizzard."), [("Microsoft", "adquirir", "Activision Blizzard")])
        raw = self.triples("Marie Curie trabalhou na Universidade de Paris.", normalize=False)
        self.assertEqual(raw, [("Marie Curie", "trabalhar_em", "na Universidade de Paris")])

    def test_coordination_inherits_subject_only_when_enabled(self) -> None:
        text = "Marie Curie nasceu em Varsóvia e estudou em Paris."
        self.assertEqual(self.triples(text, coordination=False), [("Marie Curie", "nascer_em", "Varsóvia")])
        self.assertIn(("Marie Curie", "estudar_em", "Paris"), self.triples(text))

    def test_entities_and_dependencies_follow_the_notebook_tables(self) -> None:
        from app.entities.extraction import dependencies, entities

        doc = self.nlp("O pesquisador analisou os dados.")
        rows = dependencies(doc)
        self.assertEqual(
            [(r["token"], r["dependencia"], r["nucleo"]) for r in rows[:3]],
            [("O", "det", "pesquisador"), ("pesquisador", "nsubj", "analisou"), ("analisou", "ROOT", "analisou")],
        )
        found = entities(self.nlp("A Universidade de São Paulo desenvolveu uma parceria com a Microsoft."))
        self.assertEqual(found[-1], {"entidade": "Microsoft", "categoria": "ORG", "inicio": 59, "fim": 68})

    def test_live_extractor_limits(self) -> None:
        from app.entities.live import EntityExtractor

        extractor = EntityExtractor()
        result = extractor.extract("Marie Curie nasceu em Varsóvia.")
        self.assertEqual([(e["entidade"], e["categoria"]) for e in result.entities], [("Marie Curie", "PER"), ("Varsóvia", "LOC")])
        for text in ("", "x" * 2001):
            with self.subTest(size=len(text)), self.assertRaises(ValueError):
                extractor.extract(text)


@unittest.skipUnless(HAS_SPACY, "exige o extra entidades (spaCy e pt_core_news_sm)")
class EntitiesPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from app.entities.pipeline import build

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
        stopwords.write_text("a\no\nde\ne\n", encoding="utf-8")
        collect_movies(root / "coleta.json", root / "raw", tmdb)
        process_movies(root / "raw", root / "movies", stopwords)
        (root / "credits").mkdir()
        write_jsonl(root / "credits" / "credits.jsonl", [{"movie_id": i, "cast": CREDITS[i]} for i, _, _ in SYNOPSES])
        from app.shared.artifacts import sha256

        write_json(
            root / "credits" / "manifest.json", {"movies": 3, "files": {"credits.jsonl": sha256(root / "credits" / "credits.jsonl")}}
        )
        config = {
            "model": "pt_core_news_sm",
            "stage": "02_clean.jsonl",
            "coordination": True,
            "example_ids": [1],
            "review_sample": 3,
            "random_state": 42,
            "top": 5,
        }
        write_json(root / "entidades.json", config)
        cls.output = root / "resultado"
        cls.result = build(root / "movies", root / "credits", cls.output, root / "entidades.json")
        cls.root = root

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_build_extracts_entities_triples_and_checks_credits(self) -> None:
        from app.entities.pipeline import verify

        self.assertEqual(self.result["synopses"], 3)
        statistics = read_json_object(self.output / "statistics.json")
        self.assertGreaterEqual(statistics["triplas_por_regra"].get("coordenacao", 0), 1)
        self.assertGreaterEqual(statistics["sujeitos_pronomes"], 1)
        credits = read_json_object(self.output / "credits_summary.json")
        self.assertGreaterEqual(credits["mencoes_creditadas"], 4)
        self.assertIsNotNone(credits["revocacao_per"])
        examples = json.loads((self.output / "examples.json").read_text(encoding="utf-8"))
        self.assertEqual([example["id"] for example in examples], [1])
        review = json.loads((self.output / "review_sample.json").read_text(encoding="utf-8"))
        self.assertEqual(len(review), 3)
        self.assertTrue(all(row["correta"] is None for row in review))
        self.assertIn("```mermaid", (self.output / "report.md").read_text(encoding="utf-8"))
        self.assertEqual(verify(self.output)["status"], "ok")

    def test_verify_detects_tampering(self) -> None:
        from app.entities.pipeline import verify

        copy = self.root / "adulterado"
        shutil.copytree(self.output, copy)
        (copy / "statistics.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            verify(copy)


if __name__ == "__main__":
    unittest.main()
