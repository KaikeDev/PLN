# 0018 — Tarefas do ciclo de PLN para cada representação

- Estado: Aceita
- Data: 2026-09-29

## Contexto

Na Aula 8, o quadro organizou a disciplina em duas dimensões:

- **representações:** BoW, TF-IDF, word2vec, BERT…;
- **tarefas:** busca, recomendação, agrupamento com visualização e classificação.

Cada representação deve ser aplicada às quatro tarefas. A auditoria de 29/09/2026 comparou essa exigência com o projeto:

| Lacuna | Situação encontrada |
|---|---|
| Recomendação | Ausente. Existia só um precursor: os cinco vizinhos de três filmes de exemplo, sem avaliação como recomendação |
| Visualização dos clusters | A projeção 2D era colorida só pelo gênero; o cluster encontrado pelo K-Means não aparecia em nenhum gráfico |
| Rótulos | A Etapa 2 usava o gênero do recorte de coleta que retornou o filme; a Etapa 3, os `genre_ids` do TMDB. Os números das duas etapas não eram comparáveis |
| K-Means | Implementado duas vezes, uma em cada etapa |
| Custo | A Etapa 3 recalculava os vetores densos que a Etapa 2 já tinha salvado e verificado (cerca de 100 s por execução) |

## Decisão

- **Recomendação por conteúdo** (`Recommendation`, que substitui a análise `Neighbors`):
  - item → item: para cada filme, os *k* filmes de maior cosseno, sem o próprio. As recomendações de todos os filmes ficam em `<representação>.recommendations.jsonl`, que entra na verificação de alinhamento;
  - perfil: a média, com norma L2, dos vetores dos filmes de que uma pessoa gostou, e os *k* filmes de maior cosseno fora do perfil. Os perfis ficam em `profiles` na configuração da Etapa 2;
  - avaliação offline: a precisão @k é a fração dos recomendados com ao menos um gênero em comum com o filme ou com o perfil. A referência é essa fração sobre todos os demais filmes, o esperado de uma recomendação que ignora o texto;
  - exemplos explicados: termos idênticos nas lexicais e pares de palavras próximas (≈) no word2vec.
- **Visualização dos clusters:** cada representação ganha `<representação>.clusters.svg`, com as mesmas coordenadas da projeção por gênero, coloridas pelo cluster. `clustering.json` guarda o cluster de cada sinopse (`assignments`).
- **Rótulos unificados:** `Document.genres` passa a ser o conjunto de `genre_ids` do TMDB restrito aos gêneros da coleta, em todas as etapas. Os gêneros da coleta são derivados dos recortes em `memberships.json`, que continua registrando a proveniência.
- **Um único K-Means:** `app.clustering.kmeans` (`fit_kmeans`, `project_2d`, `descriptive_terms`) é usado pelas duas etapas. A Etapa 2 agrupa as 428 sinopses; a Etapa 3 agrupa as 325 da tarefa multiclasse, para comparar com o classificador nas mesmas sinopses. Por isso o ARI das duas etapas difere.
- **Reaproveitamento dos vetores densos:** `python -m app.classification build --vectors <pasta da Etapa 2>`. `app.representations.stored` aceita a pasta só se:
  - os hashes do manifesto conferem;
  - ela veio do mesmo corpus processado;
  - as sinopses estão na mesma ordem;
  - a especificação da representação (método, etapa, modelo e revisão) é idêntica.

  As representações lexicais são sempre reconstruídas. O manifesto da Etapa 3 registra `source_vectors_manifest_sha256` e `reused_representations`.
- **Relatórios no vocabulário das tarefas:** as seções da Etapa 2 passam a se chamar Busca, Recomendação, Agrupamento e Visualização, nessa ordem. O README ganha a matriz tarefa × representação.

## Alternativas consideradas

- **Reestruturar em quatro pipelines, um por tarefa:** espelharia o quadro, mas reescreveria módulos testados sem ganho funcional. O padrão `Analysis` já acomoda cada tarefa como uma classe, e a classificação continua em pacote próprio por ter avaliação e saídas próprias.
- **Recomendação colaborativa (filtragem por usuários):** exigiria avaliações de usuários, que o corpus não tem. A recomendação por conteúdo é a que as representações de texto permitem.
- **Avaliar a recomendação com pares anotados à mão:** seria mais fiel, mas depende de anotação humana. Os gêneros são uma aproximação automática, declarada como tal.
- **Manter o recorte de coleta como rótulo na Etapa 2:** preservaria os números antigos, mas deixaria as etapas com rótulos diferentes.
- **Ler também as matrizes lexicais da Etapa 2:** o vocabulário e o idf delas foram ajustados com todas as sinopses, inclusive as de teste de cada dobra da classificação; usá-las vazaria informação para a avaliação.
- **Guardar os vetores densos com precisão total:** eliminaria a diferença de arredondamento, mas aumentaria os arquivos versionados; seis casas decimais bastam.

## Consequências

- **Arquivos da Etapa 2:** `neighbors.json` dá lugar a `recommendation.json`; `documents.json` passa a trazer os gêneros por nome; `clustering.json` ganha `assignments`. ARI, NMI e pureza foram recalculados com os novos rótulos e não são comparáveis com a versão anterior.
- **Resultados** ([relatório da Etapa 2](../../data/representacoes/tmdb_2026-09-12/report.md)):
  - recomendação: o BERTimbau tem a maior precisão @5 (63,6%, contra 37,9% da referência) e o maior ARI (0,144);
  - busca: o modelo de sentença tem o maior MRR (0,750), com só duas consultas;
  - classificação: o skip-gram tem o maior F1 macro (71,0%). Nenhuma representação vence todas as tarefas.
- **Perfis:**
  - no de terror sobrenatural, o modelo de sentença recomenda *Invocação do Mal 2*, *Invocação do Mal 4* e *A Morte do Demônio*;
  - no de animação, BoW e TF-IDF encontram as sequências de *Toy Story* pelos nomes dos personagens (woody, buzz, andy).
- **Etapa 3 com `--vectors`:** o tempo cai de cerca de 6 para cerca de 2,5 minutos, e o extra `semantico` deixa de ser necessário. Com os vetores arredondados, a regressão logística muda só na sexta casa da log loss. A floresta aleatória, que divide por limiares nos valores dos atributos, muda até 0,3 ponto de F1.
- **Busca:** continua avaliada com duas consultas. Ampliá-la depende de anotação da equipe.
