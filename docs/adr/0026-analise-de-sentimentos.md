# 0026 — Análise de sentimentos de críticas do TMDB (Aula 9)

- Estado: Aceita
- Data: 2026-10-10

## Contexto

A Aula 9 apresenta análise de sentimentos, NER e extração de relações. O corpus do projeto são sinopses, que descrevem o filme sem opinar: não há sentimento para medir nelas. O TMDB, porém, guarda críticas de usuários (`/movie/{id}/reviews`), e cada uma traz a nota de 0 a 10 que o autor deu ao filme (`author_details.rating`). Isso dá texto e rótulo juntos, sem anotação manual.

## Decisão

- **Dados:** as críticas em português dos 5.853 filmes do catálogo do site ([ADR 0024](0024-catalogo-do-site.md)), coletadas uma vez em `data/coleta/criticas_2026-10-10`.
  - O autor vira um código anônimo (SHA-256 truncado do usuário); nome, usuário e avatar não são gravados.
  - Erros de coleta registram só o tipo e o status HTTP.
- **Preparação** com as seis etapas de texto da Etapa 1, no mesmo formato de pasta, para reaproveitar `ProcessedCorpus` e as oito representações sem mudança.
  - **Críticas bilíngues:** só o texto fora das seções em inglês é usado.
  - **Ficam de fora:** críticas sem nota, com menos de 30 caracteres ou com mais palavras funcionais do inglês que do português.
- **Tarefas:**
  - **polaridade:** nota ≤ 4 é negativa, e nota ≥ 7, positiva; as do meio ficam de fora;
  - **nota:** todas as críticas, com regressão Ridge e a nota prevista limitada a 0–10.
- **Mesma avaliação da classificação de gêneros:** a validação cruzada, a regressão logística com classes balanceadas e C escolhido pela log loss em dobras internas, as métricas e os erros mais confiantes de `app.classification.evaluation`, sem cópia.
- **Dobras por filme:** críticas de um mesmo filme ficam na mesma dobra (`StratifiedGroupKFold`).
- **Teste entre autores:** um autor escreveu 67% das críticas, e agrupar por autor deixaria uma dobra com dois terços dos dados. À parte, o modelo é treinado sem esse autor e testado nele, e o contrário.
- **Transformers em partes:** a crítica é cortada em partes que cabem no modelo, pelas posições de caractere do tokenizador, e o vetor é a média normalizada das partes. Modelo, revisão e pooling continuam os da Etapa 2.
- **Na tela:** a regressão logística e o Ridge sobre o TF-IDF sem stopwords, ajustados com todas as críticas preparadas na inicialização da API. A resposta traz as palavras do texto de maior contribuição (coeficiente × valor TF-IDF) para cada polaridade.
- **Versionamento:** a coleta (4,6 MB) e o experimento (5 MB) vão para o Git; a preparação (29 MB) é refeita sem rede em segundos.

## Alternativas consideradas

- **Léxico de sentimento** (lista de palavras positivas e negativas): simples e interpretável, mas exigiria um recurso externo ao projeto e erra com negação e domínio; a regressão logística sobre o TF-IDF aprende os pesos das próprias críticas.
- **Agrupar as dobras por autor:** deixaria uma dobra com 67% das críticas. O teste entre autores mede a mesma coisa sem distorcer as dobras.
- **Ler só o começo da crítica nos transformers:** o MiniLM leria 128 tokens de uma mediana de 339 palavras e perderia o veredito, que costuma vir no fim.
- **BERTimbau na tela:** F1 macro 0,011 maior, mas 39 minutos para codificar as críticas na inicialização e sem palavras que expliquem a decisão.
- **Polaridade com três classes (neutra):** as notas 5 e 6 misturam críticas mornas e opiniões divididas; ficam só na previsão da nota.

## Consequências

- **Polaridade:** F1 macro de 0,867 (BERTimbau) e 0,856 (TF-IDF sem stopwords), contra 0,415 da referência. Nota: erro médio de 1,33 ponto (BERTimbau), contra 1,98 da média.
- **Generalização:** treinando sem o autor principal e testando nele, o TF-IDF cai para F1 0,507, e o BERTimbau mantém 0,808. Os números da validação cruzada valem sobretudo para o estilo desse autor.
- **Negação e ironia:** críticas com negação têm acurácia menor em todas as representações; os exemplos da tela mostram uma negação lida como negativa e uma ironia lida como positiva.
- **Dependência do TMDB:** uma coleta nova pode trazer outras críticas; o experimento entregue vale para a coleta de 10/10/2026.
