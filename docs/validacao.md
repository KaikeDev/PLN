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

## Aula 8 — Jev × TF-IDF + regressão logística (28/09/2026)

Execução local em Python 3.14.7, com typesafe-sdk 0.7.2 (extra `jev`), scikit-learn 1.9.1, NumPy 2.5.3 e SciPy 1.18.1, fixados em `uv.lock`. Modelo informado pela API: `jev-1.13.0`. Decisões no [ADR 0019](adr/0019-aula8-jev-classificacao-de-genero.md).

| Verificação | Resultado e alcance |
|---|---|
| Testes automatizados | 78 testes aprovados, 15 deles em `test_jev.py`. Um Jev falso substitui a API. Os testes cobrem: amostra estratificada e reprodutível, perguntas enviadas, validação das respostas (opção desconhecida, valores fora de 0 a 1, tipo errado), primeira falha sem gravar nada, falhas seguintes registradas e fora das métricas, reaproveitamento com `--reuse` idêntico byte a byte, recusa de respostas geradas com outras perguntas, configuração inválida, adulteração, conversão da resposta do SDK e chave obrigatória fora do `repr`. Sem rede nem chave. |
| Lint, formatação e tipos | `ruff check`, `ruff format --check` e `mypy` sem apontamentos. |
| Execução real | 120 sinopses (25 por gênero único e 20 com dois gêneros), nenhuma falha. Foram 110 chamadas novas e 10 respostas reaproveitadas de uma primeira execução com 48 filmes, em 53 s, com cerca de 76 mil tokens de entrada e 16 mil de saída no total. `verify` aprovou os 7 arquivos e o alinhamento das respostas e previsões com a amostra. |
| Repetição sem chamadas | `run --reuse` a partir da entrega, em outra pasta: 0 chamadas, e os 7 arquivos de conteúdo ficaram idênticos byte a byte. |
| Separação treino/teste | O TF-IDF + regressão logística foi treinado só com os filmes fora da amostra; vocabulário e IDF também não veem a amostra. |
| Segurança | A chave fica em `backend/.env` (ignorado pelo Git), é lida como `SecretStr` e passada ao construtor do SDK; não é gravada em nenhum arquivo de saída nem no manifesto (conferido por busca nos arquivos). |

```bash
uv run --frozen python -m app.jev verify --input ../data/jev/tmdb_2026-09-12
```

## Busca por tema: TF-IDF + embedding de sentença (28–29/09/2026)

Escolha da combinação e integração com a busca do site. Decisões no [ADR 0020](adr/0020-busca-hibrida-tfidf-e-sentenca.md).

| Verificação | Resultado e alcance |
|---|---|
| Consultas anotadas | 20 consultas em `config/consultas.json`, com relevantes fechados lendo as 428 sinopses antes de rodar qualquer ranking. |
| Build real | As 8 representações com as 20 consultas, numa pasta de trabalho, com os modelos de revisão fixada: `sentenca_minilm` MAP 0,560; `tfidf_sem_pontuacao` 0,460; `tfidf_sem_stopwords` 0,446; `bert_base_pt` 0,295. |
| Combinações | Soma ponderada e RRF de todas as combinações de 2 a 4 representações, num script exploratório. 0,3 × `tfidf_sem_stopwords` + 0,7 × `sentenca_minilm`: MAP 0,613, MRR 0,912, acerto @5 de 100%. Pesos escolhidos numa metade das consultas e medidos na outra: ganho sobre o `sentenca_minilm` sozinho em 95% de 500 divisões. |
| Testes automatizados | 90 testes aprovados. Com índice falso: `test_search_service.py` (12) e `test_api.py` (10), que cobrem filtros, paginação, ordem do modo automático, contrato `modo=sinopse` e aviso sem índice. Com modelos falsos, 5 novos em `test_vectors.py`: combinação, normalização pelo maior cosseno, avaliação, validação de `config/busca.json` e índice de sinopses sobre coleta e processamento reais. |
| Lint, formatação e tipos | `ruff check`, `ruff format --check` e `mypy` sem apontamentos. |
| Comando da combinação | `python -m app.vectors hybrid --queries ../config/consultas.json` com os modelos reais reproduziu os números do script: `tfidf_sem_stopwords` MAP 0,446; `sentenca_minilm` 0,560; combinação 0,613 (MRR 0,912, acerto @5 de 100%, precisão @5 de 0,56). |
| Regeneração | `data/vectors/tmdb_2026-09-12` foi regenerada com as 20 consultas; `verify` aprovou os 34 arquivos. Além de consultas, busca, relatório e manifesto, mudaram só `bert_base_pt.embeddings.jsonl`, um ponto de `projection.json` e um cosseno de `sentence_pairs.json`, todos na sexta casa decimal: variação de ponto flutuante entre máquinas (Python 3.14.0 × 3.14.7, mesmas bibliotecas). |
| Ambiente | O Controle Inteligente de Aplicativos do Windows chegou a bloquear o `python.exe` dos ambientes virtuais e DLLs do scikit-learn; as verificações acima rodaram depois de ele ser desativado. |

## Junção com a classificação de gêneros (03/10/2026)

Merge da branch `luana-classificacao` (ADRs 0017 e 0018) no `trabalho-3`. As ADRs do Jev e da busca foram renumeradas para 0019 e 0020.

| Verificação | Resultado e alcance |
|---|---|
| Testes automatizados | 107 testes aprovados: os da classificação, da recomendação e dos rótulos unificados, junto com os do Jev e da busca por tema. |
| Lint, formatação e tipos | `ruff check`, `ruff format --check` e `mypy` sem apontamentos. |
| Vetores | `data/vectors/tmdb_2026-09-12` foi regenerada com a recomendação, os rótulos do TMDB e as 20 consultas; `verify` aprovou os 50 arquivos. Em relação à versão da branch, só mudaram o relatório, o manifesto e as recomendações do BERTimbau, na sexta casa decimal. |
| Classificação | `data/classification/tmdb_2026-09-12` foi regenerada a partir dos vetores novos (`--vectors`); `verify` aprovou os 25 arquivos. Métricas e relatório idênticos aos da branch; mudaram só as probabilidades do BERTimbau, na sexta casa decimal, e o manifesto. |
| Jev com os rótulos do TMDB | Nova amostra de 120 sinopses: 47 respostas reaproveitadas e 73 chamadas novas (`jev-1.13.0`), nenhuma falha, em 41 s. `verify` aprovou os 7 arquivos. Repetição com `--reuse` a partir da entrega: 0 chamadas e arquivos de conteúdo idênticos byte a byte. Acurácia de 85,0% contra 56,0% da referência nos 100 filmes de um gênero. A primeira tentativa falhou com HTTP 403 e não gravou nada; a chave foi trocada em `backend/.env`. |

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

O teste original imprime “100% (12/12)” para campos selecionados de cinco frases. Isso não é acurácia geral do assistente, nem medida de recuperação por sinopse. O projeto não executa reconhecimento de nomes próprios, stemming ou lematização; na Etapa 2, os modelos pré-treinados foram usados sem ajuste fino, e a avaliação de consultas tem só dois casos anotados. Na Aula 8, a amostra de 120 filmes permite comparar os métodos, mas não é um teste estatístico formal. O rótulo é o recorte de coleta, e uma nova chamada ao Jev pode dar outro resultado se o modelo por trás do alias mudar. A interface não passou por avaliação visual em navegador nesta revisão; suas chamadas foram verificadas na API. O bônus e a nota final dependem da avaliação do professor.
