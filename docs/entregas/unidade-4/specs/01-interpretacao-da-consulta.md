# Spec 01. Interpretação da consulta por LLM com saída estruturada

> **Estado: implementada em 26/10/2026** ([ADR 0030](../../../adr/0030-interpretacao-da-consulta-por-llm.md)). Few-shot no site, com reserva nas regras: acerto exato de 0,94 a 0,98 (regras: 0,44) e nenhum filtro inventado (regras: 11 de 50). Na busca, os filtros do LLM levam o MAP de 0,627 a 0,640. O tema separado pelo LLM ficou fora da busca, porque não melhorou a ordenação. As 50 frases foram redigidas com apoio de IA e revisadas pela equipe.

**Depende de:** 00 · **ADR:** 0030 · **Esforço:** 2 dias

## Objetivo

Trocar ou complementar as regras léxicas da busca (ADR 0005), que transformam a frase do usuário em filtros (gênero, gêneros excluídos, período e qualidade), por um LLM com **saída estruturada**, e **medir** se ele interpreta melhor.

A comparação é direta: os dois produzem o mesmo `ExtractedFilters`, nas mesmas frases anotadas.

## Por que esta técnica

As regras têm limites já documentados:

- "família aterrorizada por espíritos" filtra o gênero Família;
- paráfrases ("um filme que dá medo", "pra dar risada") não disparam gatilho;
- a acurácia de 12/12 foi medida em só 5 frases (ADR 0005).

O LLM entende paráfrase e contexto. Em troca, custa latência e cota e pode inventar filtros. É um caso claro para "comparar com o resultado anterior".

## Itens do enunciado atendidos

Quadro do item 1: LLM, prompt engineering e saídas estruturadas. Item 3, questões 2, 3 e 5. Comparação com os resultados anteriores.

## Dados: `config/busca/interpretacao.json` (anotar ANTES de rodar)

**50 frases** escritas pela equipe, cada uma com o gabarito:

```json
{"id": "familia_espiritos", "texto": "família aterrorizada por espíritos",
 "esperado": {"generos": ["Terror"], "generos_excluidos": [], "lancado_depois": null, "lancado_antes": null, "bem_avaliado": false},
 "categoria": "armadilha_lexica"}
```

Distribuição mínima por `categoria`, para a análise por tipo:

| Categoria | Qtd. | Exemplo |
|---|---:|---|
| `explicita` (as regras devem acertar) | 10 | "comédia dos anos 90" |
| `parafrase` | 10 | "algo que me faça rir", "filme pra não dormir à noite" |
| `negacao` | 8 | "terror sem ser sangrento demais", "nada de romance" |
| `periodo` | 8 | "da década passada", "não muito antigo", "lançado depois de Matrix" |
| `armadilha_lexica` | 8 | "família aterrorizada por espíritos", "Guerra nas Estrelas" (título com gatilho) |
| `sem_filtro` (tema puro) | 6 | "astronautas perdidos no espaço" → nenhum filtro |

- Os gêneros vêm da lista **fechada** dos 19 gêneros do TMDB (`genres.json`); o esquema do LLM usa um `enum` com esses nomes.
- As datas do gabarito seguem as convenções das regras (ADR 0005: "recente" = últimos 10 anos, "antigo" = mais de 25 anos). O prompt informa a data de hoje e essas convenções, para comparar coisas iguais.

## Desenho

### Porta e implementações

- Criar a porta `PreferenceExtractor` em `search/ports.py`: `extract(text) -> ExtractedFilters`. `FilterExtractor`, das regras, já cumpre o contrato.
- Novo `search/interpretation/llm_extractor.py` com `LLMFilterExtractor(model, genres)`:
  - pede ao LLM o esquema `{generos: [enum], generos_excluidos: [enum], lancado_depois: "AAAA-MM-DD"|null, lancado_antes: ...|null, bem_avaliado: bool, tema: str}`;
  - converte os nomes em IDs com o mesmo `_resolve` e `bem_avaliado` nos mesmos limiares das regras (nota ≥ 7 e ≥ 100 votos);
  - o campo `tema` é o texto **sem** os filtros ("máquinas" em "filme de ação sobre máquinas"). Ele substitui `strip_request` na busca por tema, e a avaliação mede esse uso à parte (abaixo).
- Novo `search/interpretation/hybrid_extractor.py` com `FallbackExtractor(llm, regras, timeout)`: tenta o LLM e, se der `LLMUnavailable` ou timeout (4 s), usa as regras. O resultado registra `origem: "llm" | "regras"`.

### Prompt (versionado em `config/busca/interpretacao_prompt.json`)

- Sistema: papel, data de hoje, lista de gêneros, convenções de período e qualidade, e a regra "na dúvida, não filtre" (preferir não filtrar a filtrar errado).
- Duas variantes, para o experimento de prompt engineering:
  - **`zero_shot`**: só as instruções;
  - **`few_shot`**: instruções e 6 exemplos resolvidos, **nenhum** deles entre as 50 frases de avaliação.

### No site

- `SearchService` recebe um `PreferenceExtractor`; `main.py` injeta o `FallbackExtractor` quando há LLM e as regras quando não há.
- `GET /pesquisa` ganha o parâmetro `interpretacao=auto|regras|llm` (padrão `auto`). O bloco `interpretacao` da resposta ganha o campo `origem`.
- Frontend: um selo "interpretado por IA" ou "interpretado por regras" ao lado dos filtros entendidos.
- O título exato continua tendo prioridade **antes** de chamar o LLM (ADR 0006): "Matrix" não gasta cota.

## Avaliação: `python -m app.search interpret-eval`

Saída em `data/interpretacao/<data>/`, com manifesto: `responses.jsonl`, `predictions.jsonl` (regras, LLM zero-shot, LLM few-shot e reserva), `metrics.json` e `report.md`. Aceita `--reuse`.

| Métrica | Como |
|---|---|
| Acerto exato da frase | Todos os campos iguais ao gabarito |
| F1 de gêneros incluídos e de excluídos | Micro, sobre as 50 frases |
| Acerto de período | Intervalo igual, com tolerância de 1 ano nas bordas |
| Acerto de "bem avaliado" | Booleano |
| **Filtro inventado** | Frases em que o sistema pôs um filtro que o gabarito não tem. É o erro mais caro, porque esconde filmes certos |
| Por categoria | Todas as métricas acima, separadas pelas 6 categorias |
| Custo | Latência mediana e p95, tokens médios, falhas de JSON e quedas para as regras |

**Efeito na busca:** nas 20 consultas anotadas (`config/busca/consultas.json`), na amostra de 428 filmes, comparar o MAP da busca por tema com a consulta preparada por `strip_request` e com o `tema` do LLM. Comparar com o MAP vigente de **0,627** (precisão @5 de 0,57; `docs/3-busca.md`). O 0,613 que ainda aparece no README e na `APRESENTACAO.md` é de antes da preparação da consulta (ADR 0025); a spec 06 corrige.

**Resultado esperado, a confirmar:** o LLM ganha em `parafrase` e `armadilha_lexica`, empata em `explicita` e pode perder em `periodo` (datas relativas). Qualquer que seja o resultado, ele vai para a página "Sobre".

## Testes (sem rede)

- `LLMFilterExtractor` com `FakeLanguageModel`: conversão para IDs, gênero fora do `enum` rejeitado, datas inválidas rejeitadas, `bem_avaliado` com os limiares das regras.
- `FallbackExtractor`: timeout e `LLMUnavailable` caem nas regras e marcam `origem`.
- Título exato não chama o LLM (contagem de chamadas = 0).
- O conjunto anotado é validado no carregamento: gêneros existem, datas no formato e ids únicos.
- Rota `/pesquisa` com `interpretacao=regras|llm|auto`.

## Critérios de aceite

- [ ] As 50 frases foram anotadas e commitadas **antes** do primeiro `interpret-eval` (o histórico do Git mostra a ordem).
- [ ] `report.md` traz a tabela de regras × zero-shot × few-shot por categoria, com exemplos de acerto e de erro de cada lado.
- [ ] O site funciona igual com o LLM fora do ar (queda para as regras visível no selo).
- [ ] `verify` da pasta de saída no CI; testes, `ruff` e `mypy` verdes.
- [ ] ADR 0030: o que foi medido, qual variante foi para o site e por quê, e o custo em latência.
