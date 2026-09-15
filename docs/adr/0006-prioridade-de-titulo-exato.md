# 0006 — Modo automático prioriza título exato da primeira página

- Estado: Aceita
- Data: 2026-09-14 (decisão original na Etapa 1)

## Contexto

Títulos podem conter gatilhos de preferência: "Guerra nas Estrelas" contém "guerra". Sem prioridade para o título, a pesquisa trataria o pedido como descoberta do gênero Guerra.

## Decisão

No modo `auto`:

1. Buscar por título.
2. Se algum filme da **primeira página** tiver título localizado ou original igual ao texto (após normalização), responder no modo `titulo`.
3. Caso contrário, extrair preferências e usar `descoberta` quando houver alguma.
4. Sem preferências, responder no modo `titulo` com os resultados da busca.

A verificação usa sempre a primeira página, para que o modo não mude ao paginar. Na primeira página, os mesmos resultados são reaproveitados (uma requisição); nas demais, a primeira página vem do cache (ADR 0007). Os modos explícitos `titulo` e `descoberta` resolvem ambiguidades restantes.

## Alternativas consideradas

- Decidir pela página pedida: o modo poderia mudar entre páginas da mesma pesquisa.
- Exigir que o cliente informe o modo nas páginas seguintes: muda o contrato da API.

## Consequências

- Títulos alternativos e textos com contexto extra ("quero ver Matrix") não são reconhecidos como título exato.
