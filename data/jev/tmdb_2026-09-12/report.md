# Classificação de gênero com o Jev

Amostra de 120 sinopses: 25 de cada gênero único (Drama, Comédia, Terror, Ficção científica) e 20 com mais de um desses gêneros, sorteadas com semente 42. O Jev recebeu o texto da etapa `02_clean.jsonl` com uma Choice (gênero principal) e um Noul por gênero, na mesma chamada; não foi treinado com o corpus. O classificador de referência (TF-IDF da etapa `06_without_stopwords.jsonl` + regressão logística) foi treinado com os filmes fora da amostra e avaliado nos mesmos filmes.

Filmes avaliados: 120 de 120 (0 falhas do Jev, fora de todas as métricas). Modelo informado pela API: `jev-1.13.0`. Os gêneros de referência são os recortes de coleta do TMDB, não um julgamento sobre a sinopse.

## Resumo

| Métrica | Jev | TF-IDF + RL |
|---|---:|---:|
| Choice: gênero principal entre os do filme (toda a amostra) | 0.858 | 0.625 |
| Choice: acurácia nos 100 filmes de um gênero | 0.830 | 0.610 |
| Choice: F1 macro nos filmes de um gênero | 0.828 | 0.605 |
| Por gênero: ROC AUC macro | 0.947 | 0.838 |
| Por gênero: F1 macro com limiar 0.5 | 0.794 | 0.497 |
| Por gênero: conjunto de gêneros exato | 0.625 | 0.342 |

Os dois métodos escolhem o mesmo gênero principal em 55.0% dos filmes.

## Choice por gênero (filmes de um gênero)

| Gênero | Filmes | Precisão Jev | Revocação Jev | F1 Jev | Precisão RL | Revocação RL | F1 RL |
|---|---:|---:|---:|---:|---:|---:|---:|
| Drama | 25 | 0.774 | 0.960 | 0.857 | 0.800 | 0.480 | 0.600 |
| Comédia | 25 | 0.895 | 0.680 | 0.773 | 0.722 | 0.520 | 0.605 |
| Terror | 25 | 0.913 | 0.840 | 0.875 | 0.489 | 0.920 | 0.639 |
| Ficção científica | 25 | 0.778 | 0.840 | 0.808 | 0.650 | 0.520 | 0.578 |

Matriz de confusão — Jev (linhas: gênero de coleta; colunas: previsto):

| | Drama | Comédia | Terror | Ficção científica |
|---|---:|---:|---:|---:|
| Drama | 24 | 0 | 1 | 0 |
| Comédia | 2 | 17 | 1 | 5 |
| Terror | 2 | 1 | 21 | 1 |
| Ficção científica | 3 | 1 | 0 | 21 |

Matriz de confusão — TF-IDF + RL (linhas: gênero de coleta; colunas: previsto):

| | Drama | Comédia | Terror | Ficção científica |
|---|---:|---:|---:|---:|
| Drama | 12 | 3 | 7 | 3 |
| Comédia | 1 | 13 | 8 | 3 |
| Terror | 1 | 0 | 23 | 1 |
| Ficção científica | 1 | 2 | 9 | 13 |

## Noul × regressão binária, por gênero (toda a amostra)

Cada gênero é uma pergunta sim/não. A ROC AUC usa o valor contínuo (Noul ou probabilidade da regressão) e não depende do limiar; o F1 usa o limiar 0.5. Filmes com dois gêneros contam como positivos nos dois.

| Gênero | Positivos | AUC Jev | AUC RL | F1 Jev | F1 RL |
|---|---:|---:|---:|---:|---:|
| Drama | 37 | 0.914 | 0.787 | 0.750 | 0.449 |
| Comédia | 37 | 0.937 | 0.816 | 0.750 | 0.385 |
| Terror | 32 | 0.980 | 0.890 | 0.875 | 0.588 |
| Ficção científica | 34 | 0.958 | 0.858 | 0.800 | 0.566 |

## Confiança e coerência do Jev

- Confiança média da Choice quando acerta: 0.912; quando erra: 0.719. Confiança mede a concentração das probabilidades, não a correção.
- A Choice coincide com o Noul mais alto em 95.0% dos filmes, e o Noul do gênero escolhido passa do limiar em 86.7%.

Casos de menor confiança:

| Filme | Gêneros de coleta | Choice | Confiança | Probabilidades |
|---|---|---|---:|---|
| Possessão | Terror | Drama | 0.34 | Drama 0.51, Comédia 0.00, Terror 0.49, Ficção científica 0.00 |
| Super Mario Bros. O Filme | Comédia | Comédia | 0.36 | Drama 0.00, Comédia 0.53, Terror 0.00, Ficção científica 0.47 |
| Divertida Mente 2 | Comédia | Comédia | 0.38 | Drama 0.45, Comédia 0.54, Terror 0.00, Ficção científica 0.01 |
| Jogos Vorazes: A Esperança - Parte 1 | Ficção científica | Ficção científica | 0.42 | Drama 0.44, Comédia 0.00, Terror 0.00, Ficção científica 0.56 |
| A Morte lhe Cai Bem | Terror | Comédia | 0.45 | Drama 0.34, Comédia 0.59, Terror 0.00, Ficção científica 0.07 |

## Erros da Choice do Jev

| Filme | Gêneros de coleta | Jev | Confiança | TF-IDF + RL |
|---|---|---|---:|---|
| V de Vingança | Ficção científica | Drama | 0.530 | Drama |
| O Labirinto do Fauno | Drama | Terror | 0.460 | Terror |
| Extermínio 2 | Terror | Ficção científica | 0.490 | Terror |
| O Segredo do Abismo | Ficção científica | Drama | 0.550 | Terror |
| Police Story: A Guerra das Drogas | Comédia | Drama | 1.000 | Ficção científica |
| A Morte lhe Cai Bem | Terror | Comédia | 0.450 | Terror |
| Possessão | Terror | Drama | 0.340 | Terror |
| Os Croods | Comédia | Drama | 0.970 | Comédia |
| Meu Malvado Favorito 2 | Ficção científica | Comédia | 0.850 | Comédia |
| Operação Big Hero | Comédia | Ficção científica | 1.000 | Terror |
| O Esquadrão Suicida | Comédia | Ficção científica | 0.690 | Terror |
| Free Guy: Assumindo o Controle | Comédia | Ficção científica | 0.990 | Comédia |
| A Longa Marcha: Caminhe ou Morra | Terror | Drama | 0.540 | Terror |
| A Guerra dos Mundos | Ficção científica | Drama | 0.660 | Ficção científica |
| Guerreiras do K-Pop | Comédia | Terror | 0.940 | Ficção científica |
| Patrulha Canina: Um Filme Superpoderoso | Comédia | Ficção científica | 0.940 | Comédia |
| A Sapatona Galáctica | Comédia | Ficção científica | 0.830 | Comédia |

## Limitações

A amostra é pequena porque cada filme é uma chamada paga a uma API externa; as diferenças entre os métodos servem como ilustração, não como teste estatístico. O rótulo é o recorte de coleta, e muitos filmes pertencem a gêneros não avaliados (ação, romance, suspense), que ficam fora das opções. O Jev é acessado pelo alias mais recente: o modelo registrado acima pode mudar entre execuções, por isso as respostas brutas ficam em `responses.jsonl` e podem ser reavaliadas sem novas chamadas (`--reuse`). As perguntas e os critérios fazem parte da tarefa: outra redação pode mudar os resultados. O classificador de referência foi treinado só com os filmes deste corpus fora da amostra e não teve hiperparâmetros ajustados.

## Fonte

Dados: The Movie Database (TMDB), https://www.themoviedb.org/. Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB. Decisões estruturadas: Jev, da TypeSafe AI (https://docs.typesafe.ai/).
