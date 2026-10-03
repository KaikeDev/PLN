# Classificação de gênero com o Jev

Amostra de 120 sinopses: 25 de cada gênero único (Drama, Comédia, Terror, Ficção científica) e 20 com mais de um desses gêneros, sorteadas com semente 42. O Jev recebeu o texto da etapa `02_clean.jsonl` com uma Choice (gênero principal) e um Noul por gênero, na mesma chamada; não foi treinado com o corpus. O classificador de referência (TF-IDF da etapa `06_without_stopwords.jsonl` + regressão logística) foi treinado com os filmes fora da amostra e avaliado nos mesmos filmes.

Filmes avaliados: 120 de 120 (0 falhas do Jev, fora de todas as métricas). Modelo informado pela API: `jev-1.13.0`. Os gêneros de referência são os `genre_ids` do TMDB restritos aos gêneros avaliados, não um julgamento sobre a sinopse.

## Resumo

| Métrica | Jev | TF-IDF + RL |
|---|---:|---:|
| Choice: gênero principal entre os do filme (toda a amostra) | 0.875 | 0.600 |
| Choice: acurácia nos 100 filmes de um gênero | 0.850 | 0.560 |
| Choice: F1 macro nos filmes de um gênero | 0.847 | 0.537 |
| Por gênero: ROC AUC macro | 0.964 | 0.816 |
| Por gênero: F1 macro com limiar 0.5 | 0.823 | 0.559 |
| Por gênero: conjunto de gêneros exato | 0.675 | 0.350 |

Os dois métodos escolhem o mesmo gênero principal em 55.8% dos filmes.

## Choice por gênero (filmes de um gênero)

| Gênero | Filmes | Precisão Jev | Revocação Jev | F1 Jev | Precisão RL | Revocação RL | F1 RL |
|---|---:|---:|---:|---:|---:|---:|---:|
| Drama | 25 | 0.706 | 0.960 | 0.814 | 0.429 | 0.840 | 0.568 |
| Comédia | 25 | 1.000 | 0.640 | 0.780 | 0.591 | 0.520 | 0.553 |
| Terror | 25 | 0.893 | 1.000 | 0.943 | 1.000 | 0.200 | 0.333 |
| Ficção científica | 25 | 0.909 | 0.800 | 0.851 | 0.708 | 0.680 | 0.694 |

Matriz de confusão — Jev (linhas: gênero de coleta; colunas: previsto):

| | Drama | Comédia | Terror | Ficção científica |
|---|---:|---:|---:|---:|
| Drama | 24 | 0 | 1 | 0 |
| Comédia | 6 | 16 | 1 | 2 |
| Terror | 0 | 0 | 25 | 0 |
| Ficção científica | 4 | 0 | 1 | 20 |

Matriz de confusão — TF-IDF + RL (linhas: gênero de coleta; colunas: previsto):

| | Drama | Comédia | Terror | Ficção científica |
|---|---:|---:|---:|---:|
| Drama | 21 | 1 | 0 | 3 |
| Comédia | 10 | 13 | 0 | 2 |
| Terror | 14 | 4 | 5 | 2 |
| Ficção científica | 4 | 4 | 0 | 17 |

## Noul × regressão binária, por gênero (toda a amostra)

Cada gênero é uma pergunta sim/não. A ROC AUC usa o valor contínuo (Noul ou probabilidade da regressão) e não depende do limiar; o F1 usa o limiar 0.5. Filmes com dois gêneros contam como positivos nos dois.

| Gênero | Positivos | AUC Jev | AUC RL | F1 Jev | F1 RL |
|---|---:|---:|---:|---:|---:|
| Drama | 36 | 0.914 | 0.752 | 0.688 | 0.415 |
| Comédia | 33 | 0.966 | 0.825 | 0.828 | 0.561 |
| Terror | 32 | 0.989 | 0.808 | 0.925 | 0.528 |
| Ficção científica | 40 | 0.985 | 0.879 | 0.853 | 0.730 |

## Confiança e coerência do Jev

- Confiança média da Choice quando acerta: 0.927; quando erra: 0.634. Confiança mede a concentração das probabilidades, não a correção.
- A Choice coincide com o Noul mais alto em 94.2% dos filmes, e o Noul do gênero escolhido passa do limiar em 86.7%.

Casos de menor confiança:

| Filme | Gêneros do TMDB | Choice | Confiança | Probabilidades |
|---|---|---|---:|---|
| Esqueceram de Mim 2: Perdido em Nova York | Comédia | Drama | 0.27 | Drama 0.45, Comédia 0.28, Terror 0.27, Ficção científica 0.00 |
| Os Oito Odiados | Drama | Terror | 0.34 | Drama 0.49, Comédia 0.00, Terror 0.51, Ficção científica 0.00 |
| Kill Bill: The Whole Bloody Affair | Drama | Drama | 0.36 | Drama 0.53, Comédia 0.00, Terror 0.44, Ficção científica 0.03 |
| Um Drink no Inferno | Terror | Terror | 0.38 | Drama 0.36, Comédia 0.07, Terror 0.54, Ficção científica 0.03 |
| Maze Runner: Correr ou Morrer | Ficção científica | Terror | 0.45 | Drama 0.01, Comédia 0.00, Terror 0.59, Ficção científica 0.40 |

## Erros da Choice do Jev

| Filme | Gêneros do TMDB | Jev | Confiança | TF-IDF + RL |
|---|---|---|---:|---|
| V de Vingança | Ficção científica | Drama | 0.530 | Drama |
| Esqueceram de Mim 2: Perdido em Nova York | Comédia | Drama | 0.270 | Drama |
| O Segredo do Abismo | Ficção científica | Drama | 0.550 | Drama |
| Da Magia à Sedução | Comédia | Terror | 0.850 | Drama |
| Police Story: A Guerra das Drogas | Comédia | Drama | 1.000 | Ficção científica |
| Os Bad Boys | Comédia | Drama | 0.830 | Drama |
| Operação Cupido | Comédia | Drama | 0.640 | Drama |
| Quem é Essa Garota? | Comédia | Drama | 0.510 | Comédia |
| Maze Runner: Correr ou Morrer | Ficção científica | Terror | 0.450 | Comédia |
| Os Oito Odiados | Drama | Terror | 0.340 | Drama |
| Homem-Aranha: De Volta ao Lar | Ficção científica | Drama | 0.590 | Ficção científica |
| Deadpool 2 | Comédia | Ficção científica | 0.510 | Drama |
| Velozes & Furiosos: Hobbs & Shaw | Comédia | Ficção científica | 1.000 | Comédia |
| Entre Facas e Segredos | Comédia | Drama | 0.780 | Drama |
| A Guerra dos Mundos | Ficção científica | Drama | 0.660 | Comédia |

## Limitações

A amostra é pequena porque cada filme é uma chamada paga a uma API externa; as diferenças entre os métodos servem como ilustração, não como teste estatístico. O rótulo são os gêneros do TMDB restritos aos avaliados, e muitos filmes também pertencem a gêneros fora das opções (ação, romance, suspense), que ficam fora das opções. O Jev é acessado pelo alias mais recente: o modelo registrado acima pode mudar entre execuções, por isso as respostas brutas ficam em `responses.jsonl` e podem ser reavaliadas sem novas chamadas (`--reuse`). As perguntas e os critérios fazem parte da tarefa: outra redação pode mudar os resultados. O classificador de referência foi treinado só com os filmes deste corpus fora da amostra e não teve hiperparâmetros ajustados.

## Fonte

Dados: The Movie Database (TMDB), https://www.themoviedb.org/. Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB. Decisões estruturadas: Jev, da TypeSafe AI (https://docs.typesafe.ai/).
