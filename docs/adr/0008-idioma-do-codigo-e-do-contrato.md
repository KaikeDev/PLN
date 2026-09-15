# 0008 — Identificadores em inglês; contrato, mensagens e documentação em português

- Estado: Aceita
- Data: 2026-09-14

## Contexto

`corpus` e `vectors` usavam identificadores em inglês, `api` e `services/pln` usavam português, e alguns módulos misturavam os dois (`candidates`, `exact`, `filtros`).

## Decisão

- **Identificadores no código** (módulos, classes, funções, variáveis): inglês.
- **Contrato público da API** (rotas `/saude`, `/filmes/{filme_id}`, `/pesquisa`; parâmetros `q`, `pagina`, `ano`, `modo`; campos `modo`, `resultados`, `interpretacao`): português, sem mudança para os clientes existentes. A tradução fica em `app.api.schemas`.
- **Mensagens ao usuário, docstrings, relatórios e documentação**: português.
- **Dados do corpus** (nomes de arquivo e campos JSON): mantidos como entregues.
- **Frontend**: identificadores em português, pois é código de interface curto e voltado à disciplina.

## Alternativas consideradas

- Tudo em português: exigiria renomear `corpus` e `vectors` e mudar nomes já registrados nos manifestos entregues.
- Contrato da API em inglês: quebraria a interface e os registros em `docs/api_smoke.json`.

## Consequências

- O vocabulário de domínio aparece em dois idiomas nas fronteiras (por exemplo, `SearchMode.DISCOVERY = "descoberta"`).
