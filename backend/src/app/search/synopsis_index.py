"""Adaptador da porta `SynopsisIndex`: busca híbrida de `app.representations` sobre a amostra entregue.

A ordenação vem de `HybridIndex`, com as representações e os pesos de `config/busca/busca.json`. Os dados
exibidos de cada filme (título, sinopse, pôster, data, nota, gêneros) vêm de `movies.jsonl` da coleta
bruta, que é verificada e precisa ser a mesma que gerou a pasta processada. Os modelos são carregados
uma vez, na inicialização da API.
"""

from collections.abc import Mapping
from pathlib import Path

from app.corpus.verification import verify_raw
from app.representations.methods import METHODS, Method
from app.search.hybrid import HybridIndex, load_search_config
from app.shared.artifacts import read_json_object, read_jsonl, sha256

SUMMARY_FIELDS = ("id", "title", "original_title", "overview", "poster_path", "release_date", "vote_average", "vote_count", "genre_ids")


class CorpusSynopsisIndex:
    """Sinopses da amostra ordenadas pela busca híbrida, com os campos de resumo do TMDB."""

    def __init__(self, hybrid: HybridIndex, movies: dict[int, dict]) -> None:
        if missing := sorted(set(hybrid.corpus.ids) - movies.keys()):
            raise ValueError(f"Filmes do corpus sem dados de exibição: {missing[:5]}")
        self._hybrid = hybrid
        self._movies = movies

    @classmethod
    def load(
        cls, processed: Path, raw: Path, vectors_config: Path, search_config: Path, methods: Mapping[str, Method] = METHODS
    ) -> CorpusSynopsisIndex:
        """Verifica as duas pastas, confere que a processada veio da bruta e constrói o índice; `methods` substitui os modelos em testes."""
        verify_raw(raw)
        if read_json_object(processed / "manifest.json").get("source_movies_sha256") != sha256(raw / "movies.jsonl"):
            raise ValueError("A pasta processada não foi gerada a partir desta coleta bruta")
        movies = {row["id"]: {field: row.get(field) for field in SUMMARY_FIELDS} for row in read_jsonl(raw / "movies.jsonl")}
        return cls(HybridIndex.build(processed, vectors_config, load_search_config(search_config), methods), movies)

    def rank(self, text: str) -> list[tuple[int, float]]:
        return self._hybrid.rank(text)

    def movie(self, movie_id: int) -> dict:
        return dict(self._movies[movie_id])

    @property
    def hybrid(self) -> HybridIndex:
        """Índice híbrido, para reaproveitar as representações já construídas (o classificador da tela usa uma delas)."""
        return self._hybrid
