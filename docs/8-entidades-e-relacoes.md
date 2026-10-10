# 8. Entidades nomeadas e extração de relações

Aplica às sinopses o notebook da Aula 9 ([`PLN_2026_Aula_9_parsing,_NER_e_extração_de_relações.ipynb`](../PLN_2026_Aula_9_parsing,_NER_e_extração_de_relações.ipynb)), com o mesmo modelo e as mesmas regras:

**texto → dependências e NER → relações → normalização dos argumentos → grafo**

Decisões na [ADR 0027](adr/0027-entidades-e-relacoes.md).

| Parte | Resultado | Onde |
|---|---|---|
| NER | 1.671 menções nas 428 sinopses; **73,7%** das pessoas creditadas marcadas como pessoa | [relatório](../data/entidades/tmdb_2026-09-12/report.md) |
| Relações | 1.435 triplas sujeito — relação → objeto; 63,5% das sentenças com ao menos uma | [relatório](../data/entidades/tmdb_2026-09-12/report.md) |
| No site | Ficha do filme: sinopse com as entidades marcadas, pessoas, lugares e relações | [`entities/live.py`](../backend/src/app/entities/live.py) |

## O que vem do notebook

| Notebook | No projeto ([`entities/extraction.py`](../backend/src/app/entities/extraction.py)) |
|---|---|
| `spacy.load("pt_core_news_sm")` | O mesmo modelo (spaCy 3.8, `pt_core_news_sm` 3.8.0), instalado pelo extra `entidades` |
| `analisar_dependencias` | `dependencies`: token, lema, classe, dependência e núcleo |
| `extrair_entidades` | `entities`: menção, categoria (PER, LOC, ORG, MISC) e posições |
| `obter_sintagma`, `obter_argumento` | `phrase`, `argument`: a entidade que contém o núcleo ou o sintagma sem artigo e preposição iniciais |
| `normalizar_preposicao` | `normalize_preposition`: "na" → "em", "pela" → "por" |
| `extrair_relacoes` | `relations`: sujeito (`nsubj`, `nsubj:pass`) com cada complemento (`obj`, `iobj`, `obl`); no `obl`, a preposição entra na relação (`trabalhar_em`) |
| `desenhar_grafo` (NetworkX) | Grafo dirigido em Mermaid no relatório, desenhado pelo GitHub, sem mais uma dependência |

Um teste confere que as frases do notebook dão as mesmas triplas, por exemplo (Marie Curie, trabalhar_em, Universidade de Paris) e (Microsoft, adquirir, Activision Blizzard).

## O que vai além do notebook

1. **Coordenação.** O notebook aponta como limite que, em "nasceu … e estudou …", o segundo verbo fica sem sujeito. Aqui, um verbo coordenado (`conj`) sem sujeito próprio herda o do verbo ao qual se coordena. No texto da Marie Curie, isso acrescenta (Marie Curie, estudar_em, Paris) e (Ela, realizar, pesquisas sobre radioatividade). Cada tripla registra a regra que a gerou, para separar o efeito.
2. **Avaliação com os créditos do TMDB.** O notebook avalia à mão, numa frase. Aqui, os créditos de cada filme (os 15 primeiros nomes do elenco, ator e personagem) dão uma referência automática para as pessoas.

## Resultados nas 428 sinopses

### Entidades

| Categoria | Menções | Mais frequentes |
|---|---:|---|
| PER (pessoa) | 879 | Andy, Peter Parker, Ash, Shrek, David, Thor |
| LOC (lugar) | 491 | Terra, Nova York, Los Angeles, Estados Unidos, Paris, *Woody* |
| MISC (outros) | 199 | Segunda Guerra Mundial, *Alex*, *Blade*, Guerra do Vietnã, Matrix |
| ORG (organização) | 102 | FBI, *Marty*, Jaegers, Caso Watergate |

Os nomes em itálico são erros: personagens marcados como lugar, outros ou organização.

### Conferência com os créditos

Uma **menção creditada** é uma sequência de palavras da sinopse que fazem parte do nome de um personagem ou ator do filme. Palavras genéricas, como "Young", "Agent" e "Mrs.", não contam, e apelidos entre aspas ("Ellis 'Red' Redding") contam sem as aspas. Foram 983 menções, em 325 sinopses.

| Medida | Valor |
|---|---:|
| **Revocação de pessoas:** menções creditadas marcadas como PER | **73,7%** |
| Menções creditadas reconhecidas com qualquer categoria | 98,5% |
| **Precisão estimada (piso):** entidades PER com algum nome dos créditos | **81,6%** de 879 |

- O NER quase sempre **encontra** o nome: só 15 de 983 menções passam sem marcação.
- O erro está na **categoria**: 145 nomes de personagens viram LOC, 68 viram MISC e 31 viram ORG. Exemplos: "Maximus" (*Gladiador*), "Mathilda" e "Léon" (*O Profissional*), "Clementine" (*Brilho Eterno*) como lugares, e "Forrest Gump" como MISC. O modelo foi treinado em notícias e erra mais com nomes de personagens, muitas vezes estrangeiros ou inventados.
- A precisão é um **piso**: "Doc" e "Bill" são apelidos que os créditos não trazem (lá estão "Doctor Emmett Brown" e "Dr. William Harford") e contam como erro. Já "Hill Valley" (lugar) e "Penitenciária Cold Mountain" (lugar) como pessoas são erros de verdade.

### Relações

| Medida | Valor |
|---|---:|
| Triplas | 1.435 |
| Pelas regras do notebook | 1.347 (732 com objeto direto, 615 com complemento preposicionado) |
| A mais pela regra de coordenação | 88 |
| Sentenças com ao menos uma tripla | 775 de 1.220 (63,5%) |
| Triplas com entidades nos dois lados | 31 (2,2%) |
| Triplas cujo sujeito é só um pronome ("Ela", "que") | **499 (35%)** |

Relações mais frequentes: `ter`, `levar`, `encontrar`, `tornar`, `fazer`, `descobrir`, `conhecer`, `enfrentar`.

- **Correferência é o maior limite.** Em 35% das triplas, o sujeito é "ele", "ela" ou "que" e não é ligado ao personagem, exatamente o caso do "Ela" no grafo da Marie Curie do notebook.
- **Poucas triplas ligam duas entidades.** Sinopses descrevem ações de personagens sobre coisas ("descobre que é vítima de um sistema"), e não fatos entre entidades, como "Marie Curie nasceu em Varsóvia".
- **Voz passiva com agente** fica de fora: em "Thomas Anderson é atormentado por estranhos pesadelos", o agente é `obl:agent`, que as regras do notebook não tratam.

### Exemplo: Matrix

> O jovem programador Thomas Anderson é atormentado por estranhos pesadelos em que está sempre conectado por cabos a um imenso sistema de computadores do futuro. À medida que o sonho se repete, ele começa a desconfiar da realidade. Thomas conhece os misteriosos Morpheus e Trinity e descobre que é vítima de um sistema inteligente e artificial chamado Matrix, que manipula a mente das pessoas […]

- **Entidades:** Thomas Anderson, Thomas, Morpheus e Trinity (PER); Matrix (MISC). Todas corretas.
- **Triplas:** (Thomas, conhecer, misteriosos Morpheus e Trinity) está certa. (que, manipular, mente das pessoas) tem um pronome relativo como sujeito. (sonho, repetir, À medida que) é um erro do parser.

O relatório traz também *Forrest Gump*, *Um Sonho de Liberdade* e *Ilha do Medo*, com a tabela de dependências, as triplas e o grafo.

## Conferência manual

[`review_sample.json`](../data/entidades/tmdb_2026-09-12/review_sample.json) traz 40 triplas sorteadas, com a sentença de origem e um campo `correta` vazio, para a equipe julgar como no notebook. **Sem esse julgamento, não afirmamos a precisão das relações.**

## No site

Ao abrir a ficha de um filme, a seção **"Personagens, lugares e relações"** mostra:
- a sinopse com as entidades marcadas por cor e categoria, como o `displacy` do notebook;
- as pessoas, os lugares, as organizações e os outros;
- as triplas sujeito — relação → objeto.

Funciona para qualquer filme, inclusive os de fora do catálogo, porque a rota `GET /entidades` analisa a sinopse na hora. Sem o extra `entidades`, a seção mostra "Entidades e relações indisponíveis".

## Como executar

Em `backend`:

```bash
uv sync --frozen --extra semantico --extra jev --extra entidades
# créditos dos filmes da amostra (TMDB_BEARER_TOKEN; cerca de 30 s); os entregues estão em data/coleta/creditos_2026-10-10
uv run --frozen python -m app.entities credits --movies ../data/preparacao/tmdb_2026-09-12 --output ../data/coleta/creditos_<data>
# entidades, relações, conferência e relatório (cerca de 15 s)
uv run --frozen --extra entidades python -m app.entities build --input ../data/preparacao/tmdb_2026-09-12 --credits ../data/coleta/creditos_2026-10-10 --output ../data/entidades/<nova_pasta> --config ../config/entidades/entidades.json
uv run --frozen python -m app.entities verify --input ../data/entidades/tmdb_2026-09-12
```

## Onde está no código

| Parte | Arquivo |
|---|---|
| Regras do notebook e coordenação | [backend/src/app/entities/extraction.py](../backend/src/app/entities/extraction.py) |
| Créditos e conferência do NER | [credits.py](../backend/src/app/entities/credits.py), [evaluation.py](../backend/src/app/entities/evaluation.py) |
| Pipeline e relatório com grafos | [pipeline.py](../backend/src/app/entities/pipeline.py), [report.py](../backend/src/app/entities/report.py) |
| Rota `/entidades` e ficha do filme | [backend/src/app/api/routes/entities.py](../backend/src/app/api/routes/entities.py), [frontend/script.js](../frontend/script.js) |
| Configuração | [config/entidades/entidades.json](../config/entidades/entidades.json) |

## Limitações

São as da seção 8 do notebook, medidas nas sinopses:

- **Correferência:** 35% das triplas têm um pronome como sujeito.
- **Taxonomia do modelo:** só PER, LOC, ORG e MISC. Não há datas, valores ou obras, e "Universidade de Paris" vira LOC.
- **Nomes de personagens:** 25% das pessoas creditadas recebem outra categoria.
- **A referência dos créditos** não tem apelidos ("Doc") nem as formas traduzidas dos nomes.
- **Papéis semânticos, negação e tempo** não são representados; a voz passiva com agente não gera tripla.
- **A referência dos créditos** cobre só pessoas do elenco principal; lugares e organizações não têm referência automática.
