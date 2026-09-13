# Backend de PLN

As instruções completas, o mapa da rubrica e as evidências estão no [README principal](../README.md).

Nesta pasta:

```bash
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python -m app.corpus --help
```

O pacote `src/app/corpus` coleta e prepara a base da Etapa Prática 1. Os pacotes `services/pln` e `services/tmdb` mantêm a demonstração auxiliar de consultas. Configure a credencial apenas em `.env` local ou variável de ambiente quando usar a API; o processamento dos dados já salvos funciona offline.
