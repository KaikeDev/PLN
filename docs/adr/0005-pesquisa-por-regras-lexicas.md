# 0005 — Pesquisa auxiliar por regras léxicas e heurísticas explícitas

- Estado: Aceita
- Data: 2026-09-14 (regras originais do protótipo, revisadas na Etapa 1)

## Contexto

A interface precisa aceitar pedidos como "uma comédia recente bem avaliada, sem terror". A entrega avaliada é o corpus e as representações; a pesquisa é uma demonstração auxiliar e ainda não usa os vetores das sinopses.

## Decisão

Reconhecer preferências por regras transparentes, com valores nomeados no código:

| Regra | Valor | Onde |
|---|---|---|
| "bem avaliado", "boa avaliação", "aclamado" | nota ≥ 7 e ≥ 100 votos, ordenação por nota | `lexicon.HIGH_QUALITY` |
| "excelente", "obra-prima", "nota alta" | nota ≥ 8 e ≥ 200 votos | `lexicon.VERY_HIGH_QUALITY` |
| "recente", "novo", "não muito antigo" | lançado nos últimos 10 anos | `period.RECENT_YEARS` |
| "antigo", "clássico", "cult" | lançado há mais de 25 anos | `period.OLD_YEARS` |
| "dos anos NN" | década; NN ≤ 29 é do século XXI | `period.LAST_21ST_CENTURY_DECADE` |
| "depois de X" / "antes de X" | a partir de 01/01/X / até 31/12/(X−1) | `period` |
| negação de gênero | marcador até 3 tokens antes | `negation.GENRE_WINDOW` |
| negação de qualidade | marcador até 5 tokens antes | `negation.QUALITY_WINDOW` |
| gêneros incluídos / excluídos | qualquer um (OU) / nenhum (E) | `infra.tmdb.catalog` |

A nota não é usada para deduzir premiações. Um ano informado separadamente é intersectado com o período extraído; período vazio não gera consulta.

## Alternativas consideradas

- Classificador treinado ou LLM: sem dados anotados suficientes e menos explicável para a disciplina.
- Busca vetorial nas sinopses (Etapa 2): candidata futura; exige avaliação com consultas anotadas antes de substituir as regras.

## Consequências

- O comportamento é previsível e testável (`tests/test_search_extractor.py`), mas não cobre paráfrases, títulos alternativos nem toda a semântica da negação.
- A acurácia de 100% (12/12) vale só para cinco frases anotadas e não é medida geral.
