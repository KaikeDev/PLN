"""Relatório Markdown do processamento, preenchido a partir de `templates/report.md`.

O texto fixo fica no template; este módulo só formata números e monta as linhas das tabelas.
"""

import json
from collections.abc import Iterable
from importlib.resources import files
from string import Template

REPRESENTATION_LABELS = (
    ("original", "Original"),
    ("normalized_without_punctuation", "Normalizada sem pontuação"),
    ("filtered", "Sem stopwords"),
)


def render_report(stats: dict, collection: dict, examples: list[dict]) -> str:
    """Relatório com o estado da coleta, a comparação das representações, os recortes e os exemplos."""
    template = Template(files("app.corpus").joinpath("templates/report.md").read_text(encoding="utf-8"))
    return template.substitute(
        status=collection["status"],
        records_received=collection["records_received"],
        unique_movies=stats["unique_movies"],
        duplicates_removed=collection["duplicates_removed"],
        valid_overviews=stats["valid_overviews"],
        missing_overviews=stats["missing_overviews"],
        missing_overviews_percent=f"{stats['missing_overviews_percent']:.2f}",
        mean_characters=f"{stats['mean_characters_original']:.2f}",
        median_characters=f"{stats['median_characters_original']:.2f}",
        changed_by_cleaning=stats["changed_by_cleaning"],
        representation_rows=_rows(_representation_row(label, stats[key]) for key, label in REPRESENTATION_LABELS),
        slice_rows=_rows(_slice_row(label, value) for label, value in stats["slices"].items()),
        examples="".join(_example(item) for item in examples),
    )


def _rows(rows: Iterable[str]) -> str:
    return "".join(f"\n{row}" for row in rows)


def _representation_row(label: str, row: dict) -> str:
    return (
        f"| {label} | {row['tokens']} | {row['types']} | {row['type_token_ratio']:.4f} "
        f"| {row['mean_tokens']:.2f} | {row['median_tokens']:.2f} |"
    )


def _slice_row(label: str, value: dict) -> str:
    return f"| {label} | {value['movies']} | {value['valid_overviews']} | {value['filtered']['tokens']} | {value['filtered']['types']} |"


def _example(item: dict) -> str:
    return f"### Filme {item['id']}\n\n```json\n{json.dumps(item, ensure_ascii=False, indent=2)}\n```\n\n"
