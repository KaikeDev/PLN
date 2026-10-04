# Escolha dos modelos de classificação

**Etapa 3: classificação de gêneros a partir das sinopses (Aula 8)**
Equipe: Kaike Ventura Tuerpe, Luana Nitsche, Pedro Henrique Ortunio e Thiago Bodnar. Ciência da Computação, FURB.
Data: 28/09/2026.

Este documento justifica os modelos adotados para classificar o gênero de filmes a partir da sinopse. Também explica por que as demais abordagens apresentadas na Aula 8 não foram adotadas como modelo principal.

Seguimos a orientação da aula de que *“a adequação depende da tarefa e deve ser medida no mesmo conjunto de avaliação”*. Por isso, sempre que possível, a justificativa se apoia em medidas: as alternativas clássicas foram executadas nas mesmas dobras, com a mesma preparação dos dados. Os números citados vêm do [relatório gerado](../data/classificacao/tmdb_2026-09-12/report.md) e dos arquivos `results.json`, `alternatives.json` e `clustering.json` da mesma pasta. Os tempos vêm de `manifest.json`. A seção 11 mostra como reproduzi-los.

## 1. Decisão em resumo

| Decisão | Escolha | Principal motivo |
|---|---|---|
| Tarefa | Prever o gênero pela sinopse em duas formulações: **multiclasse** (325 filmes com um único gênero) e **multirrótulo** (428 filmes) | Os rótulos já existem no TMDB, e 24% dos filmes têm mais de um dos quatro gêneros |
| Classificador | **Regressão logística** com pesos de classe balanceados e `C` escolhido pela log loss em dobras internas do treino | Teve o maior F1 macro medido (71,0%), fica entre os melhores em 6 das 8 representações e é o único que combina probabilidades calibradas e coeficientes legíveis |
| Representações | BoW, TF-IDF, word2vec (CBOW e skip-gram), BERTimbau congelado e um modelo de sentença | Repetem a progressão da disciplina; com o mesmo classificador, isolam o efeito da representação |
| Referência | Classificador que ignora o texto e prevê o gênero mais frequente | Mostra quanto do resultado vem, de fato, da sinopse |
| Não adotados como modelo principal | Naive Bayes, SVM linear, floresta aleatória, k vizinhos e K-Means (medidos); BERT ajustado, LLM com instrução e Jev (não medidos) | Seções 5 e 6 |

## 2. Critérios de escolha

A Aula 8 propõe comparar as abordagens para o mesmo problema por cinco critérios. Acrescentamos dois critérios que o projeto já adotava desde a Etapa 1.

| Critério | Como foi avaliado |
|---|---|
| Qualidade | F1 macro (média do F1 dos quatro gêneros) em validação cruzada de 5 dobras, com as mesmas dobras para todos os modelos. O desvio entre dobras fica entre 2 e 7 pontos, então diferenças menores que isso não são conclusivas |
| Dados rotulados | 325 filmes na multiclasse, ou cerca de 260 por dobra de treino. Modelos que precisam de muitos exemplos ficam em desvantagem |
| Custo computacional | Tempo em CPU (não há GPU disponível) e número de parâmetros |
| Interpretabilidade | Se é possível explicar, em palavras, por que o modelo escolheu um gênero |
| Necessidade de texto gerado | A saída é um de quatro rótulos; gerar texto livre não é necessário |
| Tratamento da incerteza | Se o modelo fornece probabilidades e se elas acompanham a taxa real de acerto |
| Reprodutibilidade (ADR 0009) | As mesmas entradas devem gerar os mesmos arquivos, sem depender de serviços externos |

## 3. O problema e a formulação da tarefa

### 3.1 Dados e rótulos

A amostra tem 428 sinopses preenchidas; os 2 filmes sem sinopse ficam fora das duas tarefas. Os rótulos são os gêneros que o TMDB atribui ao filme (`genre_ids`), restritos aos quatro gêneros da coleta: drama, comédia, terror e ficção científica. Não houve anotação manual.

| Gênero | Multiclasse | Multirrótulo |
|---|---:|---:|
| Drama | 89 | 136 |
| Comédia | 85 | 136 |
| Terror | 66 | 119 |
| Ficção científica | 85 | 144 |

Dois exemplos mostram as características desses rótulos:

- **Filmes com mais de um gênero.** *Brilho Eterno de uma Mente sem Lembranças* é ficção científica e drama: *“Joel se surpreende ao saber que seu amor verdadeiro, Clementine, o apagou completamente de sua memória […]”*. Os dois gêneros estão corretos, e forçar um só descartaria informação.
- **O gênero é do filme, não da sinopse.** *A Hora do Rush* (ação, comédia e crime no TMDB) vira “comédia” quando restringimos aos quatro gêneros. A sinopse, porém, não tem nenhuma pista de comédia: *“Quando a filha de um diplomata chinês é sequestrada em Los Angeles, o cônsul chama o inspector Lee […] para ajudar o FBI com o caso”*. Esse ruído limita qualquer modelo que leia só a sinopse.

### 3.2 Por que multiclasse e multirrótulo

- **Multiclasse** (325 filmes com exatamente um dos gêneros): é a formulação mais simples de avaliar e interpretar. Tem uma matriz de confusão 4 × 4, F1 por gênero e acurácia comparável entre modelos. Por isso concentra a comparação entre classificadores.
- **Multirrótulo** (428 filmes; 103 têm dois ou três gêneros): corresponde à estrutura real dos dados. É resolvida com um classificador binário por gênero (*one-vs-rest*). Um gênero é atribuído quando sua probabilidade é ≥ 0,5, e o mais provável sempre é atribuído, porque todo filme tem ao menos um gênero.
- **Binária**, como tarefa principal, foi descartada. Uma pergunta do tipo “é terror?” esconderia a confusão mais importante, entre comédia e drama. Ela aparece, porém, dentro do multirrótulo: cada gênero é uma decisão binária.
- **Ordinal** não se aplica, porque gêneros não têm ordem. O único alvo ordinal disponível seria a nota (`vote_average`), que mede a recepção do público, não o conteúdo da sinopse.

## 4. O modelo escolhido: regressão logística

A regressão logística aprende, para cada gênero, um peso por atributo da representação. A probabilidade de cada gênero é obtida aplicando a função *softmax* às somas ponderadas; no multirrótulo, cada gênero usa uma sigmoide. A fronteira de decisão é um hiperplano, exatamente a figura do slide *“O modelo aprende uma fronteira de decisão”*. A regularização `C` controla o tamanho dos pesos e é escolhida pela log loss em 3 dobras internas, usando só o treino de cada dobra.

### 4.1 Motivos, com exemplos

**a) Maior F1 medido.** A melhor combinação medida entre todos os modelos e representações é word2vec skip-gram + regressão logística, com **71,0%** de F1 macro na multiclasse. O segundo e o terceiro lugares são skip-gram + SVM (70,3%) e BERTimbau + regressão logística (70,2%). Nas três representações de melhor desempenho (os dois word2vec e o BERTimbau), a regressão logística tem o maior F1. No TF-IDF e no modelo de sentença, fica a até 1,7 ponto do melhor, dentro do desvio entre dobras. Ela só perde com clareza nas contagens brutas (BoW), para o Naive Bayes (seção 5.1).

**b) Probabilidades que acompanham a taxa de acerto.** A regressão logística ajusta os pesos minimizando a log loss, então suas probabilidades têm significado. Com o BERTimbau, a confiança média é de 74,9% nos acertos e de 56,2% nos erros, com acurácia de 70,2%. A confiança média geral (0,702 × 74,9% + 0,298 × 56,2% ≈ 69,3%) fica próxima da acurácia, e o modelo sinaliza quando está inseguro. Essas probabilidades são usadas duas vezes: na regra de decisão do multirrótulo (probabilidade ≥ 0,5) e na análise de incerteza, pedida no critério *“tratamento da incerteza”*.

*Exemplo do cuidado necessário:* na versão anterior, `C` era escolhido pelo F1. Como o F1 só olha o gênero mais provável, as dobras internas preferiam uma regularização fortíssima, que achatava as probabilidades sem mudar o gênero escolhido. No modelo de sentença, a confiança média nos acertos caiu para 41,5%, com acurácia de 66,8%. Escolhendo pela log loss, o F1 ficou praticamente igual, e as probabilidades voltaram a acompanhar a acurácia.

**c) Interpretabilidade.** Nas representações lexicais, cada peso corresponde a uma palavra. Os termos de maior peso por gênero, com TF-IDF sem stopwords, são:

| Gênero | Termos com maior peso |
|---|---|
| Drama | jovem, edward, vida, história, durante, segunda, conhece, nick, soldados, dinheiro |
| Comédia | amigos, aventura, gato, novas, addams, fiona, shrek, sempre, usando, deadpool |
| Terror | demônios, grupo, casa, filho, drácula, começa, blade, caso, vampiro, vidas |
| Ficção científica | planeta, peter, futuro, terra, parker, inimigo, missão, vingadores, humanidade, mundo |

A tabela mostra o que o modelo aprendeu com sentido (“demônios”, “vampiro”, “planeta”, “futuro”). Também expõe o que não generaliza: nomes de personagens e franquias (“shrek”, “fiona”, “addams”, “peter parker”, “vingadores”). Um modelo não linear não permitiria esse diagnóstico com a mesma facilidade.

**d) Um único modelo para todas as representações.** O mesmo classificador se aplica a vetores esparsos de quase 6 mil dimensões e a vetores densos de 300 a 768 dimensões, e fica entre os melhores em 6 das 8 representações (no máximo 1,7 ponto abaixo do melhor). Isso permite atribuir as diferenças à representação. Com a regressão logística, trocar a representação muda o F1 macro em até 24,9 pontos (de 46,1% no BoW com pontuação a 71,0% no skip-gram). Os outros classificadores não oferecem essa comparação: o Naive Bayes não se aplica aos vetores densos, e o kNN varia de 28,2% a 67,7% conforme a representação.

**e) Custo baixo.** A validação cruzada completa (5 dobras, cada uma com a escolha interna de `C`) leva de 1,6 a 5,6 segundos por representação em CPU. A exceção é o BoW com pontuação, que leva 16,4 segundos. Nas representações densas, o custo está em gerar os vetores (o BERTimbau leva de 36 a 53 segundos para as 428 sinopses, conforme a execução), não no classificador; com `--vectors`, a Etapa 3 lê os vetores já gerados pela Etapa 2.

**f) Controle de sobreajuste.** Com cerca de 260 exemplos por dobra e até 6 mil atributos, um modelo sem regularização decoraria o treino. `C` é escolhido numa grade de 10⁻⁶ a 10⁴. Ela foi ampliada depois que escolhas no limite da grade antiga (0,01 a 100) indicaram que o ótimo estava fora dela. O valor escolhido se repete nas 5 dobras em quase todas as representações: 0,01 nas densas e 1000 no TF-IDF. Essa estabilidade indica que a escolha é robusta.

### 4.2 Limitações da escolha

- A fronteira é linear. Nas representações densas isso pesa pouco, porque os vetores pré-treinados já concentram a não linearidade; nas lexicais, interações entre palavras não são capturadas.
- Os pesos balanceados deslocam as probabilidades em direção a classes menores. Com gêneros quase equilibrados (66 a 89 filmes), o efeito é pequeno.
- A calibração não é perfeita em todas as representações. No skip-gram, a confiança média geral (≈ 61,5%) fica abaixo da acurácia (71,1%).

## 5. Alternativas medidas e não escolhidas

Todas as alternativas usaram as mesmas 5 dobras externas e a mesma preparação da regressão logística: vocabulário e idf ajustados no treino de cada dobra, e padronização dos vetores densos. Cada uma escolheu o próprio hiperparâmetro pelo **F1 macro** em 3 dobras internas; a floresta aleatória usou 300 árvores, sem ajuste. Como a regressão logística escolhe `C` pela log loss e não pelo F1, a comparação em F1 é conservadora para ela.

**F1 macro na tarefa multiclasse** (325 filmes; referência que ignora o texto: 10,7%). Em negrito, o maior valor de cada linha; “—” indica que não se aplica.

| Representação | Regressão logística | Naive Bayes | SVM linear | Floresta aleatória | k vizinhos |
|---|---:|---:|---:|---:|---:|
| BoW com pontuação | 46,1% | **59,1%** | 47,5% | 44,2% | 28,2% |
| BoW sem stopwords | 56,4% | **61,3%** | 56,1% | 47,4% | 53,3% |
| TF-IDF com pontuação | 59,3% | 60,1% | **60,4%** | 43,5% | 53,3% |
| TF-IDF sem stopwords | 59,2% | 58,9% | **59,4%** | 49,4% | 53,3% |
| word2vec CBOW | **67,6%** | — | 66,5% | 60,5% | 61,8% |
| word2vec skip-gram | **71,0%** | — | 70,3% | 65,4% | 61,1% |
| BERTimbau congelado | **70,2%** | — | 70,0% | 68,2% | 65,2% |
| Modelo de sentença | 66,1% | — | **67,8%** | 66,9% | 67,7% |

Na mesma representação, trocar o classificador muda o F1 em média 11,9 pontos. Trocar a representação, com a regressão logística, muda até 24,9 pontos. **A representação pesa mais que o classificador**, e por isso a Etapa 3 compara oito representações com um classificador fixo, e não o contrário.

### 5.1 Naive Bayes multinomial

**O que é.** É um modelo gerativo: estima a probabilidade de cada palavra em cada gênero a partir das contagens do treino, com suavização `alpha`, e supõe que as palavras são independentes entre si dado o gênero. É o classificador de texto clássico (McCallum e Nigam, 1998).

**O que medimos.** É o melhor classificador nas contagens brutas: 59,1% contra 46,1% da regressão logística no BoW com pontuação, e 61,3% contra 56,4% no BoW sem stopwords. Essa diferença supera o desvio entre dobras (cerca de 4 pontos). No TF-IDF, empata com os demais (58,9% a 60,1%). É também o mais rápido: cerca de 0,7 segundo para as 5 dobras.

**Por que não é o modelo principal.**
- Não se aplica às melhores representações. O modelo multinomial exige atributos não negativos, como contagens, e os vetores densos padronizados têm valores negativos. Seu melhor resultado (61,3%) fica quase 10 pontos abaixo dos 71,0% do skip-gram com regressão logística.
- A hipótese de independência não se sustenta em texto: “peter” e “parker” quase sempre aparecem juntos. Ela também produz probabilidades extremas, próximas de 0 ou 1, como mostram Niculescu-Mizil e Caruana (2005). Isso prejudica o tratamento da incerteza.

**Quando seria a escolha certa.** Se o projeto usasse só representações lexicais, ou precisasse de treino instantâneo com poucos exemplos, o Naive Bayes com BoW seria a escolha: teve o maior F1 entre as lexicais. Isso está de acordo com Ng e Jordan (2002): modelos gerativos atingem seu desempenho máximo com menos exemplos que os discriminativos.

### 5.2 SVM linear

**O que é.** Também separa os gêneros por hiperplanos, como a regressão logística, mas maximizando a margem entre as classes (perda *hinge*) em vez de modelar probabilidades. É um modelo forte para texto (Joachims, 1998).

**O que medimos.** Empata com a regressão logística em todas as representações. As diferenças, para um lado ou para o outro, vão de 0,2 a 1,7 ponto, dentro do desvio entre dobras. O SVM fica à frente em quatro representações (BoW com pontuação, os dois TF-IDF e o modelo de sentença), e a regressão logística, nas outras quatro, incluindo as três de melhor desempenho. O melhor resultado do SVM é 70,3% (skip-gram).

**Por que não é o modelo principal.**
- Não produz probabilidades, só um escore de distância à fronteira. Para obtê-las, seria preciso calibrar o escore com uma sigmoide ajustada em dados separados (Platt, 1999), o que acrescenta outra rodada de validação cruzada. Sem probabilidades, não há como aplicar a regra do multirrótulo (≥ 0,5) nem medir a incerteza.
- Com F1 equivalente, a regressão logística entrega probabilidades de graça, e o critério de desempate passa a ser o tratamento da incerteza.

**Quando seria a escolha certa.** Se só o rótulo importasse e as probabilidades fossem dispensáveis, o SVM seria uma alternativa equivalente.

### 5.3 Floresta aleatória (árvores e *ensembles*)

**O que é.** É um conjunto de árvores de decisão, cada uma treinada numa amostra com reposição e com um subconjunto aleatório de atributos em cada divisão (Breiman, 2001). A decisão é a votação das árvores. É um modelo não linear.

**O que medimos.** É fraca nas representações lexicais (43,5% a 49,4%), abaixo da regressão logística em todas elas (de 1,9 a 15,8 pontos). Nas densas, fica abaixo em três das quatro. A exceção é o modelo de sentença (66,9% contra 66,1%), dentro do desvio. Leva de 5,7 a 7,6 segundos em qualquer representação e tem a maior variação entre dobras medida (6,5 pontos, no BERTimbau).

**Por que não é o modelo principal.**
- Com cerca de 260 exemplos e milhares de atributos esparsos, cada divisão da árvore enxerga poucas palavras informativas e poucos exemplos. A não linearidade, que é a vantagem do modelo, não compensa a falta de dados.
- A interpretação se dá por importâncias globais dos atributos, que dizem quais palavras importam, mas não para qual gênero apontam. Os coeficientes da regressão logística dizem as duas coisas.

**Quando seria a escolha certa.** Com atributos tabulares heterogêneos, como ano, duração, orçamento e nota combinados com o texto, ou com muito mais exemplos.

### 5.4 k vizinhos mais próximos (cosseno)

**O que é.** Não treina um modelo: guarda as sinopses de treino e atribui o gênero mais frequente entre as `k` mais próximas pelo cosseno. É a busca por similaridade da Etapa 2 transformada em decisão.

**O que medimos.** O resultado depende inteiramente da representação: 28,2% no BoW com pontuação, com acurácia (29,2%) próxima da referência que ignora o texto (27,4%); 53,3% no TF-IDF; e 67,7% no modelo de sentença. Nesta última, empata com o melhor classificador (67,8%). Nas demais representações densas, fica 5 a 10 pontos abaixo da regressão logística.

**Por que não é o modelo principal.**
- A qualidade depende de a representação já agrupar os gêneros por proximidade, o que só o modelo de sentença faz bem. A regressão logística aprende quais dimensões importam, e o kNN pesa todas igualmente.
- O custo de previsão cresce com o tamanho do treino, porque cada nova sinopse é comparada com todas as guardadas.
- As “probabilidades” são proporções de vizinhos (múltiplos de 1/k), pouco informativas para a incerteza.

**Quando seria a escolha certa.** Quando os gêneros mudam com frequência. Basta acrescentar exemplos, sem retreinar. Também serve quando a explicação desejada é *“parecido com estes filmes”*.

### 5.5 K-Means: por que classificar e não agrupar

**O que é.** A clusterização da Etapa 2, que agrupa as sinopses por proximidade sem usar rótulos. Rodamos o K-Means com k = 4 nas mesmas 325 sinopses e comparamos os grupos com os gêneros pelo índice de Rand ajustado (ARI; Hubert e Arabie, 1985). O ARI fica perto de 0 para grupos ao acaso e vale 1 na coincidência perfeita, e mede da mesma forma grupos e previsões.

**O que medimos.** O classificador supera o agrupamento em ARI nas 8 representações.

| Representação | K-Means: ARI | Classificador: ARI | K-Means: acurácia com o melhor mapeamento | Classificador: acurácia |
|---|---:|---:|---:|---:|
| TF-IDF sem stopwords | 0,010 | 0,221 | 31,4% | 59,7% |
| word2vec skip-gram | 0,055 | 0,381 | 39,4% | 71,1% |
| BERTimbau congelado | 0,132 | 0,369 | 47,7% | 70,2% |
| Modelo de sentença | 0,129 | 0,299 | 49,8% | 65,8% |

A acurácia com o melhor mapeamento associa cada grupo ao gênero com que mais coincide, usando os rótulos. É, portanto, um teto otimista para usar grupos como classes, e mesmo assim fica 16 a 32 pontos abaixo do classificador.

**Exemplo.** No BERTimbau, um grupo reúne 58 filmes de ficção científica, mas também 21 comédias. Os filmes mais próximos do centro desse grupo são *Thor: Amor e Trovão*, *Mad Max: Estrada da Fúria* e *O Exterminador do Futuro 2*. O K-Means encontrou “filmes de ação e aventura”, que é um agrupamento real das sinopses, mas não é a divisão por gênero que queremos. Outro grupo mistura quase igualmente drama (32), comédia (35) e terror (31) em torno de “casa” e “família”.

**Por que não.** A clusterização responde a outra pergunta (*“que grupos existem?”*), como diz o slide *“Descobrir grupos ou reconhecer classes?”*. Quando as classes já estão definidas e há exemplos rotulados, a classificação usa essa informação, e o agrupamento a ignora.

**Quando seria a escolha certa.** Na exploração de um corpus sem rótulos, ou para descobrir categorias que ninguém definiu, como a “ação e aventura” acima.

## 6. Alternativas não medidas

### 6.1 BERT ajustado (*fine-tuning*)

**O que é.** Em vez de usar o BERTimbau congelado como extrator de vetores, todos os seus cerca de 109 milhões de parâmetros seriam ajustados junto com uma camada de classificação (Devlin et al., 2019; Souza et al., 2020). É a linha “BERT ajustado” da tabela da aula.

**Por que não nesta entrega.**
- **Dados:** cerca de 260 exemplos por dobra para ajustar 109 milhões de parâmetros. O risco de sobreajuste e de instabilidade é alto; o próprio artigo do BERT relata ajuste instável do BERT-Large em conjuntos pequenos, contornado com várias reinicializações.
- **Custo:** não há GPU. Só gerar os vetores das 428 sinopses em CPU levou de 36 a 53 segundos. O ajuste exige retropropagação (algumas vezes o custo da inferência) repetida por época, por dobra e por combinação de hiperparâmetros, como a taxa de aprendizado. Uma estimativa grosseira para 3 épocas × 5 dobras com uma única configuração fica na casa de 20 minutos, sem contar a busca interna de hiperparâmetros.
- **Ganho incerto:** o BERTimbau congelado (70,2%) já empata com o word2vec skip-gram (71,0%). Nesta amostra, não há evidência de que a representação contextual seja o gargalo.

**Como avaliaríamos.** Com GPU, nas mesmas 5 dobras e com validação interna para a taxa de aprendizado e o número de épocas, registrando as sementes.

### 6.2 LLM com instrução

**O que é.** Um modelo gerativo recebe a sinopse e uma instrução, por exemplo *“Classifique em exatamente um gênero: drama, comédia, terror ou ficção científica”*, e responde em texto. Não precisa de exemplos rotulados (*zero-shot*).

**Por que não nesta entrega.**
- **Não precisamos gerar texto.** O slide pergunta: *“Se a tarefa é escolher uma classe, precisamos necessariamente gerar texto?”* Aqui, não: a saída é um de quatro rótulos, e temos 325 exemplos rotulados para treinar um modelo barato.
- **Saída a restringir.** Para *A Hora do Rush*, uma resposta plausível seria “ação” ou “comédia policial”, que não pertencem à lista. A resposta precisaria ser forçada a um formato estruturado e convertida, e isso já é uma decisão tipada.
- **Contaminação da avaliação.** Um LLM treinado com dados da web provavelmente conhece esses filmes. Pela sinopse, ele pode reconhecer o título e responder o gênero que já sabe, e não o que a sinopse indica. A medida deixaria de avaliar a leitura da sinopse.
- **Reprodutibilidade, custo e dados:** cada sinopse seria enviada a um serviço externo, pago por chamada. O modelo pode mudar de versão, e as respostas variam entre execuções. Isso contraria a ADR 0009, que exige que as mesmas entradas gerem os mesmos arquivos.

**Como avaliaríamos.** Nas mesmas dobras de teste, com saída restrita às quatro opções, versão do modelo fixada e as respostas brutas guardadas como evidência. Também compararíamos filmes conhecidos com sinopses reescritas, para medir a contaminação.

### 6.3 Jev (TypeSafe)

**O que é.** Segundo a fornecedora, recebe um estado e perguntas com respostas previamente definidas e devolve decisões estruturadas com distribuições de probabilidade. No exemplo do slide, o estado é *“A entrega demorou muito.”* e as opções são positivo, neutro e negativo.

**Por que não nesta entrega.**
- É um produto em acesso inicial, cujo desempenho e calibração são anunciados pela própria fornecedora. A aula ressalta que isso exige avaliação independente.
- Depende de serviço externo, com as mesmas limitações de reprodutibilidade do LLM.
- A ideia central, decisão entre opções fixas com probabilidades, já é o que a regressão logística entrega localmente: estado = sinopse, opções = quatro gêneros, saída = probabilidades medidas na seção 4.1.

## 7. Por que estas representações

A comparação de representações acompanha a progressão da disciplina (BoW/TF-IDF → word2vec → BERT). Os vetores word2vec são os pré-treinados do NILC (Mikolov et al., 2013; Hartmann et al., 2017); o BERTimbau é usado congelado (Souza et al., 2020); o modelo de sentença é um transformer multilíngue ajustado para similaridade (Reimers e Gurevych, 2020). Com a regressão logística:

| Representação | Multiclasse: F1 macro | Multirrótulo: F1 macro | Log loss (multiclasse) |
|---|---:|---:|---:|
| Referência (ignora o texto) | 10,7% | 20,4% | 1,380 |
| BoW com pontuação | 46,1% | 54,4% | 1,220 |
| BoW sem stopwords | 56,4% | 57,6% | 1,036 |
| TF-IDF com pontuação | 59,3% | 58,0% | 1,028 |
| TF-IDF sem stopwords | 59,2% | 60,0% | 0,965 |
| word2vec CBOW | 67,6% | 68,3% | 0,854 |
| word2vec skip-gram | 71,0% | 71,1% | 0,779 |
| BERTimbau congelado | 70,2% | 69,8% | 0,725 |
| Modelo de sentença | 66,1% | 66,8% | 0,860 |

- **Densas superam lexicais** em 7 a 12 pontos (do modelo de sentença, com 66,1%, ao skip-gram, com 71,0%, contra 59,3% do melhor TF-IDF). Com cerca de 260 sinopses por dobra, filmes do mesmo gênero raramente compartilham as mesmas palavras. Os vetores pré-treinados aproximam palavras diferentes de sentido parecido. É o caso da Etapa 2: a consulta *“filme sobre simulação da realidade”* coloca Matrix entre o 11º e o 69º lugar nas representações lexicais, porque “simulação” não aparece na sinopse. Com o skip-gram, ele sobe para o 5º lugar.
- **Skip-gram e BERTimbau empatam.** A diferença (0,8 ponto) é menor que o desvio entre dobras (até 5,7 pontos). O BERTimbau tem a melhor log loss (0,725), e o skip-gram, o maior F1. Como o skip-gram custa bem menos (cerca de 7 segundos para gerar os vetores, contra 53), numa aplicação real ele seria preferível, salvo se a qualidade das probabilidades pesar mais.
- **Remover stopwords** ajuda o BoW (46,1% → 56,4%), porque palavras funcionais dominam as contagens. No TF-IDF isso quase não muda nada, pois o idf já reduz o peso dessas palavras.

## 8. Síntese: critérios × modelos

| Modelo | Usa rótulos | Custo em CPU (5 dobras) | Interpretabilidade | Probabilidades | Reprodutível | Melhor F1 macro medido |
|---|---|---|---|---|---|---|
| **Regressão logística** | sim | 1,6 a 16 s | pesos por gênero legíveis nas lexicais | sim, e acompanham a acurácia | sim | **71,0%** (skip-gram) |
| Naive Bayes multinomial | sim | ~0,7 s | probabilidade de cada palavra por gênero | extremas (hipótese de independência) | sim | 61,3% (BoW); não se aplica às densas |
| SVM linear | sim | 1,5 a 10 s | pesos por gênero | não; exige calibração | sim | 70,3% (skip-gram) |
| Floresta aleatória | sim | 5,7 a 7,6 s | só importâncias globais | votação das árvores | sim | 68,2% (BERTimbau) |
| k vizinhos | sim | 1,0 a 2,7 s | filmes vizinhos como exemplo | proporção de vizinhos | sim | 67,7% (sentença) |
| K-Means | não | < 0,3 s | termos por grupo | não | sim | ARI ≤ 0,13 (classificação: até 0,38) |
| BERT ajustado | sim | alto; exige GPU | baixa | sim | parcial (sementes, hardware) | não medido |
| LLM com instrução | não (*zero-shot*) | por chamada, externo | explicação em texto, não verificável | não nativamente | não | não medido |
| Jev (TypeSafe) | segundo a fornecedora | externo | não avaliada | segundo a fornecedora | não | não medido |

## 9. Quando a escolha mudaria

| Situação | Escolha recomendada |
|---|---|
| Só representações lexicais, ou treino instantâneo | Naive Bayes multinomial com BoW (61,3%, cerca de 0,7 s) |
| Só o rótulo importa; probabilidades dispensáveis | SVM linear, equivalente em F1 |
| Muito mais exemplos rotulados e GPU disponível | BERTimbau ajustado, avaliado nas mesmas dobras |
| Nenhum exemplo rotulado | LLM com saída restrita às opções, avaliado contra rótulos de referência |
| Categorias ainda não definidas | K-Means para explorar e nomear grupos |
| Gêneros que mudam com frequência | k vizinhos com um bom modelo de sentença (67,7%), sem retreinar |
| Explicação em linguagem natural exigida | LLM, ciente de que a explicação não é verificável |

## 10. Limitações

- A amostra é pequena e intencional (ADR 0014). Diferenças menores que o desvio entre dobras (2 a 7 pontos) não são conclusivas, e várias comparações deste documento estão nessa faixa.
- As alternativas foram comparadas só na tarefa multiclasse e só pelo gênero previsto. A floresta aleatória não teve ajuste de hiperparâmetros.
- Os tempos são de uma única máquina e servem para comparar ordens de grandeza, não para prometer desempenho.
- BERT ajustado, LLM e Jev não foram medidos; as justificativas da seção 6 são argumentos, não resultados.
- O rótulo é do filme, não da sinopse. Parte dos erros, como as comédias de ação reduzidas a “comédia”, vem do rótulo e limita qualquer modelo. Quatro dos oito erros mais confiantes do BERTimbau são desse tipo: *A Hora do Rush*, *Magnatas do Crime*, *Thor: Amor e Trovão* e *Kingsman*.

## 11. Como reproduzir os números

Em `backend`, lendo os vetores densos verificados da Etapa 2:

```bash
uv run --frozen python -m app.classification build --input ../data/preparacao/tmdb_2026-09-12 --output ../data/classificacao/completo --config ../config/classificacao/classificacao_semantica.json --vectors ../data/representacoes/tmdb_2026-09-12
uv run --frozen python -m app.classification verify --input ../data/classificacao/completo
```

Sem `--vectors`, as representações densas são recalculadas com o extra `semantico`. Os vetores guardados têm seis casas decimais, então a floresta aleatória pode variar até 0,3 ponto entre as duas formas ([ADR 0018](adr/0018-tarefas-do-ciclo-de-pln.md)).

- Resultados da regressão logística: `results.json`.
- Classificadores alternativos: `alternatives.json`.
- K-Means: `clustering.json`.
- Tempos: `manifest.json` (`seconds`).
- Tabelas prontas: `report.md`.

As decisões estão registradas na [ADR 0017](adr/0017-aula8-classificacao-de-generos.md), e a leitura geral dos resultados, em [classificacao.md](6-classificacao.md).

## Referências

- BREIMAN, L. Random forests. *Machine Learning*, v. 45, n. 1, p. 5–32, 2001.
- DEVLIN, J.; CHANG, M.-W.; LEE, K.; TOUTANOVA, K. BERT: pre-training of deep bidirectional transformers for language understanding. In: *NAACL-HLT*, 2019.
- HARTMANN, N. et al. Portuguese word embeddings: evaluating on word analogies and natural language tasks. In: *STIL*, 2017.
- HUBERT, L.; ARABIE, P. Comparing partitions. *Journal of Classification*, v. 2, p. 193–218, 1985.
- JOACHIMS, T. Text categorization with support vector machines: learning with many relevant features. In: *ECML*, 1998.
- McCALLUM, A.; NIGAM, K. A comparison of event models for naive Bayes text classification. In: *AAAI-98 Workshop on Learning for Text Categorization*, 1998.
- MIKOLOV, T.; CHEN, K.; CORRADO, G.; DEAN, J. Efficient estimation of word representations in vector space. arXiv:1301.3781, 2013.
- NG, A. Y.; JORDAN, M. I. On discriminative vs. generative classifiers: a comparison of logistic regression and naive Bayes. In: *Advances in Neural Information Processing Systems 14*, 2002.
- NICULESCU-MIZIL, A.; CARUANA, R. Predicting good probabilities with supervised learning. In: *ICML*, 2005.
- PLATT, J. Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. In: *Advances in Large Margin Classifiers*. MIT Press, 1999.
- REIMERS, N.; GUREVYCH, I. Making monolingual sentence embeddings multilingual using knowledge distillation. In: *EMNLP*, 2020.
- SOUZA, F.; NOGUEIRA, R.; LOTUFO, R. BERTimbau: pretrained BERT models for Brazilian Portuguese. In: *BRACIS*, 2020.
