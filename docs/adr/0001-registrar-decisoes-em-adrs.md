# 0001 — Registrar decisões em ADRs

- Estado: Aceita
- Data: 2026-09-14

## Contexto

Decisões relevantes estavam espalhadas em comentários no código, em `docs/decisoes.md` (texto corrido, sem alternativas) e na memória da equipe. Várias escolhas só apareciam implícitas no código: normalizações diferentes, heurísticas numéricas, política de retry, formato de saída.

## Decisão

Registrar cada decisão arquitetural ou de método em `docs/adr/NNNN-titulo.md`, no formato MADR, com um resumo de todas as decisões e suas justificativas em [`adr.md`](../../adr.md), na raiz do repositório.

O código não usa comentários fora de docstrings: a explicação fica em docstrings de módulo, classe e função e, quando envolve escolha entre alternativas, numa ADR citada pela docstring (por exemplo, "ADR 0005"). A regra vale também para arquivos de configuração que aceitam comentários, como o `.gitignore` (ADR 0016).

## Alternativas consideradas

- Manter `docs/decisoes.md` como texto único: não mostra alternativas nem histórico de substituição.
- Comentários no código: se desatualizam sem revisão e não explicam alternativas descartadas.

## Consequências

- Mudar uma heurística ou um formato exige atualizar ou substituir a ADR correspondente.
- `docs/decisoes.md` passa a ser um índice resumido que aponta para as ADRs.
- Uma ADR nova exige também uma entrada em `adr.md` e uma linha em `docs/adr/README.md`.
- Em 21/09/2026, a verificação por `tokenize` não encontrou nenhum comentário fora de docstring no Python de `backend/`, e o frontend também não tinha nenhum. Os comentários do `.gitignore` viraram a ADR 0016.
