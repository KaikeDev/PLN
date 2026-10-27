"""Exemplos gravados do RAG para o site: respostas de uma avaliação verificada, no mesmo formato de `/pergunta`.

Aparecem na aba "Perguntar" como entradas e saídas de exemplo e quando a cota do LLM acaba. Os dados de
exibição dos filmes citados vêm da coleta da amostra.
"""

from collections.abc import Sequence
from pathlib import Path

from app.rag.pipeline import verify
from app.search.synopsis_index import SUMMARY_FIELDS
from app.shared.artifacts import read_jsonl, write_json


def export_examples(evaluation: Path, movies_path: Path, output: Path, ids: Sequence[str]) -> dict:
    """Grava as respostas `ids` da avaliação em `output` (que pode ser substituído: é derivado e versionado)."""
    verify(evaluation)
    rows = {row["id"]: row for row in read_jsonl(evaluation / "predictions.jsonl")}
    if missing := [question_id for question_id in ids if question_id not in rows]:
        raise ValueError(f"Perguntas ausentes da avaliação: {missing}")
    if failed := [question_id for question_id in ids if rows[question_id]["falha"]]:
        raise ValueError(f"Perguntas sem resposta na avaliação: {failed}")
    movies = {row["id"]: {field: row.get(field) for field in SUMMARY_FIELDS} for row in read_jsonl(movies_path)}
    examples = [example(rows[question_id], movies) for question_id in ids]
    write_json(output, {"avaliacao": evaluation.name, "exemplos": examples})
    return {"exemplos": len(examples), "output": str(output)}


def example(row: dict, movies: dict[int, dict]) -> dict:
    return {
        "pergunta": row["pergunta"],
        "resposta": row["resposta"],
        "contexto_suficiente": row["contexto_suficiente"],
        "filmes_citados": [{"id": item["id"], "motivo": item["motivo"], "filme": movies.get(item["id"])} for item in row["citados"]],
        "contexto": [
            {
                "id": item["id"],
                "titulo": item["titulo"],
                "pontuacao": item["pontuacao"],
                "criticas": item["criticas_do_filme"],
                "trechos": item["trechos"],
            }
            for item in row["contexto"]
        ],
        "provedor": row["provedor"],
        "modelo": row["modelo"],
        "latencia_ms": None,
        "citacoes_removidas": len(row["inventadas"]),
        "exemplo_gravado": True,
    }
