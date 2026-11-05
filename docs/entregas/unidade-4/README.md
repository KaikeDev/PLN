# Trabalho da Unidade 4: Mostra Virtual de PLN

Entrega da etapa final, na **Modalidade B (aplicação web)**. Enunciado: [`PLN_Trabalho_Unidade_4_Mostra_Virtual.pdf`](PLN_Trabalho_Unidade_4_Mostra_Virtual.pdf).

## Onde está cada item do enunciado

| Item do enunciado | Onde está |
|---|---|
| **Link público** da aplicação | *a preencher depois da publicação ([passos](../../../deploy/space/README.md))* (Hugging Face Spaces, [ADR 0033](../../adr/0033-publicacao-no-hugging-face-spaces.md)); reserva estática da página "Sobre": *GitHub Pages com `frontend/`, a configurar* |
| **1. Quadro de técnicas** | [docs/9-tecnicas-avancadas.md](../../9-tecnicas-avancadas.md#quadro-de-técnicas-item-1-do-enunciado) e seção 6 da página "Sobre o projeto" (o mesmo texto, copiado por [`coletar_resultados.py`](coletar_resultados.py)) |
| 1. Técnica avançada **implementada e comparada** com o anterior, inclusive sem melhoria | Interpretação da consulta (regras × LLM, [ADR 0030](../../adr/0030-interpretacao-da-consulta-por-llm.md)), sentimento (TF-IDF × BERTimbau × LLM, [ADR 0031](../../adr/0031-sentimento-com-llm.md)) e RAG (busca híbrida × RAG, [ADR 0032](../../adr/0032-rag-perguntas-sobre-filmes.md)); resumo em [docs/9-tecnicas-avancadas.md](../../9-tecnicas-avancadas.md) e na seção 7 da página "Sobre" |
| B.1 Título, autores e descrição | Cabeçalho de todas as páginas (`frontend/index.html`, `frontend/sobre.html`) |
| B.2 Problema e técnicas de PLN | Seções 1 e 4 da página "Sobre" e o bloco "Como usar e o que está por trás" de cada aba |
| B.3 Interface funcional | Abas Buscar filmes, Perguntar (RAG), Classificar sinopse e Analisar crítica; ficha do filme com entidades e parecidos |
| B.4 Resultados com exemplos de entrada e saída | Botões de exemplo em todas as abas; exemplos de entrada e saída na seção 7 da página "Sobre"; respostas gravadas do RAG (`frontend/dados/exemplos_rag.json`) |
| B.5 Dados, metodologia, tecnologias e limitações | Seções 3, 4, 9 e 11 da página "Sobre" |
| B.6 Instruções de uso | Blocos "Como usar" de cada aba; [rodar-o-site.md](../../tecnico/rodar-o-site.md) para rodar localmente |
| B. Restrições técnicas, custos e dependências externas | Seção 10 da página "Sobre" |
| **3. As seis questões** | Seção 8 da página "Sobre", uma por título (8.1 a 8.6) |
| 3.5 Qualidade verificada | [validacao.md](../../tecnico/validacao.md), relatórios em `data/` e testes em `backend/tests/` |
| 4. Repositório e README | [README](../../../README.md), com link, tecnologias, instruções e uso de IA |
| 5. Amostra menor explicitada | Seção 3 da página "Sobre" ("as métricas foram medidas na amostra menor") |
| 5. Uso de IA generativa | Seção "Uso de IA generativa" do README e seção 12 da página "Sobre" |
| 5. LLM no processamento: modelo, acesso e configurações | Seção 11 da página "Sobre", `config/llm/llm.json` e a rota `/saude` |
| 5. Sem dados sensíveis ou credenciais | Chaves só em `backend/.env` e nos segredos do Space; críticas sem autor no prompt; ver o checklist abaixo |
| 5. Acessibilidade e funcionamento | Relatórios do Lighthouse em [`docs/tecnico/acessibilidade/`](../../tecnico/acessibilidade/) e a seção da Unidade 4 em [validacao.md](../../tecnico/validacao.md) |

## Checklist antes da apresentação

| Item | Situação |
|---|---|
| Quadro igual no repositório e na página | Atendido. Garantido por teste (`test_resultados.py`) |
| Três comparações com números, inclusive as sem melhoria | Atendido. Interpretação e RAG completas; sentimento: ver a ADR 0031 |
| B.1 a B.6, custos e dependências | Atendido |
| Seis questões com número ou exemplo | Atendido |
| Link público abre de outra rede e de um celular | Pendente. Depende da publicação (passos em [`deploy/space/README.md`](../../../deploy/space/README.md)) |
| Memória, arranque a frio e tamanho da imagem medidos no Space | Pendente. Depois da publicação; registrar em [validacao.md](../../tecnico/validacao.md) |
| Branch mesclada na `main` e CI verde | Pendente |
| **Token antigo do TMDB (commit `a09a21c`) revogado** no painel do TMDB | Pendente |
| Contas do Gemini e do Groq sem cartão (ou com limite de gasto zero) | Pendente. Conferir |
| `git ls-files -ci --exclude-standard` vazio | Atendido |
| Julgamento das respostas do RAG pelos dois juízes | Pendente. `python -m app.rag judgment-template` e `agreement` ([como-executar.md](../../tecnico/como-executar.md)) |
| Teste manual de cada aba no link público, em celular e computador | Pendente |
| Space acordado 10 minutos antes; reservas (página estática e vídeo) testadas | Pendente. No dia |

## Documentos da entrega

- [docs/9-tecnicas-avancadas.md](../../9-tecnicas-avancadas.md): quadro, as três técnicas, avaliação, exemplos e limitações.
- ADRs da Unidade 4: [0029](../../adr/0029-base-de-llm-por-api-gratuita.md) (base de LLM), [0030](../../adr/0030-interpretacao-da-consulta-por-llm.md) (interpretação), [0031](../../adr/0031-sentimento-com-llm.md) (sentimento), [0032](../../adr/0032-rag-perguntas-sobre-filmes.md) (RAG), [0033](../../adr/0033-publicacao-no-hugging-face-spaces.md) (publicação) e [0034](../../adr/0034-paginas-do-site-e-sobre-o-projeto.md) (páginas).
- [coletar_resultados.py](coletar_resultados.py): gera `frontend/dados/resultados.json`, de onde a página "Sobre" lê todos os números.
- [specs/](specs/): o planejamento em sete specs, mantido como histórico.

---

# Histórico: planejamento de 26/10/2026

Planejamento da etapa final: o que o enunciado pede, o que o projeto já tem, o que falta e em que ordem fazer. A implementação está dividida em **sete specs**, cada uma entregável sozinha, com critérios de aceite verificáveis.

**Decisões do grupo (26/10/2026):**

| Decisão | Escolha |
|---|---|
| Modalidade | **B (aplicação web)**: o site que já existe, publicado com link público, com uma aba nova de perguntas (RAG) e uma página "Sobre o projeto" |
| Acesso ao LLM | **API gratuita**: Gemini como principal e Groq como reserva, atrás de uma porta única. Sem modelo local |
| Técnicas da Unidade 4 | **RAG** sobre sinopses e críticas · **interpretação da consulta por LLM** com saída estruturada · **sentimento zero-shot e few-shot por LLM** |

---

## 1. O enunciado contra o projeto atual

| Item do enunciado | Situação hoje | Spec |
|---|---|---|
| **1. Quadro de técnicas avançadas** preenchido | Falta. Não existe. O Jev (Aula 8) já é um LLM com decisões estruturadas, mas não está registrado como técnica da Unidade 4 | [06](specs/06-documentacao-e-entrega.md), [05](specs/05-paginas-do-site.md) |
| 1. Ao menos uma abordagem avançada **implementada e justificada** | Falta | [01](specs/01-interpretacao-da-consulta.md), [02](specs/02-sentimento-com-llm.md), [03](specs/03-rag-perguntas-sobre-filmes.md) |
| 1. **Comparar com os resultados anteriores**, inclusive sem melhoria | Falta | 01 (regras × LLM), 02 (TF-IDF/BERTimbau × LLM), 03 (busca híbrida × RAG) |
| B.1 Título, autores e descrição **na página** | Falta. O cabeçalho diz "API de Filmes (TMDB)", sem autores | [05](specs/05-paginas-do-site.md) |
| B.2 Problema e técnicas de PLN **na página** | Parcial. Só os rodapés das abas | 05 |
| B.3 Interface funcional | Atendido. Busca, ficha, parecidos, classificação, sentimento, entidades. **Só roda localmente** | [04](specs/04-publicacao-online.md) |
| B.4 Resultados compreensíveis com exemplos de entrada e saída | Parcial. Há botões "Usar um exemplo" em duas abas | 05, 03 |
| B.5 Dados, metodologia, tecnologias e limitações **na página** | Falta. Estão em `docs/`, não no site | 05 |
| B.6 Instruções de uso | Parcial. Textos de ajuda curtos | 05 |
| B. Restrições técnicas, **custos e dependências externas** explícitos | Falta | 05 |
| **3. As seis questões críticas** respondidas | Falta. `APRESENTACAO.md` tem limitações, mas não responde às seis | 05, 06 |
| 3.5 Qualidade verificada com testes, métricas e exemplos | Atendido para as tarefas anteriores; falta para as novas | 01, 02, 03 |
| **4. Link público** da página | Falta. API presa em `127.0.0.1` | [04](specs/04-publicacao-online.md) |
| 4. Repositório com código, documentação e resultados | Atendido | — |
| 4. **README atualizado** com descrição, tecnologias, execução e links | Parcial. Desatualizado: diz "quatro tarefas", não tem link público nem a Unidade 4 | 06 |
| 4. Quadro do item 1 no repositório | Falta | 06 |
| 5. Continuidade com a base do semestre | Atendido. Mesma amostra `tmdb_2026-09-12`, mesmo catálogo e mesmas críticas | todas |
| 5. **Amostras menores explicitadas** | Parcial. Amostra de 428 × catálogo de 5.525 explicado em `docs`, não no site | 05 |
| 5. **Uso de IA generativa** declarado (fornecedor, modelo, prompts) | Parcial. Só na Unidade 3 | 06 |
| 5. **LLM no processamento:** modelo, acesso e configurações | Parcial. Só o Jev | 00, 05 |
| 5. Sem dados sensíveis, chaves ou credenciais | Parcial. `.env` ignorado e críticas com `author_key` em hash; **o token do commit `a09a21c` (ADR 0002) precisa estar revogado** antes de divulgar o link | 04, 06 |
| 5. **Acessibilidade e funcionamento** verificados | Falta. Sem verificação registrada | 05, 06 |

**Resumo:** a base técnica das unidades 1 a 3 cobre bem os critérios de domínio e de análise. O que falta para a nota é (1) a técnica avançada com comparação, (2) o link público e (3) o conteúdo explicativo dentro do próprio site.

---

## 2. A arquitetura atual é a melhor opção?

**Sim para o núcleo. Para a publicação, faltam seis ajustes.** Não vale a pena reescrever.

### O que manter

| Escolha | Por que continua sendo a certa |
|---|---|
| Código organizado por tarefa, com portas e adaptadores (ADR 0004, 0022) | O LLM entra como **mais um adaptador** atrás de uma porta, como o Jev entrou. Os testes seguem com dublês e sem rede |
| Saídas imutáveis com manifesto e `verify` (ADR 0009) | É o que permite reavaliar respostas de LLM, que não são determinísticas, sem gastar cota: grava-se a resposta bruta e reavalia-se com `--reuse`, como no Jev |
| FastAPI + HTML/JS sem build | Leve, já testado, com CSP estrita. Streamlit ou Gradio jogariam fora a interface e os testes da API sem ganho para a nota |
| `requests` com retry (ADR 0007) | Gemini e Groq têm API REST; não precisa de SDK novo. O mesmo retry trata o 429 da cota gratuita |
| Modelos com revisão fixada e sem pickle (ADR 0011) | Continua valendo; o classificador e o sentimento seguem treinando na inicialização |

### O que mudar

| # | Problema | Ajuste | Spec |
|---|---|---|---|
| 1 | Dois processos (API + `http.server`), CSP e `api-base` fixos em `127.0.0.1:8000` | A API serve também o `frontend/` (**mesma origem**): um processo, um link, sem CORS. O modo local de dois terminais continua funcionando | 04 |
| 2 | No Linux, o `uv.lock` instala o PyTorch com CUDA (`nvidia-*`, vários GB) | Índice **CPU** do PyTorch para Linux em `[tool.uv.sources]`; a imagem cai para cerca de 1 GB de PyTorch | 04 |
| 3 | O catálogo de 5.525 filmes é gerado na máquina e fica fora do Git | Gerar uma vez, publicar como **Dataset do Hugging Face** com o manifesto, e baixar e verificar (`verify`) no build da imagem | 04 |
| 4 | O limite por IP usa `request.client.host`; atrás do proxy do servidor, todos os visitantes compartilhariam um IP | `uvicorn --proxy-headers` e um limite **mais estrito para as rotas com LLM**, mais um **orçamento diário global** de chamadas | 00, 04 |
| 5 | A API só sobe em `127.0.0.1` (ADR 0002) | No contêiner, `0.0.0.0`, com as defesas acima. A ADR 0002 é parcialmente substituída por uma ADR nova | 04 |
| 6 | Nenhuma abstração para LLM genérico (o Jev tem porta própria e específica) | Pacote `app/llm/` com a porta `LanguageModel`, adaptadores Gemini e Groq, reserva automática, cache e orçamento | 00 |

### Onde hospedar

| Opção | Memória | Serve PyTorch + spaCy? | Veredito |
|---|---|---|---|
| **Hugging Face Spaces (Docker, CPU gratuita)** | 16 GB | Sim | **Escolhida.** Gratuita, aceita segredos e tem link público estável. Dorme após inatividade; acorda em cerca de 1 minuto |
| Render / Railway (grátis) | 512 MB | Não | Sem memória para o MiniLM e o spaCy |
| Vercel / Netlify (serverless) | — | Não | Limite de tamanho de função e arranque a frio |
| GitHub Pages | — | Só estático | Serve só a Modalidade A. Fica como **link de reserva** para a página "Sobre" (spec 04) |

Atualização de 05/11/2026: o Space Docker passou a exigir o plano PRO (US$ 9 por mês), e o grupo decidiu pagá-lo ([ADR 0033](../../adr/0033-publicacao-no-hugging-face-spaces.md)).

---

## 3. As specs e a ordem

```
          ┌─► 01 Interpretação da consulta ─┐
00 Base ──┼─► 02 Sentimento com LLM ────────┼─► 05 Páginas do site ─► 06 Documentação e entrega
  LLM     └─► 03 RAG ───────────────────────┘          ▲
                                                       │
04 Publicação online (começa já, em paralelo) ─────────┘
```

| Spec | O que entrega | Depende de | Esforço estimado |
|---|---|---|---|
| [00. Base de LLM](specs/00-base-llm.md) | Porta `LanguageModel`, Gemini + Groq, saída estruturada validada, cache e replay, orçamento | — | 1–2 dias |
| [01. Interpretação da consulta por LLM](specs/01-interpretacao-da-consulta.md) | Filtros extraídos por LLM × regras léxicas, em 50 frases anotadas; uso no site com reserva nas regras | 00 | 2 dias |
| [02. Sentimento com LLM](specs/02-sentimento-com-llm.md) | Zero-shot × few-shot × TF-IDF × BERTimbau nas mesmas 200 críticas | 00 | 1–2 dias |
| [03. RAG: perguntas sobre filmes](specs/03-rag-perguntas-sobre-filmes.md) | Rota `/pergunta`, aba "Perguntar", citações verificadas e avaliação nas 20 consultas | 00 | 3 dias |
| [04. Publicação online](specs/04-publicacao-online.md) | Docker, Hugging Face Spaces, mesma origem, PyTorch CPU, catálogo via Dataset, link público | Nenhuma (as rotas de LLM entram quando prontas) | 2 dias |
| [05. Páginas do site](specs/05-paginas-do-site.md) | Título e autores, página "Sobre" com metodologia, resultados, quadro, seis questões, custos, uso de IA e acessibilidade | 01–03 para os números | 2 dias |
| [06. Documentação e entrega](specs/06-documentacao-e-entrega.md) | README, quadro no repositório, ADRs, CI, números conferidos, roteiro da mostra e checklist final | todas | 1 dia |

**Por que a 04 começa já:** o link público é obrigatório e é o maior risco (build da imagem, memória, segredos). Publicar primeiro o site **atual** deixa os problemas de infraestrutura resolvidos antes de chegarem as funções novas.

### Sugestão de divisão em quatro pessoas

| Pessoa | Specs |
|---|---|
| 1 | 00 → 03 (RAG, a parte mais longa) |
| 2 | 04 (publicação) → 06 |
| 3 | 01 (interpretação da consulta) → metade da 05 (conteúdo de resultados) |
| 4 | 02 (sentimento) → metade da 05 (layout, acessibilidade) |

A pessoa 1 entrega a 00 primeiro; até lá, 01 e 02 podem escrever os conjuntos anotados e os prompts, que **não dependem de código**.

### Regras que valem para todas as specs

- **Anotar antes de rodar.** Frases, críticas e perguntas de avaliação são escritas e rotuladas antes de qualquer chamada ao LLM, como foi feito com as 20 consultas da busca.
- **Grava a resposta bruta, reavalia sem gastar cota.** Toda avaliação com LLM salva `responses.jsonl` e aceita `--reuse`, no padrão do Jev.
- **Resultado sem melhoria também entra** (exigência do enunciado). Nenhuma spec é "falha" porque o LLM perdeu para o TF-IDF; é um achado.
- **Testes sem rede:** cada módulo novo ganha dublês em `tests/fakes.py`; o CI não chama LLM.
- **Uma ADR por decisão** (0029 em diante), conforme a ADR 0001.
- **Nada de chave no Git:** `GEMINI_API_KEY` e `GROQ_API_KEY` só em `backend/.env` e nos segredos do Space.
