# 0012 — Parâmetros do experimento vetorial

- Estado: Aceita
- Data: 2026-09-14

## Contexto

A Etapa 2 compara representações (BoW, TF-IDF, word2vec e embeddings contextuais) com as mesmas análises. Várias escolhas numéricas estavam só em `config/vetorizacao*.json` e no código.

## Decisão

| Parâmetro | Valor | Justificativa |
|---|---|---|
| Tokenização | tokens versionados da Etapa 1 (`analyzer` identidade) | evita segunda tokenização divergente |
| TF-IDF | fórmula do scikit-learn, idf suavizado, norma L2 | padrão documentado e reprodutível |
| Similaridade | cosseno sobre linhas com norma L2 | independe do tamanho da sinopse |
| Vizinhos `k` | 5 (também usado como @k na recuperação) | lista curta, inspecionável no relatório |
| Clustering | K-Means, `k = 4` (número de gêneros coletados), `n_init=10` | permite comparar com os gêneros de coleta |
| Métricas externas | ARI, NMI e pureza só com filmes de um único gênero de coleta | os demais não têm rótulo inequívoco |
| Termos descritivos dos clusters | média TF-IDF sem stopwords dos membros | mesmo vocabulário para todas as representações |
| Projeção | TruncatedSVD com 2 componentes, sem centralização | funciona com matrizes esparsas; é a LSA |
| Semente | `random_state = 42` | saídas determinísticas |
| Referência de concordância | fração sobre todos os demais filmes | o esperado sem usar o texto |

## Alternativas consideradas

- Escolher `k` pela silhueta: otimizaria a métrica, mas dificultaria comparar com os quatro gêneros amostrados.
- PCA/t-SNE/UMAP: PCA densifica a matriz; t-SNE e UMAP não são determinísticos sem cuidado adicional e distorcem distâncias globais.

## Consequências

- Nenhuma representação é declarada superior só pela redução de dimensões; a escolha depende de consultas anotadas, ainda poucas.
- Usar o mesmo `k` para vizinhos e recuperação acopla os dois parâmetros; separá-los exige nova chave na configuração.
