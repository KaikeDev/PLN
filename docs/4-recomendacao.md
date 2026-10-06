# 4. Recomendação

Dado um filme (ou um conjunto de filmes de que uma pessoa gostou), recomendar outros filmes parecidos a partir das sinopses. É **recomendação por conteúdo**: o corpus não tem avaliações de usuários, então a filtragem colaborativa não se aplica.

- **Código:** [`backend/src/app/recommendation/analysis.py`](../backend/src/app/recommendation/analysis.py)
- **Resultados:** seção "Recomendação" do [relatório](../data/representacoes/tmdb_2026-09-12/report.md), [`recommendation.json`](../data/representacoes/tmdb_2026-09-12/recommendation.json) e um arquivo `<representação>.recommendations.jsonl` por representação
- **No site:** seção "Filmes parecidos" na ficha de cada filme ([`recommendation/similar.py`](../backend/src/app/recommendation/similar.py))
- **Decisões:** [ADR 0018](adr/0018-tarefas-do-ciclo-de-pln.md) e [ADR 0023](adr/0023-recomendacao-no-site.md)

## Como funciona

1. **Filme → filmes:** cada sinopse já é um vetor em cada uma das oito representações ([2-representacoes.md](2-representacoes.md)). Os recomendados são os 5 filmes de maior cosseno com o filme escolhido, sem contar o próprio filme.
2. **Perfil → filmes:** a média, com norma L2, dos vetores dos filmes do perfil. Os recomendados são os 5 filmes de maior cosseno com essa média, fora do perfil. Os perfis de exemplo ficam em [`config/representacoes/vetorizacao_semantica.json`](../config/representacoes/vetorizacao_semantica.json).
3. **Explicação:** nas representações lexicais, a recomendação mostra as palavras em comum; no word2vec, os pares de palavras próximas.

## Como foi avaliada

Sem avaliações de usuários, a avaliação usa os gêneros como aproximação. A **precisão @5** é a fração dos 5 recomendados que têm ao menos um gênero em comum com o filme. A **referência** é essa fração sobre todos os outros filmes, o que acertaria uma recomendação que ignora o texto (37,9%).

| Representação | Precisão @5 |
|---|---:|
| Referência que ignora o texto | 37,9% |
| `bow_sem_pontuacao` | 45,0% |
| `bow_sem_stopwords` | 56,1% |
| `tfidf_sem_pontuacao` | 57,0% |
| `tfidf_sem_stopwords` | 57,8% |
| `word2vec_cbow` | 55,7% |
| `word2vec_skipgram` | 60,2% |
| `bert_base_pt` | **63,6%** |
| `sentenca_minilm` | 62,6% |

## O que os resultados mostram

- **Todas as representações superam a referência.** O BERTimbau (63,6%) e o embedding de sentença (62,6%) ficam no topo.
- **Perfil "terror sobrenatural"** (Invocação do Mal, Hereditário, Sobrenatural: A Origem): o embedding de sentença recomenda Invocação do Mal 2, Invocação do Mal 4, A Morte do Demônio, A Morte do Demônio: A Ascensão e Sobrenatural: A Última Chave, todos de terror.
- **Perfil "animação e família"** (Toy Story, Up, Monstros S.A.): o TF-IDF encontra Toy Story 2, 3 e 4 pelos nomes dos personagens (Woody, Buzz, Andy). É um acerto, mas mostra que as representações lexicais dependem de palavras repetidas, como nomes de franquia.
- **Perfil "mente e realidade"** (Matrix, A Origem, Brilho Eterno): é o mais difícil; nenhuma representação traz só filmes desse tema.

## No site

Ao abrir a ficha de um filme da amostra, a seção **"Filmes parecidos"** mostra os 5 filmes de sinopse mais próxima, com a similaridade do cosseno. Cada um abre a própria ficha. Por trás, `GET /filmes/{id}/parecidos` faz a mesma conta da avaliação, sobre o embedding de sentença que a busca já carrega; um teste confirma que as recomendações do site são as mesmas da avaliação.

| Filme | Filmes parecidos no site |
|---|---|
| Invocação do Mal | Invocação do Mal 4, Invocação do Mal 2, A Morte do Demônio: A Ascensão, A Entidade, Extermínio: A Evolução |
| Toy Story | Gigantes de Aço, Toy Story 3, O Macaco, Free Guy, Sonic 3 |
| Matrix | Contato, Monstros S.A., A Hora do Pesadelo, A Mosca, Free Guy |

Filmes fora dos 428 da amostra, que o site encontra pela busca por título, mostram um aviso no lugar das recomendações.

## Limitações

A avaliação por gênero compartilhado é uma aproximação: dois filmes do mesmo gênero não são necessariamente boas recomendações um para o outro. Uma avaliação fiel exigiria pares de filmes anotados como boas recomendações entre si, ou avaliações de usuários.
