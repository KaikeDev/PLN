# Decisões de arquitetura e desenvolvimento

Este arquivo reúne as decisões de arquitetura e de desenvolvimento do projeto, cada uma com a justificativa. O registro completo de cada decisão, com contexto, alternativas descartadas e consequências, está em [`docs/adr/`](docs/adr/README.md) no formato MADR; o número de cada seção corresponde ao arquivo detalhado.

O código não tem comentários fora de docstrings. Quando uma docstring cita “ADR NNNN”, a justificativa está na seção de mesmo número abaixo.

| ADR | Decisão | Tema |
|---|---|---|
| [0001](#0001--registrar-decisões-em-adrs-e-não-em-comentários) | Registrar decisões em ADRs, não em comentários | Processo |
| [0002](#0002--credencial-do-tmdb-e-exposição-da-api-local) | Credencial do TMDB e exposição da API local | Segurança |
| [0003](#0003--normalizações-distintas-para-corpus-e-pesquisa) | Normalizações distintas para corpus e pesquisa | PLN |
| [0004](#0004--arquitetura-em-camadas-com-portas-e-adaptadores) | Arquitetura em camadas com portas e adaptadores | Arquitetura |
| [0005](#0005--pesquisa-auxiliar-por-regras-léxicas) | Pesquisa auxiliar por regras léxicas | PLN |
| [0006](#0006--título-exato-tem-prioridade-no-modo-automático) | Título exato tem prioridade no modo automático | API |
| [0007](#0007--cliente-http-síncrono-retry-e-cache-em-memória) | Cliente HTTP síncrono, retry e cache em memória | Arquitetura |
| [0008](#0008--código-em-inglês-contrato-e-documentação-em-português) | Código em inglês; contrato e documentação em português | Padrões |
| [0009](#0009--saídas-imutáveis-determinísticas-e-verificáveis) | Saídas imutáveis, determinísticas e verificáveis | Reprodutibilidade |
| [0010](#0010--amostra-entregue-versionada-no-git) | Amostra entregue versionada no Git | Dados |
| [0011](#0011--formatos-legíveis-e-modelos-com-revisão-fixada) | Formatos legíveis e modelos com revisão fixada | Segurança |
| [0012](#0012--parâmetros-do-experimento-vetorial) | Parâmetros do experimento vetorial | PLN |
| [0013](#0013--ambiente-testes-lint-tipos-e-ci) | Ambiente, testes, lint, tipos e CI | Qualidade |
| [0014](#0014--amostragem-intencional-da-coleta) | Amostragem intencional da coleta | Dados |
| [0015](#0015--bert-cbow--skip-gram-e-polissemia-aula-7) | BERT, CBOW × skip-gram e polissemia (Aula 7) | PLN |
| [0016](#0016--política-do-gitignore) | Política do `.gitignore` | Repositório |

---

## 0001 — Registrar decisões em ADRs e não em comentários

**Decisão.** Cada decisão arquitetural ou de método vira uma ADR em `docs/adr/` e ganha um resumo neste arquivo. No código, as explicações ficam em docstrings; comentários de linha não são usados, e a regra vale também para arquivos de configuração como o `.gitignore`.

**Por quê.** Comentários se desatualizam sem revisão e não mostram as alternativas descartadas. Um texto corrido único (`docs/decisoes.md`) não registrava alternativas nem substituições. Com ADRs, mudar uma heurística exige atualizar a decisão correspondente, e o histórico fica visível.

**Consequência.** Uma decisão nova exige a ADR, a linha no índice `docs/adr/README.md` e a entrada neste arquivo. [Detalhes](docs/adr/0001-registrar-decisoes-em-adrs.md)

## 0002 — Credencial do TMDB e exposição da API local

**Decisão.**

- Só o `TMDB_BEARER_TOKEN` é aceito, enviado no cabeçalho `Authorization`, lido por `pydantic-settings` e guardado como `SecretStr`.
- A API não inicia sem token e roda em `127.0.0.1`.
- O CORS aceita só as origens da interface e só `GET`.
- Há limite de requisições por IP (HTTP 429) e de 200 caracteres na consulta.
- Mensagens de erro nunca incluem URL nem cabeçalhos.

**Por quê.** Uma credencial real foi versionada no commit `a09a21c`. A `api_key` na URL pode aparecer em logs. O CORS não protege o token: ele só restringe navegadores, não `curl` nem scripts. Sem limite de requisições, qualquer cliente da rede poderia esgotar a cota do TMDB.

**Consequência.** A credencial exposta precisa ser revogada no painel do TMDB. Reescrever o histórico do Git fica a critério da equipe, e não substitui a revogação. [Detalhes](docs/adr/0002-credencial-e-exposicao-da-api.md)

## 0003 — Normalizações distintas para corpus e pesquisa

**Decisão.** O corpus usa NFC e `casefold`, preservando acentos. A pesquisa remove acentos. Os marcadores de negação (“não”, “nem”, “nunca”, “sem”) ficam num único módulo, `app.shared.language`.

**Por quê.** Acentos distinguem palavras no português (“é”/“e”, “pôde”/“pode”) e precisam ser preservados para comparar técnicas de PLN. Na pesquisa, quem digita “acao” sem acento precisa ser entendido. Os marcadores de negação estavam duplicados em três lugares, com conteúdos diferentes.

**Consequência.** “nem” passou a negar gêneros na pesquisa. Um marcador novo vale para os dois fluxos. [Detalhes](docs/adr/0003-normalizacao-do-corpus-e-da-pesquisa.md)

## 0004 — Arquitetura em camadas com portas e adaptadores

**Decisão.** O pacote é dividido em `api` (HTTP), `domain/search` (regras), `infra/tmdb` (cliente, catálogo e cache), `shared`, `corpus` (Etapa 1) e `vectors` (Etapa 2). O domínio depende de `Protocol`s (portas). O TMDB é um Adapter e o cache, um Decorator. Os modos de pesquisa e as análises vetoriais são estratégias (Strategy).

**Por quê.** Antes, a pesquisa importava o módulo concreto do TMDB, usava estado global e expunha ganchos de teste no código de produção. `vectors` importava funções internas de `corpus`, e o código de manifesto estava duplicado e já divergia. Com portas, os testes injetam dublês sem `patch` e trocar a fonte de dados exige só um novo adaptador. `corpus` e `vectors` continuam no primeiro nível para não quebrar os comandos da entrega.

**Consequência.** Os imports antigos (`app.services.*`, `app.core.config`, `app.corpus.io`) deixaram de existir. [Detalhes](docs/adr/0004-arquitetura-em-camadas.md)

## 0005 — Pesquisa auxiliar por regras léxicas

**Decisão.** Preferências como “comédia recente bem avaliada, sem terror” são reconhecidas por regras explícitas, com limiares nomeados no código:

- “bem avaliado”: nota ≥ 7 e ≥ 100 votos;
- “recente”: lançado nos últimos 10 anos; “antigo”: há mais de 25 anos;
- negação de gênero: marcador até 3 tokens antes; negação de qualidade: até 5 tokens antes.

**Por quê.** A pesquisa é uma demonstração auxiliar; o que é avaliado é o corpus e as representações. Regras são previsíveis, testáveis e explicáveis para a disciplina. Um classificador ou LLM exigiria dados anotados que não existem.

**Consequência.** Não cobre paráfrases, títulos alternativos nem toda a semântica da negação. A acurácia de 12/12 vale só para as cinco frases de teste. [Detalhes](docs/adr/0005-pesquisa-por-regras-lexicas.md)

## 0006 — Título exato tem prioridade no modo automático

**Decisão.** No modo `auto`, se um filme da primeira página tiver título igual ao texto digitado, a resposta é por título. Senão, a pesquisa usa as preferências extraídas.

**Por quê.** Títulos contêm gatilhos de preferência: “Guerra nas Estrelas” contém “guerra”. Verificar sempre a primeira página impede que o modo mude ao paginar.

**Consequência.** “quero ver Matrix” não é reconhecido como título exato; os modos explícitos resolvem a ambiguidade. [Detalhes](docs/adr/0006-prioridade-de-titulo-exato.md)

## 0007 — Cliente HTTP síncrono, retry e cache em memória

**Decisão.**

- `requests` com uma sessão por thread e timeout de 10 s.
- Até 3 tentativas com backoff para 429 e 5xx.
- Cache de gêneros por 24 h e de buscas por título por 5 min (LRU com 256 entradas).

**Por quê.** As rotas síncronas do FastAPI rodam num pool de threads, e uma sessão global compartilhada não é garantidamente segura. O modo automático repetia a consulta da primeira página a cada página pedida. O `httpx` assíncrono exigiria reescrever as rotas e a lógica de retry.

**Consequência.** O cache é por processo e pode servir resultados de até 5 minutos atrás. A coleta usa a mesma política de retry. [Detalhes](docs/adr/0007-cliente-http-e-cache.md)

## 0008 — Código em inglês; contrato e documentação em português

**Decisão.** Identificadores no código ficam em inglês. O contrato da API (`/pesquisa`, `modo`, `resultados`), as mensagens, as docstrings e a documentação ficam em português. O frontend usa identificadores em português.

**Por quê.** Os módulos misturavam os dois idiomas. Mudar o contrato quebraria a interface e os registros já entregues; renomear `corpus` e `vectors` mudaria nomes gravados nos manifestos.

**Consequência.** O vocabulário aparece em dois idiomas nas fronteiras (`SearchMode.DISCOVERY = "descoberta"`). [Detalhes](docs/adr/0008-idioma-do-codigo-e-do-contrato.md)

## 0009 — Saídas imutáveis, determinísticas e verificáveis

**Decisão.**

- Toda execução grava numa pasta nova; uma pasta existente causa erro.
- O manifesto guarda o SHA-256 de cada arquivo, a identidade do código e as versões das bibliotecas, e `verify` detecta alterações.
- JSON/JSONL são gravados sempre com LF, e o `.gitattributes` marca `data/**` como `-text`.
- A Etapa 2 calcula tudo em memória antes de criar a pasta.

**Por quê.** A disciplina exige localizar e repetir cada transformação, e a coleta online muda com o tempo. Arquivos gerados no Windows saíam em CRLF, então “idêntico byte a byte” só valia no mesmo sistema operacional.

**Consequência.** Reprocessar a amostra reproduz os arquivos byte a byte, exceto o manifesto, em qualquer sistema operacional. O hash detecta alterações acidentais, mas não impede a alteração conjunta de um arquivo e do manifesto. [Detalhes](docs/adr/0009-saidas-imutaveis-e-verificaveis.md)

## 0010 — Amostra entregue versionada no Git

**Decisão.** Só a amostra oficial `tmdb_2026-09-12` é versionada, em `data/raw`, `data/processed` e `data/vectors`. Reproduções locais e modelos pré-treinados ficam fora do repositório.

**Por quê.** A avaliação pede um repositório navegável pelo README, e os dados somam poucos megabytes. Git LFS ou DVC exigiriam instalação extra de quem avalia e quebrariam a navegação no GitHub.

**Consequência.** Uma nova amostra oficial exige uma exceção no `.gitignore` (ADR 0016). Os termos de atribuição do TMDB se aplicam. [Detalhes](docs/adr/0010-dados-versionados-no-git.md)

## 0011 — Formatos legíveis e modelos com revisão fixada

**Decisão.**

- Configurações e saídas somente em JSON/JSONL, com limite de 1 MB e validação estrita (sem campos desconhecidos, sem booleano no lugar de inteiro).
- Nada de pickle nem joblib.
- A etapa de entrada vem de uma lista fixa, nunca de um caminho livre.
- Modelos do Hugging Face com `revision` fixada por hash de commit e `trust_remote_code=False`; pesos `.bin` lidos com `weights_only=True`.
- Textos escapados no SVG.

**Por quê.** Pickle executa código ao carregar. A revisão `main` de um modelo pode mudar sem aviso, alterando os resultados. Caminhos livres na configuração permitiriam *path traversal*. Títulos vindos do TMDB poderiam injetar script num SVG aberto no navegador.

**Consequência.** As saídas são maiores. BoW e TF-IDF funcionam sem o extra `semantico`, e o CI não baixa modelos. [Detalhes](docs/adr/0011-formatos-e-modelos-seguros.md)

## 0012 — Parâmetros do experimento vetorial

**Decisão.**

- Reaproveitar os tokens da Etapa 1.
- TF-IDF do scikit-learn e cosseno sobre linhas com norma L2.
- *k* = 5 vizinhos.
- K-Means com *k* = 4; ARI, NMI e pureza só com filmes de um gênero.
- TruncatedSVD 2D e semente 42.

**Por quê.** Uma segunda tokenização divergiria da Etapa 1. O cosseno não depende do tamanho da sinopse. *k* = 4 é o número de gêneros coletados, o que permite comparar os clusters com eles; filmes com vários gêneros não têm rótulo inequívoco. A SVD funciona com matrizes esparsas e é determinística, ao contrário de t-SNE e UMAP.

**Consequência.** Nenhuma representação é declarada superior só por reduzir dimensões; a escolha depende de consultas anotadas. [Detalhes](docs/adr/0012-parametros-do-experimento-vetorial.md)

## 0013 — Ambiente, testes, lint, tipos e CI

**Decisão.**

- Python ≥ 3.14 com `uv` e `uv.lock`.
- `unittest` com dublês injetados.
- `ruff` para lint e formatação e `mypy` para tipos.
- CI no GitHub Actions sem segredos e sem o extra `semantico`.

**Por quê.** Não havia lint, tipos nem CI, e as rotas e o cliente do TMDB não tinham testes. `ruff` substitui três ferramentas. `unittest` mantém os comandos já entregues. Testes sem rede nem download são rápidos e reprodutíveis.

**Consequência.** A qualidade dos modelos reais é validada só pelas execuções registradas em `docs/validacao.md`. [Detalhes](docs/adr/0013-ferramentas-de-qualidade.md)

## 0014 — Amostragem intencional da coleta

**Decisão.** Quatro gêneros (Drama, Comédia, Terror, Ficção científica) × três períodos (1980–1999, 2000–2014, 2015–2025), com 2 páginas por popularidade, ≥ 50 votos e sem conteúdo adulto. Matrix (603) entra como semente, e a deduplicação é por ID.

**Por quê.** O catálogo inteiro é inviável para a atividade, e comparar recortes exige grupos equilibrados. Matrix é o caso didático pedido pelo professor. Uma amostra aleatória teria muitos filmes sem sinopse em português.

**Consequência.** A amostra tem viés de popularidade e não representa o catálogo. [Detalhes](docs/adr/0014-amostragem-intencional.md)

## 0015 — BERT, CBOW × skip-gram e polissemia (Aula 7)

**Decisão.**

- Acrescentar o BERTimbau (BERT contextual) e o word2vec CBOW do NILC ao lado do skip-gram.
- Renomear o modelo de sentença para `sentenca_minilm`.
- Medir a polissemia com o vetor da palavra dentro da frase.
- Guardar os exemplos da aula em `config/sondas_semanticas.json`, fora do corpus.
- Incluir uma síntese com família, dimensões, interpretabilidade e parâmetros.

**Por quê.** A Aula 7 pede a hipótese distribucional, CBOW × skip-gram, estático × contextual (polissemia) e uma comparação de informação, custo e interpretabilidade. CBOW e skip-gram do NILC têm o mesmo corpus de treino e a mesma dimensão, então a comparação isola a arquitetura. Treinar word2vec em 25 mil tokens não daria vetores úteis. O BERT usa o mesmo código do modelo de sentença, porque só muda o modelo. Os tempos de construção ficam no manifesto para preservar o determinismo.

**Consequência.** A primeira execução completa baixa cerca de 3,1 GB. O BERT sem ajuste para sentenças dá cossenos altos a quase qualquer par (anisotropia), então o relatório orienta a comparar diferenças entre pares. [Detalhes](docs/adr/0015-aula7-bert-cbow-e-polissemia.md)

## 0016 — Política do `.gitignore`

**Decisão.** O `.gitignore` não tem comentários e agrupa as regras em sete blocos:

- segredos (só os `.env.example` passam);
- ambientes e bytecode do Python;
- caches de ferramentas;
- modelos e caches do Hugging Face, com `/models/` e `/huggingface/` ancorados na raiz;
- dados fora da amostra entregue;
- front-end;
- sistema, OneDrive/Office e editores.

**Por quê.** Credenciais já foram versionadas uma vez. Os modelos chegam a GBs. A ancoragem na raiz evita esconder um pacote de código como `app/models/`. O repositório fica no OneDrive e contém um `.docx`, que gera arquivos de trava `~$*`. As pastas de reprodução sugeridas no README não devem entrar no Git.

**Consequência.** Uma nova amostra oficial exige uma exceção em `data/*`. `git ls-files -ci --exclude-standard` deve continuar vazio. [Detalhes](docs/adr/0016-politica-do-gitignore.md)
