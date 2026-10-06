# 0023 — Filmes parecidos na ficha do filme

- Estado: Aceita
- Data: 2026-10-05

## Contexto

A recomendação por conteúdo ([ADR 0018](0018-tarefas-do-ciclo-de-pln.md)) só existia como avaliação: calculava as recomendações de todos os filmes e media a precisão por gênero, mas o site não mostrava nenhuma. Das quatro tarefas, só a busca e a classificação apareciam na tela.

## Decisão

- **Onde aparece:** na ficha de cada filme, uma seção "Filmes parecidos" mostra os 5 filmes cuja sinopse mais se parece com a dele. Cada um abre a própria ficha, então dá para navegar de recomendação em recomendação.
- **Como calcula:** a mesma conta da análise `Recommendation`, em `recommendation/similar.py`: os k filmes de maior cosseno com o filme, sem contar o próprio filme, com empates resolvidos pelo ID. Um teste confirma que o site devolve as mesmas recomendações da avaliação.
- **Representação:** o embedding de sentença (`sentenca_minilm`), que a busca por tema já carrega. É configurável em `synopsis_recommendation_representation`, desde que a representação faça parte da busca.
- **API:** `GET /filmes/{id}/parecidos?quantidade=5` (1 a 20).
  - Responde com os filmes, a similaridade (`pontuacao`), a representação e `na_amostra`.
  - Um filme fora dos 428 da amostra não é erro: a resposta diz `na_amostra: false`, e a tela explica por que não há recomendações.
  - Sem índice ou sem recomendador, a rota responde 503.
- **Arquitetura:** a porta `SimilarMoviesProvider` fica em `recommendation/ports.py`, e a montagem, em `app.main`, junto com o índice de sinopses.

## Alternativas consideradas

- **BERTimbau:** teve a maior precisão @5 na avaliação (63,6% contra 62,6% do embedding de sentença), uma diferença pequena, e exigiria carregar mais um modelo na API (cerca de 0,4 GB).
- **Recomendação por perfil no site:** exigiria guardar os filmes de que cada pessoa gostou (login ou armazenamento no navegador). A recomendação a partir de um filme mostra a mesma técnica sem estado.
- **Ler as recomendações já calculadas** (`*.recommendations.jsonl`): evitaria o cálculo na hora, mas tem só 5 filmes por representação. O cálculo a partir dos vetores já carregados é imediato e permite escolher a quantidade.

## Consequências

- **Qualidade:** a esperada é a da avaliação, com 62,6% dos recomendados compartilhando um gênero com o filme. Funciona muito bem em franquias e temas marcados (Invocação do Mal → Invocação do Mal 4 e 2) e é mais fraca em filmes de tema abstrato (Matrix → Contato, Monstros S.A.).
- **Alcance:** só os 428 filmes da amostra têm recomendações; os demais filmes do TMDB, que aparecem pela busca por título, mostram o aviso.
