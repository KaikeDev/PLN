"""Repositório somente leitura da pasta processada na Etapa 1."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.corpus.contracts import TEXT_STAGES, TOKEN_STAGES, StageKey
from app.corpus.transform import representations
from app.corpus.verification import verify_processed
from app.shared.artifacts import read_jsonl, sha256
from app.vectors.config import validate_query_text

GENRE_SLICE_RE = re.compile(r"genre_(\d+)_\d{4}_\d{4}")
MIN_DOCUMENTS = 3


@dataclass(frozen=True)
class Document:
    """Sinopse preenchida do corpus; `genres` são os gêneros dos recortes de coleta que retornaram o filme."""

    id: int
    title: str
    genres: frozenset[int]


class ProcessedCorpus:
    """Isola o formato dos arquivos: as análises dependem de documentos, não de caminhos."""

    def __init__(self, root: Path, documents: tuple[Document, ...], genre_names: dict[int, str], stopwords: frozenset[str]):
        self.root = root
        self.documents = documents
        self.genre_names = genre_names
        self.stopwords = stopwords
        self.ids = tuple(document.id for document in documents)
        self.by_id = {document.id: document for document in documents}
        self._stages: dict[str, list] = {}

    @classmethod
    def load(cls, root: Path) -> ProcessedCorpus:
        """Verifica hashes e alinhamento da pasta processada antes de ler qualquer conteúdo."""
        verify_processed(root)
        memberships = json.loads((root / "memberships.json").read_text(encoding="utf-8"))
        genres = json.loads((root / "genres.json").read_text(encoding="utf-8")).get("genres", [])
        stopwords = json.loads((root / "stopwords_used.json").read_text(encoding="utf-8"))
        documents = tuple(
            Document(
                row["id"],
                row.get("title") or row.get("original_title") or f"Filme {row['id']}",
                _slice_genres(memberships.get(str(row["id"]), [])),
            )
            for row in read_jsonl(root / "metadata.jsonl")
            if not row["overview_missing"]
        )
        if len(documents) < MIN_DOCUMENTS:
            raise ValueError(f"São necessárias ao menos {MIN_DOCUMENTS} sinopses para comparar vetores")
        return cls(root, documents, {genre["id"]: genre["name"] for genre in genres}, frozenset(stopwords))

    @property
    def manifest_sha256(self) -> str:
        return sha256(self.root / "manifest.json")

    def tokens(self, stage: str) -> list[list[str]]:
        """Tokens da etapa escolhida, na ordem de `documents`; lidos uma vez e reutilizados."""
        if stage not in TOKEN_STAGES:
            raise ValueError(f"Etapa não tokenizada: {stage!r}")
        documents = self._read(stage, "tokens")
        if any(not isinstance(doc, list) or not all(isinstance(token, str) for token in doc) for doc in documents):
            raise ValueError(f"{stage} contém tokens que não são texto")
        return documents

    def texts(self, stage: str) -> list[str]:
        """Textos corridos (limpos ou normalizados), para modelos que tokenizam por conta própria."""
        if stage not in TEXT_STAGES:
            raise ValueError(f"Etapa sem texto corrido: {stage!r}")
        documents = self._read(stage, "text")
        if any(not isinstance(doc, str) or not doc.strip() for doc in documents):
            raise ValueError(f"{stage} contém textos vazios para sinopses preenchidas")
        return documents

    def query_tokens(self, text: str, stage_key: StageKey) -> list[str]:
        """Tokens da consulta com exatamente as regras que produziram a etapa tokenizada dos documentos."""
        value = self._prepare_query(text, stage_key)
        if not isinstance(value, list):
            raise ValueError(f"A etapa {stage_key!r} não é tokenizada")
        return value

    def query_text(self, text: str, stage_key: StageKey) -> str:
        """Texto da consulta com exatamente as regras que produziram a etapa de texto corrido dos documentos."""
        value = self._prepare_query(text, stage_key)
        if not isinstance(value, str):
            raise ValueError(f"A etapa {stage_key!r} não é texto corrido")
        return value

    def _prepare_query(self, text: str, stage_key: StageKey) -> object:
        prepared: dict[str, object] = dict(representations(validate_query_text(text), set(self.stopwords)))
        return prepared[stage_key]

    def _read(self, stage: str, field: str) -> list:
        if stage not in self._stages:
            rows = {row["id"]: row[field] for row in read_jsonl(self.root / stage)}
            self._stages[stage] = [rows[movie_id] for movie_id in self.ids]
        return self._stages[stage]

    def genre_name(self, document: Document) -> str | None:
        """Nome do gênero quando o filme veio de um único gênero de coleta; None caso contrário."""
        if len(document.genres) != 1:
            return None
        genre = next(iter(document.genres))
        return self.genre_names.get(genre, str(genre))


def _slice_genres(labels: list[str]) -> frozenset[int]:
    return frozenset(int(match.group(1)) for label in labels if (match := GENRE_SLICE_RE.fullmatch(label)))
