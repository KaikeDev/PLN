"""Representações densas lidas de uma pasta da Etapa 2 já verificada, em vez de recalculadas (ADR 0018).

Só as densas são reaproveitadas: as lexicais custam milissegundos e precisam ser reajustadas dentro de cada
dobra da classificação. A pasta só é aceita se os hashes conferem, se foi gerada a partir do mesmo corpus
processado e se a especificação da representação (método, etapa, modelo e revisão) é idêntica. Os vetores
guardados têm seis casas decimais; por isso um resultado com reaproveitamento pode diferir, na última casa,
do mesmo resultado com os vetores recalculados.
"""

from dataclasses import asdict
from pathlib import Path

import numpy as np

from app.representations.config import RepresentationSpec
from app.representations.corpus import ProcessedCorpus
from app.representations.metrics import rounded
from app.representations.pipeline import verify
from app.representations.space import Encoded, Representation
from app.shared.artifacts import read_json_array, read_json_object, read_jsonl, sha256
from app.shared.manifest import MANIFEST_NAME, read_manifest


class StoredDenseSpace(Representation):
    """Matriz densa lida de arquivo, com a família e os parâmetros registrados na síntese da Etapa 2.

    Serve a análises sobre as sinopses do corpus. Não codifica consultas, porque o modelo que gerou os
    vetores não é carregado.
    """

    def __init__(
        self, spec: RepresentationSpec, ids: tuple[int, ...], matrix: np.ndarray, family: str, learned: bool, parameters: int | None
    ):
        super().__init__(spec, ids, matrix)
        self.family, self.learned, self._parameters = family, learned, parameters

    def encode(self, text: str, corpus: ProcessedCorpus) -> Encoded:
        raise ValueError(f"{self.spec.name}: vetores lidos de arquivo não codificam consultas; reconstrua a representação")

    def document(self, row: int) -> Encoded:
        return Encoded(self.unit[row : row + 1])

    def export(self) -> dict[str, list | dict]:
        rows = [
            {"id": movie_id, "vector": [rounded(value) for value in row]}
            for movie_id, row in zip(self.ids, self.matrix.tolist(), strict=True)
        ]
        return {"embeddings.jsonl": rows}

    def parameters(self) -> int | None:
        return self._parameters


class StoredVectors:
    """Pasta da Etapa 2 verificada e alinhada ao corpus; entrega as representações densas guardadas."""

    def __init__(self, folder: Path, corpus: ProcessedCorpus):
        verify(folder)
        if read_manifest(folder).get("source_processed_manifest_sha256") != corpus.manifest_sha256:
            raise ValueError("A pasta de vetores foi gerada a partir de outro corpus processado")
        if tuple(document["id"] for document in read_json_array(folder / "documents.json")) != corpus.ids:
            raise ValueError("A pasta de vetores não está alinhada às sinopses do corpus processado")
        self.folder, self.corpus = folder, corpus
        self.manifest_sha256 = sha256(folder / MANIFEST_NAME)
        self.specs = {item["name"]: item for item in read_json_object(folder / "config.json")["representations"]}
        synthesis = folder / "synthesis.json"
        self.synthesis = read_json_object(synthesis) if synthesis.exists() else {}

    def load(self, spec: RepresentationSpec) -> StoredDenseSpace | None:
        """Representação densa guardada com especificação idêntica; None quando não há, e então ela é recalculada."""
        path = self.folder / f"{spec.name}.embeddings.jsonl"
        if self.specs.get(spec.name) != asdict(spec) or not path.exists():
            return None
        rows = read_jsonl(path)
        if [row["id"] for row in rows] != list(self.corpus.ids):
            raise ValueError(f"Vetores desalinhados das sinopses: {path.name}")
        info = self.synthesis.get(spec.name, {})
        matrix = np.array([row["vector"] for row in rows], dtype=np.float64)
        return StoredDenseSpace(
            spec, self.corpus.ids, matrix, info.get("family", "dense"), bool(info.get("learned", True)), info.get("parameters")
        )
