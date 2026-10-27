# Interpretação da consulta: regras × LLM

50 frases anotadas antes da execução (`config/busca/interpretacao.json`), com data de referência 2026-10-26. Modelos que responderam: `gemini:gemini-3.5-flash-lite`, `groq:openai/gpt-oss-20b`. A variante usada no site é **few_shot**; a linha “Site” é essa variante com queda para as regras quando o LLM falha.

## Resultado geral

| Sistema | Acerto exato | F1 gêneros | F1 excluídos | Período | Qualidade | Filtro inventado | Falhas |
|---|---:|---:|---:|---:|---:|---:|---:|
| Regras (ADR 0005) | 0.44 | 0.63 | 0.80 | 0.86 | 1.00 | 11 de 50 | 0 |
| LLM zero-shot | 0.98 | 0.98 | 1.00 | 1.00 | 1.00 | 1 de 50 | 0 |
| LLM few-shot | 0.98 | 0.99 | 1.00 | 1.00 | 1.00 | 0 de 50 | 0 |
| Site: LLM com reserva nas regras | 0.98 | 0.99 | 1.00 | 1.00 | 1.00 | 0 de 50 | 0 |

Período: os anos de cada limite podem diferir em um. Filtro inventado: frases em que o sistema pôs um filtro que o gabarito não tem.

## Por categoria

Acerto exato e, entre parênteses, frases com filtro inventado.

| Categoria | Frases | Regras (ADR 0005) | LLM zero-shot | LLM few-shot | Site: LLM com reserva nas regras |
|---|---:|---:|---:|---:|---:|
| Explícita | 10 | 1.00 (0) | 1.00 (0) | 1.00 (0) | 1.00 (0) |
| Paráfrase | 10 | 0.00 (0) | 1.00 (0) | 0.90 (0) | 0.90 (0) |
| Negação | 8 | 0.62 (3) | 1.00 (0) | 1.00 (0) | 1.00 (0) |
| Período | 8 | 0.12 (0) | 1.00 (0) | 1.00 (0) | 1.00 (0) |
| Armadilha léxica | 8 | 0.00 (8) | 0.88 (1) | 1.00 (0) | 1.00 (0) |
| Sem filtro | 6 | 1.00 (0) | 1.00 (0) | 1.00 (0) | 1.00 (0) |

## Custo

| Variante | Respostas | Tokens de entrada (média) | Tokens de saída (média) | Provedores | Falhas |
|---|---:|---:|---:|---|---|
| LLM zero-shot | 50 | 519.5 | 60.9 | gemini: 50 | nenhuma |
| LLM few-shot | 50 | 991.1 | 59.3 | gemini: 49, groq: 1 | nenhuma |

No site, a reserva caiu para as regras em 0 frase(s). A latência de cada variante está em `manifest.json`: ela muda a cada execução e não entra nos arquivos de conteúdo.

## Exemplos

Comparação entre as regras e a variante do site (few_shot); no máximo 8 por grupo.

### LLM acerta e regras erram (27)

| Frase | Categoria | Gabarito | Regras | LLM | Inventado pelo LLM |
|---|---|---|---|---|---|
| “algo que me faça rir” | Paráfrase | Comédia | nenhum filtro | Comédia | — |
| “um filme pra não dormir à noite” | Paráfrase | Terror | nenhum filtro | Terror | — |
| “quero um filme pra chorar” | Paráfrase | Drama | nenhum filtro | Drama | — |
| “algo pra ver com o namorado no dia dos namorados” | Paráfrase | Romance | nenhum filtro | Romance | — |
| “muita explosão e perseguição de carro” | Paráfrase | Ação | nenhum filtro | Ação | — |
| “bang-bang com cowboys no velho oeste” | Paráfrase | Faroeste | nenhum filtro | Faroeste | — |
| “desenho animado para crianças” | Paráfrase | Animação, Família | nenhum filtro | Animação, Família | — |
| “descobrir quem é o assassino só no final” | Paráfrase | Mistério | nenhum filtro | Mistério | — |

### Regras acertam e LLM erra (0)

Nenhuma frase.

### Os dois erram (1)

| Frase | Categoria | Gabarito | Regras | LLM | Inventado pelo LLM |
|---|---|---|---|---|---|
| “histórias que se passam no futuro com tecnologia avançada” | Paráfrase | Ficção científica | nenhum filtro | nenhum filtro | — |

## Efeito na busca por tema

20 consultas anotadas (`config/busca/consultas.json`) na amostra de 428 filmes, com a busca híbrida do site. Com filtros, um filme relevante recusado pelo filtro some da lista.

| Ordenação | MAP | Precisão @5 | MRR | Acerto @5 |
|---|---:|---:|---:|---:|
| Frase preparada (busca atual) | 0.627 | 0.57 | 0.912 | 1.00 |
| Tema separado pelo LLM | 0.623 | 0.57 | 0.910 | 1.00 |
| Frase + filtros das regras | 0.615 | 0.55 | 0.867 | 0.95 |
| Tema + filtros do LLM | 0.633 | 0.59 | 0.917 | 1.00 |

| Consulta | Tema do LLM | Relevantes recusados (regras) | Relevantes recusados (LLM) | AP frase | AP tema |
|---|---|---:|---:|---:|---:|
| “programador conectado a um sistema de computadores” | “programador conectado a um sistema de computadores” | 0 | 0 | 1.000 | 1.000 |
| “filme sobre simulação da realidade” | “simulação da realidade” | 0 | 0 | 0.500 | 0.500 |
| “quero um filme de ação sobre máquinas” | “máquinas” | 0 | 0 | 0.760 | 0.669 |
| “robô que cria laços de amizade com uma criança ou com animais” | “robô que cria laços de amizade com uma criança ou com animais” | 0 | 0 | 0.680 | 0.680 |
| “inteligência artificial que se volta contra a humanidade” | “inteligência artificial que se volta contra a humanidade” | 0 | 0 | 0.841 | 0.841 |
| “viagem no tempo para mudar o passado” | “viagem no tempo para mudar o passado” | 0 | 0 | 0.519 | 0.519 |
| “alienígenas invadem e atacam a Terra” | “alienígenas invadem e atacam a Terra” | 0 | 0 | 0.687 | 0.687 |
| “família aterrorizada por espíritos em uma casa assombrada” | “família aterrorizada por espíritos em uma casa assombrada” | 7 | 1 | 0.660 | 0.660 |
| “possessão demoníaca e exorcismo” | “possessão demoníaca e exorcismo” | 0 | 0 | 0.311 | 0.311 |
| “sobreviventes em um mundo tomado por zumbis” | “sobreviventes em um mundo tomado por zumbis” | 0 | 0 | 0.443 | 0.443 |
| “assassino mascarado persegue um grupo de adolescentes” | “assassino mascarado persegue um grupo de adolescentes” | 0 | 1 | 0.570 | 0.570 |
| “vampiros” | “vampiros” | 0 | 0 | 0.643 | 0.643 |
| “astronautas perdidos no espaço lutando para sobreviver” | “astronautas perdidos no espaço lutando para sobreviver” | 0 | 0 | 0.917 | 0.917 |
| “soldados lutando na Segunda Guerra Mundial” | “soldados lutando na Segunda Guerra Mundial” | 0 | 0 | 0.707 | 0.707 |
| “comédia romântica leve sobre um casal que se apaixona” | “um casal que se apaixona” | 0 | 0 | 0.121 | 0.129 |
| “homem preso injustamente sobrevivendo na prisão” | “homem preso injustamente sobrevivendo na prisão” | 0 | 0 | 0.489 | 0.489 |
| “gângsteres e a máfia” | “gângsteres e a máfia” | 0 | 0 | 0.480 | 0.480 |
| “personagem descobre que vive em um mundo falso” | “personagem descobre que vive em um mundo falso” | 0 | 0 | 0.472 | 0.472 |
| “jovens escapam de um acidente, mas a morte volta para buscá-los” | “jovens escapam de um acidente, mas a morte volta para buscá-los” | 0 | 0 | 0.740 | 0.740 |
| “dinossauros recriados a partir de DNA” | “dinossauros recriados a partir de DNA” | 0 | 0 | 1.000 | 1.000 |

