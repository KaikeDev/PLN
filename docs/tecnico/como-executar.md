# Como executar

Todos os comandos são executados na pasta `backend`, salvo indicação. Requisitos: Git, [uv](https://docs.astral.sh/uv/) e Python 3.14 ou superior (o `uv` instala a versão certa). A execução foi validada em Python 3.14.7, e o `uv.lock` fixa as dependências.

## Ambiente e verificações

```bash
cd backend
uv sync --frozen                                   # dependências básicas
uv sync --frozen --extra semantico --extra jev --extra entidades     # + modelos (torch), SDK do Jev e spaCy
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen ruff check src tests
uv run --frozen ruff format --check src tests
uv run --frozen mypy
```

As mesmas verificações rodam no CI (`.github/workflows/ci.yml`). Os testes usam dados e modelos falsos, sem rede.

## Conferir os dados entregues

Cada pasta de dados tem um `manifest.json` com o SHA-256 de cada arquivo. Estes comandos conferem tudo sem recalcular nada:

```bash
uv run --frozen python -m app.corpus verify --input ../data/preparacao/tmdb_2026-09-12
uv run --frozen python -m app.representations verify --input ../data/representacoes/tmdb_2026-09-12
uv run --frozen python -m app.classification verify --input ../data/classificacao/tmdb_2026-09-12
uv run --frozen python -m app.classification.jev verify --input ../data/jev/tmdb_2026-09-12
```

## Refazer cada etapa

Toda etapa grava numa **pasta nova**, que não pode existir; nada é sobrescrito. Com as mesmas entradas, os arquivos de conteúdo saem idênticos byte a byte; só o `manifest.json` muda, por registrar a hora e a identidade do código. As pastas de reprodução em `data/` são ignoradas pelo Git.

### 1. Coleta e preparação

Refazer a preparação a partir da coleta entregue, sem rede:

```bash
uv run --frozen python -m app.corpus process --input ../data/coleta/tmdb_2026-09-12 --output ../data/preparacao/minha_execucao --stopwords ../config/coleta/stopwords_pt.txt
uv run --frozen python -m app.corpus verify --input ../data/preparacao/minha_execucao
```

Nova coleta real (exige `TMDB_BEARER_TOKEN` em `backend/.env`; veja [Credenciais](#credenciais)):

```bash
uv run --frozen python -m app.corpus collect --config ../config/coleta/coleta.json --output ../data/coleta/nova_coleta
```

A coleta devolve código 0 quando completa e 2 quando parcial; os resultados recebidos e as falhas ficam no manifesto. Uma coleta nova pode trazer filmes diferentes, porque o ranking do TMDB muda.

### 2. Representações, busca, recomendação e agrupamento

```bash
# somente BoW e TF-IDF (leve)
uv run --frozen python -m app.representations build --input ../data/preparacao/tmdb_2026-09-12 --output ../data/representacoes/lexical --config ../config/representacoes/vetorizacao.json --queries ../config/busca/consultas.json
# completo: baixa cerca de 3,1 GB de modelos na primeira vez
uv run --frozen --extra semantico python -m app.representations build --input ../data/preparacao/tmdb_2026-09-12 --output ../data/representacoes/completo --config ../config/representacoes/vetorizacao_semantica.json --queries ../config/busca/consultas.json --probes ../config/representacoes/sondas_semanticas.json
```

### 3. Busca

```bash
# uma frase, com uma representação
uv run --frozen --extra semantico python -m app.search query --input ../data/preparacao/tmdb_2026-09-12 --config ../config/representacoes/vetorizacao_semantica.json --representation sentenca_minilm --text "uma casa assombrada por espíritos"
# a combinação do site: compara cada representação com a combinação nas 20 consultas
uv run --frozen --extra semantico python -m app.search hybrid --input ../data/preparacao/tmdb_2026-09-12 --config ../config/representacoes/vetorizacao_semantica.json --search ../config/busca/busca.json --queries ../config/busca/consultas.json
```

### 4. Classificação treinada

```bash
# completo, lendo os vetores já calculados (cerca de 3 minutos)
uv run --frozen python -m app.classification build --input ../data/preparacao/tmdb_2026-09-12 --output ../data/classificacao/minha_execucao --config ../config/classificacao/classificacao_semantica.json --vectors ../data/representacoes/tmdb_2026-09-12
# somente BoW e TF-IDF (cerca de 2 minutos)
uv run --frozen python -m app.classification build --input ../data/preparacao/tmdb_2026-09-12 --output ../data/classificacao/lexical --config ../config/classificacao/classificacao.json
```

### 5. Jev

Reavaliar a entrega **sem gastar chamadas** (reaproveita as respostas salvas):

```bash
uv run --frozen --extra jev python -m app.classification.jev run --input ../data/preparacao/tmdb_2026-09-12 --output ../data/jev/reproducao --config ../config/classificacao/jev.json --reuse ../data/jev/tmdb_2026-09-12
```

Sem `--reuse`, cada filme é uma chamada paga à API (exige `TYPESAFE_API_KEY`). Se a primeira chamada falhar, nada é gravado.

### 6. Análise de sentimentos

```bash
# preparação das críticas entregues, sem rede (segundos); necessária para a aba "Analisar crítica"
uv run --frozen python -m app.sentiment process --input ../data/coleta/criticas_2026-10-10 --output ../data/preparacao/criticas_2026-10-10 --stopwords ../config/coleta/stopwords_pt.txt
# experimento com as 8 representações (cerca de 45 minutos, 39 deles no BERTimbau)
uv run --frozen --extra semantico python -m app.sentiment build --input ../data/preparacao/criticas_2026-10-10 --output ../data/sentimento/reproducao --config ../config/sentimento/sentimento.json
```

Uma coleta nova de críticas (exige `TMDB_BEARER_TOKEN` e o catálogo do site) está em [7-sentimentos.md](../7-sentimentos.md#como-executar).

### 7. Entidades e relações

```bash
uv sync --frozen --extra semantico --extra jev --extra entidades
# cerca de 15 segundos; usa os créditos entregues em data/coleta/creditos_2026-10-10
uv run --frozen --extra entidades python -m app.entities build --input ../data/preparacao/tmdb_2026-09-12 --credits ../data/coleta/creditos_2026-10-10 --output ../data/entidades/reproducao --config ../config/entidades/entidades.json
```

## Catálogo do site

> **Obrigatório depois de clonar o repositório**, para o site usar o catálogo completo. Sem ele, a API registra um aviso no terminal, o site mostra uma faixa amarela no topo, e a busca e os filmes parecidos usam só a amostra de 428 filmes. A rota `/saude` informa a origem e o tamanho do catálogo carregado.

A busca por tema e os filmes parecidos do site procuram num catálogo de cerca de 5.500 filmes de 18 gêneros, separado da amostra avaliada ([ADR 0024](../adr/0024-catalogo-do-site.md)). Ele fica fora do Git e é gerado com três comandos, em `backend` (exige `TMDB_BEARER_TOKEN`; cerca de 5 minutos de coleta e alguns minutos de vetores):

```bash
uv run --frozen python -m app.corpus collect --config ../config/coleta/coleta_site.json --output ../data/coleta/site_2026-10-05
uv run --frozen python -m app.corpus process --input ../data/coleta/site_2026-10-05 --output ../data/preparacao/site_2026-10-05 --stopwords ../config/coleta/stopwords_pt.txt
uv run --frozen --extra semantico python -m app.representations build --input ../data/preparacao/site_2026-10-05 --output ../data/representacoes/site_2026-10-05 --config ../config/representacoes/vetorizacao_site.json
```

Sem o catálogo, a API usa a amostra avaliada de 428 filmes e registra um aviso. Uma coleta nova pode trazer filmes um pouco diferentes, porque o ranking do TMDB muda; para usar outra pasta, ajuste `SYNOPSIS_PROCESSED_DIR`, `SYNOPSIS_RAW_DIR` e `SYNOPSIS_VECTORS_DIR` em `backend/.env`.

## O site

O passo a passo completo para quem vai só abrir o site está em [rodar-o-site.md](rodar-o-site.md).

Terminal 1, em `backend` (exige `TMDB_BEARER_TOKEN`):

```bash
uv run --frozen --extra semantico --extra jev --extra entidades uvicorn app.main:app --host 127.0.0.1 --reload
```

Terminal 2, também em `backend`:

```bash
uv run --frozen python -m http.server 5500 --directory ../frontend
```

Abra <http://127.0.0.1:5500>. A API leva alguns segundos para iniciar, porque carrega os modelos da busca por tema e treina o classificador da tela. Sem o extra `semantico`, ela sobe mesmo assim, e a busca por tema e a classificação avisam que estão indisponíveis; o mesmo vale para o extra `entidades` e para as críticas preparadas. A documentação interativa da API fica em <http://127.0.0.1:8000/docs>.

| Rota | Função |
|---|---|
| `GET /saude` | Saúde da aplicação |
| `GET /pesquisa?q=...&modo=auto` | Título, tema nas sinopses ou preferências; `modo` também aceita `titulo`, `descoberta` e `sinopse`; `q` com até 200 caracteres |
| `GET /filmes/603` | Ficha do filme, com elenco e vídeos |
| `GET /filmes/603/parecidos?quantidade=5` | Filmes de sinopse mais parecida (só para os filmes do catálogo do site) |
| `GET /classificacao?texto=...` | Gênero previsto para uma sinopse e a probabilidade de cada gênero; até 1.000 caracteres |
| `GET /sentimento?texto=...` | Polaridade, probabilidade de ser positiva, nota prevista e palavras de maior peso de uma crítica; até 5.000 caracteres |
| `GET /entidades?texto=...` | Entidades (PER, LOC, ORG, MISC) e triplas sujeito — relação → objeto de um texto; até 2.000 caracteres |

Configurações opcionais em `backend/.env`: `TMDB_LANGUAGE`, `TMDB_TIMEOUT`, `CORS_ORIGINS` e `RATE_LIMIT_PER_MINUTE` (padrão de 60 requisições por minuto por IP). O CORS só libera as origens da interface, e a API roda em `127.0.0.1` ([ADR 0002](../adr/0002-credencial-e-exposicao-da-api.md)).

## Credenciais

Crie `backend/.env` a partir de `backend/.env.example`:

- `TMDB_BEARER_TOKEN`: token de leitura (Bearer) do TMDB, para o site e para uma coleta nova;
- `TYPESAFE_API_KEY`: chave do Jev, só para chamadas novas ao Jev.

O `.env` é ignorado pelo Git, e variáveis de ambiente têm precedência sobre ele. Nunca copie credenciais para comandos versionados, notebooks, saídas ou capturas de tela.

## Problemas conhecidos no Windows

- **Controle Inteligente de Aplicativos:** se o Windows bloquear o `python.exe` do ambiente virtual ou DLLs do scikit-learn ("política de Controle de Aplicativo"), o ambiente não roda. Na máquina de desenvolvimento, o controle foi desativado.
- **API rodando e `uv run` ao mesmo tempo:** com o servidor no ar, o `uv run` pode falhar ao reinstalar o projeto, porque os arquivos ficam travados. Use `uv run --frozen --no-sync ...` enquanto a API estiver rodando.
