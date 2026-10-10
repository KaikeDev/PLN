# PLN 2026/2 — Sinopses de filmes

Sinopses de filmes do TMDB coletadas, preparadas, transformadas em oito representações e usadas nas quatro tarefas de PLN da disciplina: **busca, recomendação, agrupamento com visualização e classificação**. Um site de demonstração usa a busca, a recomendação e a classificação.

Equipe: Kaike Ventura Tuerpe, Luana Nitsche, Pedro Henrique Ortunio e Thiago Bodnar — Ciência da Computação, FURB.


## As tarefas

| # | Tarefa | O que faz | Resultado principal | Documento | Código |
|---|---|---|---|---|---|
| 1 | Coleta e preparação | 430 filmes de 4 gêneros e 3 períodos; 6 preparações do texto | 428 sinopses, todas as etapas alinhadas pelo ID | [1-coleta-e-preparacao.md](docs/1-coleta-e-preparacao.md) | [`corpus/`](backend/src/app/corpus/) |
| 2 | Representações | BoW, TF-IDF, word2vec (CBOW e skip-gram), BERTimbau e embedding de sentença | 8 representações comparadas em todas as tarefas | [2-representacoes.md](docs/2-representacoes.md) | [`representations/`](backend/src/app/representations/) |
| 3 | Busca | Regras para gênero e período + 0,3 × TF-IDF + 0,7 × embedding de sentença; no site, num catálogo de 5.525 filmes | MAP de 0,613 em 20 consultas anotadas | [3-busca.md](docs/3-busca.md) | [`search/`](backend/src/app/search/) |
| 4 | Recomendação | Filmes parecidos com um filme ou com um perfil; no site, na ficha de cada filme, no mesmo catálogo | Precisão @5 de 63,6% (BERTimbau) contra 37,9% ao acaso | [4-recomendacao.md](docs/4-recomendacao.md) | [`recommendation/`](backend/src/app/recommendation/) |
| 5 | Agrupamento e visualização | K-Means sem rótulos e projeção 2D | Grupos lembram pouco os gêneros (ARI de até 0,144) | [5-agrupamento.md](docs/5-agrupamento.md) | [`clustering/`](backend/src/app/clustering/) |
| 6 | Classificação | Regressão logística nas 8 representações, Jev sem treino e classificação na tela | F1 de 71,0% (skip-gram); Jev com 85,0% de acurácia | [6-classificacao.md](docs/6-classificacao.md) | [`classification/`](backend/src/app/classification/) |
| 7 | Análise de sentimentos (Aula 9) | 1.859 críticas do TMDB rotuladas pela nota do autor; polaridade e nota com as 8 representações; análise de críticas na tela | F1 macro de 86,7% (BERTimbau) e 85,6% (TF-IDF); nota com erro médio de 1,33 ponto | [7-sentimentos.md](docs/7-sentimentos.md) | [`sentiment/`](backend/src/app/sentiment/) |
| 8 | Entidades e relações (Aula 9) | spaCy `pt_core_news_sm` e as regras de dependência do notebook nas 428 sinopses; entidades e relações na ficha do filme | 73,7% das pessoas creditadas reconhecidas como pessoa; 1.435 triplas | [8-entidades-e-relacoes.md](docs/8-entidades-e-relacoes.md) | [`entities/`](backend/src/app/entities/) |

## Tarefas × representações

Uma métrica por célula, calculada nos arquivos entregues:

| Representação | Busca: MAP | Recomendação: precisão @5 | Agrupamento: ARI | Classificação: F1 macro |
|---|---:|---:|---:|---:|
| Referência que ignora o texto | — | 37,9% | 0 | 10,7% |
| `bow_sem_pontuacao` | 0,188 | 45,0% | 0,002 | 46,1% |
| `bow_sem_stopwords` | 0,375 | 56,1% | 0,000 | 56,4% |
| `tfidf_sem_pontuacao` | 0,460 | 57,0% | 0,001 | 59,3% |
| `tfidf_sem_stopwords` | 0,446 | 57,8% | 0,024 | 59,2% |
| `word2vec_cbow` | 0,333 | 55,7% | 0,060 | 67,6% |
| `word2vec_skipgram` | 0,356 | 60,2% | 0,062 | **71,0%** |
| `bert_base_pt` | 0,295 | **63,6%** | **0,144** | 70,2% |
| `sentenca_minilm` | **0,560** | 62,6% | 0,087 | 66,1% |

Nenhuma representação vence todas as tarefas: o embedding de sentença é o melhor na busca, o BERTimbau na recomendação e no agrupamento, e o skip-gram na classificação, empatado com o BERTimbau dentro do desvio entre dobras.

## Estrutura do repositório

```
README.md                 ← esta página
APRESENTACAO.md           ← o que foi feito, para apresentar ao professor
docs/
  1-coleta-e-preparacao.md … 8-entidades-e-relacoes.md   ← uma explicação por tarefa
  tecnico/                ← como executar, arquitetura, validação, decisões, dicionário de dados
  adr/                    ← registro das decisões (ADRs) e resumo
  entregas/               ← documento Word da Etapa 1
config/                   ← parâmetros de cada etapa: coleta/, representacoes/, busca/, classificacao/, sentimento/, entidades/
data/                     ← resultados entregues, com manifesto e hashes
  coleta/  preparacao/  representacoes/  classificacao/  jev/  sentimento/  entidades/
backend/src/app/          ← código, uma pasta por tarefa
  corpus/  representations/  search/  recommendation/  clustering/  classification/  sentiment/  entities/
  api/  tmdb/  shared/  main.py  settings.py   ← site e utilitários
backend/tests/            ← testes automatizados (sem rede)
frontend/                 ← site: busca de filmes, filmes parecidos, classificação de sinopses, análise de críticas e entidades e relações
```

## Como executar

📘 **Passo a passo completo, do zero até o site aberto: [docs/tecnico/rodar-o-site.md](docs/tecnico/rodar-o-site.md)**, com o que instalar, onde rodar cada comando, o que testar em cada tela e como resolver os problemas comuns.

Resumo. Todos os comandos rodam **na pasta `backend`**, com o [uv](https://docs.astral.sh/uv/) instalado:

| Quando | Passo | Comando |
|---|---|---|
| 1ª vez | 1. Token do TMDB | Copie `backend/.env.example` para `backend/.env` e preencha `TMDB_BEARER_TOKEN` |
| 1ª vez | 2. Instalar | `uv sync --frozen --extra semantico --extra jev --extra entidades` |
| 1ª vez | 3. Catálogo do site (~8 min) | os 3 comandos de [rodar-o-site.md](docs/tecnico/rodar-o-site.md#passo-3--gerar-o-catálogo-do-site-cerca-de-8-minutos-uma-vez-só) |
| 1ª vez | 4. Críticas (segundos) | `uv run --frozen python -m app.sentiment process --input ../data/coleta/criticas_2026-10-10 --output ../data/preparacao/criticas_2026-10-10 --stopwords ../config/coleta/stopwords_pt.txt` |
| **Sempre** | 5a. API, no terminal 1 | `uv run --frozen --extra semantico --extra jev --extra entidades uvicorn app.main:app --host 127.0.0.1` |
| **Sempre** | 5b. Telas, no terminal 2 | `uv run --frozen python -m http.server 5500 --directory ../frontend` |

Depois, abra <http://127.0.0.1:5500>.

> [!IMPORTANT]
> O **catálogo do site** (passo 3) e as **críticas preparadas** (passo 4) não vêm no repositório. Sem o catálogo, a busca por tema e os filmes parecidos usam só os 428 filmes da amostra, e aparece uma faixa amarela no topo. Sem as críticas, a aba "Analisar crítica" fica indisponível. Todas as **avaliações** do projeto usam os dados que vêm no repositório ([por quê](docs/adr/0024-catalogo-do-site.md)).

Refazer cada etapa e conferir os dados entregues: [docs/tecnico/como-executar.md](docs/tecnico/como-executar.md).

## Documentação técnica

- [Como rodar o site](docs/tecnico/rodar-o-site.md): passo a passo do zero
- [Arquitetura do código](docs/tecnico/arquitetura.md)
- [Validação técnica](docs/tecnico/validacao.md): o que foi testado e verificado em cada etapa
- [Decisões e limitações](docs/tecnico/decisoes.md), [resumo das ADRs](docs/adr/resumo.md) e [ADRs completas](docs/adr/README.md)
- [Dicionário de dados](docs/tecnico/dicionario.md)

## Fonte e atribuição

Dados fornecidos por [The Movie Database](https://www.themoviedb.org/) via [API TMDB](https://developer.themoviedb.org/docs/getting-started). Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB. Os dados preservam as condições de uso da fonte; sua inclusão para a atividade acadêmica não concede uma nova licença sobre sinopses, imagens ou catálogo.
