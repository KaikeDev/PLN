# 0030 — Interpretação da consulta por LLM com saída estruturada e reserva nas regras (Unidade 4)

- Estado: Aceita
- Data: 2026-10-26

## Contexto

A busca transforma a frase do usuário em filtros (gêneros incluídos e excluídos, período e qualidade) por regras léxicas ([ADR 0005](0005-pesquisa-por-regras-lexicas.md)). As regras têm limites conhecidos:

- não reconhecem paráfrases ("algo que me faça rir");
- confundem o assunto com o gênero ("família aterrorizada por espíritos" filtra Família);
- a acurácia de 12/12 vinha de só cinco frases.

A Unidade 4 pede uma técnica avançada comparada com o resultado anterior. O LLM entende paráfrase e contexto, mas custa latência e cota e pode inventar filtros, que escondem filmes certos. A base de LLM já existe ([ADR 0029](0029-base-de-llm-por-api-gratuita.md)).

## Decisão

- **Mesma saída, porta comum.** Criar a porta `PreferenceExtractor` (`extract(texto) -> ExtractedFilters`), cumprida pelas regras (`FilterExtractor`) e pelo LLM (`LLMFilterExtractor`). Os dois são comparados nas mesmas frases e trocados no site sem mudar a busca.
- **Saída estruturada.** O LLM devolve `{generos, generos_excluidos, lancado_depois, lancado_antes, bem_avaliado, tema}`:
  - os gêneros são um `enum` com os nomes do catálogo, e o LLM não consegue inventar um gênero;
  - as datas são validadas como datas reais AAAA-MM-DD;
  - os nomes viram IDs pelo mesmo caminho das regras, e `bem_avaliado` usa o limiar das regras (nota ≥ 7 e ≥ 100 votos).
- **Prompt versionado** em `config/busca/interpretacao_prompt.json`:
  - as instruções trazem a data de hoje, a lista de gêneros, as convenções de período do ADR 0005 e a regra "na dúvida, não filtre";
  - a frase do usuário vai entre aspas, com escape de JSON, como dado;
  - **few-shot** acrescenta seis exemplos resolvidos, nenhum deles entre as frases de avaliação.
- **No site, few-shot com reserva nas regras** (`FallbackExtractor`):
  - o LLM tem 4 s; passado o prazo, ou com `LLMUnavailable` (cota, orçamento do dia, JSON inválido, sem chave), as regras interpretam;
  - a resposta diz em `interpretacao.origem` quem interpretou, e o site mostra o selo "interpretado por IA" ou "interpretado por regras";
  - o título exato continua antes de tudo e não gasta cota ([ADR 0006](0006-prioridade-de-titulo-exato.md)), e a frase é interpretada uma vez por pesquisa;
  - `GET /pesquisa?interpretacao=auto|regras|llm` permite comparar os intérpretes no próprio site; `llm` sem LLM responde 503.
- **O tema separado pelo LLM não substitui a frase na busca por tema** (`usar_tema_na_busca: false`). Os filtros do LLM filtram os filmes, mas a ordenação continua pela frase preparada (ADR 0025).
- **Avaliação reproduzível:** `python -m app.search interpret-eval`.
  - Entram 50 frases anotadas em seis categorias, **commitadas antes da primeira execução** (commit `1c15e37`).
  - As métricas são acerto exato, F1 de gêneros incluídos e excluídos, período (tolerância de um ano), qualidade e "filtro inventado", no total e por categoria.
  - O efeito na busca é medido nas 20 consultas anotadas.
  - As respostas ficam gravadas, e `--reuse` reproduz a pasta byte a byte, sem chaves e sem chamadas.
  - A latência fica no manifesto.

## Resultados

Duas execuções completas com `gemini-3.5-flash-lite` (alias `gemini-flash-lite-latest`) e temperatura 0, no mesmo dia: [`frases_2026-10-26`](../../data/interpretacao/frases_2026-10-26/report.md) (a de referência) e [`frases_2026-10-26_execucao_1`](../../data/interpretacao/frases_2026-10-26_execucao_1/report.md). Em 3 das 240 chamadas, a cota por minuto do Gemini estourou, e o Groq (`openai/gpt-oss-20b`) respondeu.

| Sistema | Acerto exato | F1 gêneros | Filtro inventado | Tokens de entrada | Latência mediana / p95 |
|---|---:|---:|---:|---:|---|
| Regras | 0,44 | 0,63 | 11 de 50 | — | — |
| LLM zero-shot | 0,92 a 0,98 | 0,95 a 0,98 | 1 a 2 de 50 | ~540 | 1,0 s / 1,9 a 2,3 s |
| **LLM few-shot (site)** | **0,94 a 0,98** | **0,99** | **0 de 50** | ~980 | 1,0 s / 1,4 a 1,9 s |

- **Por categoria (few-shot × regras, execução de referência):**
  - o LLM resolve as paráfrases (1,00 × 0,00), os períodos relativos (0,88 × 0,12) e as armadilhas léxicas (0,88 × 0,00, em que as regras puseram filtro errado nas oito);
  - as duas empatam nas frases explícitas e sem filtro (1,00);
  - em nenhuma frase as regras acertaram e o LLM errou.
- **Erros do LLM:**
  - "filme policial que não seja antigo" virou "a partir de 2001", em vez da convenção "últimos dez anos";
  - "depois de Matrix" ficou sem período numa execução;
  - "a história da família Romanov" ficou sem gênero.
- **Variação com temperatura 0:** entre as duas execuções, 3 de 50 respostas do zero-shot e 5 de 50 do few-shot mudaram. A conclusão vale nas duas; o número exato, não.
- **Efeito na busca, nas 20 consultas:**

  | Ordenação | MAP | Precisão @5 |
  |---|---:|---:|
  | Frase preparada (vigente) | 0,627 | 0,57 |
  | Frase + filtros das regras | 0,615 | 0,55 |
  | **Frase + filtros do LLM** | **0,640** | 0,57 |
  | Tema do LLM + filtros do LLM | 0,636 | 0,58 |
  | Tema do LLM, sem filtros | 0,623 | 0,57 |

  Os filtros das regras recusam 7 relevantes em "família aterrorizada por espíritos" (filtram Família). Os do LLM recusam 1 ali, 1 em "assassino mascarado" (filtram Terror, e um relevante não é Terror no TMDB) e 1 em "gângsteres e a máfia". O tema separado pelo LLM não melhora a ordenação: na maioria das consultas ele é a própria frase.

## Alternativas consideradas

- **Zero-shot no site:** acerto parecido e metade dos tokens, mas inventou filtros (1 e 2 frases) e errou mais nas armadilhas. Um filtro inventado esconde filmes certos, e é o erro que mais importa no site.
- **Usar o tema do LLM na busca:** perdeu para a frase preparada nas duas comparações (0,623 × 0,627 sem filtros; 0,636 × 0,640 com filtros).
- **Só o LLM, sem reserva:** o site ficaria sem interpretação quando a cota acaba.
- **Ampliar o léxico das regras:** cobriria as frases avaliadas, mas não paráfrases novas, e manteria as armadilhas de palavra isolada.
- **Avaliar com o mesmo conjunto usado nos exemplos do few-shot:** inflaria o resultado; os exemplos ficaram de fora das 50 frases.

## Consequências

- A busca entende paráfrases, negações e períodos relativos, e o site mostra quem interpretou cada pesquisa.
- **Custo:**
  - cada pesquisa que não é título exato gasta uma chamada (cerca de 1.000 tokens de entrada) do orçamento `interpretacao` (400 por dia);
  - repetições usam o cache;
  - acabado o orçamento, a pesquisa volta para as regras sem falhar;
  - a pesquisa fica cerca de 1 s mais lenta, com teto de 4 s.
- **Limites da evidência:**
  - as 50 frases foram redigidas com apoio de IA e precisam de revisão da equipe;
  - o gabarito reflete as convenções escolhidas (por exemplo, "o assunto sozinho não é gênero");
  - o resultado muda um pouco entre execuções;
  - a amostra de 20 consultas é pequena para afirmar que 0,640 é melhor que 0,627 em geral.
- Trocar o modelo ou o prompt exige rodar `interpret-eval` de novo; a pasta anterior continua verificável.
