"""Serialização determinística e identificação dos arquivos gerados pelos pipelines.

Todo arquivo de evidência é JSON (indentado) ou JSONL (uma linha por registro), em UTF-8, sem
escapar caracteres acentuados e sempre com quebra de linha LF. Assim, as mesmas entradas geram os
mesmos bytes em qualquer sistema operacional.
"""

import hashlib
import json
from pathlib import Path

SOURCE_SUFFIXES = frozenset({".py", ".md"})


def json_text(value: object) -> str:
    """Texto JSON indentado e terminado por quebra de linha."""
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def jsonl_text(rows: list[dict]) -> str:
    """Texto JSONL: um objeto compacto por linha."""
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def write_text(path: Path, content: str) -> None:
    """Grava texto UTF-8 com quebras LF, sem a tradução para CRLF que o Windows aplicaria."""
    path.write_text(content, encoding="utf-8", newline="\n")


def write_json(path: Path, value: object) -> None:
    """Grava `value` como JSON em `path`."""
    write_text(path, json_text(value))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    """Grava `rows` como JSONL em `path`."""
    write_text(path, jsonl_text(rows))


def read_json(path: Path) -> object:
    """Lê um arquivo JSON em UTF-8."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_object(path: Path) -> dict:
    """Lê um arquivo JSON cujo valor de topo deve ser um objeto."""
    value = read_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} deve conter um objeto JSON")
    return value


def read_json_array(path: Path) -> list:
    """Lê um arquivo JSON cujo valor de topo deve ser uma lista."""
    value = read_json(path)
    if not isinstance(value, list):
        raise ValueError(f"{path.name} deve conter uma lista JSON")
    return value


def read_jsonl(path: Path) -> list[dict]:
    """Lê um arquivo JSONL, ignorando linhas em branco."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    """Hash SHA-256 hexadecimal do conteúdo de `path`."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_identity() -> dict:
    """Hashes do código e dos templates do pacote `app`, para identificar a versão que gerou uma saída."""
    root = Path(__file__).resolve().parents[1]
    files = sorted(path for path in root.rglob("*") if path.suffix in SOURCE_SUFFIXES and "__pycache__" not in path.parts)
    return {"source_sha256": {path.relative_to(root).as_posix(): sha256(path) for path in files}}


def create_output(path: Path) -> None:
    """Cria a pasta de saída; falha se ela já existir, para nunca substituir uma execução anterior."""
    path.mkdir(parents=True, exist_ok=False)
