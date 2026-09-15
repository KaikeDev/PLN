"""Verificação de integridade das pastas da Etapa 1, sem depender do código que as produziu."""

from pathlib import Path

from app.shared.artifacts import read_jsonl, sha256
from app.shared.manifest import read_manifest, require_plain_filename, verify_hashes

RESPONSES_FOLDER = "responses"


def verify_raw(raw: Path) -> dict:
    """Confere os hashes da coleta (filmes, respostas e artefatos) e devolve o manifesto bruto."""
    manifest = read_manifest(raw)
    if sha256(raw / "movies.jsonl") != manifest["movies_sha256"]:
        raise ValueError("movies.jsonl diverge do hash da coleta")
    for item in manifest["requests"]:
        if item["status"] == "ok" and sha256(raw / _response_path(item["file"])) != item["sha256"]:
            raise ValueError(f"Resposta original alterada: {item['file']}")
    for filename, expected in manifest.get("artifact_sha256", {}).items():
        if sha256(raw / require_plain_filename(filename)) != expected:
            raise ValueError(f"Arquivo da coleta alterado: {filename}")
    return manifest


def verify_processed(output: Path) -> dict:
    """Confere os hashes da pasta processada e o alinhamento dos IDs entre etapas e metadados."""
    manifest = read_manifest(output)
    verify_hashes(output, manifest["files"])
    stages = [read_jsonl(output / require_plain_filename(filename)) for filename in manifest["stages"]]
    ids = [row["id"] for row in stages[0]]
    if len(ids) != len(set(ids)):
        raise ValueError("IDs duplicados")
    if any([row["id"] for row in stage] != ids for stage in stages):
        raise ValueError("IDs desalinhados entre as etapas")
    if [row["id"] for row in read_jsonl(output / "metadata.jsonl")] != ids:
        raise ValueError("Metadados desalinhados")
    return {"status": "ok", "movies": len(ids), "stages": len(stages), "files_verified": len(manifest["files"])}


def _response_path(filename: str) -> str:
    folder, _, name = filename.partition("/")
    if folder != RESPONSES_FOLDER:
        raise ValueError(f"Nome de arquivo inválido no manifesto: {filename!r}")
    return f"{RESPONSES_FOLDER}/{require_plain_filename(name)}"
