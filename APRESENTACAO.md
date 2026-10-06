# Apresentação do projeto

**PLN 2026/2 — Sinopses de filmes: busca, recomendação, agrupamento e classificação**

Equipe: Kaike Ventura Tuerpe, Luana Nitsche, Pedro Henrique Ortunio e Thiago Bodnar — Ciência da Computação, FURB.

Este documento resume o que foi feito, na ordem em que apresentaríamos, com os resultados e onde encontrar cada parte no repositório. Cada seção aponta para a explicação completa em `docs/`.

---

## 1. A ideia

Usamos as **sinopses de filmes do TMDB** como corpus e aplicamos a elas o ciclo completo da disciplina:

```
coleta → preparação → representações (8) ─┬─ busca
                                          ├─ recomendação
                                          ├─ agrupamento e visualização
                                          └─ classificação
```

A mesma base e as mesmas oito representações passam pelas quatro tarefas. Assim, dá para comparar as técnicas lado a lado: qual representação funciona melhor para quê, e por quê.

Por fim, um **site** usa três dessas tarefas na prática: a busca de filmes, os filmes parecidos na ficha de cada filme e a classificação de uma sinopse digitada.

## 2. Coleta e preparação (Etapa 1)

📄 [docs/1-coleta-e-preparacao.md](docs/1-coleta-e-preparacao.md) · 💻 [`corpus/`](backend/src/app/corpus/) · 📁 [`data/coleta/`](data/coleta/tmdb_2026-09-12/), [`data/preparacao/`](data/preparacao/tmdb_2026-09-12/)

- **Amostra intencional:** 4 gêneros (Drama, Comédia, Terror, Ficção científica) × 3 períodos (1980–1999, 2000–2014, 2015–2025). Pegamos os filmes mais populares de cada combinação, com pelo menos 50 votos. .
- **Volume:** 481 registros recebidos e 51 duplicatas removidas, resultando em **430 filmes únicos**, dos quais 428 têm sinopse em português.
- **Seis preparações do mesmo texto**, cada uma salva separadamente: original → limpa → normalizada → tokenizada → sem pontuação → sem stopwords. Acentos, números e negações ("não", "nunca") são preservados.
- **Reprodutível:** coleta automatizada em um comando, respostas originais da API salvas e um manifesto com o hash de cada arquivo.

## 3. As oito representações (Etapa 2 e Aula 7)

📄 [docs/2-representacoes.md](docs/2-representacoes.md) · 💻 [`representations/`](backend/src/app/representations/)

| Família | Representações | Ideia |
|---|---|---|
| Contagem | BoW e TF-IDF, cada um com e sem stopwords | Uma dimensão por palavra; só casa palavras idênticas |
| Vetores de palavra | word2vec CBOW e skip-gram (NILC) | Palavras usadas em contextos parecidos ficam próximas; a sinopse é a média |
| Contextual | BERTimbau | O vetor da palavra depende da frase |
| Embedding de sentença | MiniLM multilíngue | Transformer ajustado para comparar frases inteiras |

Dois exemplos da aula, medidos nos dados:
- **Caso do professor:** em "filme sobre simulação da realidade", as representações lexicais deixam Matrix entre o 11º e o 69º lugar, porque a palavra "simulação" não está na sinopse. O skip-gram o sobe para 5º, e o embedding de sentença, para 2º.
- **Polissemia:** no word2vec, "banco" tem o mesmo vetor em "o banco aprovou o financiamento" e em "sentou no banco da praça". No BERTimbau, os usos com o mesmo sentido ficam mais próximos (cosseno de 0,82 contra 0,55 entre sentidos diferentes).

## 4. Busca

📄 [docs/3-busca.md](docs/3-busca.md) · 💻 [`search/`](backend/src/app/search/)

**Pergunta:** qual algoritmo usar para o usuário buscar "quero um filme de ação sobre máquinas"?

1. Escrevemos **20 consultas de teste** como um usuário digitaria e marcamos os filmes relevantes de cada uma, lendo as 428 sinopses **antes** de rodar qualquer algoritmo.
2. Medimos os 8 algoritmos: o embedding de sentença foi o melhor sozinho (**MAP de 0,560**), e o TF-IDF ficou em segundo (0,446 a 0,460).
3. Eles erram em consultas diferentes:
   - o MiniLM entende o tema: "inteligência artificial contra a humanidade" teve AP de 0,86 contra 0,38 do TF-IDF;
   - o TF-IDF acerta palavras-chave: "zumbis" teve 0,62 contra 0,34 do MiniLM.
4. Testamos as combinações e escolhemos **0,3 × TF-IDF + 0,7 × MiniLM: MAP de 0,613**, com um filme relevante entre os 5 primeiros em todas as 20 consultas.
5. Para não escolher pesos "decorados", sorteamos 500 vezes metade das consultas para escolher o peso e medimos na outra metade. A combinação ganhou do MiniLM sozinho em 95% dos sorteios.

**No site:** a busca procura num **catálogo de 5.525 filmes de 18 gêneros**, coletado pelo mesmo pipeline, e não só nos 428 da avaliação. As regras extraem da frase gênero, período, nota e negação ("ação", "dos anos 80", "sem comédia"), e a combinação ordena os filmes pelo tema ("máquinas"). Em "quero um filme de ação sobre máquinas", o site traz O Exterminador do Futuro, Gigantes de Aço, Eu, Robô… Eu, Robô não tem nenhuma palavra da frase, mas o MiniLM entende que robôs são máquinas.

## 5. Recomendação

📄 [docs/4-recomendacao.md](docs/4-recomendacao.md) · 💻 [`recommendation/`](backend/src/app/recommendation/)

- **Filme → filmes:** os 5 filmes de vetor mais próximo. **Perfil → filmes:** a média dos filmes de que a pessoa gostou.
- Sem avaliações de usuários, usamos os gêneros como aproximação: o **BERTimbau acerta 63,6%**, contra 37,9% de uma recomendação que ignora o texto.
- Para quem gostou de Invocação do Mal, Hereditário e Sobrenatural, o embedding de sentença recomenda Invocação do Mal 2 e 4, A Morte do Demônio… todos de terror sobrenatural.
- **No site:** a ficha de cada filme mostra os 5 **filmes parecidos**, com a mesma conta da avaliação, buscando no catálogo de 5.525 filmes. Com o catálogo maior, Matrix passa a recomendar 13º Andar e as continuações de Matrix, e Toy Story, Lightyear e Toy Story 3.

## 6. Agrupamento e visualização

📄 [docs/5-agrupamento.md](docs/5-agrupamento.md) · 💻 [`clustering/`](backend/src/app/clustering/)

- **K-Means com 4 grupos, sem rótulos**, e projeção 2D colorida pelo gênero e pelo grupo (dois gráficos por representação).
- Os grupos **lembram pouco os gêneros**: ARI de até 0,144 (BERTimbau); nas representações lexicais, perto de zero. O K-Means agrupa por outros temas, como "vírus e missão" ou "guerra e polícia".
- **Agrupar × classificar:** com a mesma representação, o classificador coincide muito mais com os gêneros. No skip-gram, o ARI é de 0,381 contra 0,055 do K-Means. É a diferença entre aprender com e sem rótulos.

## 7. Classificação (Aula 8)

📄 [docs/6-classificacao.md](docs/6-classificacao.md) · 💻 [`classification/`](backend/src/app/classification/)

Três abordagens para o mesmo problema: **qual o gênero desta sinopse?**

| Abordagem | Como | Resultado |
|---|---|---|
| **Treinada** | Regressão logística sobre cada uma das 8 representações, com validação cruzada em 5 partes | F1 macro de **71,0%** (skip-gram) e 70,2% (BERTimbau), contra 59% do TF-IDF |
| **Sem treino (Jev)** | O modelo Jev, da TypeSafe AI, recebe a sinopse e perguntas tipadas, sem ver nenhum exemplo | **85,0%** de acurácia contra 56,0% do TF-IDF, nos mesmos 120 filmes |
| **Na tela do site** | A regressão logística sobre o MiniLM, que o site já carrega para a busca | F1 esperado de 66,1% |

- **Comédia é o gênero mais difícil** em todas as abordagens. Muitos "erros" são comédias de ação, que a restrição aos quatro gêneros transforma em "comédia".
- A regressão logística foi comparada com Naive Bayes, SVM, floresta aleatória e kNN nas mesmas dobras. A justificativa está em [6-classificacao-escolha-dos-modelos.md](docs/6-classificacao-escolha-dos-modelos.md).
- O Jev é melhor, mas cada classificação é uma **chamada paga** a um serviço externo. Por isso a tela do site usa a regressão logística.

## 8. Roteiro da demonstração

> **Antes da apresentação:** gere o catálogo do site ([passo 2 do README](README.md#como-executar)). Sem ele, a busca e os filmes parecidos usam só os 428 filmes, e os exemplos abaixo mudam. O indicador no topo do site deve mostrar "5.525 filmes".

Com o site rodando ([como executar](docs/tecnico/como-executar.md#o-site)), em <http://127.0.0.1:5500>:

**Aba "Buscar filmes"**

| Digitar | O que mostrar |
|---|---|
| `Matrix` | Título exato: o site vai direto ao filme |
| `quero um filme de ação sobre máquinas` | O gênero "ação" vira filtro, e "máquinas" ordena por tema: O Exterminador do Futuro em 1º |
| `terror sem comédia` | A negação ("sem comédia") é entendida pelas regras |
| `casa assombrada por espíritos` | Busca só por tema: O Grito, Invocação do Mal 2, Os Outros |
| `astronautas perdidos no espaço` | Tema sem palavra-chave de gênero: Apollo 13, O Enigma do Horizonte, Interestelar |
| `cobras gigantes` | Agora o catálogo tem filmes de cobra: Anaconda 3 em 1º |

**Ficha do filme (recomendação)**

Clicar num resultado da busca abre a ficha com a seção **"Filmes parecidos"**. Bons exemplos:
- **Matrix** → O Passageiro do Futuro, 13º Andar, Matrix Resurrections, Matrix Revolutions;
- **Invocação do Mal** → Invocação do Mal 4, Invocação do Mal 2, Annabelle 3;
- **Toy Story** → Lightyear, Gigantes de Aço, Bumblebee, Toy Story 3.

Clicando num parecido, abre a ficha dele, com os parecidos dele.

**Aba "Classificar sinopse"**

1. Clicar em **"Usar um exemplo"**: sinopses reais do corpus, uma por gênero, com o gênero previsto e as barras de probabilidade.
2. Escrever uma frase própria, por exemplo "um robô doméstico ganha consciência e passa a ameaçar a família". O modelo pode errar, o que é bom para discutir o limite de 66% de F1 e a dificuldade com frases curtas.

## 9. Como garantimos que os resultados são confiáveis

📄 [docs/tecnico/validacao.md](docs/tecnico/validacao.md) · [docs/adr/](docs/adr/README.md)

- **Reprodutível:** toda etapa grava numa pasta nova com um manifesto de hashes. Refazendo com as mesmas entradas, os arquivos saem idênticos byte a byte. Um comando `verify` confere tudo.
- **Sem vazamento na avaliação:** na classificação, vocabulário, pesos e regularização são aprendidos só com o treino de cada dobra. Na busca, os relevantes foram marcados antes de rodar os algoritmos.
- **Testado:** 111 testes automatizados, sem rede, mais lint e checagem de tipos, rodando no CI do GitHub.
- **Decisões registradas:** 22 ADRs explicam cada escolha, as alternativas descartadas e as consequências.

## 10. Limitações e próximos passos

- **Catálogo do site:** a busca e a recomendação do site procuram em 5.525 filmes populares de 18 gêneros. A qualidade delas foi **medida só na amostra de 428**, porque anotar milhares de filmes à mão é inviável. No catálogo, a busca fica mais ruidosa: em "filme de cobra", aparecem filmes em que "Cobra" é nome de personagem.
- **Rótulos aproximados:** os gêneros do TMDB restritos a quatro opções apagam outros gêneros, como ação e romance, e geram parte dos "erros".
- **Avaliação da equipe:** as 20 consultas da busca foram escritas e julgadas por nós; a recomendação é avaliada por gênero, não por usuários.
- **Busca:**
  - não há nota mínima de corte, então a página sempre traz 20 filmes;
  - palavras de pedido ("quero", "me indica", "filme sobre") são removidas antes da busca por tema, e acentos que faltam voltam ("saude" → "saúde"); formas fora da lista continuam pesando, e temas abstratos, como saúde mental, trazem resultados mais misturados que temas concretos;
  - as regras tratam "família" como o gênero Família: "família aterrorizada por espíritos" filtra só filmes familiares.

---

**Onde está cada coisa:** veja a tabela de tarefas e a estrutura do repositório no [README](README.md).
