"""Preparação da consulta da busca por tema com frases e vocabulário escritos para o teste."""

import unittest

from app.search.query import AccentRestorer, prepare_query, strip_request


class StripRequestTests(unittest.TestCase):
    def test_removes_request_and_film_words(self) -> None:
        cases = {
            "filmes sobre saude mental": "saude mental",
            "quero um filme de ação sobre máquinas": "ação sobre máquinas",
            "me indica algum filme que fale de luto": "luto",
            "um bom filme sobre depressão": "depressão",
            "Filmes com robôs": "robôs",
            "quero ver filmes de terror dos anos 80": "terror dos anos 80",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(strip_request(text), expected)

    def test_keeps_theme_text_and_similar_words(self) -> None:
        for text in ("casa assombrada por espíritos", "diretor perde a filmagem", "programador conectado a um sistema"):
            with self.subTest(text=text):
                self.assertEqual(strip_request(text), text)

    def test_returns_original_when_nothing_would_remain(self) -> None:
        self.assertEqual(strip_request("quero um filme"), "quero um filme")


class AccentRestorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.restorer = AccentRestorer(["saúde", "mental", "música", "musica", "família"])

    def test_restores_unique_accented_form(self) -> None:
        self.assertEqual(self.restorer.restore("saude mental"), "saúde mental")
        self.assertEqual(self.restorer.restore("Familia"), "família")

    def test_keeps_ambiguous_accented_short_and_unknown_words(self) -> None:
        self.assertEqual(self.restorer.restore("musica"), "musica")
        self.assertEqual(self.restorer.restore("a que"), "a que")
        self.assertEqual(self.restorer.restore("saudável"), "saudável")
        self.assertEqual(self.restorer.restore("dragões"), "dragões")

    def test_prepare_query_cleans_then_restores(self) -> None:
        self.assertEqual(prepare_query("filmes sobre saude mental", self.restorer), "saúde mental")
        self.assertEqual(prepare_query("filmes sobre saude mental"), "saude mental")


if __name__ == "__main__":
    unittest.main()
