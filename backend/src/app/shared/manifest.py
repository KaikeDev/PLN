"""Verificação de integridade das pastas de saída a partir do manifesto.

O manifesto lista cada arquivo gerado e o seu SHA-256. A verificação recusa nomes com caminho, para
que um manifesto adulterado não aponte para fora da pasta, e detecta qualquer alteração de conteúdo.
O hash não é assinatura: não impede a alteração conjunta de um arquivo e do manifesto.
"""

from pathlib import Path

from app.shared.artifacts import read_json_object, sha256

MANIFEST_NAME = "manifest.json"


def hash_files(folder: Path) -> dict[str, str]:
    """SHA-256 de cada arquivo direto de `folder`, em ordem alfabética."""
    return {path.name: sha256(path) for path in sorted(folder.iterdir()) if path.is_file()}


def require_plain_filename(filename: str, where: str = "manifesto") -> str:
    """Garante que `filename` é um nome simples, sem diretórios nem referência a pastas superiores."""
    if not isinstance(filename, str) or Path(filename).name != filename or filename in {"", ".", ".."}:
        raise ValueError(f"Nome de arquivo inválido no {where}: {filename!r}")
    return filename


def read_manifest(folder: Path) -> dict:
    """Lê o manifesto de `folder`."""
    return read_json_object(folder / MANIFEST_NAME)


def verify_hashes(folder: Path, expected: dict[str, str]) -> None:
    """Confere o SHA-256 de cada arquivo listado; falha no primeiro nome inválido ou hash divergente."""
    for filename, digest in expected.items():
        require_plain_filename(filename)
        if sha256(folder / filename) != digest:
            raise ValueError(f"Hash divergente: {filename}")
