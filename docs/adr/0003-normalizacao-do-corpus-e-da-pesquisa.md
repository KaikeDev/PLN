# 0003 — Normalizações distintas para corpus e pesquisa

- Estado: Aceita
- Data: 2026-09-14 (decisão original na Etapa 1, 12/09/2026)

## Contexto

O corpus de sinopses serve para comparar técnicas de PLN; acentos distinguem palavras ("é"/"e", "pôde"/"pode") e precisam ser preservados. A pesquisa auxiliar compara o que a pessoa digita, com ou sem acento, com um léxico fixo de gatilhos. Antes, os marcadores de negação estavam duplicados em três lugares, com conteúdo diferente (com e sem "nem").

## Decisão

- **Corpus** (`app.corpus.transform`): limpeza com Unicode NFC e `casefold`, preservando acentos.
- **Pesquisa** (`app.domain.search.normalization`): minúsculas e remoção de acentos (NFKD sem marcas combinantes).
- **Regras compartilhadas** (`app.shared.language`): marcadores de negação ("não", "nem", "nunca", "sem") e limites de ano de lançamento ficam em um único lugar, na forma acentuada. Cada consumidor aplica a própria normalização.

## Alternativas consideradas

- Uma única normalização sem acentos: perderia distinções do português no corpus e mudaria as representações já entregues.
- Uma única normalização com acentos: a pesquisa deixaria de reconhecer "acao" digitado sem acento.

## Consequências

- "nem" passou a negar gêneros na pesquisa ("ação, nem terror" exclui Terror), comportamento antes restrito às expressões de qualidade.
- Um marcador novo entra em `app.shared.language` e vale para os dois fluxos. No corpus, muda a lista preservada no filtro de stopwords e, portanto, as saídas processadas.
