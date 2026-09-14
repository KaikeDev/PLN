"""Serialização e identificação dos arquivos da experiência."""
import hashlib
import json
from pathlib import Path


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_identity() -> dict:
    root = Path(__file__).resolve().parents[1]
    return {"source_sha256": {str(p.relative_to(root)): sha256(p) for p in sorted(root.rglob("*.py"))}}


def create_output(path: Path) -> None:
    """Uma execução nunca substitui uma amostra ou transformação anterior."""
    path.mkdir(parents=True, exist_ok=False)
