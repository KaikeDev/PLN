"""`frontend/dados/resultados.json` bate com os arquivos de origem em `data/` e `config/` (spec 05, ADR 0034).

A página "Sobre o projeto" não tem número digitado à mão: tudo vem desse JSON, gerado por
`docs/entregas/unidade-4/coletar_resultados.py`. O teste roda o coletor de novo e compara. O catálogo do site fica fora
do Git; sem ele, o coletor mantém o valor do JSON, e o teste só confere que é um inteiro.
"""

import importlib.util
import json
import re
import unittest

from app.settings import REPOSITORY_DIR

COLLECTOR = REPOSITORY_DIR / "docs" / "entregas" / "unidade-4" / "coletar_resultados.py"
RESULTS = REPOSITORY_DIR / "frontend" / "dados" / "resultados.json"


def load_collector():
    spec = importlib.util.spec_from_file_location("coletar_resultados", COLLECTOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResultsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.collector = load_collector()
        cls.saved = json.loads(RESULTS.read_text(encoding="utf-8"))

    def test_json_matches_sources(self) -> None:
        fresh = self.collector.collect(self.saved)
        if not self.collector.CATALOG.exists():
            self.assertIsInstance(self.saved["dados"]["catalogo_do_site"], int)
        self.assertEqual(fresh, self.saved, "Rode python docs/entregas/unidade-4/coletar_resultados.py e commite o JSON")

    def test_board_matches_document(self) -> None:
        document = (REPOSITORY_DIR / "docs" / "9-tecnicas-avancadas.md").read_text(encoding="utf-8")
        self.assertEqual(len(self.saved["quadro"]), 7)
        for row in self.saved["quadro"]:
            self.assertIn(row["justificativa"], document)
            self.assertIn(row["utilizada"], {"Sim", "Não", "Parcial"})

    def test_pages_only_reference_existing_numbers(self) -> None:
        for page in ("index.html", "sobre.html"):
            html = (REPOSITORY_DIR / "frontend" / page).read_text(encoding="utf-8")
            for path in re.findall(r'data-resultado="([^"]+)"', html):
                value = self.saved
                for key in path.split("."):
                    self.assertIsInstance(value, dict, f"{page}: {path}")
                    self.assertIn(key, value, f"{page}: {path}")
                    value = value[key]
                self.assertIsInstance(value, (int, float), f"{page}: {path}")


if __name__ == "__main__":
    unittest.main()
