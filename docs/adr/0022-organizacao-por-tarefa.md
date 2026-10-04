# 0022 — Repositório organizado por tarefa da disciplina

- Estado: Aceita
- Data: 2026-10-03

## Contexto

O repositório cresceu em etapas (Etapa 1, Etapa 2, Aulas 7 e 8), e a organização acompanhou essa ordem, não as tarefas que o professor avalia:

- **Busca espalhada em cinco lugares:** `vectors/retrieval.py`, `vectors/hybrid.py`, uma classe em `vectors/analyses.py`, `domain/search/` e `infra/synopsis/`.
- **Tarefas misturadas:** busca, recomendação e agrupamento estavam no mesmo arquivo `vectors/analyses.py`, de 438 linhas, e as seções de relatório delas, em `vectors/report.py`.
- **Camadas genéricas:** `domain/` e `infra/` (ADR 0004) separavam o código por camada técnica, e não por assunto.
- **Pastas com nomes de etapa:** documentação, configurações e dados (`docs/relatorio.md`, `data/vectors`, `config/*.json`) tinham nomes que só faziam sentido para quem acompanhou o desenvolvimento.
- **Restos sem uso:** uma pasta `app/` vazia na raiz e pastas `core/`, `exceptions/` e `services/` só com cache de bytecode.

## Decisão

- **Código por tarefa** em `backend/src/app`, com a mesma ordem da apresentação:
  - `corpus` (coleta e preparação);
  - `representations` (as oito representações e o pipeline);
  - `search`, `recommendation`, `clustering`;
  - `classification` (com o Jev em `classification/jev`).

  A API fica em `api/`, `main.py` e `settings.py`; o cliente do TMDB, em `tmdb/`.
- **Análises separadas por tarefa:**
  - `Retrieval` vai para `search/evaluation.py`;
  - `Recommendation`, para `recommendation/analysis.py`;
  - `Clustering` e `Projection`, para `clustering/analysis.py`;
  - cada uma leva junto a sua seção do relatório.

  `representations/analyses.py` guarda a classe base e as análises próprias das representações (dimensões, sondas da Aula 7, síntese). `DEFAULT_ANALYSES` passa a ser montado em `representations/pipeline.py`.
- **Portas e adaptadores mantidos dentro de cada tarefa:**
  - `search/ports.py` e `search/synopsis_index.py`;
  - `classification/ports.py` e `classification/live.py`;
  - `classification/jev/ports.py` e `classification/jev/typesafe_client.py`.

  A regra da ADR 0004 continua: regras e serviços não importam a API, e as dependências externas ficam atrás de interfaces. O que muda é o critério de agrupamento.
- **Comandos:**
  - `python -m app.vectors` vira `python -m app.representations` (`build`, `verify`);
  - os comandos de busca vão para `python -m app.search` (`query`, `hybrid`);
  - `python -m app.jev` vira `python -m app.classification.jev`.
- **Configurações e dados por etapa:**
  - `config/coleta/`, `config/representacoes/`, `config/busca/`, `config/classificacao/`;
  - `data/coleta/`, `data/preparacao/`, `data/representacoes/`, `data/classificacao/`, `data/jev/`.
- **Documentação na ordem da apresentação:**
  - `docs/1-coleta-e-preparacao.md` a `docs/6-classificacao.md`;
  - documentos técnicos em `docs/tecnico/`;
  - entrega da Etapa 1 em `docs/entregas/`;
  - resumo das ADRs em `docs/adr/resumo.md`.

  Na raiz ficam só `README.md` e `APRESENTACAO.md`.

## Alternativas consideradas

- **Manter o código e só reorganizar documentação e dados:** menos risco e sem mudar comandos, mas o código continuaria espalhado, e o professor teria de usar um mapa para achar cada tarefa.
- **Um pipeline por tarefa:** espelharia ainda mais o quadro da disciplina, mas recalcularia as oito representações quatro vezes. Busca, recomendação e agrupamento continuam rodando sobre as mesmas representações num único pipeline, cada um no seu pacote.
- **Nomes de pasta de código em português:** combinaria com a documentação, mas contraria a ADR 0008 (identificadores em inglês). Configurações e dados, que são lidos pelo professor, ficaram em português.

## Consequências

- **Os arquivos de dados não mudaram:** os hashes conferem, e os quatro `verify` passam nas pastas novas. Os manifestos guardam a identidade do código da época em que foram gerados (`source_identity`), com os caminhos antigos dos módulos, como registro histórico.
- **A branch antiga `luana-classificacao` fica incompatível** com a estrutura nova; trabalhos futuros devem partir do `trabalho-3`.
- **As ADRs anteriores** citam os caminhos da época; links para arquivos movidos foram corrigidos.
