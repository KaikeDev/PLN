"""Casos controlados: sinopses e um Jev falso escritos para o teste, sem rede nem chave; não são filmes nem respostas reais."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.classification.jev.config import draw_sample, load_config
from app.classification.jev.pipeline import run, verify
from app.classification.jev.ports import Question
from app.classification.jev.responses import validate_response
from app.classification.jev.typesafe_client import normalize_response
from app.corpus.collect import collect
from app.corpus.process import process
from app.representations.corpus import ProcessedCorpus
from app.settings import Settings
from app.shared.artifacts import read_json_object, read_jsonl, write_json

DRAMA = [
    (1, "Família em crise", "Uma família enfrenta o luto e reconstrói a vida depois da perda do pai."),
    (2, "Luto na cidade", "Depois da perda da mãe, uma família em luto tenta reconstruir a vida."),
    (3, "Amor e perda", "Um casal enfrenta a perda do filho e o luto da família."),
    (4, "Recomeço", "Uma mulher reconstrói a vida em outra cidade depois da perda do emprego."),
    (5, "Herança", "Irmãos disputam a herança e revivem o luto da família."),
]
SCIFI = [
    (6, "Programador preso", "Um programador descobre que vive conectado a um sistema artificial de computadores."),
    (7, "Rede artificial", "Um sistema artificial de computadores controla a mente das pessoas."),
    (8, "Robôs do futuro", "No futuro, robôs dominam o planeta e as pessoas."),
    (9, "Nave perdida", "A tripulação de uma nave espacial perdida enfrenta um sistema artificial."),
    (10, "Colônia", "Robôs constroem uma colônia em uma nave espacial."),
]
BOTH = [
    (11, "Luto artificial", "Após a perda do filho, uma família recria o menino com um sistema artificial."),
    (12, "Robô da família", "Um robô cuida de uma família em luto depois da perda da avó."),
]
WORDS = {"drama": ("luto", "família", "perda", "vida"), "ficcao_cientifica": ("robô", "sistema", "nave", "computador", "artificial")}
GENRES = [
    {"id": 18, "key": "drama", "description": "Drama: conflitos pessoais e familiares.", "question": "Este filme é um drama?"},
    {
        "id": 878,
        "key": "ficcao_cientifica",
        "description": "Ficção científica: tecnologia e futuro.",
        "question": "Este filme é de ficção científica?",
    },
]
CONFIG = {
    "stage": "02_clean.jsonl",
    "sample_per_genre": 2,
    "multi_genre_sample": 1,
    "random_state": 42,
    "threshold": 0.5,
    "request_interval_seconds": 0.2,
    "choice_question": "Qual é o gênero principal do filme?",
    "genres": GENRES,
    "baseline": {"stage": "06_without_stopwords.jsonl", "min_df": 1, "c": 1.0},
}


def fetch(endpoint, **params):
    if endpoint == "/genre/movie/list":
        return {"genres": [{"id": 18, "name": "Drama"}, {"id": 878, "name": "Ficção científica"}]}
    genre = int(params["with_genres"])
    own = DRAMA if genre == 18 else SCIFI
    results = [{"id": i, "title": title, "overview": text, "genre_ids": [genre]} for i, title, text in own]
    results += [{"id": i, "title": title, "overview": text, "genre_ids": [18, 878]} for i, title, text in BOTH]
    return {"page": 1, "total_pages": 1, "results": results}


class FakeJev:
    """Decide pelo número de palavras de cada gênero. `fail_at` e `invalid_at` estragam a chamada de número indicado (a partir de 0)."""

    def __init__(self, fail_at=None, invalid_at=None):
        self.fail_at = fail_at
        self.invalid_at = invalid_at
        self.states = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def decide(self, state, questions):
        call = len(self.states)
        self.states.append(state)
        if call == self.fail_at:
            raise RuntimeError("serviço indisponível")
        text = state.lower()
        counts = {key: sum(text.count(word) for word in words) for key, words in WORDS.items()}
        total = sum(counts.values()) or 1
        choice = "outro" if call == self.invalid_at else max(counts, key=counts.get)
        return {
            "model": "jev-teste",
            "usage": {"input_tokens": 10, "output_tokens": 2},
            "answers": {
                "genero": {
                    "type": "choice",
                    "choice": choice,
                    "probabilities": {k: v / total for k, v in counts.items()},
                    "confidence": 0.9,
                },
                **{f"e_{key}": {"type": "noul", "noul": 0.9 if count else 0.1} for key, count in counts.items()},
            },
        }


def never_called():
    raise AssertionError("O cliente do Jev não deveria ser aberto")


class JevTests(unittest.TestCase):
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
        stopwords.write_text("a\no\nde\nda\ndo\num\numa\ne\nem\nas\nque\n", encoding="utf-8")
        collect(cls.root / "coleta.json", cls.root / "raw", fetch)
        cls.processed = cls.root / "processed"
        process(cls.root / "raw", cls.processed, stopwords)
        cls.config = cls.write_config("jev.json", CONFIG)
        cls.fake = FakeJev()
        cls.pauses = []
        cls.output = cls.root / "jev"
        cls.result = run(cls.processed, cls.output, cls.config, lambda: cls.fake, sleep=cls.pauses.append)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def write_config(cls, name, value):
        path = cls.root / name
        write_json(path, value)
        return path

    def read(self, output, filename):
        return json.loads((output / filename).read_text(encoding="utf-8"))

    def test_run_writes_verified_outputs_without_overwrite(self):
        self.assertEqual(verify(self.output), {"status": "ok", "films": 5, "files_verified": 7})
        self.assertEqual(self.result["api_calls"], 5)
        self.assertEqual(len(self.fake.states), 5)
        self.assertEqual(self.pauses, [0.2] * 4)
        with self.assertRaises(FileExistsError):
            run(self.processed, self.output, self.config, never_called)

    def test_sample_is_stratified_and_reproducible(self):
        sample = self.read(self.output, "sample.json")
        golds = sorted(tuple(row["gold"]) for row in sample)
        self.assertEqual(golds, [("drama",), ("drama",), ("drama", "ficcao_cientifica"), ("ficcao_cientifica",), ("ficcao_cientifica",)])
        corpus, config = ProcessedCorpus.load(self.processed), load_config(self.config)
        self.assertEqual([row["id"] for row in sample], [document.id for document in draw_sample(corpus, config)])

    def test_questions_are_one_choice_and_one_noul_per_genre(self):
        questions = self.read(self.output, "questions.json")
        self.assertEqual(list(questions), ["genero", "e_drama", "e_ficcao_cientifica"])
        self.assertEqual(questions["genero"]["kind"], "choice")
        self.assertEqual([key for key, _ in questions["genero"]["options"]], ["drama", "ficcao_cientifica"])

    def test_metrics_compare_both_methods_on_same_films(self):
        metrics = self.read(self.output, "metrics.json")
        self.assertEqual((metrics["evaluated"], metrics["failed"], metrics["single_genre"]), (5, 0, 4))
        jev = metrics["methods"]["jev"]
        self.assertEqual(jev["choice"]["hit_rate"], 1.0)
        self.assertEqual(jev["labels"]["exact_match"], 1.0)
        self.assertEqual(jev["choice"]["confusion"]["matrix"], [[2, 0], [0, 2]])
        baseline = metrics["methods"]["tfidf_logreg"]
        self.assertEqual(set(baseline), {"choice", "labels"})
        self.assertEqual(metrics["jev_consistency"]["choice_is_top_noul"], 1.0)
        for row in read_jsonl(self.output / "predictions.jsonl"):
            self.assertIn(row["tfidf_logreg"]["choice"], {"drama", "ficcao_cientifica"})
            self.assertAlmostEqual(sum(row["tfidf_logreg"]["choice_probabilities"].values()), 1.0, places=4)

    def test_report_is_generated_from_results(self):
        report = (self.output / "report.md").read_text(encoding="utf-8")
        self.assertIn("# Classificação de gênero com o Jev", report)
        self.assertIn("`jev-teste`", report)
        self.assertIn("| Ficção científica |", report)
        self.assertNotIn("## Falhas do Jev", report)

    def test_reuse_makes_no_calls_and_reproduces_content(self):
        again = self.root / "reuso"
        result = run(self.processed, again, self.config, never_called, reuse=self.output)
        self.assertEqual(result["api_calls"], 0)
        self.assertEqual(read_json_object(again / "manifest.json")["reused_responses"], 5)
        for filename in read_json_object(self.output / "manifest.json")["files"]:
            self.assertEqual((again / filename).read_bytes(), (self.output / filename).read_bytes(), filename)

    def test_reuse_requires_same_questions(self):
        changed = self.write_config("outra_pergunta.json", {**CONFIG, "choice_question": "Qual é o gênero?"})
        with self.assertRaisesRegex(ValueError, "outras perguntas"):
            run(self.processed, self.root / "outra", changed, never_called, reuse=self.output)
        self.assertFalse((self.root / "outra").exists())

    def test_first_failure_aborts_without_output(self):
        output = self.root / "falha_inicial"
        with self.assertRaisesRegex(ValueError, "primeira chamada"):
            run(self.processed, output, self.config, lambda: FakeJev(fail_at=0), sleep=lambda _: None)
        self.assertFalse(output.exists())

    def test_later_failures_are_recorded_and_excluded(self):
        output = self.root / "falhas"
        run(self.processed, output, self.config, lambda: FakeJev(fail_at=2, invalid_at=3), sleep=lambda _: None)
        responses = read_jsonl(output / "responses.jsonl")
        self.assertIn("serviço indisponível", responses[2]["error"])
        self.assertIn("opção fora das enviadas", responses[3]["error"])
        metrics = self.read(output, "metrics.json")
        self.assertEqual((metrics["evaluated"], metrics["failed"]), (3, 2))
        self.assertIn("## Falhas do Jev", (output / "report.md").read_text(encoding="utf-8"))
        partial = run(self.processed, self.root / "retomada", self.config, lambda: FakeJev(), reuse=output, sleep=lambda _: None)
        self.assertEqual(partial["api_calls"], 2)

    def test_response_validation_rejects_untrusted_values(self):
        questions = {"genero": Question("choice", "?", (("a", "A"), ("b", "B"))), "e_a": Question("noul", "?")}
        valid = {
            "answers": {
                "genero": {"type": "choice", "choice": "a", "probabilities": {"a": 0.7, "b": 0.3}},
                "e_a": {"type": "noul", "noul": 0.8},
            }
        }
        self.assertEqual(validate_response(valid, questions)["answers"]["genero"]["confidence"], None)
        broken = [
            {"answers": {"genero": valid["answers"]["genero"]}},
            {"answers": {**valid["answers"], "e_a": {"type": "noul", "noul": 1.5}}},
            {"answers": {**valid["answers"], "e_a": {"type": "noul", "noul": True}}},
            {"answers": {**valid["answers"], "e_a": {"type": "choice", "choice": "a"}}},
            {"answers": {**valid["answers"], "genero": {"type": "choice", "choice": "a", "probabilities": {"c": 1.0}}}},
            {**valid, "usage": {"input_tokens": -1}},
            [],
        ]
        for response in broken:
            with self.subTest(response=response), self.assertRaises(ValueError):
                validate_response(response, questions)

    def test_config_rejects_invalid_values(self):
        cases = {
            "desconhecido": {**CONFIG, "extra": 1},
            "etapa": {**CONFIG, "stage": "04_tokens.jsonl"},
            "referencia": {**CONFIG, "baseline": {**CONFIG["baseline"], "stage": "02_clean.jsonl"}},
            "repetido": {**CONFIG, "genres": [GENRES[0], {**GENRES[1], "key": "drama"}]},
            "chave": {**CONFIG, "genres": [GENRES[0], {**GENRES[1], "key": "../x"}]},
            "limiar": {**CONFIG, "threshold": 1},
            "unico": {**CONFIG, "genres": [GENRES[0]]},
        }
        for name, value in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                load_config(self.write_config(f"invalida_{name}.json", value))

    def test_sample_needs_known_genres_and_training_films(self):
        corpus = ProcessedCorpus.load(self.processed)
        unknown = load_config(self.write_config("genero_ausente.json", {**CONFIG, "genres": [GENRES[0], {**GENRES[1], "id": 27}]}))
        with self.assertRaisesRegex(ValueError, "ausentes"):
            draw_sample(corpus, unknown)
        greedy = load_config(self.write_config("amostra_grande.json", {**CONFIG, "sample_per_genre": 5}))
        with self.assertRaisesRegex(ValueError, "treino"):
            draw_sample(corpus, greedy)

    def test_tampering_is_rejected(self):
        output = self.root / "adulterada"
        run(self.processed, output, self.config, lambda: FakeJev(), sleep=lambda _: None)
        path = output / "metrics.json"
        path.write_text(path.read_text(encoding="utf-8").replace('"hit_rate": 1.0', '"hit_rate": 0.5', 1), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Hash divergente"):
            verify(output)

    def test_sdk_response_is_converted_to_port_format(self):
        questions = {"genero": Question("choice", "?", (("a", "A"), ("b", "B"))), "e_a": Question("noul", "?")}
        response = SimpleNamespace(
            answers={
                "genero": SimpleNamespace(choice="a", probabilities={"a": 0.75, "b": 0.25}, confidence=0.5),
                "e_a": SimpleNamespace(noul=1),
            },
            model="jev-1.13.0",
            usage=SimpleNamespace(input_tokens=12, output_tokens=3),
        )
        converted = normalize_response(response, questions)
        self.assertEqual(converted["answers"]["e_a"], {"type": "noul", "noul": 1.0})
        self.assertEqual(validate_response(converted, questions)["usage"], {"input_tokens": 12, "output_tokens": 3})
        by_kind = SimpleNamespace(choices={"genero": response.answers["genero"]}, nouls={"e_a": response.answers["e_a"]})
        self.assertEqual(normalize_response(by_kind, questions)["answers"]["genero"]["choice"], "a")

    def test_api_key_is_required_and_secret(self):
        with self.assertRaisesRegex(ValueError, "TYPESAFE_API_KEY"):
            Settings(_env_file=None, typesafe_api_key=None).require_typesafe_key()
        settings = Settings(_env_file=None, typesafe_api_key=" chave-de-teste ")
        self.assertEqual(settings.require_typesafe_key(), "chave-de-teste")
        self.assertNotIn("chave-de-teste", repr(settings))


if __name__ == "__main__":
    unittest.main()
