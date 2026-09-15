# 0013 — Ambiente, testes, lint, tipos e CI

- Estado: Aceita
- Data: 2026-09-14

## Contexto

O projeto usava `uv` e `unittest`, mas não tinha formatador, lint, verificação de tipos, grupo de dependências de desenvolvimento nem integração contínua. Rotas HTTP e o cliente do TMDB não tinham testes.

## Decisão

- **Ambiente**: Python ≥ 3.14 e `uv`, com `uv.lock` fixando as versões. Ferramentas de desenvolvimento ficam no grupo `dev`.
- **Testes**: `unittest` da biblioteca padrão, com dados controlados e dublês injetados (`tests/fakes.py`, sessões e relógios falsos). Nenhum teste acessa a rede ou baixa modelos. Rotas são testadas com `TestClient` e `create_app(settings, catalog)`.
- **Lint e formatação**: `ruff` (regras E, F, W, I, B, UP, S, SIM, RUF), linha de 140 caracteres. `E501` fica a cargo do formatador.
- **Tipos**: `mypy` sobre `src`, com o plugin do Pydantic.
- **CI** (`.github/workflows/ci.yml`): lint, formatação, tipos, testes, `verify` dos dados entregues e checagem de sintaxe do JavaScript. Sem segredos e sem o extra `semantico`.

## Alternativas consideradas

- `pytest`: mais conciso, mas a suíte existente e os comandos entregues usam `unittest`.
- `black` + `flake8` + `isort`: três ferramentas para o que o `ruff` faz sozinho.

## Consequências

- Todo pull request precisa passar pelo CI.
- Os testes de `vectors` usam modelos falsos; a qualidade dos modelos reais é validada só pelas execuções registradas em `docs/validacao.md`.
