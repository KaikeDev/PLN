"""Regras de língua e de domínio compartilhadas pelo corpus e pela pesquisa auxiliar.

As duas partes do projeto normalizam o texto de formas diferentes (ADR 0003): o corpus preserva
acentos e a pesquisa os remove. Por isso as listas ficam aqui na forma acentuada, e cada consumidor
aplica a própria normalização.
"""

NEGATION_MARKERS = frozenset({"não", "nem", "nunca", "sem"})

MIN_RELEASE_YEAR = 1874
MAX_RELEASE_YEAR = 9998
