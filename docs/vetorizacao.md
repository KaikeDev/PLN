# Etapa 2 — Representações vetoriais

Implementa o pipeline da Unidade 3 sobre o corpus da Etapa 1:

```
texto → preparação (Etapa 1) → representação ─┬─ BoW / TF-IDF         (esparsa, uma dimensão por termo)
                                              ├─ word2vec CBOW / skip-gram (densa, estática: um vetor por palavra)
                                              ├─ BERT                  (densa, contextual: vetor da palavra depende da frase)
                                              └─ embedding de sentença (densa, transformer ajustado para similaridade)
                                                   │
                                                   ├─ similaridade do cosseno (vizinhos e consultas)
                                                   ├─ clustering (K-Means)
                                                   ├─ projeção em 2 dimensões (SVD / LSA)
                                                   ├─ hipótese distribucional (palavras vizinhas e pares de palavras)
                                                   ├─ similaridade lexical × semântica (pares de frases)
                                                   ├─ polissemia (mesma palavra em sentidos diferentes)
                                                   └─ síntese comparativa (informação, custo, interpretabilidade)
```

Os resultados calculados estão em [data/vectors/tmdb_2026-09-12/report.md](../data/vectors/tmdb_2026-09-12/report.md).

## Como executar

Em `backend`. **Somente lexical** (BoW e TF-IDF), sem dependências pesadas:

```bash
uv sync --frozen
uv run --frozen python -m app.vectors build --input ../data/processed/tmdb_2026-09-12 --output ../data/vectors/lexical --config ../config/vetorizacao.json --queries ../config/consultas.json
```

**Completo** (inclui word2vec CBOW e skip-gram, BERT e embedding de sentença). Instala o extra opcional `semantico`, com torch CPU, e baixa cerca de 3,1 GB de modelos para o cache do Hugging Face na primeira execução:

```bash
uv sync --frozen --extra semantico
uv run --frozen --extra semantico python -m app.vectors build --input ../data/processed/tmdb_2026-09-12 --output ../data/vectors/completo --config ../config/vetorizacao_semantica.json --queries ../config/consultas.json --probes ../config/sondas_semanticas.json
uv run --frozen python -m app.vectors verify --input ../data/vectors/completo
```

Depois do primeiro download, defina `HF_HUB_OFFLINE=1` para garantir que nenhuma chamada de rede seja feita. Consulta avulsa:

```bash
uv run --frozen --extra semantico python -m app.vectors query --input ../data/processed/tmdb_2026-09-12 --config ../config/vetorizacao_semantica.json --representation sentenca_minilm --text "uma casa assombrada por espíritos" --k 5
```

Como na Etapa 1, a pasta de saída precisa ser nova. Repetir o build com as mesmas entradas gera arquivos de conteúdo idênticos, inclusive nas representações densas; só o manifesto muda. As saídas usam sempre quebra de linha LF ([ADR 0009](adr/0009-saidas-imutaveis-e-verificaveis.md)).

## Experimento

| Representação | Entrada | Método | O que a comparação isola |
|---|---|---|---|
| `bow_sem_pontuacao` | `05_without_punctuation` | Contagem | Linha de base: palavras funcionais dominam |
| `bow_sem_stopwords` | `06_without_stopwords` | Contagem | Efeito de remover stopwords |
| `tfidf_sem_pontuacao` | `05_without_punctuation` | TF-IDF | Efeito do IDF, sem remover stopwords |
| `tfidf_sem_stopwords` | `06_without_stopwords` | TF-IDF | Os dois efeitos combinados |
| `word2vec_cbow` | `06_without_stopwords` | word2vec NILC CBOW 300d | Contexto → palavra central; vetor estático por palavra |
| `word2vec_skipgram` | `06_without_stopwords` | word2vec NILC skip-gram 300d | Palavra central → contexto; mesmo corpus e dimensão do CBOW |
| `bert_base_pt` | `02_clean` | BERTimbau base (`neuralmind/bert-base-portuguese-cased`, 768d) | Vetor da palavra depende da frase (contextual), sem ajuste para sentenças |
| `sentenca_minilm` | `02_clean` | `paraphrase-multilingual-MiniLM-L12-v2` (384d) | Transformer ajustado para similaridade de sentenças (embedding semântico de texto) |

- **Tokenização:** as representações lexicais e o word2vec reaproveitam os tokens versionados da Etapa 1. Os transformers recebem o texto limpo, com maiúsculas, pontuação e stopwords, e aplicam o próprio tokenizador de subpalavras. Por isso não têm “termos fora do vocabulário”, mas truncam textos longos: 512 tokens no BERT (nenhuma sinopse truncada) e 128 no modelo de sentença (40 sinopses truncadas).
- **TF-IDF:** usa idf = ln((1 + n) / (1 + df)) + 1, com norma L2 por sinopse. O vocabulário salvo registra `document_frequency` e `idf` de cada termo.
- **Word2vec:** usa os vetores pré-treinados do NILC (Hartmann et al., 2017), treinados sobre um grande corpus em português, e não sobre as 428 sinopses, que seriam poucas. A sinopse é a média dos vetores das palavras conhecidas pelo modelo. Dígitos viram `0`, como no treino do NILC.
- **Vetores e direções:** todas as análises usam linhas com norma L2. Assim o produto escalar é o cosseno, que compara direções e não depende do tamanho da sinopse.
- **Similaridade:** para cada filme, são listados os *k* vizinhos e uma explicação. Nas representações lexicais, são os termos idênticos que mais pesam; no word2vec, pares de palavras próximas (por exemplo, `simulação ≈ artificial`). O modelo contextual não é interpretável por palavras.
- **Clustering:** K-Means com *k* = 4, igual ao número de gêneros coletados. ARI, NMI e pureza usam os filmes de um único gênero de coleta, e a silhueta usa distância do cosseno. Os termos de cada cluster vêm de um TF-IDF de referência igual para todas as representações, o que permite comparar os clusters.
- **Dimensões:** o relatório compara ~6 mil dimensões esparsas com 300 ou 384 densas. A TruncatedSVD projeta tudo em 2D (nas matrizes lexicais, é a LSA) e gera um SVG por representação.
- **Palavras vizinhas:** para as palavras de `probe_words`, lista as palavras do corpus com vetor mais próximo no word2vec, separadamente para CBOW e skip-gram.
- **Consultas:** a consulta passa pelas mesmas regras de preparação da entrada de cada representação. O resultado registra os termos fora do vocabulário, se o vetor ficou nulo, a posição do filme anotado e a explicação.

## Aula 7: word2vec, BERT e embeddings modernos

As sondas de `config/sondas_semanticas.json` usam os exemplos da aula e são validadas por `app.vectors.probes`. As decisões estão no [ADR 0015](adr/0015-aula7-bert-cbow-e-polissemia.md).

| Objetivo da aula | Como o projeto mostra | Onde ver |
|---|---|---|
| Hipótese distribucional | Palavras vizinhas e cosseno entre pares de palavras (`gato × cachorro`, `cão × cachorro`...) | `word_neighbors.json`, seção “Hipótese distribucional” |
| CBOW × skip-gram | Dois word2vec do NILC com o mesmo corpus de treino e 300 dimensões; mudam só a tarefa de previsão | `word2vec_cbow` × `word2vec_skipgram` em todas as seções |
| Similaridade lexical ≠ semântica | Pares de frases da aula: paráfrase sem palavras em comum e frases que só compartilham “banco” | `sentence_pairs.json`, seção “Similaridade lexical não é similaridade semântica” |
| Estático × contextual e polissemia | Vetor de “banco” e “manga” em frases com sentidos diferentes: igual no word2vec, diferente no BERT | `word_senses.json`, seção “Polissemia” |
| Comparar informação, custo e interpretabilidade | Tabela no formato da síntese da aula, com dimensões e parâmetros medidos; tempos em `manifest.json` | `synthesis.json`, seção “Síntese comparativa” |

Resultados da execução entregue:

- **Polissemia (“banco”):** no word2vec, os cossenos entre os quatro usos são todos 1,000. No BERTimbau, 0,823 entre usos com o mesmo sentido e 0,545 entre sentidos diferentes; no modelo de sentença, 0,858 × 0,193.
- **Pares de frases:**
  - O BoW e o TF-IDF sem stopwords dão cosseno 1,000 a “O banco aprovou o financiamento” × “Ele sentou no banco da praça”, porque só “banco” está no vocabulário do corpus.
  - Na paráfrase cachorro/cão, as representações lexicais dão 0,000. O word2vec aproxima `cachorro ≈ cão, perseguiu ≈ correu` (0,49 a 0,54), e os transformers chegam a 0,68 e 0,79.
- **BERT sem ajuste para sentenças:** dá cosseno alto a quase qualquer par (0,594 até no par polissêmico) e tem o menor MRR nas consultas (0,30). O modelo de sentença separa bem os pares (−0,033 × 0,677). Essa diferença corresponde à distinção da aula entre embeddings contextuais e embeddings semânticos de textos.
- **Clustering:** o BERTimbau tem o maior ARI com os gêneros de coleta (0,122) e a maior concordância de gênero @5 (0,552).

## Arquitetura (`backend/src/app/vectors`)

| Módulo | Responsabilidade |
|---|---|
| `config.py` | Lê e valida a configuração e as consultas: tipos, limites, campos desconhecidos, etapas permitidas por método, modelo e revisão (validadores em `app.shared.validation`) |
| `corpus.py` | Repositório somente leitura da pasta processada; confere os hashes (`app.corpus.verification`) antes de ler tokens ou textos e prepara consultas com as mesmas regras |
| `context.py` | `AnalysisContext`: corpus, configuração, consultas, sondas e TF-IDF de referência compartilhados pelas análises |
| `probes.py` | Sondas da Aula 7: pares de frases, pares de palavras e palavras polissêmicas, com validação |
| `space.py` | Contrato `Representation`, valor `Encoded` e representação lexical (`LexicalSpace`, `BOW`, `TFIDF`) |
| `embeddings.py` | `Word2VecSpace` (estático), `ContextualSpace` (transformers) e adaptadores do sentence-transformers, carregados só quando usados; inclui o vetor da palavra no contexto |
| `methods.py` | Registro `METHODS`: nome do método → fábrica da representação |
| `analyses.py` | Uma classe por análise: `Dimensions`, `Neighbors`, `Clustering`, `Projection`, `WordNeighbors`, `SentencePairs`, `WordSenses`, `Retrieval`, `Synthesis`; cada uma calcula (`run`) e escreve a própria seção do relatório (`report_section`) |
| `retrieval.py` | Consulta → vetor → ranking |
| `metrics.py` | Métricas puras (pureza, concordância, posição recíproca) |
| `svg.py` / `report.py` | Apresentação: gráfico e funções de seção; `make_report` só junta introdução, seções das análises e limitações |
| `pipeline.py` | Orquestração, serialização e verificação (artefatos e manifesto em `app.shared`) |

**Padrões e princípios aplicados**

- **Strategy + registro (aberto/fechado):** cada método de representação e cada análise é uma classe intercambiável. O word2vec e o modelo contextual entraram sem nenhuma mudança nas análises; basta registrá-los em `METHODS` ou `DEFAULT_ANALYSES`. Uma análise nova também não altera `report.py`, porque escreve a própria seção.
- **Template/contrato (Liskov):** `Representation` define `unit`, `encode`, `document`, `explain`, `summary` e `export`, e a família (`lexical`, `static`, `contextual`). Métodos opcionais (`explain`, `word_similarity`, `word_in_context`, `parameters`) têm um comportamento padrão neutro, então qualquer representação serve para qualquer análise.
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
- **Cadeia de suprimentos dos modelos:** `model` precisa ser `organização/modelo` e `revision` é obrigatoriamente um hash de commit de 40 caracteres, então uma atualização no repositório remoto não muda o modelo usado. O carregamento usa `trust_remote_code=False`, portanto nenhum código do repositório do modelo é executado. O modelo de sentença usa safetensors; os `.bin` do word2vec e do BERTimbau são lidos com `torch.load(weights_only=True)`, que não desserializa objetos arbitrários.
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
| `word_neighbors.json` | Palavras vizinhas das palavras de sondagem e cosseno dos pares de palavras |
| `sentence_pairs.json` | Cosseno e explicação de cada par de frases das sondas |
| `word_senses.json` | Matriz de cossenos entre os usos de cada palavra polissêmica e diferença entre mesmo sentido e sentidos diferentes |
| `synthesis.json` | Propriedades de cada representação para a síntese comparativa |
| `retrieval.json` | Consultas anotadas: tokens, termos fora do vocabulário, posição, explicação, MRR e acerto @k |
| `config.json` / `queries_config.json` / `probes_config.json` | Configuração, consultas e sondas efetivamente usadas, incluindo modelos e revisões |
| `report.md` | Relatório gerado a partir dos arquivos acima |
| `manifest.json` | Hashes, versões das bibliotecas, identidade do código e da entrada, tempo de construção de cada representação (`build_seconds`) |

## Limitações e próximos passos

- **Consultas:** as consultas anotadas são poucas e a lista de relevantes é parcial. Em “simulação da realidade”, as duas representações semânticas põem *Free Guy* em 1º lugar, um filme que se passa dentro de um jogo simulado e provavelmente relevante, mas não anotado. A equipe deve ampliar `config/consultas.json` antes de concluir qual representação é melhor.
- **Word2vec:** a média ignora ordem e negação e mistura nomes próprios. As explicações mostram pares como `thomas ≈ carlyle`.
- **Transformers:** o modelo de sentença foi treinado principalmente para paráfrases curtas e trunca 40 sinopses. O BERTimbau não foi ajustado para comparar sentenças; um modelo de sentenças em português (BERTimbau ajustado em paráfrases, por exemplo) pode entrar como nova configuração, sem mudar código.
- **Sondas:** são poucas frases escritas pela equipe e ilustram os conceitos da aula; não medem desempenho.
- **Variação simples:** a média ponderada por TF-IDF dos vetores word2vec pode ser acrescentada como nova estratégia.
