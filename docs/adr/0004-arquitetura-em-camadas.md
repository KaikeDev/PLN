# 0004 — Arquitetura em camadas com portas e adaptadores

- Estado: Aceita
- Data: 2026-09-14

## Contexto

O pacote `app` misturava dois subsistemas sem fronteira clara: pipelines offline (`corpus`, `vectors`) e a API online (`api`, `services/pln`, `services/tmdb`, `core`, `exceptions`). A pesquisa importava o módulo concreto do TMDB, usava sessão HTTP e cache globais e expunha ganchos de teste no código de produção. `vectors` importava funções internas de `corpus.process`, e manifesto e verificação estavam duplicados e já divergiam.

## Decisão

```
app/
├── api/            HTTP: rotas, esquemas de resposta, dependências, limite de taxa
├── domain/search/  regras da pesquisa; depende só das portas em ports.py
├── infra/tmdb/     cliente HTTP, catálogo (Adapter) e cache (Decorator)
├── shared/         artefatos, manifesto, validação de configuração, regras de língua
├── corpus/         Etapa 1 (CLI python -m app.corpus)
├── vectors/        Etapa 2 (CLI python -m app.vectors)
├── settings.py     configuração
└── main.py         composição da aplicação (create_app)
```

- **Portas e adaptadores**: `MovieCatalog` e `MovieDetailsProvider` são `Protocol`s do domínio. `TMDBMovieCatalog` os implementa, e `CachedMovieCatalog` os decora. `create_app` monta a composição e aceita um catálogo falso nos testes.
- **Strategy**: cada modo de pesquisa é uma estratégia (`TitleSearch`, `DiscoverySearch`, `AutomaticSearch`). Em `vectors`, métodos de representação e análises são estratégias registradas.
- **Contrato entre etapas**: `app.corpus.contracts` define etapas e campos; `app.corpus.verification` verifica pastas. `vectors` depende só desses dois módulos.
- **Open/Closed no relatório vetorial**: cada `Analysis` implementa `report_section`; `make_report` só percorre as análises.
- `corpus` e `vectors` continuam no primeiro nível para preservar os comandos citados na entrega da Etapa 1.

## Alternativas consideradas

- Mover `corpus` e `vectors` para `pipelines/`: mais simétrico, mas quebraria os comandos documentados no relatório entregue.
- Manter módulos com funções e estado global: menos arquivos, mas testes dependentes de `patch` em caminhos de módulo.

## Consequências

- Trocar o TMDB por outra fonte exige só um novo adaptador.
- Os imports antigos (`app.services.*`, `app.core.config`, `app.exceptions.tmdb`, `app.corpus.io`) deixaram de existir.
