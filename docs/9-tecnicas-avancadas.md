# 9. Técnicas avançadas com LLM (Unidade 4)

Etapa final do projeto: as técnicas da Unidade 4 aplicadas à mesma base do semestre (amostra `tmdb_2026-09-12`, catálogo do site e críticas `criticas_2026-10-10`), sempre comparadas com o que já existia. Planejamento e critérios de aceite em [`entregas/unidade-4/`](entregas/unidade-4/README.md).

## Quadro de técnicas (item 1 do enunciado)

O mesmo quadro aparece na página "Sobre o projeto" do site: o script [`coletar_resultados.py`](entregas/unidade-4/coletar_resultados.py) o copia desta tabela para `frontend/dados/resultados.json`.

| Tecnologia ou abordagem | Utilizada? | Aplicação ou justificativa |
|---|---|---|
| LLMs e modelos de linguagem | **Sim** | Gemini (principal) e Groq (reserva), por API gratuita, em três tarefas: interpretação da consulta, sentimento e perguntas com RAG. Na classificação de gênero (Aula 8), o Jev (TypeSafe AI). Desde a Etapa 2, os modelos pré-treinados MiniLM e BERTimbau sustentam as representações. |
| Prompt engineering e saídas estruturadas | **Sim** | Respostas em JSON com esquema (gêneros do catálogo como enum, datas validadas, nota de 0 a 10, citações por id), validadas com Pydantic e com uma nova tentativa quando o JSON vem quebrado. Comparações zero-shot × few-shot (interpretação e sentimento) e com e sem justificativa (sentimento). Prompts versionados em config/. |
| RAG e recuperação de informações | **Sim** | Aba "Perguntar": a busca híbrida já avaliada recupera 8 filmes pela sinopse e pelos títulos citados, junta trechos das críticas, e o LLM responde citando só esses filmes; citações fora do contexto são removidas antes de aparecer. Avaliado nas 20 consultas anotadas contra a busca sozinha e em 33 perguntas (tema, opinião, sem resposta e injeção de prompt). |
| Agentes e integração com ferramentas | **Não** | O RAG com etapas fixas responde às perguntas do projeto com uma chamada ao LLM. Um agente que escolhesse entre busca, ficha, parecidos e sentimento faria várias chamadas por pergunta (incompatível com a cota gratuita) e seria mais difícil de avaliar com o gabarito que temos. A integração com serviços existe no sentido de API: o site junta TMDB, LLM e os modelos locais. |
| Modelos locais ou quantizados | **Parcial** | Locais, sim: MiniLM, BERTimbau, word2vec NILC e spaCy rodam na máquina, sem API, com revisão fixada. Quantizados, não: um LLM local quantizado foi descartado para a demonstração, porque na CPU gratuita do servidor seria lento demais e mais fraco em português. Fica como trabalho futuro. |
| Processamento multimodal (texto, imagem, áudio) | **Não** | O problema é textual. Os pôsteres do TMDB aparecem no site, mas não são processados. Pôster + sinopse (por exemplo, com CLIP) fica como trabalho futuro. |
| Outras técnicas avançadas de PLN | **Sim** | Busca híbrida (TF-IDF + embedding de sentença) com preparação da consulta; NER e extração de relações por dependências (spaCy); sentimento com teste de generalização por autor; classificação multirrótulo; comparação sistemática de 8 representações em 5 tarefas. |

## A base comum: uma porta para o LLM

As três técnicas usam o pacote [`llm/`](../backend/src/app/llm/) ([ADR 0029](adr/0029-base-de-llm-por-api-gratuita.md)):

- porta `LanguageModel`, com adaptadores REST para o **Gemini** (principal) e o **Groq** (reserva), por API gratuita;
- resposta em JSON validada por um modelo Pydantic, com uma nova tentativa quando o formato vem errado;
- reserva automática quando um provedor falha por cota, prazo ou indisponibilidade;
- cache, orçamento diário por uso e limite de 5 chamadas por minuto por visitante no site;
- gravação das respostas (`responses.jsonl`) e replay sem rede (`--reuse`), para reavaliar sem gastar cota.

| Configuração ([`config/llm/llm.json`](../config/llm/llm.json)) | Valor |
|---|---|
| Provedores, na ordem | `gemini-flash-lite-latest` (respondeu como `gemini-3.5-flash-lite`) e `openai/gpt-oss-20b` no Groq |
| Acesso | API REST gratuita, chave em cabeçalho, sem SDK |
| Temperatura | 0 |
| Máximo de tokens de saída | 512 (interpretação e sentimento), 1.024 (RAG) |
| Orçamento diário do site | 400 (interpretação), 150 (sentimento), 250 (RAG) |

## 1. Interpretação da consulta: regras × LLM

[ADR 0030](adr/0030-interpretacao-da-consulta-por-llm.md) · [relatório](../data/interpretacao/frases_2026-10-26/report.md)

O LLM recebe a frase do usuário e devolve gêneros incluídos e excluídos, período e "bem avaliado" num JSON em que os gêneros são um `enum` do catálogo. No site, a variante few-shot tem 4 s; se falhar, as regras léxicas assumem, e o selo mostra quem interpretou.

| Nas 50 frases anotadas | Regras | LLM zero-shot | LLM few-shot (site) |
|---|---:|---:|---:|
| Acerto exato dos filtros | 44% | 92% | 94% |
| Paráfrases ("algo que me faça rir") | 0% | 90% | 100% |
| Filtros inventados | 11 | 2 | 0 |

**Na busca, o ganho é pequeno:** nas 20 consultas anotadas, o MAP vai de 0,627 (frase sem filtros) para 0,640 com os filtros do LLM, e cai para 0,615 com os das regras. As consultas anotadas falam mais de tema do que de gênero e período. Separar o tema da frase pelo LLM não melhorou a ordenação e ficou fora do site.

## 2. Sentimento: TF-IDF × BERTimbau × LLM

[ADR 0031](adr/0031-sentimento-com-llm.md) · [relatório](../data/sentimento/llm_2026-11-01/report.md)

As mesmas 200 críticas, sorteadas antes das chamadas (metade negativas, metade do autor principal), comparadas com as predições fora da dobra do TF-IDF e do BERTimbau da Aula 9. O LLM recebe a crítica e devolve polaridade, nota de 0 a 10 e justificativa em JSON. No site, o botão "Comparar com IA" mostra o resultado ao lado do modelo treinado.

| Sistema | F1 macro | Erro médio da nota | Respondidas |
|---|---:|---:|---:|
| Chutar a média das notas | — | 2,83 | 200 |
| TF-IDF (fora da dobra) | 0,791 | 1,80 | 200 |
| BERTimbau (fora da dobra) | 0,880 | 1,53 | 200 |
| LLM zero-shot (Gemini) | 0,930 | 0,91 | 172 |
| LLM few-shot (Gemini) | 0,925 | 1,00 | 173 |
| LLM zero-shot sem justificativa (Gemini) | 0,930 | 0,94 | 171 |
| LLM few-shot (Groq, reserva) | 0,915 | 1,04 | 200 |

**Leitura:** sem nenhum treino, o LLM supera os dois modelos treinados. A comparação completa é a da reserva no Groq, que respondeu as 200: F1 de 0,915 contra 0,880 do BERTimbau, e erro da nota de 1,04 contra 1,53. Ele também generaliza melhor para os outros autores (F1 de 0,93 contra 0,70 do TF-IDF). **Sem melhoria:** o few-shot não superou o zero-shot e gasta cerca de 60% mais tokens, e a justificativa não muda a polaridade. O LLM erra críticas benevolentes com nota baixa ("Um bom filme familiar, ainda que não seja brilhante", nota 4), que os modelos treinados acertam.

A cota diária do Gemini acabou nas duas execuções: cada variante respondeu cerca de 172 das 200 críticas, e as faltantes são todas de autores que não o principal. Ficaram sem resposta a repetição de 20 críticas (estabilidade) e os quatro casos da equipe; o mesmo comando com `--reuse ../data/sentimento/llm_2026-11-01` completa o que faltou quando a cota renovar.

## 3. Perguntas com RAG × busca híbrida

[ADR 0032](adr/0032-rag-perguntas-sobre-filmes.md) · [relatório](../data/rag/2026-11-01/report.md)

Para cada pergunta, a busca híbrida recupera 8 filmes (filtros do intérprete e títulos citados), junta até 2 trechos de crítica por filme, sem o autor, e o LLM responde em JSON citando os filmes por id. A conferência remove citações fora do contexto. A aba "Perguntar" mostra a resposta, os cartões dos filmes citados e o bloco "De onde veio a resposta".

| Medida (179 chamadas, sem falha) | Resultado |
|---|---|
| Precisão, busca híbrida sozinha (5 primeiros) | 0,57 |
| Precisão dos filmes citados, com 5 / 10 / 20 filmes no contexto | 0,95 / 0,90 / 0,93 (cerca de 2,7 filmes por resposta) |
| Revocação dentro do contexto (5 / 10 / 20) | 0,87 / 0,68 / 0,59 |
| Perguntas sem resposta no catálogo recusadas | 5 de 5 |
| Citações inventadas | 0 |
| Tentativas de *prompt injection* obedecidas | 0 de 3 (o sinal automático marcou 1, falso positivo: a recusa repete "gatos") |
| Perguntas de opinião recusadas: com / sem trechos de crítica | 1 de 10 / 10 de 10 |
| Tokens por resposta (média) | 2.264 de entrada e 220 de saída |

**Leitura:** a precisão dos citados não é comparável um a um com a precisão @5, porque o LLM cita menos filmes. O que muda é o tipo de saída: uma resposta que escolhe, explica e cita, em vez de uma lista. As **críticas são indispensáveis** para as perguntas de opinião e não alteram as de tema.

Exemplo (“Tem algum filme sobre luto e sobre lidar com a perda de alguém?”):

> Em Guardiões da Galáxia: Vol. 3 [F447365], Peter Quill se recupera da perda de Gamora. Em Avatar: Fogo e Cinzas [F83533], Jake Sully e Neytiri enfrentam a perda de seu filho mais velho. Além disso, em Midsommar [F530385], Dani está de luto após uma tragédia familiar. […]

Os três filmes citados estão no contexto e as frases vêm das sinopses, mas um leitor esperaria dramas sobre luto antes de Guardiões da Galáxia: a fidelidade não garante a utilidade. É isso que o julgamento humano mede, com dois juízes e a rubrica de [`config/rag/rubrica.md`](../config/rag/rubrica.md) (`python -m app.rag judgment-template` e `agreement`).

## Limitações

- **Avaliação na amostra:** todas as métricas são da amostra de 428 filmes; o catálogo do site não tem gabarito.
- **Anotações internas:** a primeira redação das 50 frases e das perguntas do RAG teve apoio de IA e foi revisada pela equipe; não houve avaliadores externos.
- **Cota e não determinismo:** com temperatura 0, até 5 de 50 interpretações mudaram entre duas execuções. A cota gratuita do Gemini acabou durante a avaliação do sentimento e o serviço devolveu 503 durante a do RAG; a reserva no Groq cobriu parte dessas falhas.
- **Fidelidade:** a conferência garante só que os filmes citados estão no contexto; a fidelidade de cada frase depende do julgamento humano, que ainda não tinha sido feito em 01/11/2026.

## Como executar

Comandos de avaliação e de reprodução sem rede em [como-executar.md](tecnico/como-executar.md#rag-aba-perguntar); a página "Sobre o projeto" lê os números de `frontend/dados/resultados.json`, gerado por [`coletar_resultados.py`](entregas/unidade-4/coletar_resultados.py).
