# Spec 02 — Sentimento com LLM: zero-shot e few-shot × modelos treinados

> **Estado: implementada; avaliação parcial em 26/10/2026.** Amostra e prompts commitados antes das chamadas (`1880036`). A primeira execução ([`data/sentimento/llm_2026-10-26`](../../../../data/sentimento/llm_2026-10-26/report.md)) parou na **cota diária do Gemini** (cerca de 500 chamadas por dia no plano gratuito, somando as avaliações do dia): as três variantes no Gemini responderam 86 a 87 das 200 críticas, e a reserva no Groq, todas. Nas 86 críticas respondidas por todas, o LLM zero-shot teve F1 de 0,94 e erro da nota de 0,91, contra 0,91 e 1,58 do BERTimbau e 0,86 e 1,59 do TF-IDF. **Pendente:** completar com `--reuse` depois que a cota renovar, escolher a variante e escrever a ADR 0031.

**Depende de:** 00 · **ADR:** 0031 · **Esforço:** 1–2 dias

## Objetivo

Classificar a polaridade e prever a nota das críticas do TMDB com um LLM **sem treino** e comparar, **nas mesmas críticas**, com o TF-IDF (F1 macro de 85,6%) e o BERTimbau (86,7%; nota com erro médio de 1,33) da Aula 9 (ADR 0026). É a continuação natural da comparação Jev × TF-IDF feita na Aula 8.

## Por que esta técnica

- O experimento já tem rótulos sem anotação manual (a nota do autor) e **predições fora da dobra** gravadas para as oito representações (`data/sentimento/criticas_2026-10-10/*.predictions.jsonl`). A comparação sai justa e barata.
- Responde a perguntas que ficaram abertas na Aula 9: negação e ironia enganam os modelos treinados ("Não é um filme ruim…", "Ótimo… Genial."). Um LLM lida melhor com isso? E o desempenho do LLM depende do autor principal, que escreveu 67% das críticas?
- É o experimento de **prompt engineering** do quadro: zero-shot × few-shot e o efeito de pedir justificativa.

## Itens do enunciado atendidos

Quadro do item 1: LLM e prompt engineering. Item 3, questões 2, 3, 4 e 5. "Resultados sem melhoria também devem ser apresentados."

## Amostra: `config/sentimento/sentimento_llm.json` (fixar ANTES de rodar)

**200 críticas**, sorteadas com semente fixa entre as 1.422 que têm polaridade (nota ≤ 4 ou ≥ 7). Estratos:

| Estrato | Qtd. | Por quê |
|---|---:|---|
| Negativas | 100 | Equilibra; no conjunto completo são só 29% |
| Positivas | 100 | |
| Dentro delas: com negação (marcadores de `app.shared.language`) | ≥ 80 | Análise do subgrupo "negação" |
| Dentro delas: do autor principal × dos demais | ≈ 50/50 | Repete o teste de generalização por autor |

- Mais 3 críticas da equipe (as da aba do site: negação e ironia) como **casos qualitativos**, fora das métricas.
- Críticas longas: cortar em 2.000 caracteres (início e fim) e registrar quantas foram cortadas. A mesma crítica cortada vai para todas as variantes.
- Sem o `author_key` no prompt. O esquema de saída é `{polaridade: "positivo"|"negativo", nota: number 0–10, justificativa: string ≤ 200 caracteres}`.

## Variantes

| Variante | Prompt | Chamadas |
|---|---|---:|
| `zero_shot` | Instruções e esquema | 200 |
| `few_shot` | Instruções, 4 exemplos (2 por polaridade, um com negação, **fora** da amostra) e esquema | 200 |
| `zero_shot_sem_justificativa` | Como `zero_shot`, sem o campo `justificativa` | 200 |
| `reserva` (Groq) | A melhor das variantes acima, no outro provedor | 200 |

São 800 chamadas no total. Com `request_interval_seconds` e o orçamento, distribuí-las em **mais de um dia** se a cota pedir; o `--reuse` continua de onde parou.

## Comparação

As predições do TF-IDF e do BERTimbau saem dos arquivos já gravados, filtradas pelo `review_id` das 200 críticas. **Nada é retreinado.** Por serem fora da dobra, os dois modelos nunca viram aquela crítica no treino; o LLM também não. A comparação é justa.

| Métrica | Onde |
|---|---|
| F1 macro, acurácia e matriz de confusão de polaridade | Geral e por estrato (negação, autor principal) |
| Erro médio absoluto da nota | Comparar com 1,33 (BERTimbau) e 1,98 (chutar a média), **nas mesmas 200** |
| Concordância entre os sistemas | Em quantas críticas o LLM acerta e os dois modelos erram, e o contrário. Mostrar 3 exemplos de cada lado |
| Efeito do prompt | zero-shot × few-shot × sem justificativa |
| Estabilidade | 20 críticas repetidas 2 vezes na variante escolhida; percentual de respostas iguais |
| Custo | Tokens médios, latência, falhas de JSON, chamadas que esgotaram a cota |

**Atenção ao F1 de referência:** os 85,6% e 86,7% do relatório valem para o conjunto completo, com 71% de positivas. Na amostra equilibrada, **recalcular** o TF-IDF e o BERTimbau. Comparar o LLM com o número do relatório seria injusto.

## Desenho

- Novo `sentiment/llm.py`: `LLMSentiment(model, prompt_config)` com `analyze(text) -> {polaridade, prob_positivo: None, nota, justificativa}`.
- Novo comando `python -m app.sentiment llm-eval --input ../data/preparacao/criticas_2026-10-10 --predictions ../data/sentimento/criticas_2026-10-10 --config ../config/sentimento/sentimento_llm.json --output ../data/sentimento/llm_<data> [--reuse ...]`. Grava `sample.json`, `responses.jsonl`, `predictions.jsonl`, `metrics.json`, `report.md` e o manifesto. `verify` também.
- **No site (opcional):** a aba "Analisar crítica" ganha o botão "Comparar com IA", que mostra lado a lado o TF-IDF (com as palavras de maior peso) e o LLM (com a justificativa). Rota `GET /sentimento/llm?texto=` com o limite e o orçamento da spec 00. Se o tempo apertar, fica só a avaliação offline e os exemplos gravados na página "Sobre".

## Testes (sem rede)

- Sorteio da amostra determinístico e com os estratos respeitados.
- Junção com as predições gravadas pelo `review_id`; falha se algum `review_id` faltar.
- Métricas com predições fixas; `ReplayModel` reproduz `metrics.json` byte a byte.
- Esquema: nota fora de 0–10 ou polaridade fora do `enum` é rejeitada.

## Critérios de aceite

- [ ] Amostra e prompts commitados **antes** da primeira chamada.
- [ ] `report.md` traz a tabela LLM (3 variantes) × TF-IDF × BERTimbau, geral e por estrato, com os mesmos números da página "Sobre".
- [ ] Os 3 casos da equipe (negação e ironia) aparecem com a saída dos três sistemas.
- [ ] `verify` no CI; `--reuse` reproduz as métricas sem rede.
- [ ] ADR 0031: amostra, variantes, resultado e se o LLM vai ou não para a tela, com o porquê (custo × ganho).
