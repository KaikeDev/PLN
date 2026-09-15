"""Validadores de arquivos de configuração: dados JSON nunca são tratados como código.

Cada função recebe um valor ainda não confiável e devolve o valor tipado ou levanta `ValueError`
com uma mensagem que identifica o campo. Booleanos não são aceitos onde se espera inteiro.
"""

import json
import re
from collections.abc import Collection
from pathlib import Path

MAX_JSON_BYTES = 1_000_000
NAME_RE = re.compile(r"[a-z0-9_]{1,40}")


def read_config_json(path: Path) -> object:
    """Lê JSON local com limite de tamanho; não usa pickle, eval ou YAML com construtores."""
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError(f"{path.name} excede {MAX_JSON_BYTES} bytes")
    return json.loads(path.read_text(encoding="utf-8"))


def require_object(value: object, where: str, required: Collection[str], optional: Collection[str] = ()) -> dict:
    """Objeto JSON com todos os campos obrigatórios e nenhum campo desconhecido."""
    if not isinstance(value, dict):
        raise ValueError(f"{where} deve ser um objeto JSON")
    if missing := set(required) - value.keys():
        raise ValueError(f"Campos obrigatórios ausentes em {where}: {sorted(missing)}")
    if unknown := value.keys() - set(required) - set(optional):
        raise ValueError(f"Campos desconhecidos em {where}: {sorted(unknown)}")
    return value


def require_name(value: object, where: str) -> str:
    """Identificador seguro para nomes de arquivo: apenas a-z, 0-9 e _, com até 40 caracteres."""
    if not isinstance(value, str) or not NAME_RE.fullmatch(value):
        raise ValueError(f"{where} deve usar apenas a-z, 0-9 e _, com até 40 caracteres")
    return value


def require_int(value: object, where: str, low: int, high: int) -> int:
    """Inteiro (não booleano) no intervalo fechado [low, high]."""
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{where} deve ser inteiro entre {low} e {high}")
    return value


def require_number(value: object, where: str, low: float, high: float) -> float:
    """Número (inteiro ou real, não booleano) no intervalo fechado [low, high]."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not low <= value <= high:
        raise ValueError(f"{where} deve ser número entre {low} e {high}")
    return float(value)


def require_bool(value: object, where: str) -> bool:
    """Booleano JSON."""
    if type(value) is not bool:
        raise ValueError(f"{where} deve ser true ou false")
    return value


def require_ids(value: object, where: str, allow_empty: bool = False) -> tuple[int, ...]:
    """Lista de IDs inteiros positivos, sem repetição e na ordem original."""
    if not isinstance(value, list) or (not value and not allow_empty) or any(type(i) is not int or i <= 0 for i in value):
        raise ValueError(f"{where} deve ser uma lista de IDs inteiros positivos")
    return tuple(dict.fromkeys(value))


def require_unique(values: list[str], message: str) -> None:
    """Falha quando `values` contém repetições."""
    if len(values) != len(set(values)):
        raise ValueError(message)
