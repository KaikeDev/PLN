# Decisões de arquitetura e desenvolvimento

Este arquivo reúne as decisões de arquitetura e de desenvolvimento do projeto, cada uma com a justificativa. O registro completo de cada decisão, com contexto, alternativas descartadas e consequências, está nos arquivos desta pasta, no formato MADR ([índice](README.md)); o número de cada seção corresponde ao arquivo detalhado.

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
| [0017](#0017--classificação-de-gêneros-aula-8) | Classificação de gêneros (Aula 8) | PLN |
| [0018](#0018--tarefas-do-ciclo-de-pln-para-cada-representação) | Tarefas do ciclo de PLN para cada representação | PLN |
| [0019](#0019--jev-e-tf-idf--regressão-logística-aula-8) | Jev e TF-IDF + regressão logística (Aula 8) | PLN |
| [0020](#0020--busca-por-tema-tf-idf--embedding-de-sentença) | Busca por tema: TF-IDF + embedding de sentença | PLN |
| [0021](#0021--classificação-de-gênero-na-tela) | Classificação de gênero na tela | API |
| [0022](#0022--repositório-organizado-por-tarefa) | Repositório organizado por tarefa | Repositório |
| [0023](#0023--filmes-parecidos-na-ficha-do-filme) | Filmes parecidos na ficha do filme | API |

---

## 0001 — Registrar decisões em ADRs e não em comentários

**Decisão.** Cada decisão arquitetural ou de método vira uma ADR em `docs/adr/` e ganha um resumo neste arquivo. No código, as explicações ficam em docstrings; comentários de linha não são usados, e a regra vale também para arquivos de configuração como o `.gitignore`.

**Por quê.** Comentários se desatualizam sem revisão e não mostram as alternativas descartadas. Um texto corrido único (`docs/decisoes.md`) não registrava alternativas nem substituições. Com ADRs, mudar uma heurística exige atualizar a decisão correspondente, e o histórico fica visível.

**Consequência.** Uma decisão nova exige a ADR, a linha no índice `docs/adr/README.md` e a entrada neste arquivo. [Detalhes](0001-registrar-decisoes-em-adrs.md)

## 0002 — Credencial do TMDB e exposição da API local

**Decisão.**

- Só o `TMDB_BEARER_TOKEN` é aceito, enviado no cabeçalho `Authorization`, lido por `pydantic-settings` e guardado como `SecretStr`.
- A API não inicia sem token e roda em `127.0.0.1`.
- O CORS aceita só as origens da interface e só `GET`.
- Há limite de requisições por IP (HTTP 429) e de 200 caracteres na consulta.
- Mensagens de erro nunca incluem URL nem cabeçalhos.

**Por quê.** Uma credencial real foi versionada no commit `a09a21c`. A `api_key` na URL pode aparecer em logs. O CORS não protege o token: ele só restringe navegadores, não `curl` nem scripts. Sem limite de requisições, qualquer cliente da rede poderia esgotar a cota do TMDB.

**Consequência.** A credencial exposta precisa ser revogada no painel do TMDB. Reescrever o histórico do Git fica a critério da equipe, e não substitui a revogação. [Detalhes](0002-credencial-e-exposicao-da-api.md)

## 0003 — Normalizações distintas para corpus e pesquisa

**Decisão.** O corpus usa NFC e `casefold`, preservando acentos. A pesquisa remove acentos. Os marcadores de negação (“não”, “nem”, “nunca”, “sem”) ficam num único módulo, `app.shared.language`.

**Por quê.** Acentos distinguem palavras no português (“é”/“e”, “pôde”/“pode”) e precisam ser preservados para comparar técnicas de PLN. Na pesquisa, quem digita “acao” sem acento precisa ser entendido. Os marcadores de negação estavam duplicados em três lugares, com conteúdos diferentes.

**Consequência.** “nem” passou a negar gêneros na pesquisa. Um marcador novo vale para os dois fluxos. [Detalhes](0003-normalizacao-do-corpus-e-da-pesquisa.md)

## 0004 — Arquitetura em camadas com portas e adaptadores

**Decisão.** O pacote é dividido em `api` (HTTP), `domain/search` (regras), `infra/tmdb` (cliente, catálogo e cache), `shared`, `corpus` (Etapa 1) e `vectors` (Etapa 2). O domínio depende de `Protocol`s (portas). O TMDB é um Adapter e o cache, um Decorator. Os modos de pesquisa e as análises vetoriais são estratégias (Strategy).

**Por quê.** Antes, a pesquisa importava o módulo concreto do TMDB, usava estado global e expunha ganchos de teste no código de produção. `vectors` importava funções internas de `corpus`, e o código de manifesto estava duplicado e já divergia. Com portas, os testes injetam dublês sem `patch` e trocar a fonte de dados exige só um novo adaptador. `corpus` e `vectors` continuam no primeiro nível para não quebrar os comandos da entrega.

**Consequência.** Os imports antigos (`app.services.*`, `app.core.config`, `app.corpus.io`) deixaram de existir. [Detalhes](0004-arquitetura-em-camadas.md)

## 0005 — Pesquisa auxiliar por regras léxicas

**Decisão.** Preferências como “comédia recente bem avaliada, sem terror” são reconhecidas por regras explícitas, com limiares nomeados no código:

- “bem avaliado”: nota ≥ 7 e ≥ 100 votos;
- “recente”: lançado nos últimos 10 anos; “antigo”: há mais de 25 anos;
- negação de gênero: marcador até 3 tokens antes; negação de qualidade: até 5 tokens antes.

**Por quê.** A pesquisa é uma demonstração auxiliar; o que é avaliado é o corpus e as representações. Regras são previsíveis, testáveis e explicáveis para a disciplina. Um classificador ou LLM exigiria dados anotados que não existem.

**Consequência.** Não cobre paráfrases, títulos alternativos nem toda a semântica da negação. A acurácia de 12/12 vale só para as cinco frases de teste. [Detalhes](0005-pesquisa-por-regras-lexicas.md)

## 0006 — Título exato tem prioridade no modo automático

**Decisão.** No modo `auto`, se um filme da primeira página tiver título igual ao texto digitado, a resposta é por título. Senão, a pesquisa usa as preferências extraídas.

**Por quê.** Títulos contêm gatilhos de preferência: “Guerra nas Estrelas” contém “guerra”. Verificar sempre a primeira página impede que o modo mude ao paginar.

**Consequência.** “quero ver Matrix” não é reconhecido como título exato; os modos explícitos resolvem a ambiguidade. [Detalhes](0006-prioridade-de-titulo-exato.md)

## 0007 — Cliente HTTP síncrono, retry e cache em memória

**Decisão.**

- `requests` com uma sessão por thread e timeout de 10 s.
- Até 3 tentativas com backoff para 429 e 5xx.
- Cache de gêneros por 24 h e de buscas por título por 5 min (LRU com 256 entradas).

**Por quê.** As rotas síncronas do FastAPI rodam num pool de threads, e uma sessão global compartilhada não é garantidamente segura. O modo automático repetia a consulta da primeira página a cada página pedida. O `httpx` assíncrono exigiria reescrever as rotas e a lógica de retry.

**Consequência.** O cache é por processo e pode servir resultados de até 5 minutos atrás. A coleta usa a mesma política de retry. [Detalhes](0007-cliente-http-e-cache.md)

## 0008 — Código em inglês; contrato e documentação em português

**Decisão.** Identificadores no código ficam em inglês. O contrato da API (`/pesquisa`, `modo`, `resultados`), as mensagens, as docstrings e a documentação ficam em português. O frontend usa identificadores em português.

**Por quê.** Os módulos misturavam os dois idiomas. Mudar o contrato quebraria a interface e os registros já entregues; renomear `corpus` e `vectors` mudaria nomes gravados nos manifestos.

**Consequência.** O vocabulário aparece em dois idiomas nas fronteiras (`SearchMode.DISCOVERY = "descoberta"`). [Detalhes](0008-idioma-do-codigo-e-do-contrato.md)

## 0009 — Saídas imutáveis, determinísticas e verificáveis

**Decisão.**

- Toda execução grava numa pasta nova; uma pasta existente causa erro.
- O manifesto guarda o SHA-256 de cada arquivo, a identidade do código e as versões das bibliotecas, e `verify` detecta alterações.
- JSON/JSONL são gravados sempre com LF, e o `.gitattributes` marca `data/**` como `-text`.
- A Etapa 2 calcula tudo em memória antes de criar a pasta.

**Por quê.** A disciplina exige localizar e repetir cada transformação, e a coleta online muda com o tempo. Arquivos gerados no Windows saíam em CRLF, então “idêntico byte a byte” só valia no mesmo sistema operacional.

**Consequência.** Reprocessar a amostra reproduz os arquivos byte a byte, exceto o manifesto, em qualquer sistema operacional. O hash detecta alterações acidentais, mas não impede a alteração conjunta de um arquivo e do manifesto. [Detalhes](0009-saidas-imutaveis-e-verificaveis.md)

## 0010 — Amostra entregue versionada no Git

**Decisão.** Só a amostra oficial `tmdb_2026-09-12` é versionada, em `data/coleta`, `data/preparacao` e `data/representacoes`. Reproduções locais e modelos pré-treinados ficam fora do repositório.

**Por quê.** A avaliação pede um repositório navegável pelo README, e os dados somam poucos megabytes. Git LFS ou DVC exigiriam instalação extra de quem avalia e quebrariam a navegação no GitHub.

**Consequência.** Uma nova amostra oficial exige uma exceção no `.gitignore` (ADR 0016). Os termos de atribuição do TMDB se aplicam. [Detalhes](0010-dados-versionados-no-git.md)

## 0011 — Formatos legíveis e modelos com revisão fixada

**Decisão.**

- Configurações e saídas somente em JSON/JSONL, com limite de 1 MB e validação estrita (sem campos desconhecidos, sem booleano no lugar de inteiro).
- Nada de pickle nem joblib.
- A etapa de entrada vem de uma lista fixa, nunca de um caminho livre.
- Modelos do Hugging Face com `revision` fixada por hash de commit e `trust_remote_code=False`; pesos `.bin` lidos com `weights_only=True`.
- Textos escapados no SVG.

**Por quê.** Pickle executa código ao carregar. A revisão `main` de um modelo pode mudar sem aviso, alterando os resultados. Caminhos livres na configuração permitiriam *path traversal*. Títulos vindos do TMDB poderiam injetar script num SVG aberto no navegador.

**Consequência.** As saídas são maiores. BoW e TF-IDF funcionam sem o extra `semantico`, e o CI não baixa modelos. [Detalhes](0011-formatos-e-modelos-seguros.md)

## 0012 — Parâmetros do experimento vetorial

**Decisão.**

- Reaproveitar os tokens da Etapa 1.
- TF-IDF do scikit-learn e cosseno sobre linhas com norma L2.
- *k* = 5 vizinhos.
- K-Means com *k* = 4; ARI, NMI e pureza só com filmes de um gênero.
- TruncatedSVD 2D e semente 42.

**Por quê.** Uma segunda tokenização divergiria da Etapa 1. O cosseno não depende do tamanho da sinopse. *k* = 4 é o número de gêneros coletados, o que permite comparar os clusters com eles; filmes com vários gêneros não têm rótulo inequívoco. A SVD funciona com matrizes esparsas e é determinística, ao contrário de t-SNE e UMAP.

**Consequência.** Nenhuma representação é declarada superior só por reduzir dimensões; a escolha depende de consultas anotadas. [Detalhes](0012-parametros-do-experimento-vetorial.md)

## 0013 — Ambiente, testes, lint, tipos e CI

**Decisão.**

- Python ≥ 3.14 com `uv` e `uv.lock`.
- `unittest` com dublês injetados.
- `ruff` para lint e formatação e `mypy` para tipos.
- CI no GitHub Actions sem segredos e sem o extra `semantico`.

**Por quê.** Não havia lint, tipos nem CI, e as rotas e o cliente do TMDB não tinham testes. `ruff` substitui três ferramentas. `unittest` mantém os comandos já entregues. Testes sem rede nem download são rápidos e reprodutíveis.

**Consequência.** A qualidade dos modelos reais é validada só pelas execuções registradas em `docs/validacao.md`. [Detalhes](0013-ferramentas-de-qualidade.md)

## 0014 — Amostragem intencional da coleta

**Decisão.** Quatro gêneros (Drama, Comédia, Terror, Ficção científica) × três períodos (1980–1999, 2000–2014, 2015–2025), com 2 páginas por popularidade, ≥ 50 votos e sem conteúdo adulto. Matrix (603) entra como semente, e a deduplicação é por ID.

**Por quê.** O catálogo inteiro é inviável para a atividade, e comparar recortes exige grupos equilibrados. Matrix é o caso didático pedido pelo professor. Uma amostra aleatória teria muitos filmes sem sinopse em português.

**Consequência.** A amostra tem viés de popularidade e não representa o catálogo. [Detalhes](0014-amostragem-intencional.md)

## 0015 — BERT, CBOW × skip-gram e polissemia (Aula 7)

**Decisão.**

- Acrescentar o BERTimbau (BERT contextual) e o word2vec CBOW do NILC ao lado do skip-gram.
- Renomear o modelo de sentença para `sentenca_minilm`.
- Medir a polissemia com o vetor da palavra dentro da frase.
- Guardar os exemplos da aula em `config/representacoes/sondas_semanticas.json`, fora do corpus.
- Incluir uma síntese com família, dimensões, interpretabilidade e parâmetros.

**Por quê.** A Aula 7 pede a hipótese distribucional, CBOW × skip-gram, estático × contextual (polissemia) e uma comparação de informação, custo e interpretabilidade. CBOW e skip-gram do NILC têm o mesmo corpus de treino e a mesma dimensão, então a comparação isola a arquitetura. Treinar word2vec em 25 mil tokens não daria vetores úteis. O BERT usa o mesmo código do modelo de sentença, porque só muda o modelo. Os tempos de construção ficam no manifesto para preservar o determinismo.

**Consequência.** A primeira execução completa baixa cerca de 3,1 GB. O BERT sem ajuste para sentenças dá cossenos altos a quase qualquer par (anisotropia), então o relatório orienta a comparar diferenças entre pares. [Detalhes](0015-aula7-bert-cbow-e-polissemia.md)

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

**Consequência.** Uma nova amostra oficial exige uma exceção em `data/*`. `git ls-files -ci --exclude-standard` deve continuar vazio. [Detalhes](0016-politica-do-gitignore.md)

## 0017 — Classificação de gêneros (Aula 8)

**Decisão.**

- Prever o gênero do filme a partir da sinopse em duas formulações: multiclasse (325 filmes com exatamente um dos quatro gêneros) e multirrótulo (428 filmes, um classificador binário por gênero).
- Usar como rótulos os `genre_ids` do TMDB, não o recorte de coleta.
- Aplicar a mesma regressão logística, com pesos balanceados, às oito representações da Etapa 2.
- Escolher `C` pela log loss em dobras internas e avaliar em 5 dobras externas iguais para todas as representações, sem vazamento: vocabulário, idf, padronização e `C` vêm só do treino.
- Reportar uma referência que ignora o texto, F1 macro/micro, métricas por gênero, desvio entre dobras, matriz de confusão, Hamming, acerto exato, log loss e confiança em acertos × erros.

**Por quê.** A Aula 8 pede classificação × clusterização, os tipos de classificação, pipelines TF-IDF × BERT e métricas além da acurácia. O corpus já traz rótulos de gênero, e cerca de um quarto dos filmes tem mais de um, o que torna o multirrótulo natural. Com `C` fixo, o TF-IDF ficava regularizado demais (probabilidades quase uniformes), e um único `C` não serve igualmente a representações de escalas e dimensões diferentes. Escolher `C` pelo F1 achatava as probabilidades; pela log loss, elas acompanham a acurácia sem perda de F1. O ajuste fino do BERT e o LLM zero-shot ficaram de fora por custo, pela amostra pequena e pela reprodutibilidade.

**Consequência.** Na multiclasse, as representações densas superam o melhor TF-IDF em 7 a 12 pontos de F1 macro; skip-gram e BERTimbau empatam dentro do desvio entre dobras. Medidos nas mesmas dobras, o Naive Bayes vence só nas contagens brutas, o SVM empata sem dar probabilidades, e o K-Means coincide muito menos com os gêneros que o classificador ([justificativa](../6-classificacao-escolha-dos-modelos.md)). Parte dos erros confiantes vem de rótulos ruidosos (filmes de ação reduzidos a “comédia”). [Detalhes](0017-aula8-classificacao-de-generos.md)

## 0018 — Tarefas do ciclo de PLN para cada representação

**Decisão.**

- Aplicar cada representação às quatro tarefas do quadro da Aula 8: busca, recomendação, agrupamento com visualização e classificação.
- Implementar a recomendação por conteúdo (`Recommendation`): item → item para todos os filmes e por perfil (média dos filmes de que a pessoa gostou), avaliada pela precisão @k de gênero compartilhado contra uma referência que ignora o texto.
- Gerar, para cada representação, a projeção 2D colorida pelo cluster ao lado da colorida pelo gênero.
- Unificar os rótulos das duas etapas nos `genre_ids` do TMDB restritos aos gêneros da coleta, e usar um único K-Means (`app.clustering.kmeans`).
- Permitir que a Etapa 3 leia os vetores densos verificados da Etapa 2 (`--vectors`) em vez de recalculá-los.

**Por quê.** A auditoria de 29/09/2026 mostrou que a recomendação não existia, que os clusters não eram visualizados, que as etapas usavam rótulos diferentes e que a Etapa 3 recalculava cerca de 100 s de vetores já salvos. Sem avaliações de usuários, só a recomendação por conteúdo é possível; os gêneros são a aproximação automática de relevância. Reestruturar em quatro pipelines reescreveria código testado sem ganho: o padrão `Analysis` já acomoda cada tarefa.

**Consequência.** Nenhuma representação vence todas as tarefas: o modelo de sentença lidera a busca, o BERTimbau a recomendação (63,6% contra 37,9% da referência) e o agrupamento, e o skip-gram a classificação. Os números de agrupamento da Etapa 2 mudaram com os novos rótulos. Com `--vectors`, a Etapa 3 cai para cerca de 2,5 minutos e dispensa o extra `semantico`. [Detalhes](0018-tarefas-do-ciclo-de-pln.md)

## 0019 — Jev e TF-IDF + regressão logística (Aula 8)

**Decisão.**

- Classificar o gênero das sinopses com o Jev: uma Choice (gênero principal) e um Noul por gênero, na mesma chamada.
- Comparar com TF-IDF + regressão logística treinada com os filmes fora da amostra, nos mesmos filmes e com as mesmas métricas.
- Amostra de 120 filmes: 25 de cada gênero único e 20 com dois gêneros, com semente fixa.
- Perguntas em `config/classificacao/jev.json`; SDK no extra opcional `jev`, atrás da porta `DecisionClient`; chave `TYPESAFE_API_KEY` como `SecretStr`.
- Respostas validadas e guardadas em `responses.jsonl`, reaproveitáveis com `--reuse`; a primeira falha interrompe sem gravar nada.

**Por quê.** A Aula 8 contrapõe decisões estruturadas sem treino ao pipeline clássico. Os gêneros de coleta são o único rótulo do corpus que a sinopse expressa, por isso não há Score. Cada chamada é paga e o alias do modelo muda, então as respostas brutas precisam ser guardadas e reavaliadas sem novas chamadas.

**Consequência.** A amostra pequena ilustra a comparação, mas não é teste estatístico. A redação das perguntas faz parte da tarefa. O `uv.lock` precisa incluir o extra `jev`. [Detalhes](0019-aula8-jev-classificacao-de-genero.md)

## 0020 — Busca por tema: TF-IDF + embedding de sentença

**Decisão.**

- Ampliar as consultas anotadas de 2 para 20 e acrescentar MAP e precisão @5 à análise de busca.
- Comparar as oito representações e as combinações entre elas.
- Usar no site 0,3 × `tfidf_sem_stopwords` + 0,7 × `sentenca_minilm`, com cada cosseno dividido pelo maior da consulta.
- Criar o modo `sinopse`, que aplica os filtros das regras (gênero, período, nota, negação) aos filmes da amostra; o modo `auto` o usa quando o texto não é um título exato.

**Por quê.** O embedding de sentença foi o melhor sozinho (MAP de 0,56) e acerta o tema sem palavras em comum. O TF-IDF acerta palavras-chave fortes, como "zumbis" e "casa assombrada". Juntos, chegam a MAP de 0,61. O ganho se manteve quando o peso foi escolhido numa metade das consultas e medido na outra (95% de 500 divisões). O skip-gram quase não somava e custaria mais um modelo.

**Consequência.** A busca por tema cobre só os 428 filmes da amostra, e a API passa a depender do extra `semantico`; sem ele, o modo `sinopse` avisa que está indisponível. [Detalhes](0020-busca-hibrida-tfidf-e-sentenca.md)

## 0021 — Classificação de gênero na tela

**Decisão.** Uma seção do site recebe uma sinopse e mostra o gênero previsto, com a probabilidade de cada um. Por trás, `GET /classificacao` usa a regressão logística da Etapa 3, ajustada com as 325 sinopses de um gênero sobre o embedding de sentença `sentenca_minilm`, que a busca por tema já carrega.

**Por quê.** A classificação só existia em relatórios. Reaproveitar a representação da busca evita carregar outro modelo e não tem custo por uso. O BERTimbau e o skip-gram dariam alguns pontos a mais de F1, mas exigiriam mais um modelo na API; o Jev seria uma chamada paga por classificação.

**Consequência.** A qualidade esperada é o F1 macro de 66,1% medido na validação cruzada. Comédia é o gênero mais difícil, e frases curtas fora do estilo das sinopses erram com frequência. Sem o extra `semantico`, a rota responde 503. [Detalhes](0021-classificacao-na-tela.md)

## 0022 — Repositório organizado por tarefa

**Decisão.** O código, as configurações, os dados e a documentação passam a ser organizados pelas tarefas da disciplina, na ordem da apresentação:

- código: `corpus`, `representations`, `search`, `recommendation`, `clustering`, `classification` (com o Jev em `classification/jev`);
- configurações e dados: `coleta`, `representacoes`, `busca`, `classificacao`;
- documentação: `docs/1-…` a `docs/6-…`, mais `docs/tecnico/` e `APRESENTACAO.md`.

As análises que estavam juntas em `vectors/analyses.py` foram separadas por tarefa, e as portas e adaptadores ficaram dentro de cada pasta.

**Por quê.** A estrutura seguia a ordem das etapas, e a busca, por exemplo, estava espalhada em cinco lugares. Organizar por tarefa deixa cada parte avaliada pelo professor numa pasta só, do algoritmo à avaliação e aos resultados.

**Consequência.** Os comandos mudaram de nome (`python -m app.representations`, `python -m app.search`, `python -m app.classification.jev`). Os dados não mudaram, e os quatro `verify` passam nas pastas novas. A branch antiga `luana-classificacao` fica incompatível com a estrutura nova. [Detalhes](0022-organizacao-por-tarefa.md)

## 0023 — Filmes parecidos na ficha do filme

**Decisão.** A ficha de cada filme da amostra mostra os 5 filmes de sinopse mais parecida, pela mesma conta da análise `Recommendation` (maior cosseno, sem o próprio filme), sobre o embedding de sentença que a busca já carrega. A rota é `GET /filmes/{id}/parecidos`.

**Por quê.** A recomendação só existia como avaliação. Mostrá-la a partir de um filme dispensa guardar perfis de usuários e não carrega modelo novo; o BERTimbau teria só 1 ponto a mais de precisão @5.

**Consequência.** Funciona muito bem em franquias e temas marcados e é mais fraca em temas abstratos. Filmes fora dos 428 da amostra mostram um aviso no lugar das recomendações. [Detalhes](0023-recomendacao-no-site.md)
