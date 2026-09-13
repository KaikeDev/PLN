# PLN 2026/2 — Etapa Prática 1

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

Os pesos identificam dimensões da rubrica; não são notas atribuídas à entrega. Stemming, lematização e vetorização **não foram executados** nesta versão. A comparação entre recortes e a coleta automatizada estão implementadas, mas a concessão do bônus cabe ao professor.

- [Documento Word da entrega](docs/PLN_2026_2_Avaliacao_Pratica_1_Atualizado.docx)
- [Validação técnica](docs/validacao.md)
- [Decisões e limitações](docs/decisoes.md)

## Ambiente e reprodução

Requisitos: Git, [uv](https://docs.astral.sh/uv/) e Python 3.14 ou superior, conforme `backend/pyproject.toml`. A execução foi validada em Python 3.14.7. O `uv` pode instalar a versão de Python necessária. Execute, a partir da raiz do repositório:

```bash
cd backend
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
```

O arquivo `uv.lock` fixa as dependências resolvidas. Os módulos do corpus usam a biblioteca padrão do Python; a coleta utiliza o cliente HTTP do projeto. Os testes usam dados controlados, identificados como testes, sem consultas à API.

### Repetir as transformações sem rede

Ainda em `backend`, use a amostra já entregue e escolha uma pasta de saída nova:

```bash
uv run --frozen python -m app.corpus process --input ../data/raw/tmdb_2026-09-12 --output ../data/processed/minha_execucao --stopwords ../config/stopwords_pt.txt
uv run --frozen python -m app.corpus verify --input ../data/processed/minha_execucao
```

Não é necessário token para esses dois comandos. A pasta de saída não pode existir: isso evita substituir uma execução anterior. Para repetir outra vez, escolha outro nome. Com as mesmas entradas e regras, os arquivos de conteúdo são idênticos; o manifesto varia por registrar a hora da execução e a identidade do código.

### Fazer uma nova coleta real

Crie `backend/.env` a partir de `backend/.env.example` e preencha `TMDB_BEARER_TOKEN` com sua credencial. O arquivo local é ignorado pelo Git. Variáveis de ambiente também são aceitas. Nunca copie a credencial para comandos versionados, notebooks, saídas ou screenshots.

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
uv run --frozen uvicorn app.main:app --reload
```

API: <http://127.0.0.1:8000/docs>. Em outro terminal, a partir da raiz:

```bash
cd frontend
python -m http.server 5500
```

Interface: <http://127.0.0.1:5500>. A pesquisa permite escolher título, preferências por regras ou modo automático. O modo automático prioriza correspondência exata com título localizado/original; o modo de título permite resolver ambiguidades. A pesquisa auxiliar ainda não usa os vetores das sinopses.

| Rota implementada | Função |
|---|---|
| `GET /saude` | Saúde da aplicação |
| `GET /busca?q=Matrix` | Busca direta por título |
| `GET /filmes/603` | Detalhes do filme |
| `GET /pesquisa?q=...&modo=auto` | Título ou preferências reconhecidas; `modo=titulo` e `modo=descoberta` também disponíveis |

O cliente chama `/discover/movie` para preferências; não há rota pública local `/descobrir`. O CORS permite apenas as duas origens locais da interface, definidas em `backend/src/app/main.py`.

## Próxima etapa

Usar as mesmas sinopses e consultas de avaliação para comparar representações vetoriais e recuperação. O exemplo de Matrix envolve encontrar assuntos relacionados à sinopse; a mera filtragem por gênero não satisfaz esse objetivo. A palavra “simulação” não aparece literalmente na sinopse coletada de Matrix, portanto busca por contagem de palavras não garante recuperá-lo por esse termo.

## Fonte e atribuição

Dados fornecidos por [The Movie Database](https://www.themoviedb.org/) via [API TMDB](https://developer.themoviedb.org/docs/getting-started). Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB. Os dados preservam as condições de uso da fonte; sua inclusão para a atividade acadêmica não concede uma nova licença sobre sinopses, imagens ou catálogo. Confira os termos e exigências de atribuição antes de redistribuir ou publicar outra aplicação.
