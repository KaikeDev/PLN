"""Conferência das citações antes de mostrar a resposta.

- Um filme em `filmes` que não está no contexto é removido e conta como **citação inventada**.
- Uma marca `[F<id>]` no texto com id fora do contexto também é removida do texto e contada.
- Um filme marcado no texto e ausente de `filmes` é acrescentado, sem motivo, para que o site mostre o cartão.
- Se a resposta dizia que o contexto bastava e nenhuma citação válida sobrou, ela é trocada pela resposta
  padrão "não encontrei": uma resposta sem nenhum filme do contexto não está apoiada nele.
"""

import re
from collections.abc import Collection
from dataclasses import dataclass

CITATION = re.compile(r"\[F(\d+)\]")


@dataclass(frozen=True)
class Cited:
    id: int
    reason: str


@dataclass(frozen=True)
class Grounded:
    """Resposta conferida e o que foi corrigido."""

    answer: str
    cited: tuple[Cited, ...]
    sufficient: bool
    invented: tuple[int, ...]
    added_from_text: tuple[int, ...]
    replaced: bool


def ground(data: dict, context_ids: Collection[int], max_cited: int, no_context_answer: str) -> Grounded:
    """Aplica as regras acima à saída validada do LLM (`resposta`, `filmes`, `contexto_suficiente`)."""
    allowed = set(context_ids)
    invented: list[int] = []
    cited: list[Cited] = []
    for item in data["filmes"]:
        movie_id = int(item["id"])
        if movie_id not in allowed:
            invented.append(movie_id)
        elif all(existing.id != movie_id for existing in cited):
            cited.append(Cited(movie_id, str(item.get("motivo") or "").strip()))

    def keep(match: re.Match[str]) -> str:
        movie_id = int(match.group(1))
        if movie_id in allowed:
            return match.group(0)
        invented.append(movie_id)
        return ""

    answer = " ".join(CITATION.sub(keep, str(data["resposta"])).split())
    added = [int(found) for found in dict.fromkeys(CITATION.findall(answer)) if all(existing.id != int(found) for existing in cited)]
    cited += [Cited(movie_id, "") for movie_id in added]
    cited = cited[:max_cited]
    sufficient = bool(data["contexto_suficiente"])
    replaced = sufficient and not cited
    if replaced:
        answer, sufficient = no_context_answer, False
    return Grounded(answer, tuple(cited), sufficient, tuple(dict.fromkeys(invented)), tuple(added), replaced)
