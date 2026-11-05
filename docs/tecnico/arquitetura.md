# Arquitetura do código

O backend (`backend/src/app`) é organizado **por tarefa da disciplina**: cada pasta reúne o código de uma etapa ou tarefa, do algoritmo à avaliação ([ADR 0022](../adr/0022-organizacao-por-tarefa.md)). A API do site e os utilitários compartilhados ficam em pastas próprias. As razões de cada escolha estão nas [ADRs](../adr/README.md).

## Pastas

| Pasta | Tarefa | Conteúdo principal |
|---|---|---|
| `corpus/` | 1. Coleta e preparação | Coleta no TMDB, seis preparações do texto, estatísticas, relatório e verificação |
| `representations/` | 2. Representações | As oito representações (`space.py`, `embeddings.py`, `methods.py`), o pipeline que as constrói e roda as análises (`pipeline.py`), sondas da Aula 7 e relatório |
| `search/` | 3. Busca | Regras léxicas (`rules/`), interpretação da frase por LLM e a sua avaliação (`interpretation/`, [ADR 0030](../adr/0030-interpretacao-da-consulta-por-llm.md)), busca por cosseno (`retrieval.py`), combinação TF-IDF + embedding de sentença (`hybrid.py`), avaliação com consultas anotadas (`evaluation.py`), serviço do site (`service.py`) e índice de sinopses (`synopsis_index.py`) |
| `recommendation/` | 4. Recomendação | Filme → filmes e perfil → filmes, com avaliação por gênero compartilhado (`analysis.py`), e os filmes parecidos do site (`similar.py`) |
| `clustering/` | 5. Agrupamento e visualização | K-Means e projeção 2D (`kmeans.py`), avaliação (`analysis.py`) e gráficos SVG (`svg.py`) |
| `classification/` | 6. Classificação | Regressão logística com validação cruzada (`pipeline.py`, `evaluation.py`), classificadores alternativos, classificador da tela (`live.py`) e o Jev (`jev/`) |
| `sentiment/` | Aula 9 e Unidade 4 | Coleta e preparação das críticas, polaridade e nota com as oito representações (`pipeline.py`), analisador da tela (`live.py`) e o sentimento com LLM comparado aos modelos treinados (`llm/`, [ADR 0031](../adr/0031-sentimento-com-llm.md)) |
| `rag/` | Unidade 4 | Perguntas sobre os filmes: críticas por filme e escolha dos trechos (`reviews.py`), recuperação com títulos citados e a busca híbrida (`retrieval.py`), contexto numerado (`prompt.py`), conferência das citações (`grounding.py`), serviço (`service.py`) e avaliação (`pipeline.py`, [ADR 0032](../adr/0032-rag-perguntas-sobre-filmes.md)) |
| `api/` | Site | Rotas `/pesquisa`, `/filmes`, `/filmes/{id}/parecidos`, `/classificacao`, `/sentimento`, `/sentimento/llm`, `/entidades`, `/pergunta` e `/saude`, esquemas de resposta, limite geral de requisições e limite próprio das rotas com LLM ([ADR 0033](../adr/0033-publicacao-no-hugging-face-spaces.md)) |
| `tmdb/` | Fonte de dados | Cliente HTTP do TMDB, catálogo e cache, usados pela coleta e pela API |
| `llm/` | Unidade 4 | Porta `LanguageModel`, adaptadores Gemini e Groq, saída estruturada validada, reserva, cache, orçamento diário e replay das respostas ([ADR 0029](../adr/0029-base-de-llm-por-api-gratuita.md)) |
| `shared/` | — | Artefatos determinísticos, manifesto, validação de configuração e regras de língua |
| `main.py`, `settings.py` | Site | Montagem da API (`create_app`) e configuração lida do ambiente e de `backend/.env`; com `SERVE_FRONTEND=true`, a API também serve o `frontend/` na mesma origem ([ADR 0033](../adr/0033-publicacao-no-hugging-face-spaces.md)) |

Fora do backend: `frontend/` tem a demonstração (`index.html` e `script.js`), a página "Sobre o projeto" (`sobre.html` e `sobre.js`), o leitor dos números (`resultados.js`) e os dados das páginas (`dados/resultados.json`, gerado por `docs/entregas/unidade-4/coletar_resultados.py`, e `dados/exemplos_rag.json`, [ADR 0034](../adr/0034-paginas-do-site-e-sobre-o-projeto.md)). `deploy/space/` tem o `Dockerfile` e o script que monta a pasta publicada no Hugging Face Spaces.

Busca, recomendação e agrupamento rodam dentro do pipeline das representações: cada um é uma classe do padrão `Analysis`, e `representations/pipeline.py` as reúne em `DEFAULT_ANALYSES`. A classificação tem pipeline próprio, porque tem avaliação (validação cruzada) e saídas próprias.

## Dependências entre as pastas

```mermaid
flowchart LR
    CORPUS[corpus] --> REP[representations]
    REP --> SEARCH[search]
    REP --> RECO[recommendation]
    REP --> CLUS[clustering]
    REP --> CLASS[classification]
    CLUS -. K-Means .-> CLASS
    SEARCH -. análises .-> REP
    RECO -. análises .-> REP
    CLUS -. análises .-> REP
    API[api + main] --> SEARCH
    API --> CLASS
    API --> RECO
    API --> TMDB[tmdb]
    CORPUS --> TMDB
    API --> SENT[sentiment]
    API --> ENT[entities]
    API --> RAG[rag]
    RAG --> SEARCH
    RAG --> LLM[llm]
    SEARCH --> LLM
    SENT --> LLM
```

As setas pontilhadas de volta para `representations` indicam que o pipeline importa as análises das tarefas para montar o relatório. As tarefas dependem só da classe base `Analysis` e dos tipos das representações, então não há importação circular.

## Dados e configurações

Cada etapa lê e grava pastas próprias. Toda saída tem `manifest.json` com o SHA-256 de cada arquivo e um comando `verify` ([ADR 0009](../adr/0009-saidas-imutaveis-e-verificaveis.md)).

| Etapa | Configuração | Comando | Saída |
|---|---|---|---|
| Coleta | `config/coleta/coleta.json` | `python -m app.corpus collect` | `data/coleta/` |
| Preparação | `config/coleta/stopwords_pt.txt` | `python -m app.corpus process` | `data/preparacao/` |
| Representações, busca, recomendação, agrupamento | `config/representacoes/`, `config/busca/consultas.json` | `python -m app.representations build` | `data/representacoes/` |
| Busca combinada | `config/busca/busca.json` | `python -m app.search hybrid` | saída no terminal |
| Classificação treinada | `config/classificacao/classificacao*.json` | `python -m app.classification build` | `data/classificacao/` |
| Jev | `config/classificacao/jev.json` | `python -m app.classification.jev run` | `data/jev/` |
| Análise de sentimentos | `config/sentimento/coleta_criticas.json`, `config/sentimento/sentimento.json` | `python -m app.sentiment collect`, `process`, `build` e `verify`; com LLM, `llm-sample`, `llm-eval` e `llm-verify` | `data/coleta/criticas_2026-10-10/`, `data/preparacao/criticas_2026-10-10/` (fora do Git), `data/sentimento/` (o experimento e `llm_2026-10-26/`) |
| Número de clusters | `config/agrupamento/varredura_k.json` | `python -m app.clustering sweep` e `verify` | `data/agrupamento/` |
| Entidades e relações | `config/entidades/entidades.json` | `python -m app.entities credits`, `build` e `verify` | `data/coleta/creditos_2026-10-10/`, `data/entidades/` |
| Catálogo do site (busca e recomendação na API) | `config/coleta/coleta_site.json`, `config/representacoes/vetorizacao_site.json` | `corpus collect`, `corpus process` e `representations build` | `data/*/site_2026-10-05/` (fora do Git) |

Os rótulos de gênero são os mesmos em todas as etapas: `Document.genres` é o conjunto de `genre_ids` do TMDB restrito aos quatro gêneros da coleta.

## Fluxo de uma pesquisa no site

1. `GET /pesquisa` valida `q`, `pagina`, `ano`, `modo` e `interpretacao` e aplica o limite de requisições.
2. `search/service.py` escolhe a estratégia do modo e o intérprete da frase. Com `interpretacao=auto` (o padrão), o LLM extrai os filtros e, se falhar ou passar de 4 s, as regras assumem; sem LLM configurado, só as regras ([ADR 0030](../adr/0030-interpretacao-da-consulta-por-llm.md)):
   - **título:** busca o título no TMDB, sem interpretar a frase;
   - **preferências:** o intérprete extrai gênero, período e nota, e o TMDB faz a descoberta;
   - **tema:** os filmes da amostra são ordenados por 0,3 × TF-IDF + 0,7 × embedding de sentença e filtrados pelo intérprete ([ADR 0020](../adr/0020-busca-hibrida-tfidf-e-sentenca.md));
   - **automático:** título exato, depois tema, depois preferências, depois título ([ADR 0006](../adr/0006-prioridade-de-titulo-exato.md)).
3. A resposta é traduzida para o contrato JSON em português (`modo`, `resultados`, `interpretacao`, que diz em `origem` quem interpretou). Falhas do TMDB viram 502, filme inexistente vira 404, e `interpretacao=llm` com o LLM fora do ar vira 503.

`GET /filmes/{id}/parecidos` devolve os filmes de maior cosseno com o filme, na mesma representação ([ADR 0023](../adr/0023-recomendacao-no-site.md)). `GET /classificacao` passa o texto ao classificador da tela, treinado na inicialização com a representação que a busca por tema já carrega ([ADR 0021](../adr/0021-classificacao-na-tela.md)).

## Fluxo de uma pergunta (RAG)

1. `GET /pergunta?q=` valida o texto (até 300 caracteres) e aplica o limite geral e o limite próprio das rotas com LLM (5 por minuto por IP).
2. `rag/retrieval.py` interpreta a frase com o mesmo intérprete da pesquisa (LLM com reserva nas regras), procura os títulos citados na pergunta e completa até k = 8 filmes com a busca híbrida filtrada.
3. `rag/reviews.py` escolhe, para cada filme, até 2 trechos de crítica pelo embedding de sentença, sem o autor.
4. `rag/prompt.py` numera o contexto (`[F<id>]`) e neutraliza marcas `[F…]` que viessem das sinopses ou das críticas; a pergunta vai como dado.
5. O LLM responde em JSON (`resposta`, `contexto_suficiente`, `citados`), com o orçamento diário `rag`.
6. `rag/grounding.py` remove citações a filmes fora do contexto; resposta sem nenhuma citação válida vira "não encontrei". A rota devolve a resposta, os filmes citados e o contexto usado, que o site mostra em "De onde veio a resposta" ([ADR 0032](../adr/0032-rag-perguntas-sobre-filmes.md)).

Sem LLM configurado, a rota responde 503. Com a cota ou o orçamento no fim, também 503 com o motivo, e o site mostra a resposta gravada na avaliação quando a pergunta é um dos exemplos.

## Portas e adaptadores

Mesmo organizado por tarefa, o código mantém as dependências externas atrás de interfaces ([ADR 0004](../adr/0004-arquitetura-em-camadas.md)):

| Porta | Onde | Implementação real | Nos testes |
|---|---|---|---|
| `MovieCatalog`, `MovieDetailsProvider` | `search/ports.py` | `tmdb/catalog.py` com cache | `FakeCatalog` |
| `SynopsisIndex` | `search/ports.py` | `search/synopsis_index.py` | `FakeSynopsisIndex` |
| `PreferenceExtractor` | `search/ports.py` | `search/rules/extractor.py` (regras), `search/interpretation/llm_extractor.py` (LLM) e `hybrid_extractor.py` (LLM com reserva nas regras) | `LLMFilterExtractor` sobre `FakeLanguageModel` |
| `GenreClassifier` | `classification/ports.py` | `classification/live.py` | `FakeGenreClassifier` |
| `SimilarMoviesProvider` | `recommendation/ports.py` | `recommendation/similar.py` | `FakeRecommender` |
| `DecisionClient` | `classification/jev/ports.py` | `classification/jev/typesafe_client.py` | Jev falso em `test_jev.py` |
| `LanguageModel` | `llm/ports.py` | `llm/compose.py` (cache → orçamento → reserva → `llm/gemini.py` e `llm/groq.py`) | `FakeLanguageModel` |

## Como estender

| Para | Faça |
|---|---|
| Nova representação | Implemente `Representation` e um método com `build` e registre-o em `representations/methods.py` |
| Nova análise sobre as representações | Subclasse de `Analysis` com `run` e `report_section` no pacote da tarefa, acrescentada a `DEFAULT_ANALYSES` em `representations/pipeline.py` |
| Outra combinação na busca por tema | Edite `config/busca/busca.json` e compare com `python -m app.search hybrid --queries ../config/busca/consultas.json` |
| Novo modo de pesquisa | Crie uma estratégia com `search(request)` em `search/service.py` e acrescente o valor em `SearchMode` |
| Novo gatilho de gênero ou negação | Edite `search/rules/lexicon.py` ou `shared/language.py` |
| Novo classificador de comparação | Registre um `Alternative` em `classification/alternatives.py` e inclua o nome na configuração |
| Nova pergunta ao Jev | Edite `config/classificacao/jev.json`; outra redação exige novas chamadas |

## Testes

| Arquivo | Cobertura |
|---|---|
| `test_corpus.py` | Transformações, coleta simulada, validação da configuração, integridade e determinismo |
| `test_representations.py` | Representações (com modelos falsos), rótulos, busca, recomendação, agrupamento e gráficos, sondas, relatório, segurança da configuração, verificação, busca combinada e índice de sinopses |
| `test_search_extractor.py` | Regras: gatilhos, negação, qualidade e períodos |
| `test_search_service.py` | Estratégias de pesquisa e busca por tema com índice falso |
| `test_search_interpretation.py` | Prompt e variantes, extrator por LLM (esquema com os gêneros do catálogo, datas, limiares), reserva nas regras por falha e por prazo, rota com `interpretacao`, frases anotadas, métricas e avaliação com `--reuse` |
| `test_classification.py` | Tarefas, validação cruzada, decisão multirrótulo, K-Means × classificador, alternativos, reaproveitamento dos vetores e classificador da tela |
| `test_sentiment_llm.py` | Variantes do prompt, corte das críticas longas, esquema da saída, amostra equilibrada e conferida, junção com as predições gravadas, métricas, cota diária e chave ausente, e avaliação com `--reuse` sem chamadas e com os mesmos bytes |
| `test_rag.py` | Janelas e trechos de crítica sem autor, títulos citados, filtros e k, contexto determinístico e sem citações falsas, conferência das citações, rota `/pergunta` com limite próprio, kappa, avaliação com `--reuse`, julgamentos e exemplos gravados |
| `test_jev.py` | Amostra, perguntas, validação das respostas, falhas, reaproveitamento, métricas e adaptador do SDK (com um Jev falso) |
| `test_tmdb.py` | Cliente, catálogo e cache do TMDB |
| `test_llm.py` | Configuração, corpo e cabeçalhos dos pedidos ao Gemini e ao Groq, erros sem vazar chave, saída estruturada, reserva, cache, orçamento, replay e os modelos das avaliações em lote |
| `test_api.py` | Contrato das rotas, validação, erros, CORS, limite de requisições (também atrás do proxy, com `X-Forwarded-For`) e o frontend servido na mesma origem |
| `test_resultados.py` | `frontend/dados/resultados.json` igual ao que o coletor gera a partir de `data/` e `config/`, quadro igual ao de `docs/9-tecnicas-avancadas.md` e todo número das páginas presente no JSON |

`tests/fakes.py` contém os dublês compartilhados. Nenhum teste acessa a rede.
