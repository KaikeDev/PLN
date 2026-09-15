# Backend de PLN

As instruções completas, o mapa da rubrica e as evidências estão no [README principal](../README.md). A organização do código está em [docs/arquitetura.md](../docs/arquitetura.md), e as decisões, em [docs/adr](../docs/adr/README.md).

Nesta pasta:

```bash
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen ruff check src tests && uv run --frozen ruff format --check src tests
uv run --frozen mypy
uv run --frozen python -m app.corpus --help
uv run --frozen python -m app.vectors --help
uv run --frozen uvicorn app.main:app --host 127.0.0.1
```

| Pacote | Conteúdo |
|---|---|
| `src/app/corpus` | Etapa 1: coleta e preparação da base |
| `src/app/vectors` | Etapa 2: representações vetoriais e análises |
| `src/app/api`, `src/app/domain`, `src/app/infra` | Demonstração auxiliar de pesquisa (API FastAPI sobre o TMDB) |
| `src/app/shared` | Artefatos, manifesto, validação e regras de língua compartilhadas |

A credencial fica apenas em `backend/.env` (modelo em `.env.example`) ou em variável de ambiente, e só é necessária para a API e para uma nova coleta. O processamento e a vetorização dos dados já salvos funcionam offline.
