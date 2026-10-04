# 0021 — Classificação de gênero na tela do site

- Estado: Aceita
- Data: 2026-10-03

## Contexto

A classificação de gêneros ([ADR 0017](0017-aula8-classificacao-de-generos.md)) e o Jev ([ADR 0019](0019-aula8-jev-classificacao-de-genero.md)) produziam só avaliações, em relatórios e métricas. Não havia como testar uma sinopse qualquer no site. A equipe pediu uma área em que se escreve ou cola uma sinopse e se vê o gênero previsto.

## Decisão

- **Classificador:** a mesma regressão logística avaliada na Etapa 3 (`estimator`: padronização, `C` escolhido pela log loss em dobras internas e classes balanceadas), ajustada com as 325 sinopses de um único gênero, sobre o embedding de sentença `sentenca_minilm`.
- **Por que o `sentenca_minilm`:** a busca por tema ([ADR 0020](0020-busca-hibrida-tfidf-e-sentenca.md)) já carrega esse modelo. O classificador reaproveita a representação construída por ela, sem modelo novo nem custo por uso. A representação é configurável (`synopsis_classifier_representation`), desde que faça parte da busca.
- **API:** `GET /classificacao?texto=...` (1 a 1.000 caracteres) devolve o gênero previsto, a probabilidade de cada gênero, a representação e o número de sinopses de treino.
  - Sem classificador, a rota responde 503.
  - Texto que a representação não consegue codificar responde 422.
  - Textos acima de 500 caracteres são cortados no último espaço antes do limite, já que o modelo de sentença trunca a entrada em 128 tokens.
- **Tela:** a seção "Classificar uma sinopse", com um campo de texto, mostra o gênero previsto e uma barra (`<progress>`) por gênero. A barra não depende de estilo inline, que a política de segurança da página bloqueia.
- **Arquitetura:**
  - a porta `GenreClassifier` fica em `app.classification`;
  - o modelo, em `app.classification.live`;
  - a montagem, em `app.main`, logo depois do índice de sinopses.

## Alternativas consideradas

- **BERTimbau ou skip-gram + regressão logística:** F1 macro um pouco maior na avaliação (70,2% e 71,0% contra 66,1%), mas cada um carregaria mais um modelo na API (cerca de 0,4 GB e 1,1 GB).
- **Jev:** a maior acurácia medida (85%), mas cada classificação seria uma chamada paga a um serviço externo, e a tela dependeria da chave.
- **Multirrótulo** (um "sim/não" por gênero): mostraria filmes de dois gêneros, mas o resultado da tela ficaria mais difícil de ler. A tarefa multiclasse é a que tem gênero previsto único.
- **TF-IDF + regressão logística:** dispensa modelo pré-treinado, mas tem o pior F1 entre as opções (59,2%) e erra quando o texto não repete palavras do corpus.

## Consequências

- **Qualidade:** a esperada é a da avaliação por validação cruzada, F1 macro de 66,1% para `sentenca_minilm`. Comédia é o gênero mais difícil. Frases curtas, que fogem do estilo das sinopses do TMDB, erram com frequência. Por exemplo, "um robô doméstico ganha consciência e passa a ameaçar a família" saiu como comédia.
- **Inicialização:** o ajuste com dobras internas leva alguns segundos a mais na API.
- **Sem o extra `semantico`:** como a busca por tema, a classificação fica indisponível, e a API continua subindo.
