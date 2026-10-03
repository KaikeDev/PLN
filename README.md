# PLN 2026/2 — Etapas Práticas 1, 2 e 3

**Sinopses de filmes coletadas, preparadas, representadas e usadas nas quatro tarefas de PLN da disciplina: busca, recomendação, agrupamento com visualização e classificação.** O projeto preserva o corpus original, seis preparações do texto e oito representações vetoriais, todas alinhadas pelo ID do TMDB. Na classificação, além dos classificadores treinados, o Jev (TypeSafe AI) decide o gênero sem treino; a busca do site combina TF-IDF e embedding de sentença. A consulta de filmes na interface é uma demonstração auxiliar; a entrega está nos dados, scripts e evidências abaixo.

Equipe: Kaike Ventura Tuerpe, Luana Nitsche, Pedro Henrique Ortunio e Thiago Bodnar — Ciência da Computação, FURB.

## Comece pela entrega

A amostra real de 12/09/2026 contém **430 filmes únicos**, **428 sinopses preenchidas** e **2 ausentes**. Foram recebidos 481 registros e removidas 51 ocorrências duplicadas por ID. Todas as etapas mantêm os 430 registros, inclusive os que não têm sinopse.

| Critério do professor | Onde localizar | Evidência |
|---|---|---|
| Justificativa, volume e abrangência — 0,4 | [Relatório](docs/relatorio.md), [configuração](config/coleta.json) | Amostra intencional de quatro gêneros e três períodos; critérios e limitações explícitos |
| Organização e dicionário — 0,4 | [Dicionário](docs/dicionario.md), [dados brutos](data/raw/tmdb_2026-09-12/) | IDs, campos, tipos, valores ausentes e proveniência |
| Script Python e reprodução — 0,3 | [Coleta](backend/src/app/corpus/collect.py), [CLI](backend/src/app/corpus/__main__.py), [ambiente](backend/uv.lock) | Paginação, retries, deduplicação, respostas salvas e manifesto |
| Limpeza, normalização e tokenização — 0,3 | [Transformações](backend/src/app/corpus/transform.py), [saídas](data/processed/tmdb_2026-09-12/) | Seis representações identificadas, sem sobrescrever as anteriores |
| Stopwords e pontuação — 0,3 | [Lista versionada](config/stopwords_pt.txt), [lista efetivamente usada](data/processed/tmdb_2026-09-12/stopwords_used.json) | Acentos, números e negações preservados; títulos fora do filtro |
| Comparação entre recortes e coleta automatizada — bônus a avaliar | [Resultados calculados](data/processed/tmdb_2026-09-12/report.md) | Comparação dos 12 recortes e coleta de múltiplas páginas em um comando |

Os pesos identificam dimensões da rubrica da Etapa 1; não são notas atribuídas à entrega. Stemming, lematização e vetorização **não foram executados** na Etapa 1; a vetorização está na [Etapa 2](#etapa-2--representações-vetoriais) e a classificação, na [Etapa 3](#etapa-3--classificação-de-gêneros). A comparação entre recortes e a coleta automatizada estão implementadas, mas a concessão do bônus cabe ao professor.

- [Documento Word da entrega](docs/PLN_2026_2_Avaliacao_Pratica_1_Atualizado.docx)
- [Validação técnica](docs/validacao.md)
- [Decisões de arquitetura e desenvolvimento, com justificativas (`adr.md`)](adr.md), [ADRs detalhadas](docs/adr/README.md) e [limitações](docs/decisoes.md)
- [Arquitetura do código](docs/arquitetura.md)

## Tarefas × representações

Na Aula 8, o quadro organizou a disciplina em representações (BoW, TF-IDF, word2vec, BERT…) e tarefas (busca, recomendação, agrupamento com visualização e classificação). Cada representação é aplicada às quatro tarefas ([ADR 0018](docs/adr/0018-tarefas-do-ciclo-de-pln.md)). A tabela traz uma métrica por célula, calculada nos arquivos entregues:

| Representação | [Busca](data/vectors/tmdb_2026-09-12/report.md#busca-consultas-anotadas): MAP | [Recomendação](data/vectors/tmdb_2026-09-12/report.md#recomendação-filmes-parecidos): precisão @5 | [Agrupamento](data/vectors/tmdb_2026-09-12/report.md#agrupamento-k-means): ARI | [Classificação](data/classification/tmdb_2026-09-12/report.md): F1 macro |
|---|---:|---:|---:|---:|
| Referência que ignora o texto | — | 37,9% | 0 | 10,7% |
| `bow_sem_pontuacao` | 0,188 | 45,0% | 0,002 | 46,1% |
| `bow_sem_stopwords` | 0,375 | 56,1% | 0,000 | 56,4% |
| `tfidf_sem_pontuacao` | 0,460 | 57,0% | 0,001 | 59,3% |
| `tfidf_sem_stopwords` | 0,446 | 57,8% | 0,024 | 59,2% |
| `word2vec_cbow` | 0,333 | 55,7% | 0,060 | 67,6% |
| `word2vec_skipgram` | 0,356 | 60,2% | 0,062 | **71,0%** |
| `bert_base_pt` | 0,295 | **63,6%** | **0,144** | 70,2% |
| `sentenca_minilm` | **0,560** | 62,6% | 0,087 | 66,1% |

- **Busca:** a consulta vira um vetor e as sinopses são ordenadas pelo cosseno. A precisão média (MAP) usa 20 consultas anotadas pela equipe e considera a posição de todos os filmes relevantes. A busca do site combina 0,3 × `tfidf_sem_stopwords` + 0,7 × `sentenca_minilm` (MAP de 0,613; [docs/busca.md](docs/busca.md)).
- **Recomendação:** os cinco filmes de maior cosseno com cada filme, ou com a média dos filmes de um perfil. A precisão é a fração dos recomendados com ao menos um gênero em comum; a referência é uma recomendação que ignora o texto.
- **Agrupamento + visualização:** K-Means sem rótulos; o ARI compara os clusters com os gêneros (0 = acaso). Cada representação tem dois gráficos com as mesmas coordenadas, um colorido pelo gênero e outro pelo cluster.
- **Classificação:** regressão logística em validação cruzada de 5 dobras, na tarefa de um gênero por filme.
- **Leitura:** nenhuma representação vence todas as tarefas. O modelo de sentença é o melhor na busca, o BERTimbau na recomendação e no agrupamento, e o skip-gram na classificação, empatado com o BERTimbau dentro do desvio entre dobras.

## Ambiente e reprodução

Requisitos: Git, [uv](https://docs.astral.sh/uv/) e Python 3.14 ou superior, conforme `backend/pyproject.toml`. A execução foi validada em Python 3.14.7. O `uv` pode instalar a versão de Python necessária. Execute, a partir da raiz do repositório:

```bash
cd backend
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen ruff check src tests
uv run --frozen ruff format --check src tests
uv run --frozen mypy
```

As mesmas verificações rodam no CI (`.github/workflows/ci.yml`). O arquivo `uv.lock` fixa as dependências resolvidas. Os módulos do corpus usam a biblioteca padrão do Python; a coleta utiliza o cliente HTTP do projeto. Os testes usam dados controlados, identificados como testes, sem consultas à API.

### Repetir as transformações sem rede

Ainda em `backend`, use a amostra já entregue e escolha uma pasta de saída nova:

```bash
uv run --frozen python -m app.corpus process --input ../data/raw/tmdb_2026-09-12 --output ../data/processed/minha_execucao --stopwords ../config/stopwords_pt.txt
uv run --frozen python -m app.corpus verify --input ../data/processed/minha_execucao
```

Não é necessário token para esses dois comandos. A pasta de saída não pode existir: isso evita substituir uma execução anterior. Para repetir outra vez, escolha outro nome. Com as mesmas entradas e regras, os arquivos de conteúdo são idênticos byte a byte em qualquer sistema operacional (sempre com quebra de linha LF); o manifesto varia por registrar a hora da execução e a identidade do código.

### Fazer uma nova coleta real

Crie `backend/.env` a partir de `backend/.env.example` e preencha `TMDB_BEARER_TOKEN` com o token de leitura (Bearer) do TMDB; a chave `api_key` não é mais aceita. O `.env` é ignorado pelo Git, e variáveis de ambiente têm precedência sobre ele. Nunca copie a credencial para comandos versionados, notebooks, saídas, screenshots ou CI. Uma credencial chegou a ser versionada em um commit antigo e precisa ser revogada no TMDB ([ADR 0002](docs/adr/0002-credencial-e-exposicao-da-api.md)).

Em `backend`:

```bash
uv run --frozen python -m app.corpus collect --config ../config/coleta.json --output ../data/raw/nova_coleta
uv run --frozen python -m app.corpus process --input ../data/raw/nova_coleta --output ../data/processed/nova_coleta --stopwords ../config/stopwords_pt.txt
uv run --frozen python -m app.corpus verify --input ../data/processed/nova_coleta
```

A coleta devolve código de saída 0 quando completa e 2 quando parcial. Em falhas, leia `manifest.json`: os resultados já recebidos e as falhas são preservados. Uma falha de página interrompe aquele recorte; os demais são tentados. Não há retomada automática nem agendamento periódico. Uma nova coleta online pode produzir registros diferentes devido a mudanças do TMDB e do ranking.

## As representações

| Arquivo na pasta processada | Conteúdo | Entrada |
|---|---|---|
| `01_original.jsonl` | Sinopse sem alteração; `text` pode ser null | `movies.jsonl` |
| `02_clean.jsonl` | HTML/URLs/controles tratados, espaços uniformizados e Unicode NFC | Original |
| `03_normalized.jsonl` | Texto em minúsculas por `casefold`, conservando acentos | Limpa |
| `04_tokens.jsonl` | Tokens lexicais e pontuação separados | Normalizada |
| `05_without_punctuation.jsonl` | Apenas tokens com letras ou números | Tokenizada |
| `06_without_stopwords.jsonl` | Filtro pela lista conservadora versionada | Sem pontuação |

Cada linha possui o mesmo `id` da correspondente nas demais etapas. `metadata.jsonl` mantém títulos originais/localizados e metadados; `memberships.json` registra os recortes que retornaram cada filme. As versões intermediárias continuam disponíveis: mais transformação não significa melhor recuperação.

## Demonstração auxiliar

Com a credencial configurada, em `backend`:

```bash
uv sync --frozen --extra semantico
uv run --frozen --extra semantico uvicorn app.main:app --host 127.0.0.1 --reload
```

A API não inicia sem `TMDB_BEARER_TOKEN`. Com o extra `semantico`, ela carrega a busca por tema na inicialização, o que leva alguns segundos; sem ele, sobe normalmente e o modo `sinopse` avisa que está indisponível. API: <http://127.0.0.1:8000/docs>. Em outro terminal, a partir da raiz:

```bash
cd frontend
python -m http.server 5500
```

Interface: <http://127.0.0.1:5500>. A pesquisa permite escolher título, preferências por regras, tema nas sinopses ou modo automático. O modo automático segue esta ordem:
1. correspondência exata com título localizado ou original;
2. busca por tema nas sinopses, quando encontra filmes;
3. descoberta pelas preferências;
4. busca por título.

O modo de título permite resolver ambiguidades.

**Classificar uma sinopse:** na aba "Classificar sinopse", escreva ou cole uma sinopse (ou use um dos exemplos do corpus) para ver o gênero previsto e a probabilidade de cada um. O modelo é a regressão logística da Etapa 3 sobre o embedding de sentença, com F1 macro de 66,1% na validação cruzada. Comédia é o gênero mais difícil, e frases curtas fora do estilo das sinopses erram com frequência ([ADR 0021](docs/adr/0021-classificacao-na-tela.md)).

**Busca por tema** (`modo=sinopse`): ordena os 428 filmes da amostra por 0,3 × TF-IDF sem stopwords + 0,7 × embedding de sentença (`sentenca_minilm`). Gênero, período, nota e negação reconhecidos pelas regras filtram os filmes. Em "quero um filme de ação sobre máquinas", só entram filmes de ação, ordenados pela proximidade com "máquinas". A combinação foi escolhida comparando as oito representações em 20 consultas anotadas ([ADR 0020](docs/adr/0020-busca-hibrida-tfidf-e-sentenca.md)). Filmes fora da amostra continuam acessíveis pelo título e pela descoberta. Explicação completa, com os algoritmos, o exemplo passo a passo e os limites: [docs/busca.md](docs/busca.md).

| Rota implementada | Função |
|---|---|
| `GET /saude` | Saúde da aplicação |
| `GET /filmes/603` | Detalhes do filme, com elenco e vídeos |
| `GET /classificacao?texto=...` | Gênero previsto para uma sinopse e a probabilidade de cada gênero (regressão logística sobre o embedding de sentença); `texto` com até 1.000 caracteres |
| `GET /pesquisa?q=...&modo=auto` | Título, tema nas sinopses ou preferências reconhecidas; `modo=titulo`, `modo=descoberta` e `modo=sinopse` também disponíveis; `q` com até 200 caracteres |

A rota `/busca` foi removida: `GET /pesquisa?q=...&modo=titulo` faz a mesma busca por título. O cliente chama `/discover/movie` para preferências. Configurações opcionais em `backend/.env`: `TMDB_LANGUAGE`, `TMDB_TIMEOUT`, `CORS_ORIGINS` e `RATE_LIMIT_PER_MINUTE` (padrão 60 requisições por minuto por IP; acima disso, HTTP 429). O CORS só libera as origens da interface e não é controle de acesso; por isso a API roda em `127.0.0.1` e tem limite de requisições. A interface lê o endereço da API na meta tag `api-base` de `frontend/index.html`, que também define a política de segurança de conteúdo (CSP).

## Etapa 2 — Representações vetoriais

O módulo `app.vectors` compara oito representações das mesmas sinopses, na progressão das Aulas 6 e 7:
- BoW e TF-IDF, a partir das etapas `05` e `06`;
- word2vec pré-treinado do NILC, nas arquiteturas CBOW e skip-gram;
- BERTimbau (BERT contextual em português);
- um modelo de embeddings de sentença multilíngue (sentence-transformers).

Sobre cada uma, executa as tarefas busca (consultas anotadas), recomendação (item → item e por perfil), agrupamento (K-Means) e visualização (projeção 2D por gênero e por cluster). Também compara as representações nos exemplos da aula: palavras vizinhas, pares de frases, polissemia (“banco”, “manga”) e síntese comparativa. Em `backend`:

```bash
# somente BoW e TF-IDF (leve)
uv run --frozen python -m app.vectors build --input ../data/processed/tmdb_2026-09-12 --output ../data/vectors/lexical --config ../config/vetorizacao.json --queries ../config/consultas.json
# completo: instala o extra opcional (torch CPU) e baixa ~3,1 GB de modelos na primeira vez
uv sync --frozen --extra semantico
uv run --frozen --extra semantico python -m app.vectors build --input ../data/processed/tmdb_2026-09-12 --output ../data/vectors/completo --config ../config/vetorizacao_semantica.json --queries ../config/consultas.json --probes ../config/sondas_semanticas.json
uv run --frozen python -m app.vectors verify --input ../data/vectors/completo
```

- **Caso do professor:** a consulta “filme sobre simulação da realidade” coloca Matrix em 11º a 69º lugar nas representações lexicais, porque “simulação” não aparece na sinopse. Com word2vec skip-gram, Matrix sobe para 5º; com o modelo de sentença, para 2º.
- **Polissemia:** no word2vec, “banco” tem o mesmo vetor em “o banco aprovou o financiamento” e em “sentou no banco da praça”. No BERTimbau, os usos com o mesmo sentido ficam mais próximos (cosseno 0,82 × 0,55 entre sentidos diferentes).
- **Recomendação por perfil:** para quem gostou de *Invocação do Mal*, *Hereditário* e *Sobrenatural: A Origem*, o modelo de sentença recomenda *Invocação do Mal 2*, *Invocação do Mal 4* e *A Morte do Demônio*. Para o perfil de animação (*Toy Story*, *Up*, *Monstros S.A.*), BoW e TF-IDF encontram as sequências de *Toy Story* pelos nomes dos personagens (woody, buzz, andy).

- [Decisões, arquitetura e segurança](docs/vetorizacao.md)
- [Resultados calculados](data/vectors/tmdb_2026-09-12/report.md)
- Configurações [lexical](config/vetorizacao.json) e [completa](config/vetorizacao_semantica.json), com os perfis de recomendação; [consultas anotadas](config/consultas.json); [sondas da Aula 7](config/sondas_semanticas.json)

## Etapa 3 — Classificação de gêneros

O módulo `app.classification` aplica a Aula 8: prevê o gênero do filme a partir da sinopse, usando os `genre_ids` do TMDB como rótulos, em duas formulações:
- **multiclasse:** 325 filmes com exatamente um de drama, comédia, terror e ficção científica;
- **multirrótulo:** 428 filmes, um classificador binário por gênero.

A mesma regressão logística é aplicada às oito representações da Etapa 2, com validação cruzada em 5 dobras e `C` escolhido pela log loss só com o treino de cada dobra. Nas mesmas dobras, o K-Means (sem rótulos) e quatro classificadores alternativos (Naive Bayes, SVM linear, floresta aleatória e k vizinhos) servem de comparação. Em `backend`:

```bash
# somente BoW e TF-IDF (cerca de 2 minutos)
uv run --frozen python -m app.classification build --input ../data/processed/tmdb_2026-09-12 --output ../data/classification/lexical --config ../config/classificacao.json
# completo, lendo os vetores densos verificados da Etapa 2 (cerca de 2,5 minutos; dispensa o extra semantico)
uv run --frozen python -m app.classification build --input ../data/processed/tmdb_2026-09-12 --output ../data/classification/completo --config ../config/classificacao_semantica.json --vectors ../data/vectors/tmdb_2026-09-12
uv run --frozen python -m app.classification verify --input ../data/classification/completo
```

Sem `--vectors`, as representações densas são recalculadas: é preciso o extra `semantico`, e o build leva cerca de 6 minutos. A pasta entregue foi gerada com `--vectors`.

| F1 macro (multiclasse) | Valor |
|---|---:|
| Referência que ignora o texto | 10,7% |
| Melhor lexical (`tfidf_sem_pontuacao`) | 59,3% |
| word2vec CBOW / skip-gram | 67,6% / 71,0% |
| BERTimbau congelado | 70,2% |
| Modelo de sentença | 66,1% |

- **Resultado:** as representações densas superam as lexicais. Skip-gram e BERTimbau empatam dentro do desvio entre dobras, que chega a 5,7 pontos.
- **Classificador:** a regressão logística tem o maior F1 nas três melhores representações e fica a até 1,7 ponto do melhor em outras três. Nas contagens brutas (BoW), o Naive Bayes vence com folga. O SVM empata em F1, mas não dá probabilidades.
- **Agrupar × classificar:** nas mesmas 325 sinopses e com a mesma representação, o K-Means (sem rótulos) coincide muito menos com os gêneros que o classificador (ARI de até 0,13 contra até 0,38).
- **Erros:** comédia é o gênero mais difícil, e parte dos erros vem de filmes de ação com comédia que a restrição aos quatro gêneros reduz a “comédia”.
- **Sem treino:** o Jev (TypeSafe AI) também classifica o gênero, sem ver nenhum exemplo rotulado; os resultados estão na seção [Aula 8 — Classificação de gênero com o Jev](#aula-8--classificação-de-gênero-com-o-jev). LLM com instrução foi discutido e não executado.

- [Por que estes modelos e não os outros](docs/escolha-dos-modelos.md), com medidas e exemplos
- [Decisões e leitura dos resultados](docs/classificacao.md) e [ADR 0017](docs/adr/0017-aula8-classificacao-de-generos.md)
- [Resultados calculados](data/classification/tmdb_2026-09-12/report.md)
- Configurações [lexical](config/classificacao.json) e [completa](config/classificacao_semantica.json)

## Aula 8 — Classificação de gênero com o Jev

O módulo `app.jev` usa o [Jev](https://docs.typesafe.ai/introduction), da TypeSafe AI, para classificar o gênero das sinopses **sem treino**. Cada filme recebe, numa única chamada:
- uma **Choice** com o gênero principal (Drama, Comédia, Terror ou Ficção científica);
- um **Noul** por gênero, que dá a probabilidade de o filme ser daquele gênero.

As mesmas sinopses passam por um **TF-IDF + regressão logística**, o pipeline clássico, treinado com os filmes fora da amostra. Os dois são medidos nos mesmos filmes e com as mesmas métricas. A amostra tem 120 filmes (25 por gênero único e 20 com dois gêneros), ou seja, 120 chamadas à API, e deixa cerca de 300 filmes para o treino da referência. As perguntas e os critérios ficam em [`config/jev.json`](config/jev.json). O rótulo são os `genre_ids` do TMDB restritos aos quatro gêneros, o mesmo da classificação da Etapa 3.


| Métrica (120 filmes, modelo `jev-1.13.0`) | Jev | TF-IDF + RL |
|---|---:|---:|
| Gênero principal entre os gêneros do filme | **87,5%** | 60,0% |
| Acurácia nos 100 filmes de um gênero | **85,0%** | 56,0% |
| F1 macro da Choice | **0,85** | 0,54 |
| ROC AUC macro por gênero (Noul × regressão binária) | **0,96** | 0,82 |
| Conjunto de gêneros exato | **67,5%** | 35,0% |

- **O Jev foi melhor em todas as métricas do resumo** sem ver nenhum exemplo rotulado do corpus. Com 100 filmes, o intervalo de 95% da diferença de acurácia vai de cerca de 17 a 41 pontos, portanto a vantagem não se explica só pelo tamanho da amostra. Na classificação da Etapa 3, com validação cruzada nas 325 sinopses de um gênero, o melhor classificador treinado chega a 71,0% de F1 macro (skip-gram); os conjuntos de teste são diferentes, mas a ordem de grandeza mostra a vantagem do Jev neste corpus.
- **O TF-IDF puxa muitos filmes para drama:** 14 dos 25 filmes de terror e 10 das 25 comédias saíram como drama. O Jev acertou os 25 filmes de terror e 24 dos 25 dramas; o erro mais comum dele foi comédia classificada como drama (6 de 25), em comédias de ação como Police Story e Os Bad Boys.
- **Confiança não é acerto:** a confiança média da Choice é 0,93 quando o Jev acerta e 0,63 quando erra, mas há erros com confiança alta (Velozes & Furiosos: Hobbs & Shaw, comédia, saiu como ficção científica com confiança 1,0). A Choice coincide com o Noul mais alto em 94% dos filmes.

Resultados completos: [relatório](data/jev/tmdb_2026-09-12/report.md), [métricas](data/jev/tmdb_2026-09-12/metrics.json) e [respostas brutas](data/jev/tmdb_2026-09-12/responses.jsonl). Decisões: [ADR 0019](docs/adr/0019-aula8-jev-classificacao-de-genero.md).

### Reproduzir

Reavaliar a entrega **não gasta chamadas**: `--reuse` reaproveita as respostas salvas, e o resultado é idêntico byte a byte (exceto o manifesto). Em `backend`:

```bash
uv sync --frozen --extra jev
uv run --frozen --extra jev python -m app.jev run --input ../data/processed/tmdb_2026-09-12 --output ../data/jev/reproducao --config ../config/jev.json --reuse ../data/jev/tmdb_2026-09-12
uv run --frozen python -m app.jev verify --input ../data/jev/tmdb_2026-09-12
```

Uma execução nova, sem `--reuse`, chama a API: coloque a chave em `backend/.env` como `TYPESAFE_API_KEY=...`, nunca em notebooks ou comandos versionados. Se a primeira chamada falhar, nada é gravado. O alias `jev-latest` pode apontar para outro modelo com o tempo, por isso a versão usada fica registrada no manifesto.

## Próxima etapa

- **Busca:** avaliar a busca por tema com consultas escritas por outras pessoas e ampliar o corpus além dos 428 filmes. As 20 consultas atuais foram escritas e julgadas pela equipe e servem para comparar as representações, não como avaliação com usuários.
- **Recomendação:** a avaliação por gênero compartilhado é uma aproximação. Pares de filmes anotados como boas recomendações entre si, ou avaliações de usuários, permitiriam medi-la de fato.

## Fonte e atribuição

Dados fornecidos por [The Movie Database](https://www.themoviedb.org/) via [API TMDB](https://developer.themoviedb.org/docs/getting-started). Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB. Os dados preservam as condições de uso da fonte; sua inclusão para a atividade acadêmica não concede uma nova licença sobre sinopses, imagens ou catálogo. Confira os termos e exigências de atribuição antes de redistribuir ou publicar outra aplicação.
