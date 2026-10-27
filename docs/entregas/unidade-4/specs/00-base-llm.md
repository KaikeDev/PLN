# Spec 00 — Base de LLM: porta, provedores gratuitos, saída estruturada e orçamento

> **Estado: implementada em 26/10/2026** ([ADR 0029](../../../adr/0029-base-de-llm-por-api-gratuita.md)). `ping` real em 26/10/2026: Gemini (`gemini-flash-lite-latest` → `gemini-3.5-flash-lite`, 1,1 s) e Groq (`openai/gpt-oss-20b`, 0,4 s) responderam no formato pedido.

**Depende de:** nada · **Bloqueia:** 01, 02, 03 · **ADR:** 0029 · **Esforço:** 1–2 dias

## Objetivo

Criar uma camada única para chamar um LLM, usada pelas três técnicas da Unidade 4. Ela devolve **JSON validado** contra um esquema, troca de provedor quando a cota acaba, grava as respostas para reavaliar sem gastar cota e impede que o site público esgote a cota gratuita.

## Itens do enunciado atendidos

- Quadro do item 1: "LLMs e modelos de linguagem" e "Prompt engineering e saídas estruturadas".
- Item 5: "informem o modelo, a modalidade de acesso (local/API) e as configurações relevantes". A configuração fica num arquivo versionado, e a rota `/saude` a expõe.

## Desenho

### Pacote `backend/src/app/llm/`

| Arquivo | Conteúdo |
|---|---|
| `ports.py` | `LanguageModel` (Protocol): `generate(request: LLMRequest) -> LLMResponse`. `LLMRequest`: `system`, `prompt`, `schema` (JSON Schema), `temperature`, `max_output_tokens`, `purpose` (`"interpretacao"`, `"sentimento"` ou `"rag"`). `LLMResponse`: `data` (dict já validado), `raw_text`, `provider`, `model`, `input_tokens`, `output_tokens`, `latency_ms`. `LLMUnavailable(RuntimeError)` com `reason` (`"cota"`, `"timeout"`, `"json_invalido"`, `"sem_chave"` ou `"orcamento"`) |
| `gemini.py` | Adaptador REST: `POST {base}/models/{model}:generateContent`, chave no cabeçalho `x-goog-api-key` (**nunca na URL**, conforme a ADR 0002), `generationConfig.responseMimeType = "application/json"` e `responseSchema` |
| `groq.py` | Adaptador REST compatível com OpenAI: `POST {base}/chat/completions`, `Authorization: Bearer`, `response_format` em modo JSON, com o esquema também no prompt |
| `structured.py` | Valida `raw_text` contra o esquema (`json.loads` seguido de validação com Pydantic). Uma única nova tentativa com a mensagem do erro anexada ("corrija o JSON"). Depois disso, `LLMUnavailable("json_invalido")` |
| `fallback.py` | `FallbackModel([primário, reserva])`: em `cota` ou `timeout`, tenta o seguinte e registra qual respondeu |
| `cache.py` | `CachedModel`: LRU em memória por `sha256(purpose, system, prompt, schema)` (`LLMRequest.key`), usado pelo site. Na avaliação, quem cuida da reprodutibilidade é o replay em disco (abaixo) |
| `budget.py` | `DailyBudget`: contador global por dia (UTC) e por `purpose`. Acima do limite, `LLMUnavailable("orcamento")`. Estado em memória (um único processo uvicorn, spec 04) |
| `replay.py` | `RecordingModel` grava cada par (pedido, resposta) em `responses.jsonl`; `ReplayModel` lê esse arquivo e responde sem rede, falhando se o pedido não existir. É o `--reuse` do Jev, generalizado |
| `config.py` | Lê `config/llm/llm.json` com `app.shared.validation` (estrito, sem campos desconhecidos) |

Usar o cliente `requests` com a política de retry existente (ADR 0007). O 429 do provedor vira `LLMUnavailable("cota")` depois das tentativas.

### Configuração `config/llm/llm.json`

```json
{
  "providers": [
    {"name": "gemini", "model": "<id exato e versionado>", "base_url": "https://generativelanguage.googleapis.com/v1beta", "timeout_seconds": 20},
    {"name": "groq",   "model": "<id exato>",             "base_url": "https://api.groq.com/openai/v1",               "timeout_seconds": 20}
  ],
  "temperature": 0.0,
  "max_output_tokens": {"interpretacao": 300, "sentimento": 200, "rag": 700},
  "daily_budget": {"interpretacao": 400, "sentimento": 150, "rag": 250},
  "request_interval_seconds": 4.0
}
```

- **Modelos:** fixar o identificador exato no dia da implementação, preferindo um modelo "flash/lite" do Gemini e um modelo instruído de 70B ou equivalente no Groq. Conferir no painel de cada provedor a cota gratuita atual (pedidos por minuto e por dia) e pôr o `daily_budget` **abaixo** dela.
- `request_interval_seconds` vale só para os comandos de avaliação em lote, para respeitar o limite por minuto.

### Configurações e segredos (`settings.py` e `.env.example`)

Acrescentar `gemini_api_key: SecretStr | None`, `groq_api_key: SecretStr | None` e `llm_config: Path`. Sem nenhuma chave, as funções com LLM respondem **503 com mensagem clara**, e o restante do site funciona (mesmo padrão do extra `semantico`).

### Composição em `main.py`

`_load_llm(settings)` monta `CachedModel(DailyBudget(FallbackModel([StructuredModel(provedor), ...])))`, com o cache por fora para que repetições não gastem orçamento, e guarda o resultado em `app.state.llm` (`LLMStack`). Na rota `/saude`, incluir:

```json
"llm": {"provedores": ["gemini:<modelo>", "groq:<modelo>"], "temperatura": 0.0, "orcamento_restante": {"rag": 231, "...": 0}}
```

## Privacidade e uso responsável

- **Enviar ao LLM só dados públicos:** sinopses, críticas públicas sem o autor (só `author_key` em hash, que **não** vai no prompt) e o texto que o visitante digitou.
- O plano gratuito do Gemini pode usar as entradas para melhorar o produto. Por isso a página avisa: "não digite dados pessoais" (spec 05).
- Não registrar o texto das perguntas junto com o IP nos logs.

## Testes (sem rede)

- `FakeLanguageModel` em `tests/fakes.py`, com respostas programáveis e contagem de chamadas.
- Adaptadores Gemini e Groq: montar o corpo do pedido (esquema, temperatura, chave no cabeçalho e não na URL) com uma `Session` falsa; ler respostas reais gravadas como fixture (sem a chave).
- `structured`: JSON válido, JSON quebrado que a nova tentativa corrige, JSON que viola o esquema duas vezes.
- `FallbackModel`: o 429 no primário passa ao reserva; erro de esquema **não** passa (é falha do prompt, não do provedor).
- `DailyBudget`: limite por propósito e virada do dia, com relógio injetado.
- `ReplayModel`: pedido conhecido devolve a resposta gravada; pedido desconhecido falha.
- `test_api.py`: `/saude` mostra o bloco `llm` sem chaves; sem chave, as rotas de LLM respondem 503.

## Critérios de aceite

- [ ] `uv run --frozen python -m app.llm ping` faz uma chamada real a cada provedor configurado e imprime provedor, modelo, latência e tokens (comando manual, fora do CI).
- [ ] Uma resposta com JSON inválido nunca chega ao chamador sem validação.
- [ ] Nenhuma chave aparece em URL, log, exceção, `repr`, manifesto nem em `responses.jsonl`; um teste confere isso com uma chave falsa marcada.
- [ ] O CI passa sem chaves e sem rede; `ruff`, `mypy` e os testes ficam verdes.
- [ ] A ADR 0029 registra provedores, modelos, temperatura, orçamento, por que não há SDK e por que não há modelo local, e entra em `docs/adr/README.md` e `resumo.md`.

## Riscos

| Risco | Mitigação |
|---|---|
| A cota gratuita muda ou acaba durante a mostra | Reserva no Groq, orçamento abaixo da cota, cache e exemplos pré-gravados no site (spec 05) |
| Um modelo é descontinuado | Identificador exato no arquivo de configuração e no manifesto; trocar exige só editar o JSON e regravar as avaliações |
| Respostas diferentes a cada execução | `temperature = 0`, respostas brutas gravadas e reavaliação com `ReplayModel` |
