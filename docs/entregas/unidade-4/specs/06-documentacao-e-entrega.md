# Spec 06 — Documentação, quadro de técnicas e entrega

**Depende de:** todas · **Esforço:** 1 dia

## Objetivo

Fechar os itens 4 e 5 do enunciado no repositório e conferir, item por item, que nada ficou de fora antes da apresentação.

## 1. Quadro de técnicas (item 1): `docs/9-tecnicas-avancadas.md`

Rascunho a completar com os números finais. A versão final aparece **igual** no repositório e na página "Sobre" (spec 05).

| Tecnologia ou abordagem | Utilizada? | Aplicação ou justificativa |
|---|---|---|
| LLMs e modelos de linguagem | **Sim** | Gemini (principal) e Groq (reserva), por API gratuita, em três tarefas: RAG, interpretação da consulta e sentimento. Também o Jev (TypeSafe AI) na classificação de gênero (Aula 8). Os modelos de linguagem pré-treinados MiniLM e BERTimbau sustentam as representações desde a Etapa 2 |
| Prompt engineering e saídas estruturadas | **Sim** | Saída em JSON com esquema (`enum` de gêneros, datas, nota de 0 a 10, citações), validada com Pydantic e com uma nova tentativa. Experimentos zero-shot × few-shot (specs 01 e 02) e com e sem justificativa (spec 02). Prompts versionados em `config/` |
| RAG e recuperação de informações | **Sim** | Aba "Perguntar": a busca híbrida já avaliada (MAP de 0,627) recupera sinopses e trechos de críticas; o LLM responde citando os filmes, e as citações são conferidas contra o contexto. Avaliado com as 20 consultas anotadas e 30 perguntas com julgamento duplo |
| Agentes e integração com ferramentas | **Não** | O RAG com etapas fixas resolve as perguntas do projeto com custo de 1 chamada. Um agente escolheria entre busca, ficha, parecidos e sentimento, mas faria várias chamadas por pergunta (incompatível com a cota gratuita) e seria mais difícil de avaliar com o gabarito que temos. *Integração com ferramentas* existe no sentido de API: o site integra TMDB, LLM e os modelos locais |
| Modelos locais ou quantizados | **Parcial** | **Locais, sim:** MiniLM, BERTimbau, word2vec NILC e spaCy rodam na máquina, sem API, com revisão fixada. **Quantizados, não:** um LLM local quantizado foi considerado e descartado para a demonstração, porque na CPU gratuita do servidor seria lento demais e mais fraco em português. Fica como trabalho futuro |
| Processamento multimodal | **Não** | O problema é textual. Os pôsteres do TMDB estão disponíveis e aparecem no site, mas não foram processados. Pôster + sinopse (ex.: CLIP) fica como trabalho futuro |
| Outras técnicas avançadas de PLN | **Sim** | Busca híbrida (TF-IDF + embedding de sentença) com preparação da consulta; NER e extração de relações por dependências (spaCy); análise de sentimentos com teste de generalização por autor; classificação multirrótulo; comparação sistemática de 8 representações em 5 tarefas |

## 2. README (item 4)

- No topo: **link público** (com destaque), link de reserva (GitHub Pages) e o vídeo da demonstração.
- Intro corrigida: hoje diz "**quatro** tarefas" e "um site usa a busca, a recomendação e a classificação". Atualizar para as oito tarefas e as funções novas.
- Nova linha 9 na tabela de tarefas: "Técnicas avançadas com LLM (Unidade 4)", com resultado principal, documento e código.
- **Corrigir o MAP da busca: 0,613 → 0,627** (vigente desde a ADR 0025; `docs/3-busca.md`), também na `APRESENTACAO.md`.
- Seção "Tecnologias" (o enunciado pede no README): linguagem, bibliotecas, modelos com versão, LLM (provedor, modelo, acesso por API e temperatura) e hospedagem.
- Seção "Como executar": acrescentar `GEMINI_API_KEY` e `GROQ_API_KEY` (opcionais) e o comportamento sem elas.
- Link para o quadro de técnicas e para `docs/entregas/unidade-4/`.

## 3. Outros documentos

| Arquivo | Atualização |
|---|---|
| `docs/9-tecnicas-avancadas.md` | Documento da tarefa no padrão de `docs/1…8`: quadro, as três técnicas, avaliação, exemplos e limitações |
| `APRESENTACAO.md` | Seção da Unidade 4; **corrigir números velhos** ("111 testes" → contagem atual; "22 ADRs" → contagem atual; MAP 0,613 → 0,627); roteiro da demonstração com a aba "Perguntar" e o link público |
| `docs/tecnico/arquitetura.md` | Pastas `llm/` e `rag/`, a porta `PreferenceExtractor`, o diagrama de dependências e o fluxo de uma pergunta |
| `docs/tecnico/como-executar.md` e `rodar-o-site.md` | Comandos novos (`app.llm ping`, `interpret-eval`, `llm-eval`, `app.rag eval` e `verify`); chaves opcionais; publicação |
| `docs/tecnico/validacao.md` | O que foi medido nas specs 01 a 04; memória e arranque no Space; relatórios de acessibilidade |
| `docs/tecnico/decisoes.md` | Limitações novas (cota, não determinismo, fidelidade) |
| `docs/adr/` | 0029 a 0034 nos arquivos, no índice `README.md` e em `resumo.md` (com a ADR 0002 marcada como parcialmente substituída pela 0033) |
| `.gitignore` | Exceções para as pastas oficiais novas em `data/` (`interpretacao/`, `sentimento/llm_*`, `rag/`), conforme a ADR 0016 |
| `docs/entregas/unidade-4/README.md` | Trocar o plano pelo índice da entrega (link, quadro, documentos e uso de IA), mantendo as specs como histórico |

## 4. CI (`.github/workflows/ci.yml`)

- `verify` das novas pastas de dados (`interpretacao`, `sentimento/llm_*` e `rag`).
- Testes novos sem rede (já exigidos nas specs).
- `node --check` em todos os `.js` do `frontend/`.
- Workflow manual `deploy-space.yml` (spec 04).

## 5. Uso de IA generativa (item 5)

Seção no README e na página "Sobre":

- **Fornecedor e modelo:** Anthropic, Claude Opus 5.5, pelo Claude Code (extensão do VS Code).
- **Usos:** planejamento (estas specs), código, testes, documentação, páginas do site e marcação inicial de anotações, **sempre revisada pela equipe**. Dizer quais anotações foram feitas só pela equipe: as frases da spec 01, as perguntas da spec 03 e os julgamentos de fidelidade.
- **Principais prompts:** guardar 5 a 10 prompts representativos em `docs/entregas/unidade-4/prompts-ia.md`.
- **Separar** o uso de IA como **ferramenta de desenvolvimento** (Claude) do uso de LLM **no processamento** (Gemini e Groq, com modelo e configurações). O enunciado pede os dois.

## 6. Checklist final, antes da apresentação

| Item do enunciado | Conferência |
|---|---|
| 1 — Quadro | [ ] No repositório e na página, iguais |
| 1 — Comparação com o anterior | [ ] Três comparações com números, inclusive as sem melhoria |
| 2B.1 a 2B.6 | [ ] Título e autores; problema e técnicas; interface; exemplos; dados, metodologia e limitações; instruções |
| 2B — Custos e dependências externas | [ ] Seção 10 da página "Sobre" |
| 3.1 a 3.6 | [ ] Seis títulos na página, cada resposta com número ou exemplo |
| 4 — Link público | [ ] Abre de outra rede e de um celular; o indicador fica verde |
| 4 — Repositório e README | [ ] Branch mesclada na `main`; README com link, tecnologias e instruções |
| 5 — Amostra menor explicitada | [ ] Seção 3 da página "Sobre" |
| 5 — IA generativa e LLM declarados | [ ] Seções 11 e 12 |
| 5 — Sem segredos | [ ] Token antigo revogado; `git ls-files -ci --exclude-standard` vazio; nenhuma chave no Space nem nas imagens |
| 5 — Acessibilidade e funcionamento | [ ] Relatórios do Lighthouse e do axe; teste manual de cada aba no link público |
| Demonstração | [ ] Space acordado 10 minutos antes; roteiro da `APRESENTACAO.md` ensaiado; reservas (GitHub Pages e vídeo) testadas |

## Critérios de aceite

- [ ] Toda linha do checklist marcada.
- [ ] Nenhum número diverge entre o README, a `APRESENTACAO.md`, `docs/9-…` e a página "Sobre". Na página, os números vêm de `resultados.json`; nos documentos, conferir com uma busca pelos números antigos (`0,613`, `111 testes`, `22 ADRs`).
- [ ] CI verde na `main`.
