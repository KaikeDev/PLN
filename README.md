# PLN 2026/2 — Etapas Práticas 1 e 2

**Coleta e preparação de sinopses de filmes para comparação posterior de técnicas de PLN.** O projeto preserva o corpus original e seis representações alinhadas pelo ID do TMDB. A consulta de filmes na interface é uma demonstração auxiliar; a entrega desta etapa está nos dados, scripts e evidências abaixo.

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

Os pesos identificam dimensões da rubrica; não são notas atribuídas à entrega. Stemming, lematização e vetorização **não foram executados** na Etapa 1; a vetorização está na [Etapa 2](#etapa-2--representações-vetoriais). A comparação entre recortes e a coleta automatizada estão implementadas, mas a concessão do bônus cabe ao professor.

- [Documento Word da entrega](docs/PLN_2026_2_Avaliacao_Pratica_1_Atualizado.docx)
- [Validação técnica](docs/validacao.md)
- [Decisões de arquitetura e desenvolvimento, com justificativas (`adr.md`)](adr.md), [ADRs detalhadas](docs/adr/README.md) e [limitações](docs/decisoes.md)
- [Arquitetura do código](docs/arquitetura.md)

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
uv run --frozen uvicorn app.main:app --host 127.0.0.1 --reload
```

A API não inicia sem `TMDB_BEARER_TOKEN`. API: <http://127.0.0.1:8000/docs>. Em outro terminal, a partir da raiz:

```bash
cd frontend
python -m http.server 5500
```

Interface: <http://127.0.0.1:5500>. A pesquisa permite escolher título, preferências por regras ou modo automático. O modo automático prioriza correspondência exata com título localizado/original; o modo de título permite resolver ambiguidades. A pesquisa auxiliar ainda não usa os vetores das sinopses.

| Rota implementada | Função |
|---|---|
| `GET /saude` | Saúde da aplicação |
| `GET /filmes/603` | Detalhes do filme, com elenco e vídeos |
| `GET /pesquisa?q=...&modo=auto` | Título ou preferências reconhecidas; `modo=titulo` e `modo=descoberta` também disponíveis; `q` com até 200 caracteres |

A rota `/busca` foi removida: `GET /pesquisa?q=...&modo=titulo` faz a mesma busca por título. O cliente chama `/discover/movie` para preferências. Configurações opcionais em `backend/.env`: `TMDB_LANGUAGE`, `TMDB_TIMEOUT`, `CORS_ORIGINS` e `RATE_LIMIT_PER_MINUTE` (padrão 60 requisições por minuto por IP; acima disso, HTTP 429). O CORS só libera as origens da interface e não é controle de acesso; por isso a API roda em `127.0.0.1` e tem limite de requisições. A interface lê o endereço da API na meta tag `api-base` de `frontend/index.html`, que também define a política de segurança de conteúdo (CSP).

## Etapa 2 — Representações vetoriais

O módulo `app.vectors` compara oito representações das mesmas sinopses, na progressão das Aulas 6 e 7:
- BoW e TF-IDF, a partir das etapas `05` e `06`;
- word2vec pré-treinado do NILC, nas arquiteturas CBOW e skip-gram;
- BERTimbau (BERT contextual em português);
- um modelo de embeddings de sentença multilíngue (sentence-transformers).

Sobre cada uma, calcula similaridade do cosseno, clustering K-Means, projeção 2D e avaliação de consultas anotadas. Também compara as representações nos exemplos da aula: palavras vizinhas, pares de frases, polissemia (“banco”, “manga”) e síntese comparativa. Em `backend`:

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

- [Decisões, arquitetura e segurança](docs/vetorizacao.md)
- [Resultados calculados](data/vectors/tmdb_2026-09-12/report.md)
- Configurações [lexical](config/vetorizacao.json) e [completa](config/vetorizacao_semantica.json); [consultas anotadas](config/consultas.json); [sondas da Aula 7](config/sondas_semanticas.json)

## Próxima etapa

Ampliar as consultas anotadas e a lista de filmes relevantes antes de escolher uma representação. As métricas atuais usam só dois casos de Matrix e servem de ilustração, não de avaliação estatística.

## Fonte e atribuição

Dados fornecidos por [The Movie Database](https://www.themoviedb.org/) via [API TMDB](https://developer.themoviedb.org/docs/getting-started). Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB. Os dados preservam as condições de uso da fonte; sua inclusão para a atividade acadêmica não concede uma nova licença sobre sinopses, imagens ou catálogo. Confira os termos e exigências de atribuição antes de redistribuir ou publicar outra aplicação.
