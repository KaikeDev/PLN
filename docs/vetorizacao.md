# Etapa 2 — Representações vetoriais

Implementa o pipeline da Unidade 3 sobre o corpus da Etapa 1:

```
texto → preparação (Etapa 1) → representação ─┬─ BoW / TF-IDF      (esparsa, uma dimensão por termo)
                                              ├─ word2vec          (densa, média de vetores de palavras)
                                              └─ embedding contextual (densa, transformer)
                                                   │
                                                   ├─ similaridade do cosseno (vizinhos e consultas)
                                                   ├─ clustering (K-Means)
                                                   ├─ projeção em 2 dimensões (SVD / LSA)
                                                   └─ palavras vizinhas (word2vec)
```

Os resultados calculados estão em [data/vectors/tmdb_2026-09-12/report.md](../data/vectors/tmdb_2026-09-12/report.md).

## Como executar

Em `backend`. **Somente lexical** (BoW e TF-IDF), sem dependências pesadas:

```bash
uv sync --frozen
uv run --frozen python -m app.vectors build --input ../data/processed/tmdb_2026-09-12 --output ../data/vectors/lexical --config ../config/vetorizacao.json --queries ../config/consultas.json
```

**Completo** (inclui word2vec e embeddings contextuais). Instala o extra opcional `semantico`, com torch CPU, e baixa cerca de 1,6 GB de modelos para o cache do Hugging Face na primeira execução:

```bash
uv sync --frozen --extra semantico
uv run --frozen --extra semantico python -m app.vectors build --input ../data/processed/tmdb_2026-09-12 --output ../data/vectors/completo --config ../config/vetorizacao_semantica.json --queries ../config/consultas.json
uv run --frozen python -m app.vectors verify --input ../data/vectors/completo
```

Depois do primeiro download, defina `HF_HUB_OFFLINE=1` para garantir que nenhuma chamada de rede seja feita. Consulta avulsa:

```bash
uv run --frozen --extra semantico python -m app.vectors query --input ../data/processed/tmdb_2026-09-12 --config ../config/vetorizacao_semantica.json --representation contextual_minilm --text "uma casa assombrada por espíritos" --k 5
```

Como na Etapa 1, a pasta de saída precisa ser nova. Repetir o build com as mesmas entradas gera arquivos de conteúdo idênticos, inclusive nas representações densas; só o manifesto muda. As saídas usam sempre quebra de linha LF ([ADR 0009](adr/0009-saidas-imutaveis-e-verificaveis.md)); a pasta `tmdb_2026-09-12` foi gerada antes dessa regra, no Windows, e continua verificável.

## Experimento

| Representação | Entrada | Método | O que a comparação isola |
|---|---|---|---|
| `bow_sem_pontuacao` | `05_without_punctuation` | Contagem | Linha de base: palavras funcionais dominam |
| `bow_sem_stopwords` | `06_without_stopwords` | Contagem | Efeito de remover stopwords |
| `tfidf_sem_pontuacao` | `05_without_punctuation` | TF-IDF | Efeito do IDF, sem remover stopwords |
| `tfidf_sem_stopwords` | `06_without_stopwords` | TF-IDF | Os dois efeitos combinados |
| `word2vec_sem_stopwords` | `06_without_stopwords` | word2vec NILC skip-gram 300d | Palavras diferentes com significado próximo passam a se aproximar |
| `contextual_minilm` | `02_clean` | `paraphrase-multilingual-MiniLM-L12-v2` (384d) | Contexto da frase inteira, com tokenização própria em subpalavras |

- **Tokenização:** as representações lexicais e o word2vec reaproveitam os tokens versionados da Etapa 1. O modelo contextual recebe o texto limpo, com maiúsculas, pontuação e stopwords, e aplica o próprio tokenizador de subpalavras. Por isso ele não tem “termos fora do vocabulário”, mas trunca sinopses acima de 128 tokens; o relatório informa quantas foram truncadas.
- **TF-IDF:** usa idf = ln((1 + n) / (1 + df)) + 1, com norma L2 por sinopse. O vocabulário salvo registra `document_frequency` e `idf` de cada termo.
- **Word2vec:** usa os vetores pré-treinados do NILC (Hartmann et al., 2017), treinados sobre um grande corpus em português, e não sobre as 428 sinopses, que seriam poucas. A sinopse é a média dos vetores das palavras conhecidas pelo modelo. Dígitos viram `0`, como no treino do NILC.
- **Vetores e direções:** todas as análises usam linhas com norma L2. Assim o produto escalar é o cosseno, que compara direções e não depende do tamanho da sinopse.
- **Similaridade:** para cada filme, são listados os *k* vizinhos e uma explicação. Nas representações lexicais, são os termos idênticos que mais pesam; no word2vec, pares de palavras próximas (por exemplo, `simulação ≈ artificial`). O modelo contextual não é interpretável por palavras.
- **Clustering:** K-Means com *k* = 4, igual ao número de gêneros coletados. ARI, NMI e pureza usam os filmes de um único gênero de coleta, e a silhueta usa distância do cosseno. Os termos de cada cluster vêm de um TF-IDF de referência igual para todas as representações, o que permite comparar os clusters.
- **Dimensões:** o relatório compara ~6 mil dimensões esparsas com 300 ou 384 densas. A TruncatedSVD projeta tudo em 2D (nas matrizes lexicais, é a LSA) e gera um SVG por representação.
- **Palavras vizinhas:** para as palavras de `probe_words`, lista as palavras do corpus com vetor mais próximo no word2vec.
- **Consultas:** a consulta passa pelas mesmas regras de preparação da entrada de cada representação. O resultado registra os termos fora do vocabulário, se o vetor ficou nulo, a posição do filme anotado e a explicação.

## Arquitetura (`backend/src/app/vectors`)

| Módulo | Responsabilidade |
|---|---|
| `config.py` | Lê e valida a configuração e as consultas: tipos, limites, campos desconhecidos, etapas permitidas por método, modelo e revisão (validadores em `app.shared.validation`) |
| `corpus.py` | Repositório somente leitura da pasta processada; confere os hashes (`app.corpus.verification`) antes de ler tokens ou textos e prepara consultas com as mesmas regras |
| `context.py` | `AnalysisContext`: corpus, configuração, consultas e TF-IDF de referência compartilhados pelas análises |
| `space.py` | Contrato `Representation`, valor `Encoded` e representação lexical (`LexicalSpace`, `BOW`, `TFIDF`) |
| `embeddings.py` | `Word2VecSpace`, `ContextualSpace` e adaptadores do sentence-transformers, carregados só quando usados |
| `methods.py` | Registro `METHODS`: nome do método → fábrica da representação |
| `analyses.py` | Uma classe por análise: `Dimensions`, `Neighbors`, `Clustering`, `Projection`, `WordNeighbors`, `Retrieval`; cada uma calcula (`run`) e escreve a própria seção do relatório (`report_section`) |
| `retrieval.py` | Consulta → vetor → ranking |
| `metrics.py` | Métricas puras (pureza, concordância, posição recíproca) |
| `svg.py` / `report.py` | Apresentação: gráfico e funções de seção; `make_report` só junta introdução, seções das análises e limitações |
| `pipeline.py` | Orquestração, serialização e verificação (artefatos e manifesto em `app.shared`) |

**Padrões e princípios aplicados**

- **Strategy + registro (aberto/fechado):** cada método de representação e cada análise é uma classe intercambiável. O word2vec e o modelo contextual entraram sem nenhuma mudança nas análises; basta registrá-los em `METHODS` ou `DEFAULT_ANALYSES`. Uma análise nova também não altera `report.py`, porque escreve a própria seção.
- **Template/contrato (Liskov):** `Representation` define `unit`, `encode`, `document`, `explain`, `summary` e `export`. Métodos opcionais têm um comportamento padrão neutro, como `explain` devolvendo lista vazia, então qualquer representação serve para qualquer análise.
- **Adapter:** `SentenceTransformerWordVectors` e `SentenceTransformerEncoder` adaptam a biblioteca externa aos contratos `WordVectors` e `TextEncoder` do projeto.
- **Injeção de dependência (inversão):** `Word2VecMethod(loader)`, `ContextualMethod(loader)`, `build(..., methods=..., analyses=...)`. Os testes injetam vetores e codificadores falsos e não baixam modelos.
- **Repository:** `ProcessedCorpus` esconde o formato JSONL; as análises dependem de documentos e representações.
- **Factory:** as fábricas de `METHODS` constroem cada representação a partir da especificação.
- **Value objects imutáveis:** `RepresentationSpec`, `ExperimentConfig`, `QuerySpec`, `Document`, `Encoded` e `SearchResult` são dataclasses congeladas.
- **Carregamento preguiçoso:** torch e sentence-transformers só são importados ao construir um método semântico. `cached_property` evita recalcular normalizações e vocabulários.

Decisões numéricas do experimento: [ADR 0012](adr/0012-parametros-do-experimento-vetorial.md). Formatos e modelos: [ADR 0011](adr/0011-formatos-e-modelos-seguros.md).

## Segurança e integridade

- **Entrada verificada:** os hashes do manifesto da Etapa 1 são conferidos antes do uso, e arquivos alterados são rejeitados.
- **Sem path traversal:** a etapa de entrada vem de uma lista fixa, que depende do método (tokens ou texto), e os nomes de representação seguem `[a-z0-9_]`. `verify` recusa manifestos com caminhos, e o pipeline recusa nomes de arquivo gerados que não sejam simples.
- **Cadeia de suprimentos dos modelos:** `model` precisa ser `organização/modelo` e `revision` é obrigatoriamente um hash de commit de 40 caracteres, então uma atualização no repositório remoto não muda o modelo usado. O carregamento usa `trust_remote_code=False`, portanto nenhum código do repositório do modelo é executado. O modelo contextual usa safetensors; o `.bin` do word2vec é lido pelo sentence-transformers com `torch.load(weights_only=True)`, que não desserializa objetos arbitrários.
- **Sem pickle nas saídas:** matrizes, embeddings e vocabulários são JSON/JSONL legíveis. O comando `query` reconstrói a representação a partir dos dados verificados.
- **Limites de entrada:** JSON até 1 MB, consultas até 500 caracteres, limites para *k*, clusters, representações e palavras de sondagem. Campos desconhecidos e booleanos no lugar de inteiros são recusados.
- **Sem saída parcial:** tudo é calculado e serializado em memória antes de criar a pasta. Pastas existentes nunca são sobrescritas.
- **SVG seguro:** títulos vindos do TMDB são escapados, o que impede injeção de script ao abrir o gráfico.
- **Sem segredos:** não há credenciais. `HF_HUB_OFFLINE=1` permite rodar sem rede depois do download.

## Arquivos gerados

| Arquivo | Conteúdo |
|---|---|
| `documents.json` | Ordem das linhas: `id`, `title` e gêneros de coleta |
| `<representação>.matrix.jsonl` | Lexical: pesos diferentes de zero por filme (contagens inteiras no BoW) |
| `<representação>.vocabulary.json` | Lexical: colunas da matriz, com frequência em documentos e idf |
| `<representação>.embeddings.jsonl` | Densa: vetor de cada filme |
| `dimensions.json` | Dimensões, densidade, termos de maior peso, cobertura do vocabulário e truncamento |
| `neighbors.json` | Concordância de gênero @k, referência e vizinhos explicados dos filmes de exemplo |
| `clustering.json` | ARI, NMI, pureza, silhueta, termos e gêneros de cada cluster |
| `projection.json` / `<representação>.projection.svg` | Coordenadas 2D e gráfico |
| `word_neighbors.json` | Palavras vizinhas das palavras de sondagem |
| `retrieval.json` | Consultas anotadas: tokens, termos fora do vocabulário, posição, explicação, MRR e acerto @k |
| `config.json` / `queries_config.json` | Configuração efetivamente usada, incluindo modelos e revisões |
| `report.md` | Relatório gerado a partir dos arquivos acima |
| `manifest.json` | Hashes, versões das bibliotecas, identidade do código e da entrada |

## Limitações e próximos passos

- **Consultas:** as consultas anotadas são poucas e a lista de relevantes é parcial. Em “simulação da realidade”, as duas representações semânticas põem *Free Guy* em 1º lugar, um filme que se passa dentro de um jogo simulado e provavelmente relevante, mas não anotado. A equipe deve ampliar `config/consultas.json` antes de concluir qual representação é melhor.
- **Word2vec:** a média ignora ordem e negação e mistura nomes próprios. As explicações mostram pares como `thomas ≈ carlyle`.
- **Modelo contextual:** foi treinado principalmente para paráfrases curtas e trunca 40 sinopses. Modelos maiores ou específicos para português (por exemplo, BERTimbau) podem entrar como nova configuração, sem mudar código.
- **Variação simples:** a média ponderada por TF-IDF dos vetores word2vec pode ser acrescentada como nova estratégia.
