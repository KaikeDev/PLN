# 0014 — Amostragem intencional da coleta

- Estado: Aceita
- Data: 2026-09-14 (coleta realizada em 12/09/2026)

## Contexto

O professor pediu representações sucessivas dos mesmos dados, comparação futura e um repositório navegável (orientação em vídeo de 31/08/2026). O catálogo completo do TMDB é inviável para a atividade, e comparar recortes exige grupos equilibrados.

## Decisão

- **Gêneros**: Drama (18), Comédia (35), Terror (27) e Ficção científica (878).
- **Períodos**: 1980–1999, 2000–2014 e 2015–2025.
- **Por recorte**: 2 páginas ordenadas por popularidade, com pelo menos 50 votos e sem conteúdo adulto.
- **Filme semente**: ID 603 (Matrix), caso didático pedido pelo professor. Os filmes semente também são os primeiros exemplos do relatório processado.
- **Deduplicação por ID**: a primeira ocorrência é preservada e `memberships.json` registra todos os recortes de cada filme.
- **Intervalo entre chamadas**: 0,3 s.

Os parâmetros ficam em `config/coleta.json`, validado por `app.corpus.config`.

## Alternativas consideradas

- Amostra aleatória do catálogo: muitos filmes sem sinopse em português e grupos desequilibrados.
- Mais páginas por recorte: maior custo de coleta, sem necessidade para a comparação pedida.

## Consequências

- A amostra tem viés de popularidade e de disponibilidade de metadados e não representa o catálogo.
- O parâmetro `pt-BR` pede tradução, mas não garante o idioma de cada sinopse.
