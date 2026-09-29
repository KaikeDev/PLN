# Classificação de gêneros a partir das sinopses

Cada representação da Etapa 2 alimenta a mesma regressão logística, com classes de peso balanceado. A regularização C é escolhida pela log loss entre 10⁻⁶, 10⁻⁵, 10⁻⁴, 10⁻³, 0,01, 0,1, 1, 10, 100, 1000, 10000 em 3 dobras internas do próprio treino, e o modelo é avaliado por validação cruzada em 5 dobras externas (semente 42), as mesmas para todas as representações. Toda métrica usa só previsões fora da dobra: cada sinopse é classificada por um modelo que não a viu no treino. Os rótulos são os gêneros atribuídos pelo TMDB (`genre_ids`) restritos aos gêneros da coleta.

## Tarefas

- **Multiclasse:** 325 filmes com exatamente um dos gêneros; o modelo escolhe um gênero.
- **Multirrótulo:** 428 filmes com ao menos um dos gêneros; um classificador binário por gênero decide cada gênero com probabilidade ≥ 0,5, e o mais provável é sempre atribuído.

| Gênero | Multiclasse | Multirrótulo |
|---|---:|---:|
| Drama | 89 | 136 |
| Comédia | 85 | 136 |
| Terror | 66 | 119 |
| Ficção científica | 85 | 144 |

## Multiclasse: um gênero por filme

| Representação | Família | Acurácia | F1 macro | F1 macro por dobra | Log loss | Confiança nos acertos | Confiança nos erros |
|---|---|---:|---:|---:|---:|---:|---:|
| referência: gênero mais frequente | — | 27,4% | 10,7% | 10,7% ± 0,2% | 1,380 | 27,4% | 27,4% |
| `bow_sem_pontuacao` | lexical | 46,2% | 46,1% | 45,7% ± 1,9% | 1,220 | 46,9% | 42,0% |
| `bow_sem_stopwords` | lexical | 56,6% | 56,4% | 55,9% ± 3,8% | 1,036 | 59,8% | 47,0% |
| `tfidf_sem_pontuacao` | lexical | 59,4% | 59,3% | 59,2% ± 3,1% | 1,028 | 68,6% | 56,9% |
| `tfidf_sem_stopwords` | lexical | 59,7% | 59,2% | 58,8% ± 4,0% | 0,965 | 70,9% | 54,4% |
| `word2vec_cbow` | static | 67,7% | 67,6% | 67,2% ± 2,0% | 0,854 | 62,0% | 50,8% |
| `word2vec_skipgram` | static | 71,1% | 71,0% | 70,8% ± 5,7% | 0,779 | 65,6% | 51,4% |
| `bert_base_pt` | contextual | 70,2% | 70,2% | 69,9% ± 4,0% | 0,725 | 74,9% | 56,2% |
| `sentenca_minilm` | contextual | 65,8% | 66,1% | 66,0% ± 3,6% | 0,860 | 69,6% | 54,7% |

A confiança é a probabilidade média do gênero escolhido. Quando ela é menor nos erros que nos acertos, o modelo sinaliza a própria incerteza.

`word2vec_skipgram` tem o maior F1 macro, 0,8 pontos acima de `bert_base_pt`. A diferença é menor que o maior desvio entre dobras das duas (5,7 pontos): a ordem entre as duas não é conclusiva nesta amostra.

### F1 por gênero

| Representação | Drama | Comédia | Terror | Ficção científica |
|---|---:|---:|---:|---:|
| referência: gênero mais frequente | 43,0% | 0,0% | 0,0% | 0,0% |
| `bow_sem_pontuacao` | 49,5% | 41,5% | 44,4% | 49,0% |
| `bow_sem_stopwords` | 56,1% | 50,9% | 53,7% | 64,7% |
| `tfidf_sem_pontuacao` | 62,4% | 50,6% | 58,7% | 65,5% |
| `tfidf_sem_stopwords` | 62,9% | 48,1% | 58,7% | 67,1% |
| `word2vec_cbow` | 67,0% | 61,8% | 67,2% | 74,4% |
| `word2vec_skipgram` | 70,2% | 65,8% | 69,6% | 78,3% |
| `bert_base_pt` | 73,4% | 58,9% | 73,8% | 74,6% |
| `sentenca_minilm` | 63,7% | 57,6% | 69,3% | 73,7% |

### Melhor F1 macro: `word2vec_skipgram`

| Gênero | Precisão | Revocação | F1 | Suporte |
|---|---:|---:|---:|---:|
| Drama | 66,7% | 74,2% | 70,2% | 89 |
| Comédia | 69,7% | 62,4% | 65,8% | 85 |
| Terror | 68,1% | 71,2% | 69,6% | 66 |
| Ficção científica | 80,2% | 76,5% | 78,3% | 85 |

Matriz de confusão (linhas = gênero real, colunas = previsto):

| Real ↓ / Previsto → | Drama | Comédia | Terror | Ficção científica |
|---|---:|---:|---:|---:|
| Drama | 66 | 13 | 5 | 5 |
| Comédia | 19 | 53 | 8 | 5 |
| Terror | 6 | 7 | 47 | 6 |
| Ficção científica | 8 | 3 | 9 | 65 |

## Descobrir grupos ou reconhecer classes?

O K-Means da Etapa 2 (k = 4, k-means++, sem rótulos) agrupa as mesmas 325 sinopses da tarefa multiclasse em cada representação. Os gêneros só entram depois, para medir a coincidência entre grupos e classes. O ARI vale 1 na coincidência perfeita e fica perto de 0 para grupos ao acaso, porque desconta o acaso; o NMI vai de 0 (grupos independentes dos gêneros) a 1. Nenhum dos dois depende do nome de cada grupo, por isso medem da mesma forma os grupos do K-Means e as previsões do classificador (fora da dobra). A acurácia com o melhor mapeamento associa cada grupo a um gênero diferente usando os rótulos: é um teto otimista para usar grupos como classes.

| Representação | K-Means: ARI | K-Means: NMI | K-Means: acurácia com o melhor mapeamento | Classificador: ARI | Classificador: NMI | Classificador: acurácia |
|---|---:|---:|---:|---:|---:|---:|
| `bow_sem_pontuacao` | -0,001 | 0,009 | 30,2% | 0,074 | 0,087 | 46,2% |
| `bow_sem_stopwords` | 0,003 | 0,013 | 30,2% | 0,175 | 0,171 | 56,6% |
| `tfidf_sem_pontuacao` | 0,003 | 0,028 | 31,1% | 0,211 | 0,202 | 59,4% |
| `tfidf_sem_stopwords` | 0,010 | 0,016 | 31,4% | 0,221 | 0,208 | 59,7% |
| `word2vec_cbow` | 0,053 | 0,071 | 36,9% | 0,327 | 0,308 | 67,7% |
| `word2vec_skipgram` | 0,055 | 0,065 | 39,4% | 0,381 | 0,358 | 71,1% |
| `bert_base_pt` | 0,132 | 0,142 | 47,7% | 0,369 | 0,349 | 70,2% |
| `sentenca_minilm` | 0,129 | 0,146 | 49,8% | 0,299 | 0,287 | 65,8% |

O classificador tem ARI maior que o agrupamento em 8 de 8 representações. Os dois partem do mesmo espaço vetorial e só o objetivo muda: o K-Means procura os grupos mais compactos, e o classificador procura a fronteira que separa os gêneros rotulados.

### Grupos de `bert_base_pt`, o agrupamento mais próximo dos gêneros

Contagem de sinopses de cada gênero real por grupo, termos de maior peso médio no TF-IDF de referência e sinopses mais próximas do centroide.

| Grupo | Tamanho | Gênero associado | Drama | Comédia | Terror | Ficção científica | Termos descritivos | Mais próximos do centroide |
|---:|---:|---|---:|---:|---:|---:|---|---|
| 0 | 45 | Terror | 3 | 12 | 20 | 10 | dois, vidas, estão, demônios, juntos, presos, descobrem, cidade, misterioso, família | A Morte do Demônio; Pânico 2; Os Oito Odiados |
| 1 | 74 | Drama | 42 | 17 | 7 | 8 | história, jovem, polícia, guerra, ser, policial, vida, anos, caso, mesmo | Um Sonho de Liberdade; O Grande Lebowski; Entre Facas e Segredos |
| 2 | 99 | Ficção científica | 12 | 21 | 8 | 58 | ser, está, mundo, planeta, após, peter, precisa, terra, missão, combater | Thor: Amor e Trovão; Mad Max: Estrada da Fúria; O Exterminador do Futuro 2: O Julgamento Final |
| 3 | 107 | Comédia | 32 | 35 | 31 | 9 | casa, não, família, está, ter, começa, ser, dois, agora, vida | Up: Altas Aventuras; 365 Dias: Hoje; Uma Noite de Crime: Anarquia |

## Outros classificadores (multiclasse)

F1 macro de cada classificador nas mesmas dobras externas e com a mesma preparação da regressão logística. Cada alternativa escolhe o próprio hiperparâmetro pelo F1 macro em 3 dobras internas do treino (Naive Bayes: alpha; SVM: C; k vizinhos: k); a floresta aleatória usa 300 árvores, sem ajuste. A regressão logística escolhe C pela log loss, porque suas probabilidades são usadas; o critério das alternativas é o próprio F1, o que torna a comparação conservadora para a regressão logística. “—” indica que o classificador não se aplica: o Naive Bayes multinomial exige atributos não negativos, e os vetores densos padronizados têm valores negativos.

| Representação | Regressão logística | Naive Bayes multinomial | SVM linear | Floresta aleatória | k vizinhos (cosseno) |
|---|---:|---:|---:|---:|---:|
| `bow_sem_pontuacao` | 46,1% | 59,1% | 47,5% | 44,2% | 28,2% |
| `bow_sem_stopwords` | 56,4% | 61,3% | 56,1% | 47,4% | 53,3% |
| `tfidf_sem_pontuacao` | 59,3% | 60,1% | 60,4% | 43,5% | 53,3% |
| `tfidf_sem_stopwords` | 59,2% | 58,9% | 59,4% | 49,4% | 53,3% |
| `word2vec_cbow` | 67,6% | — | 66,5% | 60,8% | 61,8% |
| `word2vec_skipgram` | 71,0% | — | 70,3% | 65,4% | 61,1% |
| `bert_base_pt` | 70,2% | — | 70,0% | 67,9% | 65,2% |
| `sentenca_minilm` | 66,1% | — | 67,8% | 66,9% | 67,7% |

A regressão logística tem o maior F1 macro em 3 de 8 representações. Com ela, trocar a representação muda o F1 macro em até 24,9 pontos; na mesma representação, trocar o classificador muda em média 11,9 pontos (até 30,9). A melhor combinação medida é `word2vec_skipgram` + Regressão logística (71,0%).

## Multirrótulo: todos os gêneros do filme

| Representação | F1 micro | F1 macro | F1 macro por dobra | Perda de Hamming | Acerto exato | Gêneros previstos por filme |
|---|---:|---:|---:|---:|---:|---:|
| referência: gênero mais frequente | 26,2% | 20,4% | 11,3% ± 1,1% | 41,5% | 18,7% | 1,00 |
| `bow_sem_pontuacao` | 54,5% | 54,4% | 54,1% ± 2,5% | 28,1% | 33,9% | 1,22 |
| `bow_sem_stopwords` | 58,0% | 57,6% | 57,1% ± 3,8% | 24,5% | 43,5% | 1,08 |
| `tfidf_sem_pontuacao` | 58,1% | 58,0% | 57,7% ± 3,5% | 24,5% | 42,1% | 1,08 |
| `tfidf_sem_stopwords` | 60,3% | 60,0% | 59,5% ± 4,2% | 23,0% | 45,6% | 1,06 |
| `word2vec_cbow` | 68,5% | 68,3% | 67,8% ± 4,6% | 20,7% | 43,0% | 1,38 |
| `word2vec_skipgram` | 71,3% | 71,1% | 70,7% ± 4,0% | 19,2% | 45,1% | 1,43 |
| `bert_base_pt` | 69,8% | 69,8% | 69,5% ± 3,7% | 20,0% | 45,8% | 1,41 |
| `sentenca_minilm` | 66,8% | 66,8% | 66,6% ± 3,2% | 22,3% | 41,6% | 1,43 |

Em média, cada filme tem 1,25 dos 4 gêneros. Um classificador que nunca atribuísse gênero algum erraria só 31,2% das decisões gênero a gênero (perda de Hamming), menos que a referência (41,5%), com F1 zero: com rótulos esparsos, acertar “não pertence” é fácil, e por isso o F1 é a métrica principal. O acerto exato exige todos os gêneros certos ao mesmo tempo e é a métrica mais severa.

## O que os modelos lexicais aprenderam

Termos com maior coeficiente para cada gênero, num modelo ajustado com todas as sinopses da tarefa multiclasse. Nas representações densas as dimensões não correspondem a palavras, e esta leitura não é possível.

### `bow_sem_pontuacao`

| Gênero | Termos |
|---|---|
| Drama | jovem, durante, vida, é, seu, história, nick, edward, segunda, anos |
| Comédia | amigos, quando, que, sempre, onde, aventura, shrek, mundo, grande, entre |
| Terror | filho, demônios, casa, grupo, caso, cidade, drácula, vidas, mais, a |
| Ficção científica | planeta, peter, futuro, parker, terra, inimigo, mundo, os, missão, contra |

### `bow_sem_stopwords`

| Gênero | Termos |
|---|---|
| Drama | jovem, história, durante, vida, conhece, edward, segunda, nick, morte, assassinato |
| Comédia | amigos, aventura, vive, gato, encontram, novas, mundo, onde, provar, sempre |
| Terror | grupo, demônios, filho, casa, drácula, vidas, começa, caso, vampiro, antiga |
| Ficção científica | planeta, peter, futuro, parker, terra, missão, mundo, inimigo, vingadores, lado |

### `tfidf_sem_pontuacao`

| Gênero | Termos |
|---|---|
| Drama | jovem, edward, história, durante, vida, seu, segunda, nick, conhece, noah |
| Comédia | amigos, aventura, novas, addams, shrek, gato, sempre, usando, fiona, diretora |
| Terror | demônios, grupo, filho, casa, blade, drácula, a, caso, vampiro, cidade |
| Ficção científica | planeta, peter, futuro, terra, parker, inimigo, missão, humanidade, vingadores, homem-aranha |

### `tfidf_sem_stopwords`

| Gênero | Termos |
|---|---|
| Drama | jovem, edward, vida, história, durante, segunda, conhece, nick, soldados, dinheiro |
| Comédia | amigos, aventura, gato, novas, addams, fiona, shrek, sempre, usando, deadpool |
| Terror | demônios, grupo, casa, filho, drácula, começa, blade, caso, vampiro, vidas |
| Ficção científica | planeta, peter, futuro, terra, parker, inimigo, missão, vingadores, humanidade, mundo |

## Erros com mais convicção: `word2vec_skipgram`

Filmes da tarefa multiclasse em que o modelo deu a maior probabilidade a um gênero errado. As probabilidades de cada filme estão nos arquivos `*.predictions.jsonl`.

| Filme | Real | Previsto | Probabilidade |
|---|---|---|---:|
| Os Suspeitos (629) | Drama | Terror | 87,7% |
| Gente Grande (38365) | Comédia | Drama | 87,3% |
| V de Vingança (752) | Ficção científica | Drama | 80,3% |
| Velozes & Furiosos: Hobbs & Shaw (384018) | Comédia | Ficção científica | 78,2% |
| Your Name. (372058) | Drama | Comédia | 77,7% |
| Blade II: O Caçador de Vampiros (36586) | Terror | Ficção científica | 77,2% |
| Fargo: Uma Comédia de Erros (275) | Drama | Comédia | 74,7% |
| Robô Selvagem (1184918) | Ficção científica | Comédia | 69,5% |

## Custo e interpretabilidade

| Representação | Família | Dimensões | Parâmetros pré-treinados | Coeficientes legíveis como termos |
|---|---|---:|---:|---|
| `bow_sem_pontuacao` | lexical | 5988 | — | sim |
| `bow_sem_stopwords` | lexical | 5921 | — | sim |
| `tfidf_sem_pontuacao` | lexical | 5988 | — | sim |
| `tfidf_sem_stopwords` | lexical | 5921 | — | sim |
| `word2vec_cbow` | static | 300 | 278.882.100 | não |
| `word2vec_skipgram` | static | 300 | 278.882.100 | não |
| `bert_base_pt` | contextual | 768 | 108.923.136 | não |
| `sentenca_minilm` | contextual | 384 | 117.653.760 | não |

Nas lexicais, as dimensões são o vocabulário do corpus inteiro; dentro de cada dobra o vocabulário vem só das sinopses de treino. Os tempos de construção e de validação de cada representação estão em `manifest.json` (`seconds`), porque variam entre execuções.

## Limitações

A amostra é pequena (428 sinopses) e intencional (ADR 0014): os valores dependem das dobras, por isso o desvio entre dobras acompanha o F1. O gênero é atribuído ao filme, não à sinopse; uma sinopse curta pode não conter pistas do gênero. Os classificadores alternativos foram comparados só na tarefa multiclasse e só pelo gênero previsto; a floresta aleatória usa parâmetros fixos. O BERT e o modelo de sentença são usados como extratores de atributos congelados, sem ajuste fino. LLM com instrução e decisões tipadas (Jev) não foram avaliados: dependem de serviço externo e não seriam reproduzíveis nesta entrega.

## Fonte

Dados: The Movie Database (TMDB), https://www.themoviedb.org/. Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB.
