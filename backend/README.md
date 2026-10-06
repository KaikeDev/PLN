# Backend de PLN

O código fica em `src/app`, com uma pasta por tarefa da disciplina. A visão geral está no [README principal](../README.md), a apresentação em [APRESENTACAO.md](../APRESENTACAO.md), todos os comandos em [docs/tecnico/como-executar.md](../docs/tecnico/como-executar.md) e a organização do código em [docs/tecnico/arquitetura.md](../docs/tecnico/arquitetura.md).

| Pasta em `src/app` | Tarefa | Comando |
|---|---|---|
| `corpus/` | 1. Coleta e preparação | `python -m app.corpus collect / process / verify` |
| `representations/` | 2. As oito representações e o pipeline das análises | `python -m app.representations build / verify` |
| `search/` | 3. Busca (regras, combinação TF-IDF + embedding de sentença, avaliação) | `python -m app.search query / hybrid` |
| `recommendation/` | 4. Recomendação | roda dentro de `app.representations build` |
| `clustering/` | 5. Agrupamento e visualização | roda dentro de `app.representations build` |
| `classification/` | 6. Classificação (regressão logística, Jev em `jev/`, classificador da tela) | `python -m app.classification build / verify`, `python -m app.classification.jev run / verify` |
| `api/`, `main.py`, `settings.py` | Site: API FastAPI | `uvicorn app.main:app --host 127.0.0.1` |
| `tmdb/` | Cliente da API do TMDB | — |
| `shared/` | Artefatos, manifesto, validação e regras de língua | — |

Nesta pasta:

```bash
uv sync --frozen --extra semantico --extra jev
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen ruff check src tests && uv run --frozen ruff format --check src tests
uv run --frozen mypy
```

**Depois de clonar:** gere o catálogo do site (passo 2 do [README principal](../README.md#como-executar)); sem ele, a busca por tema e os filmes parecidos usam só os 428 filmes da amostra.

As credenciais ficam só em `backend/.env` (modelo em `.env.example`) ou em variáveis de ambiente. Elas só são necessárias para o site, para uma coleta nova e para chamadas novas ao Jev. Conferir e refazer os dados já entregues funciona sem rede.
