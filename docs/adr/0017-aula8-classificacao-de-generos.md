# 0017 — Classificação de gêneros a partir das sinopses (Aula 8)

- Estado: Aceita
- Data: 2026-09-28

## Contexto

A Aula 8 (classificação de textos) pede para:

- distinguir classificação de clusterização;
- diferenciar classificação binária, multiclasse, multirrótulo e ordinal;
- comparar pipelines com TF-IDF, BERT e modelos generativos;
- avaliar com precisão, revocação e F1, sabendo que a acurácia engana em bases desbalanceadas;
- discutir critérios de escolha: dados rotulados, custo, interpretabilidade, necessidade de gerar texto e tratamento da incerteza.

O corpus já tem rótulos: o TMDB atribui gêneros a cada filme (`genre_ids`), e a coleta foi feita por quatro gêneros (drama, comédia, terror e ficção científica). Das 428 sinopses preenchidas, 325 têm exatamente um desses gêneros e 103 têm dois ou três. A Etapa 2 já constrói oito representações das mesmas sinopses.

## Decisão

- **Tarefa:** prever o gênero a partir da sinopse, em duas formulações sobre os mesmos quatro gêneros.
  - **Multiclasse:** só os 325 filmes com exatamente um gênero; o modelo escolhe um.
  - **Multirrótulo:** todos os 428 filmes; um classificador binário por gênero (*one-vs-rest*). Um gênero é atribuído com probabilidade ≥ 0,5, e o mais provável sempre é atribuído, porque todo filme da tarefa tem ao menos um gênero.
- **Rótulos:** `genre_ids` do TMDB restritos aos gêneros configurados. O recorte de coleta que retornou o filme (usado na Etapa 2 como aproximação) não serve de rótulo: depende do ranking e do limite de páginas. Por isso `Document` ganhou o campo `tmdb_genres`. A [ADR 0018](0018-tarefas-do-ciclo-de-pln.md) estendeu esse rótulo à Etapa 2.
- **Classificador:** a mesma regressão logística para todas as representações, com pesos de classe balanceados. Ela é o exemplo da aula, é rápida em CPU e seus coeficientes são legíveis nas representações lexicais.
- **Representações:** as oito da Etapa 2, pelo mesmo esquema de configuração e pelos mesmos métodos (`parse_representation` e `METHODS`). O BERTimbau e o modelo de sentença são extratores de atributos congelados.
- **Avaliação sem vazamento:**
  - validação cruzada em 5 dobras externas, iguais para todas as representações (estratificadas por gênero na multiclasse; embaralhadas simples na multirrótulo);
  - vocabulário e idf do BoW/TF-IDF, padronização dos vetores densos e escolha de `C` (grade de 10⁻⁶ a 10⁴, 3 dobras internas, pela log loss) ajustados só com o treino de cada dobra;
  - todas as métricas vêm de previsões fora da dobra.
- **Métricas:**
  - uma referência que ignora o texto (gênero mais frequente);
  - F1 macro e micro;
  - precisão, revocação e F1 por gênero;
  - desvio do F1 entre dobras;
  - matriz de confusão;
  - na multirrótulo, perda de Hamming e acerto exato;
  - log loss e confiança média em acertos e erros, para o tratamento da incerteza.
- **Clusterização × classificação:** o K-Means da Etapa 2 (k = 4, sem rótulos) agrupa as mesmas 325 sinopses em cada representação. ARI, NMI e pureza medem grupos e previsões do classificador pela mesma régua, porque não dependem do nome de cada grupo.
- **Outros classificadores:** Naive Bayes multinomial, SVM linear, floresta aleatória e k vizinhos (cosseno) são avaliados na multiclasse, nas mesmas dobras e com a mesma preparação. Cada um ajusta o próprio hiperparâmetro em dobras internas; a floresta usa 300 árvores fixas. Eles existem para justificar a escolha da regressão logística com medidas; a justificativa completa está em [`docs/escolha-dos-modelos.md`](../escolha-dos-modelos.md).
- **Interpretabilidade e erros:** termos de maior coeficiente por gênero nas representações lexicais e os erros com maior probabilidade no gênero errado. As probabilidades de cada filme ficam em `*.predictions.jsonl`.
- **Saídas:** as regras da Etapa 2 (ADR 0009): pasta nova, conteúdo determinístico, tempos só no manifesto e comando `verify`.

## Alternativas consideradas

- **Ajuste fino do BERTimbau:** exige GPU para ser prático e tende a sobreajustar com cerca de 260 exemplos de treino por dobra. O BERT como extrator congelado já mede o ganho da representação contextual.
- **LLM com instrução (zero-shot):** responderia à pergunta da aula sobre gerar texto para escolher uma classe. Porém depende de serviço externo, custo e credencial, e não seria reproduzível byte a byte. Fica para uma etapa futura, avaliada nas mesmas dobras.
- **Jev (TypeSafe):** produto em acesso inicial, com desempenho anunciado pela fornecedora ainda sem avaliação independente, como a própria aula alerta.
- **Classificação ordinal pela nota (`vote_average`):** a sinopse diz pouco sobre a qualidade do filme; o resultado seria fraco e difícil de interpretar.
- **`C` fixo:** foi a primeira versão. Com `C = 1`, o TF-IDF (vetores de norma 1) ficava tão regularizado que a probabilidade média do gênero escolhido ficava perto de 30%, quase uniforme entre quatro gêneros. Além disso, um único `C` não serve igualmente a representações com escalas e dimensões tão diferentes (de 300 a quase 6 mil).
- **`C` escolhido pelo F1:** foi a segunda versão. O F1 só olha o gênero de maior probabilidade, então as dobras internas preferiam regularização fortíssima, que não muda esse gênero mas achata as probabilidades. No modelo de sentença, a confiança média nos acertos caiu para 41,5% com acurácia de 66,8%. Pela log loss, o F1 fica praticamente igual, as probabilidades acompanham a acurácia e o `C` escolhido se repete entre dobras.
- **Grade de `C` de 0,01 a 100:** vários valores escolhidos caíam no limite da grade (0,01 nos vetores densos; 1000 seria o ótimo do TF-IDF pela log loss), sinal de que o ótimo estava fora dela. A grade foi ampliada até que as escolhas ficassem no interior.
- **Estratificação multirrótulo iterativa:** exigiria uma dependência nova (`iterative-stratification`); várias combinações de gêneros têm menos filmes que dobras.

## Consequências

- **Resultados** ([relatório](../../data/classification/tmdb_2026-09-12/report.md)): na multiclasse, as representações densas superam o melhor TF-IDF em 7 a 12 pontos de F1 macro (66,1% a 71,0% contra 59,3%). Skip-gram (71,0%) e BERTimbau (70,2%) empatam dentro do desvio entre dobras. A regressão logística tem o maior F1 nas três melhores representações; o Naive Bayes vence nas contagens brutas, e o SVM empata sem dar probabilidades ([escolha-dos-modelos.md](../escolha-dos-modelos.md)). O K-Means coincide muito menos com os gêneros que o classificador (ARI de até 0,13 contra até 0,38).
- **Ruído dos rótulos:** a restrição aos quatro gêneros apaga os demais gêneros do filme. Por exemplo, *A Hora do Rush* (ação, comédia e crime) vira “comédia”. Quatro dos oito erros mais confiantes do BERTimbau são filmes de ação com comédia.
- **Custo:** o build completo leva cerca de 6 minutos em CPU; a construção das representações densas e os classificadores alternativos respondem pela maior parte. O build lexical (`config/classificacao.json`) dispensa o extra `semantico` e leva cerca de 2 minutos.
- **Compatibilidade:** o scikit-learn 1.9 falha ao usar pontuação por nome em `LogisticRegressionCV` com duas classes; por isso as pontuações das dobras internas são funções.
