# Etapa 3 — Classificação de gêneros

Aplica a Aula 8 ao corpus: das representações da Etapa 2 passamos à **decisão**, que é atribuir gênero a uma sinopse.

```
sinopse → representação (Etapa 2) ─┬─ BoW / TF-IDF          ─┐
                                   ├─ word2vec CBOW / skip-gram ├─ regressão logística ─┬─ multiclasse: 1 gênero entre 4
                                   ├─ BERTimbau (congelado)     │  (C escolhido no treino) └─ multirrótulo: 1 binário por gênero
                                   └─ embedding de sentença    ─┘
                                                  │
                                                  └─ validação cruzada em 5 dobras → F1, precisão, revocação, confusão, incerteza
```

Os resultados calculados estão em [data/classification/tmdb_2026-09-12/report.md](../data/classification/tmdb_2026-09-12/report.md). As decisões e as alternativas descartadas estão na [ADR 0017](adr/0017-aula8-classificacao-de-generos.md).

## Como executar

Em `backend`. **Somente lexical**, sem dependências pesadas (cerca de 2 minutos):

```bash
uv sync --frozen
uv run --frozen python -m app.classification build --input ../data/processed/tmdb_2026-09-12 --output ../data/classification/lexical --config ../config/classificacao.json
```

**Completo**, com word2vec, BERTimbau e o modelo de sentença, lendo os vetores densos verificados da Etapa 2 (cerca de 2,5 minutos; dispensa o extra `semantico`):

```bash
uv run --frozen python -m app.classification build --input ../data/processed/tmdb_2026-09-12 --output ../data/classification/completo --config ../config/classificacao_semantica.json --vectors ../data/vectors/tmdb_2026-09-12
uv run --frozen python -m app.classification verify --input ../data/classification/completo
```

Sem `--vectors`, as representações densas são recalculadas: instale o extra (`uv sync --frozen --extra semantico`) e rode com `uv run --frozen --extra semantico`; leva cerca de 6 minutos. A pasta de vetores só é aceita se os hashes conferem, se veio do mesmo corpus e se a especificação de cada modelo é idêntica ([ADR 0018](adr/0018-tarefas-do-ciclo-de-pln.md)).

A pasta de saída não pode existir. Com as mesmas entradas, os arquivos de conteúdo se repetem; só `manifest.json` muda (hora e tempos de execução).

## Como a aula aparece no projeto

| Conceito da Aula 8 | No projeto |
|---|---|
| Clusterização × classificação | O K-Means da Etapa 2 agrupa as mesmas 325 sinopses sem rótulos, e o relatório compara grupos e previsões do classificador pela mesma régua (ARI, NMI, pureza) |
| Tipos de classificação | **Multiclasse** (325 filmes com um único gênero entre drama, comédia, terror e ficção científica) e **multirrótulo** (428 filmes; 103 têm dois ou três gêneros). A binária aparece dentro do multirrótulo, com um classificador “é/não é” por gênero. Ordinal não se aplica: gênero não tem ordem |
| Fronteira de decisão | A regressão logística aprende hiperplanos no espaço de cada representação. O mesmo classificador em todas isola o efeito da representação |
| Precisão, revocação e F1 | Por gênero e agregados (macro e micro), sempre com previsões fora da dobra |
| Acurácia engana | Há uma referência que ignora o texto. No multirrótulo, a perda de Hamming parece boa sem que o modelo reconheça gênero algum; o relatório mostra o cálculo |
| Pipeline clássico × BERT | TF-IDF + regressão logística contra BERTimbau congelado + regressão logística, nas mesmas dobras |
| Outros classificadores | Naive Bayes, SVM linear, floresta aleatória e k vizinhos nas mesmas dobras; a justificativa da escolha está em [escolha-dos-modelos.md](escolha-dos-modelos.md) |
| Critérios de escolha | Dados rotulados (os do TMDB), custo (tempo e parâmetros), interpretabilidade (termos por gênero só nas lexicais) e incerteza (log loss e confiança em acertos × erros) |
| LLM e Jev | O Jev foi executado à parte, sem treino, com uma Choice e um Noul por gênero, e comparado a TF-IDF + regressão logística nos mesmos filmes ([ADR 0019](adr/0019-aula8-jev-classificacao-de-genero.md), [resultados](../data/jev/tmdb_2026-09-12/report.md)). LLM com instrução foi discutido e não executado ([ADR 0017](adr/0017-aula8-classificacao-de-generos.md)) |

## Na tela do site

A seção "Classificar uma sinopse" usa `GET /classificacao`: a regressão logística desta etapa, ajustada com as 325 sinopses de um gênero sobre `sentenca_minilm`, a mesma representação da busca por tema ([ADR 0021](adr/0021-classificacao-na-tela.md)). A qualidade esperada é a medida aqui por validação cruzada (F1 macro de 66,1%).

## Arquivos gerados

| Arquivo | Conteúdo |
|---|---|
| `report.md` | Relatório com todas as tabelas |
| `results.json` | Métricas por tarefa, representação e referência, com F1 por dobra e `C` escolhido |
| `documents.json` | Cada sinopse, seus gêneros e a dobra de teste em cada tarefa (`null` = fora da tarefa) |
| `<representação>.<tarefa>.predictions.jsonl` | Gêneros reais, previstos e a probabilidade de cada gênero, por filme |
| `top_terms.json` | Termos de maior coeficiente por gênero (só representações lexicais) |
| `errors.json` | Erros com maior probabilidade no gênero errado |
| `clustering.json` | K-Means de cada representação: ARI, NMI, pureza, acurácia com o melhor mapeamento e descrição dos grupos |
| `alternatives.json` | F1 macro, acurácia e hiperparâmetro escolhido dos classificadores alternativos, por representação |
| `representations.json` | Família, dimensões e parâmetros de cada representação |
| `config.json`, `manifest.json` | Configuração validada; hashes, versões, tempos e identidade do código |

## Leitura dos resultados

- **Densas > lexicais:** na multiclasse, as representações densas ficam 7 a 12 pontos de F1 macro acima do melhor TF-IDF (66,1% a 71,0% contra 59,3%). Com cerca de 260 sinopses de treino por dobra, o vocabulário esparso quase não se repete entre filmes do mesmo gênero; vetores pré-treinados aproximam palavras diferentes com o mesmo sentido.
- **BERT ≈ word2vec:** o skip-gram (71,0%) e o BERTimbau (70,2%) diferem menos que o desvio entre dobras. Nesta amostra não dá para afirmar que o BERT congelado é melhor que a média de word2vec; ele tem, porém, a melhor log loss (0,725).
- **Comédia é o gênero mais difícil** em todas as representações e se confunde sobretudo com drama. Quatro dos oito erros mais confiantes do BERTimbau são filmes de ação com comédia (*A Hora do Rush*, *Magnatas do Crime*, *Thor: Amor e Trovão*, *Kingsman*), que a restrição aos quatro gêneros reduz a “comédia”: parte do erro está no rótulo, não no modelo.
- **Agrupar × classificar:** o K-Means, sem rótulos, coincide pouco com os gêneros (ARI de −0,001 a 0,132); nas lexicais, os grupos são praticamente independentes deles. Na mesma representação, o classificador sempre coincide mais: no skip-gram, 0,381 contra 0,055 do K-Means; no BERTimbau, 0,369 contra 0,132.
- **Outros classificadores:** o Naive Bayes vence nas contagens brutas (61,3% no BoW sem stopwords), mas não se aplica aos vetores densos. O SVM empata com a regressão logística em F1, mas não dá probabilidades. A floresta e o kNN ficam abaixo na maioria das representações. A justificativa completa está em [escolha-dos-modelos.md](escolha-dos-modelos.md).
- **Interpretabilidade:** o TF-IDF mostra por que decide (terror: “demônios”, “casa”; ficção: “planeta”, “futuro”). Também mostra que ele memoriza nomes de franquias (“shrek”, “peter”, “parker”), o que não generaliza.
