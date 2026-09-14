# Representação Numérica: Bag of Words (BoW)

Este documento descreve a construção, estrutura e utilização da **representação numérica Bag of Words (Saco de Palavras)** elaborada sobre o corpus de sinopses do TMDB.

---

## 1. O que é o modelo Bag of Words?

O modelo **Bag of Words (BoW)** é uma técnica vetorial de Processamento de Linguagem Natural (PLN) que converte documentos de texto em vetores numéricos.

- **Premissa**: A ordem das palavras e a estrutura gramatical são desconsideradas; preserva-se a frequência de ocorrência dos termos no documento.
- **Vocabulário ($V$)**: Conjunto de todos os termos únicos presentes no corpus pré-processado (na etapa sem stopwords `06_without_stopwords.jsonl`).
- **Vetor do Documento ($\mathbf{v}_i$)**: Para cada sinopse $i$, cria-se um vetor numérico de dimensão $|V|$, no qual a posição $j$ armazena a contagem (ou peso) do termo $j$ daquele vocabulário.

$$\mathbf{v}_{i, j} = \text{frequência do termo } w_j \text{ no filme } i$$

---

## 2. Estatísticas do Corpus e da Matriz BoW

Calculado sobre a amostra oficial (`data/processed/tmdb_2026-09-12`):

| Métrica | Valor Calculado | Significado |
|---|---:|---|
| **Filmes (Documentos $N$)** | 430 | Quantidade de filmes únicos no corpus |
| **Sinopses Válidas** | 428 | Filmes com sinopse preenchida |
| **Tamanho do Vocabulário ($|V|$)** | 5.921 | Quantidade de termos distintos |
| **Dimensão da Matriz** | $430 \times 5.921$ | Total de posições na matriz ($2.546.030$) |
| **Elementos Não Nulos (nnz)** | 13.913 | Ocorrências de termos nas sinopses |
| **Esparsidade da Matriz** | **99,45%** | Porcentagem de posições com valor zero |

---

## 3. Formato de Armazenamento (`07_bag_of_words.json`)

Para eficiência de armazenamento e inspeção rastreável, a representação utiliza **vetores esparsos em JSON**:

```json
{
  "vocabulary_size": 5921,
  "total_documents": 430,
  "sparsity_percent": 99.4535,
  "top_20_terms": [
    {"index": 3962, "term": "não", "doc_frequency": 79, "term_frequency": 90},
    {"index": 2232, "term": "está", "doc_frequency": 76, "term_frequency": 87},
    {"index": 5067, "term": "ser", "doc_frequency": 69, "term_frequency": 80}
  ],
  "documents": [
    {
      "id": 603,
      "total_tokens": 30,
      "distinct_terms": 27,
      "vector_sparse_indices": {
        "83": 1,
        "761": 1,
        "1276": 1,
        "1380": 1,
        "1487": 1,
        "1994": 1,
        "2232": 1,
        "2337": 1,
        "2672": 1,
        "2943": 1,
        "3062": 1,
        "3169": 1,
        "3754": 1,
        "3759": 1,
        "3765": 1,
        "3962": 1,
        "4265": 1,
        "4347": 1,
        "4348": 1,
        "4538": 1,
        "4616": 1,
        "4762": 1,
        "4894": 1,
        "5067": 1,
        "5182": 1,
        "5635": 1,
        "5775": 1
      },
      "vector_sparse_terms": {
        "está": 1,
        "mundo": 1,
        "realidade": 1,
        "sistema": 1,
        "jovem": 1,
        "descobre": 1,
        "computador": 1,
        "programador": 1,
        "maquinas": 1
      }
    }
  ]
}
```

---

## 4. Demonstração Prática de Uso: Similaridade de Cosseno

A representação numérica permite comparar sinopses no espaço vetorial utilizando a **Similaridade de Cosseno**:

$$\text{sim}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|} = \frac{\sum_{k} u_k v_k}{\sqrt{\sum u_k^2} \sqrt{\sum v_k^2}}$$

### Exemplo: Comparação a partir de Matrix (ID 603)

Ao calcular o cosseno entre o vetor numérico de *Matrix* e todos os outros filmes do corpus:

| Filme Comparado | ID | Similaridade de Cosseno | Termos Compartilhados |
|---|---|---:|---|
| **Barbie** | 346698 | 0,1680 | `está`, `começa`, `descobre`, `mundo`, `real` |
| **Possessão** | 21484 | 0,1509 | `está`, `estranhos`, `começa`, `descobre`, `jovem` |
| **Madrugada dos Mortos** | 924 | 0,1213 | `está`, `enquanto`, `descobre`, `mundo`, `real` |
| **Free Guy: Assumindo o Controle** | 550988 | 0,1040 | `mundo`, `realidade`, `descobre` |

---

## 5. Como Reproduzir e Utilizar

Para gerar ou recalcular a representação numélica Bag of Words via CLI:

```bash
cd backend
PYTHONPATH=src python3 -m app.corpus bow --input ../data/processed/tmdb_2026-09-12 --output ../data/processed/tmdb_2026-09-12/07_bag_of_words.json
```

Em código Python:

```python
from app.corpus.bow import BagOfWordsVectorizer, cosine_similarity, generate_bow_dataset

# 1. Carregar dataset e gerar vocabulário/vetores
bow_data = generate_bow_dataset(Path("data/processed/tmdb_2026-09-12"))

# 2. Instanciar vetorizador programaticamente
vectorizer = BagOfWordsVectorizer()
documents_tokens = [["matrix", "computador", "ficção"], ["robô", "futuro", "computador"]]
vectors = vectorizer.fit_transform(documents_tokens)

# 3. Vetor esparso e denso
print("Vocabulário:", vectorizer.vocabulary_)
print("Vetor Esparso [0]:", vectors[0])
print("Vetor Denso [0]:", vectorizer.to_dense(vectors[0]))
```
