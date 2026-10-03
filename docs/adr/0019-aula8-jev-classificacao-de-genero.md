# 0019 — Classificação de gênero com o Jev comparada a TF-IDF + regressão logística (Aula 8)

- Estado: Aceita
- Data: 2026-09-28

## Contexto

A Aula 8 troca o pipeline clássico (`textos rotulados → TF-IDF → treino → classificador`) pelo **Jev**, modelo System One da TypeSafe AI. O Jev recebe um texto (`state`) e perguntas tipadas e devolve decisões estruturadas:

- **Choice** escolhe uma opção de um conjunto;
- **Score** posiciona o texto numa escala ordenada;
- **Noul** dá um valor de 0 a 1 para uma proposição.

O notebook de exemplo da aula classifica avaliações do B2W. Aqui, o corpus é o de sinopses do TMDB, e os rótulos disponíveis são os quatro gêneros dos recortes de coleta (ADR 0014). Cada chamada é paga, e o alias `jev-latest` pode apontar para outro modelo com o tempo.

## Decisão

- **Tarefa:** gênero da sinopse, com os quatro gêneros de coleta.
  - Uma **Choice** pergunta o gênero principal.
  - Um **Noul** por gênero pergunta se o filme é daquele gênero, o que cobre os filmes com dois gêneros.
  - As cinco perguntas vão numa única chamada por filme.
- **Sem Score:** o corpus não tem rótulo ordinal expresso na sinopse. A nota do TMDB não aparece no texto, e medir a escala contra ela avaliaria outra coisa.
- **Perguntas como dado:** instruções e critérios ficam em `config/jev.json`. O texto exato enviado vai para `questions.json`, e o hash dele, para o manifesto.
- **Amostra:** 25 filmes de gênero único por gênero e 20 com dois gêneros avaliados, sorteados com semente 42 (120 chamadas). A primeira execução usou 10 e 8 (48 chamadas); ao ampliar, a margem de erro da acurácia caiu de cerca de ±13 para cerca de ±8 pontos percentuais, e ainda sobram cerca de 300 filmes para o treino da referência. A amostra precisa deixar filmes de cada grupo para o treino.
- **Referência:** TF-IDF (etapa `06`) + regressão logística, treinada com os filmes fora da amostra.
  - Uma regressão multinomial, treinada só com filmes de um gênero, responde a Choice.
  - Uma regressão binária por gênero, com classes balanceadas, faz o papel do Noul.
  - Os dois métodos são medidos nos mesmos filmes e com as mesmas métricas: acerto do gênero principal, acurácia, F1 macro, matriz de confusão, ROC AUC e F1 por gênero, conjunto exato.
- **Porta e adaptador (ADR 0004):** o pipeline depende de `app.jev.ports.DecisionClient`. O SDK `typesafe-sdk` fica no extra opcional `jev`, só é importado em `app.infra.typesafe` e só na execução real.
- **Chave:** `TYPESAFE_API_KEY` no ambiente ou em `backend/.env`, lida como `SecretStr`, como o token do TMDB (ADR 0002).
- **Respostas como dado externo:** cada resposta é validada antes de entrar em métricas. A opção precisa estar entre as enviadas, e probabilidades, Nouls e confiança precisam ficar entre 0 e 1.
- **Falhas e custo:**
  - Se a primeira chamada falhar, nada é gravado.
  - As falhas seguintes ficam registradas e fora de todas as métricas, inclusive das da referência.
  - As respostas validadas vão para `responses.jsonl`, e `--reuse` as reaproveita, sem novas chamadas, quando perguntas e etapa são as mesmas.
  - O modelo informado pela API e o tempo das chamadas vão para o manifesto.

## Alternativas consideradas

- **Rodar o notebook do B2W:** reproduziria a aula, mas ficaria fora do corpus e das evidências do projeto.
- **Só a Choice:** perderia os filmes com dois gêneros e a ROC AUC, que não depende de limiar.
- **Uma chamada por pergunta:** multiplicaria o custo por cinco, sem ganho.
- **Treinar a referência com o corpus inteiro:** a amostra do Jev entraria no treino, e a comparação favoreceria a referência.
- **Chamar a API nos testes ou no CI:** exigiria segredo no CI e teria custo. Os testes usam um Jev falso.

## Consequências

- Com 120 filmes, as diferenças entre os métodos ilustram a aula, mas não são teste estatístico formal.
- Desde a [ADR 0018](0018-tarefas-do-ciclo-de-pln.md), o rótulo são os `genre_ids` do TMDB restritos aos quatro gêneros, os mesmos da classificação da [ADR 0017](0017-aula8-classificacao-de-generos.md), e o código do Jev passou a usá-los. Muitos filmes têm gêneros fora das opções (ação, romance, suspense).
- **Nova execução com os rótulos do TMDB (03/10/2026):** a amostra mudou; 47 das 120 sinopses reaproveitaram a resposta guardada (`--reuse`) e 73 foram chamadas de novo. Resultado: acurácia de 85,0% contra 56,0% do TF-IDF + regressão logística nos 100 filmes de um gênero, F1 macro de 0,85 contra 0,54 e ROC AUC macro por gênero de 0,96 contra 0,82.
- A redação das perguntas faz parte da tarefa: mudá-la muda o hash e impede o reaproveitamento das respostas.
- Com as mesmas respostas, os arquivos de conteúdo são idênticos byte a byte (ADR 0009). Já uma nova chamada ao Jev pode dar outro resultado.
- O `uv.lock` precisa ser regenerado (`uv lock`) para incluir o extra `jev`.
- A saída entregue fica em `data/jev/tmdb_2026-09-12/` e é versionada; outras pastas em `data/jev/` são ignoradas (ADR 0016). O CI roda `app.jev verify` nela a cada push, sem chamar a API.
