# 5. Agrupamento e visualização

Agrupar as sinopses **sem usar rótulos** e ver se os grupos encontrados lembram os gêneros. É a tarefa não supervisionada da disciplina, em contraste com a classificação ([6-classificacao.md](6-classificacao.md)), que aprende com os rótulos.

- **Código:** [`backend/src/app/clustering/`](../backend/src/app/clustering/): `kmeans.py` (K-Means e projeção 2D), `analysis.py` (avaliação) e `svg.py` (gráficos)
- **Resultados:** seções "Agrupamento" e "Visualização" do [relatório](../data/representacoes/tmdb_2026-09-12/report.md), [`clustering.json`](../data/representacoes/tmdb_2026-09-12/clustering.json), [`projection.json`](../data/representacoes/tmdb_2026-09-12/projection.json) e dois gráficos por representação
- **Decisões:** [ADR 0012](adr/0012-parametros-do-experimento-vetorial.md) e [ADR 0018](adr/0018-tarefas-do-ciclo-de-pln.md)

## Como funciona

1. **K-Means com k = 4** (o número de gêneros da coleta) sobre os vetores de cada representação, com norma L2 e semente fixa.
2. **Avaliação contra os gêneros**, só com os filmes de um único gênero, os únicos com rótulo inequívoco:
   - **ARI:** 0 = grupos ao acaso, 1 = grupos iguais aos gêneros;
   - **NMI:** informação compartilhada entre grupos e gêneros;
   - **pureza:** fração de filmes que pertencem ao gênero mais comum do próprio grupo.
3. **Visualização:** as sinopses são projetadas em 2 dimensões (TruncatedSVD) e desenhadas duas vezes com as mesmas coordenadas:
   - `<representação>.projection.svg`, colorida pelo gênero;
   - `<representação>.clusters.svg`, colorida pelo grupo do K-Means.

## Resultados

| Representação | ARI | NMI | Pureza |
|---|---:|---:|---:|
| `bow_sem_pontuacao` | 0,002 | 0,013 | 31,7% |
| `bow_sem_stopwords` | 0,000 | 0,014 | 29,8% |
| `tfidf_sem_pontuacao` | 0,001 | 0,011 | 31,4% |
| `tfidf_sem_stopwords` | 0,024 | 0,044 | 35,1% |
| `word2vec_cbow` | 0,060 | 0,072 | 40,3% |
| `word2vec_skipgram` | 0,062 | 0,080 | 41,2% |
| `bert_base_pt` | **0,144** | **0,168** | **48,9%** |
| `sentenca_minilm` | 0,087 | 0,121 | 44,6% |

Exemplos de gráfico: [BERTimbau por gênero](../data/representacoes/tmdb_2026-09-12/bert_base_pt.projection.svg) e [BERTimbau por grupo](../data/representacoes/tmdb_2026-09-12/bert_base_pt.clusters.svg).

## O que os resultados mostram

- **Os grupos lembram pouco os gêneros.** Mesmo o melhor caso, o BERTimbau, tem ARI de 0,144. Nas lexicais, os grupos são praticamente independentes dos gêneros (ARI perto de 0).
- **O K-Means agrupa por outros temas.** No BERTimbau, um grupo junta terror e ficção científica com termos como "grupo", "vírus" e "missão"; outro reúne drama com "guerra", "polícia" e "jovem".
- **Agrupar × classificar:** nas mesmas sinopses e com a mesma representação, a classificação coincide muito mais com os gêneros. No skip-gram, o ARI é de 0,381 contra 0,055 do K-Means; no BERTimbau, de 0,369 contra 0,132 ([6-classificacao.md](6-classificacao.md)). É a diferença entre aprender com rótulos e sem eles.

## Quantos clusters

Uma varredura de k = 2 a 10 ([ADR 0028](adr/0028-varredura-do-numero-de-clusters.md); [relatório](../data/agrupamento/tmdb_2026-09-12/report.md)) mede, para cada representação:
- a compactação dos grupos (distância ao centroide, inércia);
- a separação entre eles (distância entre centroides);
- os índices que combinam as duas: silhueta, Davies-Bouldin e Calinski-Harabasz.

```bash
uv run --frozen --extra semantico python -m app.clustering sweep --input ../data/preparacao/tmdb_2026-09-12 --vectors-config ../config/representacoes/vetorizacao_semantica.json --vectors ../data/representacoes/tmdb_2026-09-12 --output ../data/agrupamento/<nova_pasta> --config ../config/agrupamento/varredura_k.json
```

- **Não há grupos naturais bem separados:** a silhueta fica abaixo de 0,10 em todas as representações e é praticamente zero nas lexicais.
- **As métricas internas se contradizem:** a silhueta e o Calinski-Harabasz preferem k = 2, o Davies-Bouldin melhora sempre com mais grupos, e a inércia cai sem cotovelo.
- **Contra os gêneros, k = 4 a 5 é o melhor:** o ARI do BERTimbau tem o pico de 0,144 nos dois. Com k = 5, o grupo de ameaça coletiva se divide em fim do mundo (*O Exterminador do Futuro 2*, *2012*) e terror de grupo (*A Morte do Demônio*, *Terror em Silent Hill*).

## Limitações

Os gêneros são uma régua aproximada: o K-Means pode encontrar agrupamentos legítimos (tom, época, tema) que não coincidem com eles. Filmes com vários gêneros ficam fora das métricas.
