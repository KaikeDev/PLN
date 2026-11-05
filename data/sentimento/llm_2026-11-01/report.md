# Sentimento com LLM × modelos treinados

200 críticas do TMDB sorteadas antes das chamadas (`config/sentimento/sentimento_llm_amostra.json`), metade negativas e metade positivas, metade do autor principal. 93 críticas passaram de 2000 caracteres e foram cortadas no meio, igual para todas as variantes. Modelos que responderam: `gemini:gemini-3.5-flash-lite`, `groq:openai/gpt-oss-20b`. As variantes de prompt rodam em `gemini`, e a reserva repete a variante escolhida (**few_shot**) em `groq`. O TF-IDF e o BERTimbau são as predições fora da dobra da Aula 9: nenhum dos sistemas viu essas críticas antes.

## Polaridade

| Sistema | F1 macro | Acurácia | Negativas lidas como positivas | Positivas lidas como negativas | Falhas |
|---|---:|---:|---:|---:|---:|
| TF-IDF (fora da dobra) | 0.791 | 0.795 | 35 | 6 | 0 |
| BERTimbau (fora da dobra) | 0.880 | 0.880 | 16 | 8 | 0 |
| LLM zero-shot | 0.930 | 0.930 | 10 | 2 | 28 |
| LLM few-shot | 0.925 | 0.925 | 9 | 4 | 27 |
| LLM zero-shot sem justificativa | 0.929 | 0.930 | 9 | 3 | 29 |
| LLM reserva (groq, few_shot) | 0.915 | 0.915 | 6 | 11 | 0 |

Na Aula 9, o F1 macro de 0,856 (TF-IDF) e 0,867 (BERTimbau) foi medido no conjunto completo, com 71% de positivas; aqui ele é recalculado na amostra equilibrada. As métricas do LLM contam só as críticas respondidas.

### Por estrato (F1 macro)

| Sistema | Com negação (177) | Sem negação (23) | Autor principal (100) | Demais autores (100) |
|---|---:|---:|---:|---:|
| TF-IDF (fora da dobra) | 0.806 | 0.516 | 0.870 | 0.696 |
| BERTimbau (fora da dobra) | 0.893 | 0.732 | 0.890 | 0.868 |
| LLM zero-shot | 0.934 | 0.892 | 0.909 | 0.958 |
| LLM few-shot | 0.928 | 0.896 | 0.919 | 0.931 |
| LLM zero-shot sem justificativa | 0.934 | 0.896 | 0.919 | 0.944 |
| LLM reserva (groq, few_shot) | 0.915 | 0.904 | 0.900 | 0.930 |

## Nota

| Sistema | Erro absoluto médio | Até 1 ponto | Respondidas |
|---|---:|---:|---:|
| Média das notas fora da amostra (6.48) | 2.83 | 0.14 | 200 |
| TF-IDF (fora da dobra) | 1.80 | 0.30 | 200 |
| BERTimbau (fora da dobra) | 1.53 | 0.41 | 200 |
| LLM zero-shot | 0.91 | 0.75 | 172 |
| LLM few-shot | 1.00 | 0.73 | 173 |
| LLM zero-shot sem justificativa | 0.94 | 0.73 | 171 |
| LLM reserva (groq, few_shot) | 1.04 | 0.74 | 200 |

## Nas mesmas críticas (169 de 200)

Alguma variante falhou em parte das críticas; aqui todos os sistemas são medidos só nas que todas as variantes responderam.

| Sistema | F1 macro | Acurácia | Erro absoluto médio da nota |
|---|---:|---:|---:|
| TF-IDF (fora da dobra) | 0.800 | 0.805 | 1.78 |
| BERTimbau (fora da dobra) | 0.881 | 0.882 | 1.60 |
| LLM zero-shot | 0.929 | 0.929 | 0.92 |
| LLM few-shot | 0.923 | 0.923 | 1.01 |
| LLM zero-shot sem justificativa | 0.929 | 0.929 | 0.94 |
| LLM reserva (groq, few_shot) | 0.905 | 0.905 | 1.08 |

## Onde os sistemas discordam

### Só o LLM (few_shot) acerta: os dois modelos treinados erram (10)

| Filme | Nota do autor | Trecho | LLM | TF-IDF | BERTimbau |
|---|---:|---|---|---|---|
| Meninos Não Choram | 1 | O filme é muito bem feito, entretanto fica aquela ideia de que um relacionamento entre homem e mulher, quando não dá certo, deveria ser substituído por mulher e mulher, homem e homem. Discordo. É um convite à heterofobia. Mas a atuação dela é brilhante no filme. | negativo, 4.5 — Elogia aspectos técnicos e atuação, mas rejeita a mensagem ideológica. | positivo (100%), nota 8.1 | positivo (86%), nota 6.3 |
| King Kong | 3 | Uma longa e tediosa hora de filme que poderia ter sido resumida em 5 min, foi o que fez esse filme ficar pior que o de 1976, Se Quiser assitir a historia contada aqui assista o 1976, E se quiser a Historia com elementos novos na ilha que foram aderidos nesse filme assista o de 2017. | negativo, 3 — Considera o filme longo e tedioso, inferior às versões anteriores. | positivo (71%), nota 4.2 | positivo (89%), nota 7.0 |
| Gallipoli | 8 | **A Austrália “nasceu” na Turquia.** Este é um filme muito interessante que aborda a participação conjunta da Austrália e a Nova Zelândia na Primeira Guerra Mundial. Ambos os países tinham tido a sua independência do Reino Unido há pouco tempo, não havia uma real sensação de identidade nacional e,… | positivo, 7.5 — Elogia a abordagem histórica interessante e as atuações principais, apesar de ressalvas sobre a violência atenuada. | negativo (47%), nota 5.3 | negativo (39%), nota 5.4 |

### Só os modelos treinados acertam: o LLM erra (8)

| Filme | Nota do autor | Trecho | LLM | TF-IDF | BERTimbau |
|---|---:|---|---|---|---|
| A Garota Ideal | 3 | **Apesar de Ryan Gosling ser extraordinariamente bom aqui, o filme não tem piada e o roteiro é incrivelmente inverosímil e exagerado.** Confesso que não sei muito bem o que pensar acerca deste filme. Reconheço a originalidade do assunto em causa, mas se a ideia era fazer comédia isso fracassou… | positivo, 7 — Apesar de criticar o humor e o roteiro, o autor elogia a excelente atuação de Ryan Gosling e aprova o filme. | negativo (1%), nota 4.3 | negativo (24%), nota 5.1 |
| Querida, Encolhi as Crianças | 4 | **Um bom filme familiar, ainda que não seja brilhante.** Há alguns filmes que deixam pouca memória na história do cinema mas que fazem a nossa memória pessoal voltar atrás no tempo. Este é um deles. Trata-se de uma comédia familiar bastante divertida, em que um cientista muito distraído cria uma… | positivo, 6.5 — Apesar de não ser brilhante, o autor o considera divertido e um bom filme familiar. | negativo (34%), nota 5.1 | negativo (27%), nota 5.2 |
| A Joia do Nilo | 7 | Seria uma tentativa de surfar na onda de "Indiana Jones" não tão bem sucedida? Sequencia de "Tudo por uma Esmeralda" um fofo que não conclui… Longe de ser ruim, Danny DeVito é sempre muito cativante, doses generosas de aventura, pitadas açucaradas de humor, roteiro simples, nada muito inesquecível,… | negativo, 4.5 — Apesar de elogiar Danny DeVito, considera o filme longo, cansativo e pouco inesquecível. | positivo (83%), nota 6.8 | positivo (92%), nota 5.5 |

## Casos da equipe

Críticas escritas pela equipe (as da aba do site), fora das métricas. TF-IDF da tela e LLM (few_shot). O BERTimbau não entra aqui: o experimento não guarda um modelo treinado com ele.

| Tipo | Crítica | TF-IDF da tela | LLM |
|---|---|---|---|
| elogio direto | Que filme maravilhoso! A fotografia é deslumbrante, as atuações são excelentes e a trilha sonora emociona do começo ao fim. Saí do cinema querendo ver de novo. | positivo (100% positiva), nota 9.33 | falhou (cota) |
| crítica negativa | Uma perda de tempo. O roteiro é confuso, os diálogos são fracos e o final é previsível. Fiquei entediado na metade e não recomendo. | negativo (41% positiva), nota 4.52 | falhou (cota) |
| negações | Não é um filme ruim. Não chega a ser uma obra-prima, mas não decepciona, e o elenco não deixa a desejar. | negativo (28% positiva), nota 4.88 | falhou (cota) |
| ironia | Ótimo, mais uma continuação que ninguém pediu, com as mesmas piadas de sempre e duas horas e meia de explosões. Genial. | positivo (96% positiva), nota 6.83 | falhou (cota) |

## Estabilidade

20 críticas pedidas duas vezes ao LLM (few_shot), com temperatura 0; 0 responderam nas duas.

| Polaridade igual | Nota igual | Diferença média da nota |
|---:|---:|---:|
| — | — | — |

## Custo

| Variante | Respostas | Tokens de entrada (média) | Tokens de saída (média) | Provedores | Falhas |
|---|---:|---:|---:|---|---|
| LLM zero-shot | 172 | 520.6 | 55.3 | gemini: 172 | cota: 28 |
| LLM few-shot | 173 | 825.1 | 49.0 | gemini: 173 | cota: 27 |
| LLM zero-shot sem justificativa | 171 | 494.3 | 21.2 | gemini: 171 | cota: 29 |
| LLM reserva (groq, few_shot) | 200 | 1071.1 | 98.8 | groq: 200 | nenhuma |

A latência de cada variante está em `manifest.json`: ela muda a cada execução e não entra nos arquivos de conteúdo.
