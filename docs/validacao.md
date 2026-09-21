# Validação técnica

Execução em 12/09/2026, Python 3.14.7, ambiente instalado com `uv sync --frozen` a partir de `backend/uv.lock`.

## Verificações concluídas

| Verificação | Resultado e alcance |
|---|---|
| Testes automatizados | 16 testes aprovados: os 5 originais, 6 para o corpus e 5 para pesquisa/integração de parâmetros. Dados controlados; sem rede. |
| Coleta real | 26 chamadas bem-sucedidas ao TMDB: 1 mapa de gêneros, 24 páginas de descoberta e 1 detalhe do ID 603. Manifesto com estado `complete`, 481 ocorrências, 430 IDs e 51 duplicatas removidas. |
| Processamento real | 430 IDs em seis representações, 428 sinopses válidas e 2 ausentes conservadas. |
| Integridade | 13 arquivos verificados por hash e alinhamento dos IDs entre representações e metadados. |
| Repetição offline | Nova pasta processada a partir da mesma amostra: os 13 arquivos de conteúdo ficaram idênticos byte a byte. O manifesto muda para registrar a nova execução. |
| API em execução | HTTP 200 para saúde, detalhes de Matrix e pesquisa por título/preferências. [Saídas resumidas](api_smoke.json). |

A API foi iniciada com Uvicorn e consultada via HTTP local, com acesso real ao TMDB. Matrix apareceu no modo título; a preferência por Drama, sem Terror, entre 2015 e 2019 retornou resultados com a interpretação esperada. Esse teste comprova essas chamadas, não uma avaliação geral da linguagem natural.

## Comandos reproduzíveis

Em `backend`:

```bash
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python -m app.corpus verify --input ../data/processed/tmdb_2026-09-12
uv run --frozen python -m app.corpus process --input ../data/raw/tmdb_2026-09-12 --output ../data/processed/reproducao --stopwords ../config/stopwords_pt.txt
```

A pasta `reproducao` deve ser nova. Os testes exercitam paginação, duplicidade, ausência de texto, negação, integridade, repetição determinística, recusa a sobrescrita e falhas de coleta sem vazamento da credencial. Os testes auxiliares verificam prioridade de título exato, limites de período, mapeamento para descoberta e ausência de filtro positivo para qualidade negada.

## Etapa 2 — Representações vetoriais (14/09/2026)

Execução local em Python 3.14.0, com scikit-learn 1.9.1, NumPy 2.5.3 e SciPy 1.18.1. No extra `semantico`: torch 2.14.0 (CPU), transformers 5.17.0 e sentence-transformers 6.0.1. Todas as versões estão fixadas em `uv.lock`.

| Verificação | Resultado e alcance |
|---|---|
| Testes automatizados | 32 testes aprovados: os 16 anteriores e 16 de `test_vectors.py`. Dados controlados passam pela coleta simulada e pelo processamento reais. Word2vec e modelo contextual são substituídos por implementações falsas injetadas; sem rede nem download. |
| Build real | 428 sinopses em 6 representações (4 lexicais, word2vec NILC 300d e MiniLM multilíngue 384d), executado com `HF_HUB_OFFLINE=1`; 26 arquivos verificados por hash e vetores alinhados a `documents.json`. |
| Repetição | Segunda execução completa em outra pasta: todos os arquivos, exceto o manifesto, idênticos byte a byte, inclusive os embeddings densos. |
| Caminho leve | A configuração só lexical roda sem importar torch nem sentence-transformers. |
| Segurança | Testes rejeitam: etapa com `../`, etapa incompatível com o método, nome de representação inválido, método desconhecido, modelo sem revisão fixa ou com caminho, `model` em método lexical, campos extras, booleano no lugar de inteiro, consulta longa, manifesto com caminho, entrada processada alterada e títulos com HTML no SVG. |

```bash
uv run --frozen python -m app.vectors verify --input ../data/vectors/tmdb_2026-09-12
```

## Aula 7 — BERT, CBOW × skip-gram e polissemia (21/09/2026)

Mesmo ambiente da Etapa 2. Modelos novos com revisão fixada: `neuralmind/bert-base-portuguese-cased` (`94d69c95…`) e `pt-mteb/average_pt_nilc_word2vec_cbow_s300` (`0d556458…`). Decisões no [ADR 0015](adr/0015-aula7-bert-cbow-e-polissemia.md).

| Verificação | Resultado e alcance |
|---|---|
| Testes automatizados | 63 testes aprovados, 22 deles em `test_vectors.py`. Dublês implementam `word_vectors` e `parameters`. Testes novos cobrem: vetor estático igual em qualquer frase, contextual separando sentidos, pares de frases lexical × semântico, pares de palavras, síntese e rejeição de sondas inválidas. Sem rede nem download. |
| Lint, formatação e tipos | `ruff check`, `ruff format --check` e `mypy` sem apontamentos. |
| Build real | 428 sinopses em 8 representações, com consultas e sondas, executado com `HF_HUB_OFFLINE=1`; 34 arquivos verificados por hash e vetores alinhados a `documents.json`. Tempos de construção (`build_seconds`): lexicais < 0,03 s, word2vec 14–20 s, BERTimbau 39 s, modelo de sentença 15 s. |
| Repetição | Segunda execução completa em outra pasta: todos os arquivos, exceto o manifesto, idênticos byte a byte, inclusive BERT e modelo de sentença. |
| Regeneração | `data/vectors/tmdb_2026-09-12` foi regenerada com LF e substitui a execução de 14/09 (seis representações); os valores das representações que já existiam não mudaram. |

## Revisão de arquitetura e segurança (14/09/2026)

Execução local em Python 3.14.0, após a refatoração descrita em [docs/arquitetura.md](arquitetura.md) e nas [ADRs](adr/README.md).

| Verificação | Resultado e alcance |
|---|---|
| Testes automatizados | 57 testes aprovados: corpus (incluindo validação da configuração de coleta), vetores, extrator e serviço de pesquisa, cliente/catálogo/cache do TMDB e rotas HTTP com catálogo falso (contrato JSON, validação, 404/502, CORS e limite 429). Sem rede. |
| Lint, formatação e tipos | `ruff check`, `ruff format --check` e `mypy` sem apontamentos. |
| Regressão da Etapa 1 | `process` sobre `data/raw/tmdb_2026-09-12` reproduziu byte a byte os arquivos de conteúdo de `data/processed/tmdb_2026-09-12`, também no Windows, depois de fixar LF na gravação. |
| Regressão da Etapa 2 | `build` com `config/vetorizacao.json` gerou os mesmos arquivos da execução anterior à refatoração (comparação ignorando CR). `verify` dos 26 arquivos de `data/vectors/tmdb_2026-09-12` aprovado (antes da regeneração de 21/09). |
| Inicialização da API | Com `backend/.env`, `/saude` responde e o OpenAPI lista `/saude`, `/filmes/{filme_id}` e `/pesquisa`; sem token, a inicialização falha com mensagem orientativa. O TMDB não foi consultado. |
| Interface | Sintaxe verificada com `node --check`; não houve teste visual em navegador. |

## Limites da validação

O teste original imprime “100% (12/12)” para campos selecionados de cinco frases. Isso não é acurácia geral do assistente, nem medida de recuperação por sinopse. O projeto não executa reconhecimento de nomes próprios, stemming ou lematização; na Etapa 2, os modelos pré-treinados foram usados sem ajuste fino, e a avaliação de consultas tem só dois casos anotados. A interface não passou por avaliação visual em navegador nesta revisão; suas chamadas foram verificadas na API. O bônus e a nota final dependem da avaliação do professor.
