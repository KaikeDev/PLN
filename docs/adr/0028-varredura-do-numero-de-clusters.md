# 0028 — Varredura do número de clusters com métricas intra e intercluster

- Estado: Aceita
- Data: 2026-10-10

## Contexto

O agrupamento da Etapa 2 usa o K-Means com k = 4, o número de gêneros da coleta, e só o compara com os gêneros (ARI, NMI e pureza). O Trabalho da Unidade 3 pede outras duas coisas: a quantidade de clusters que melhor expressa os dados e a interpretação de métricas intra e intercluster.

## Decisão

- **Mesmo K-Means da Etapa 2** (`fit_kmeans`: k-means++, 10 inicializações, semente fixa, linhas com norma L2), para k de 2 a 10, nas oito representações e nas 428 sinopses da amostra.
- **Métricas por k:**
  - intracluster: inércia e distância de cosseno média ao centroide do próprio grupo;
  - intercluster: distância de cosseno média entre os centroides;
  - as que combinam as duas: silhueta de cosseno, Davies-Bouldin e Calinski-Harabasz;
  - contra os gêneros: ARI, NMI e pureza, nos filmes de um só gênero, como na Etapa 2.
- **Leitura dos grupos:** os termos de maior peso no TF-IDF de referência e os três filmes mais próximos do centroide de cada grupo.
- **Saída separada** em `data/agrupamento/tmdb_2026-09-12`, com manifesto. O agrupamento da Etapa 2 e as análises entregues não mudam.

## Alternativas consideradas

- **Escolher k só pelas métricas internas:** a silhueta e o Calinski-Harabasz preferem k = 2, e o Davies-Bouldin melhora sempre com mais grupos. Sem estrutura forte nos dados, elas não convergem.
- **Mudar o k da Etapa 2:** alteraria resultados já entregues, e k = 4 continua entre os melhores pelo ARI.
- **Método do cotovelo pela inércia:** a cada k a mais, a inércia cai 0,3% no TF-IDF e de 1% a 3% nas densas, de forma suave e sem cotovelo.

## Consequências

- **Silhueta abaixo de 0,10 em todas as representações:** as sinopses não formam grupos naturais bem separados, e nas lexicais a silhueta é praticamente zero.
- **O BERTimbau tem os grupos mais próximos dos gêneros**, com ARI de 0,144 em k = 4 e 5. Os grupos seguem temas legíveis: ameaça coletiva, super-heróis, família e polícia/guerra.
- **k = 4 a 5** é a faixa que melhor expressa as características originais dos dados; a métrica interna sozinha não indicaria isso.
