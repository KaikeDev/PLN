# 0025 — Preparação da consulta da busca por tema

- Estado: Aceita
- Data: 2026-10-05

## Contexto

Com o catálogo do site ([ADR 0024](0024-catalogo-do-site.md)), um teste com "filmes sobre saude mental" trouxe filmes **sobre cinema**: *O Guia Pervertido do Cinema*, *Império dos Sonhos: A História da Trilogia Star Wars*, *The Cutting Edge: The Magic of Movie Editing*. Havia dois motivos:

- **Palavras de pedido:** "filmes sobre" descreve o pedido, não o tema. Para o TF-IDF e para o embedding de sentença, porém, "filmes" é tão conteúdo quanto "mental", e as sinopses que falam de filmes subiam. A limitação já estava registrada na [página da busca](../3-busca.md#limitações) ("Holocausto Canibal em 'filme sobre simulação da realidade'").
- **Falta de acento:** o vocabulário do TF-IDF guarda "saúde", e "saude" não casava com nenhuma palavra; sobrava "mental".

## Decisão

Antes de ordenar, `HybridIndex.rank` prepara a consulta com [`app/search/query.py`](../../backend/src/app/search/query.py):

- **Tira as palavras de pedido:**
  - no começo da frase: "quero", "queria", "gostaria de", "preciso de", "procuro", "busco", "me indica", "me recomenda", "me mostra"…, seguidos ou não de "ver" ou "assistir";
  - em qualquer lugar: "filme(s)" ou "longa(s)", com o artigo ("um", "algum"…), o adjetivo ("bom", "ótimo") e a ligação que vierem junto ("sobre", "de", "com", "que fala de"…).
  - Se nada sobrar ("quero um filme"), a frase original é usada.
- **Recoloca acentos que faltam:** uma palavra digitada **sem acento**, com **4 letras ou mais** e **fora do vocabulário do TF-IDF** é trocada pela forma do vocabulário com as mesmas letras sem acento, se houver **uma só** ("saude" → "saúde"). Palavras curtas ficam como estão, porque "a", "que" e "da" virariam "á", "quê" e "dá".
- **Só a busca por tema:** as regras de gênero e período continuam lendo a frase original. O embedding de sentença recebe a mesma frase preparada que o TF-IDF.
- **Sem modelo novo:** a busca continua com as mesmas duas representações e os mesmos pesos.

## Alternativas consideradas

- **Lista de stopwords maior:** tiraria "filme" do TF-IDF, mas não do embedding de sentença, que lê a frase inteira.
- **Remover acentos do corpus e da consulta:** exigiria refazer todas as representações e análises entregues.
- **Trocar o embedding de sentença por um modelo maior:** o trabalho usa só as representações do projeto (BoW, TF-IDF, word2vec, BERTimbau e o embedding de sentença).

## Consequências

- **Nas 20 consultas anotadas,** só mudaram as duas que tinham palavras de pedido ("filme sobre simulação da realidade" e "quero um filme de ação sobre máquinas"). Nenhuma piorou:

  | Algoritmo | MAP antes | MAP depois | MRR antes | MRR depois | Precisão @5 antes | Precisão @5 depois |
  |---|---:|---:|---:|---:|---:|---:|
  | TF-IDF sem stopwords | 0,446 | 0,459 | 0,880 | 0,913 | 0,44 | 0,46 |
  | Embedding de sentença | 0,560 | 0,566 | 0,879 | 0,879 | 0,49 | 0,49 |
  | **Combinação** | **0,613** | **0,627** | 0,912 | 0,912 | 0,56 | 0,57 |

  Na combinação, "quero um filme de ação sobre máquinas" passou de MAP 0,483 para 0,760.
- **No catálogo do site:** "filmes sobre saude mental" passa a dar o mesmo resultado que "saúde mental" (*Van Gogh*, *Whiplash*, *Garota, Interrompida*, *O Homem Elefante*), e não mais filmes sobre cinema.
- **Temas abstratos continuam difíceis:** a lista de "saúde mental" ainda mistura filmes ligados ao tema com filmes só próximos. É um limite do embedding de sentença em temas abstratos, já visto na recomendação ([ADR 0023](0023-recomendacao-no-site.md)).
- **Regras escritas à mão:** frases de pedido fora da lista ("tem algum filme…") continuam entrando na busca por tema.
