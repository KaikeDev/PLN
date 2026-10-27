# 0029 — Base de LLM por API gratuita: Gemini e Groq com saída estruturada, reserva, orçamento e replay (Unidade 4)

- Estado: Aceita
- Data: 2026-10-26

## Contexto

A Unidade 4 pede ao menos uma técnica avançada com LLM e um link público para o site. O grupo escolheu três técnicas, todas com LLM: interpretação da consulta, sentimento zero-shot e few-shot, e RAG ([specs 01 a 03](../entregas/unidade-4/README.md)). Também decidiu usar só **API gratuita**: não há orçamento para API paga, e um modelo local seria lento demais na CPU gratuita do servidor.

O plano gratuito impõe três restrições:

- a cota muda sem aviso e acaba;
- o site público pode esgotá-la;
- as respostas variam entre execuções.

O Jev (ADR 0019) já resolvia a reprodutibilidade gravando as respostas, mas tem porta própria, específica para decisões tipadas.

## Decisão

- **Pacote `app.llm`**, com a porta `LanguageModel.generate(LLMRequest) -> LLMResponse`. O pedido traz o modelo Pydantic da saída; quem chama recebe `data` já validado. As falhas são `LLMUnavailable` com `reason`: `cota`, `timeout`, `indisponivel`, `json_invalido`, `sem_chave` ou `orcamento`.
- **Provedores:** Gemini como principal (`gemini-flash-lite-latest`) e Groq como reserva (`openai/gpt-oss-20b`, com esforço de raciocínio baixo), na ordem de `config/llm/llm.json`. Um alias pode mudar de modelo com o tempo, por isso cada resposta grava o modelo exato que o provedor informa (`modelVersion` no Gemini, `model` no Groq).
- **Sem SDK:** os dois provedores são chamados por REST com `requests`, como o TMDB (ADR 0007). A chave vai só em cabeçalho (`x-goog-api-key` e `Authorization`), nunca na URL (ADR 0002). Erros 5xx são repetidos; o 429 não é repetido e vai direto para a reserva.
- **Saída estruturada:**
  - o Gemini recebe `responseSchema`, convertido do JSON Schema do Pydantic para o subconjunto que ele aceita;
  - o Groq usa o modo JSON, com o esquema nas instruções;
  - nos dois casos, a resposta é validada pelo Pydantic. Uma resposta fora do formato ganha uma nova tentativa, com o erro anexado; na segunda falha, vira `json_invalido`.
- **Pilha do site:** cache LRU → orçamento diário por propósito → reserva → saída estruturada sobre cada provedor. O cache fica por fora do orçamento, para que perguntas repetidas não gastem cota. O orçamento (`daily_budget`) fica abaixo da cota gratuita e zera à meia-noite UTC.
- **Reserva só para falhas de disponibilidade:** `json_invalido` e `orcamento` não passam para o outro provedor, porque não são falhas dele.
- **Replay:** `RecordingModel` grava cada resposta como registro determinístico, sem latência (ADR 0009); `ReplayModel` reavalia sem rede. Um pedido não gravado vira `indisponivel`, e `FallbackModel([ReplayModel, real])` retoma uma avaliação interrompida de onde parou.
- **Configuração e segredos:** `GEMINI_API_KEY` e `GROQ_API_KEY` como `SecretStr` em `backend/.env`. Só entram os provedores com chave; sem nenhuma, as funções com LLM respondem 503, e o resto do site funciona. A rota `/saude` informa provedores, temperatura e orçamento restante, nunca as chaves.
- **Privacidade:** ao LLM vão só dados públicos (sinopses, críticas sem o autor e o texto digitado). O plano gratuito do Gemini pode usar as entradas para melhorar o produto, e o site avisa para não digitar dados pessoais.
- **Verificação manual:** `python -m app.llm ping` faz uma chamada real a cada provedor com chave. Os testes e o CI não usam rede.

## Alternativas consideradas

- **API paga (Claude, GPT ou Gemini pago):** melhor qualidade e cota previsível, mas com custo por chamada e risco de cobrança por abuso no site público. Descartada pelo grupo.
- **Modelo local quantizado (llama.cpp ou Ollama):** sem custo e marcaria "modelos locais ou quantizados" no quadro. Mas na CPU gratuita do Hugging Face Spaces responderia em dezenas de segundos e seria mais fraco em português. Fica como trabalho futuro.
- **SDKs oficiais (`google-genai`, `groq`):** duas dependências a mais, com políticas de retry e de erro diferentes das do projeto, para chamadas que cabem em um POST.
- **Só um provedor:** a demonstração cairia inteira quando a cota acabasse.
- **Modo JSON sem esquema e sem validação:** respostas com campos faltando ou valores fora da lista chegariam às métricas e à tela.

## Consequências

- As três técnicas da Unidade 4 usam a mesma porta e são testadas com `FakeLanguageModel`, sem rede.
- O comportamento depende da cota gratuita do dia. O site degrada para as regras (interpretação) ou para os exemplos gravados (perguntas), e as avaliações ficam reproduzíveis pelas respostas gravadas.
- Com a temperatura 0, as respostas ainda podem variar entre execuções, e um alias pode passar a apontar para outro modelo. O que vale é o modelo exato gravado em cada resposta.
- O cache e o orçamento ficam na memória de um único processo; com mais processos, cada um teria o seu.
