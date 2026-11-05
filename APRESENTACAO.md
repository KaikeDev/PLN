# Apresentação do projeto

**Sinopses de filmes: do corpus ao LLM (PLN 2026/2)**

Site publicado: *a preencher depois da publicação ([passos](deploy/space/README.md))* (Mostra Virtual de PLN, Modalidade B)

Equipe: Kaike Ventura Tuerpe, Luana Nitsche, Pedro Henrique Ortunio e Thiago Bodnar (Ciência da Computação, FURB).

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

Depois vieram a análise de sentimentos e as entidades (Aula 9) e, na Unidade 4, **LLMs** onde as técnicas anteriores tinham limites: interpretar a frase do usuário, ler o sentimento de críticas e responder perguntas com **RAG**. Um **site publicado** usa tudo isso na prática e traz a página "Sobre o projeto", com a metodologia, os resultados e a avaliação crítica.

## 2. Coleta e preparação (Etapa 1)

Documento: [docs/1-coleta-e-preparacao.md](docs/1-coleta-e-preparacao.md) · Código: [`corpus/`](backend/src/app/corpus/) · Dados: [`data/coleta/`](data/coleta/tmdb_2026-09-12/), [`data/preparacao/`](data/preparacao/tmdb_2026-09-12/)

- **Amostra intencional:** 4 gêneros (Drama, Comédia, Terror, Ficção científica) × 3 períodos (1980–1999, 2000–2014, 2015–2025). Pegamos os filmes mais populares de cada combinação, com pelo menos 50 votos. .
- **Volume:** 481 registros recebidos e 51 duplicatas removidas, resultando em **430 filmes únicos**, dos quais 428 têm sinopse em português.
- **Seis preparações do mesmo texto**, cada uma salva separadamente: original → limpa → normalizada → tokenizada → sem pontuação → sem stopwords. Acentos, números e negações ("não", "nunca") são preservados.
- **Reprodutível:** coleta automatizada em um comando, respostas originais da API salvas e um manifesto com o hash de cada arquivo.

## 3. As oito representações (Etapa 2 e Aula 7)

Documento: [docs/2-representacoes.md](docs/2-representacoes.md) · Código: [`representations/`](backend/src/app/representations/)

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

Documento: [docs/3-busca.md](docs/3-busca.md) · Código: [`search/`](backend/src/app/search/)

**Pergunta:** qual algoritmo usar para o usuário buscar "quero um filme de ação sobre máquinas"?

1. Escrevemos **20 consultas de teste** como um usuário digitaria e marcamos os filmes relevantes de cada uma, lendo as 428 sinopses **antes** de rodar qualquer algoritmo.
2. Medimos os 8 algoritmos: o embedding de sentença foi o melhor sozinho (**MAP de 0,560**), e o TF-IDF ficou em segundo (0,446 a 0,460).
3. Eles erram em consultas diferentes:
   - o MiniLM entende o tema: "inteligência artificial contra a humanidade" teve AP de 0,86 contra 0,38 do TF-IDF;
   - o TF-IDF acerta palavras-chave: "zumbis" teve 0,62 contra 0,34 do MiniLM.
4. Testamos as combinações e escolhemos **0,3 × TF-IDF + 0,7 × MiniLM: MAP de 0,613**, com um filme relevante entre os 5 primeiros em todas as 20 consultas. Depois, tirando da consulta as palavras de pedido ("quero", "filme sobre"), o MAP subiu para **0,627** ([ADR 0025](docs/adr/0025-preparacao-da-consulta.md)), o número vigente.
5. Para não escolher pesos "decorados", sorteamos 500 vezes metade das consultas para escolher o peso e medimos na outra metade. A combinação ganhou do MiniLM sozinho em 95% dos sorteios.

**No site:** a busca procura num **catálogo de cerca de 5.500 filmes de 18 gêneros** (5.458 na coleta publicada), coletado pelo mesmo pipeline, e não só nos 428 da avaliação. As regras extraem da frase gênero, período, nota e negação ("ação", "dos anos 80", "sem comédia"), e a combinação ordena os filmes pelo tema ("máquinas"). Em "quero um filme de ação sobre máquinas", o site traz O Exterminador do Futuro, Gigantes de Aço, Eu, Robô… Eu, Robô não tem nenhuma palavra da frase, mas o MiniLM entende que robôs são máquinas.

## 5. Recomendação

Documento: [docs/4-recomendacao.md](docs/4-recomendacao.md) · Código: [`recommendation/`](backend/src/app/recommendation/)

- **Filme → filmes:** os 5 filmes de vetor mais próximo. **Perfil → filmes:** a média dos filmes de que a pessoa gostou.
- Sem avaliações de usuários, usamos os gêneros como aproximação: o **BERTimbau acerta 63,6%**, contra 37,9% de uma recomendação que ignora o texto.
- Para quem gostou de Invocação do Mal, Hereditário e Sobrenatural, o embedding de sentença recomenda Invocação do Mal 2 e 4, A Morte do Demônio… todos de terror sobrenatural.
- **No site:** a ficha de cada filme mostra os 5 **filmes parecidos**, com a mesma conta da avaliação, buscando no mesmo catálogo. Com o catálogo maior, Matrix passa a recomendar 13º Andar e as continuações de Matrix, e Toy Story, Lightyear e Toy Story 3.

## 6. Agrupamento e visualização

Documento: [docs/5-agrupamento.md](docs/5-agrupamento.md) · Código: [`clustering/`](backend/src/app/clustering/)

- **K-Means com 4 grupos, sem rótulos**, e projeção 2D colorida pelo gênero e pelo grupo (dois gráficos por representação).
- Os grupos **lembram pouco os gêneros**: ARI de até 0,144 (BERTimbau); nas representações lexicais, perto de zero. O K-Means agrupa por outros temas, como "vírus e missão" ou "guerra e polícia".
- **Agrupar × classificar:** com a mesma representação, o classificador coincide muito mais com os gêneros. No skip-gram, o ARI é de 0,381 contra 0,055 do K-Means. É a diferença entre aprender com e sem rótulos.

## 7. Classificação (Aula 8)

Documento: [docs/6-classificacao.md](docs/6-classificacao.md) · Código: [`classification/`](backend/src/app/classification/)

Três abordagens para o mesmo problema: **qual o gênero desta sinopse?**

| Abordagem | Como | Resultado |
|---|---|---|
| **Treinada** | Regressão logística sobre cada uma das 8 representações, com validação cruzada em 5 partes | F1 macro de **71,0%** (skip-gram) e 70,2% (BERTimbau), contra 59% do TF-IDF |
| **Sem treino (Jev)** | O modelo Jev, da TypeSafe AI, recebe a sinopse e perguntas tipadas, sem ver nenhum exemplo | **85,0%** de acurácia contra 56,0% do TF-IDF, nos mesmos 120 filmes |
| **Na tela do site** | A regressão logística sobre o MiniLM, que o site já carrega para a busca | F1 esperado de 66,1% |

- **Comédia é o gênero mais difícil** em todas as abordagens. Muitos "erros" são comédias de ação, que a restrição aos quatro gêneros transforma em "comédia".
- A regressão logística foi comparada com Naive Bayes, SVM, floresta aleatória e kNN nas mesmas dobras. A justificativa está em [6-classificacao-escolha-dos-modelos.md](docs/6-classificacao-escolha-dos-modelos.md).
- O Jev é melhor, mas cada classificação é uma **chamada paga** a um serviço externo. Por isso a tela do site usa a regressão logística.

## 7b. Análise de sentimentos (Aula 9)

Documento: [docs/7-sentimentos.md](docs/7-sentimentos.md) · Código: [`sentiment/`](backend/src/app/sentiment/)

Sinopses não opinam, então o sentimento foi medido em **críticas de usuários do TMDB**, que vêm com a nota que o próprio autor deu ao filme: um conjunto rotulado **sem anotação manual**.

| | Resultado |
|---|---|
| Dados | 1.859 críticas em português de 1.634 filmes; 414 negativas (nota ≤ 4) e 1.008 positivas (nota ≥ 7) |
| Polaridade | F1 macro de **86,7%** (BERTimbau) e 85,6% (TF-IDF), contra 41,5% de chutar sempre "positivo" |
| Nota de 0 a 10 | Erro médio de **1,33 ponto** (BERTimbau), contra 1,98 de chutar a média |

- **Um autor escreveu 67% das críticas.** Treinando sem ele e testando nele, o TF-IDF cai para 50,7%, e o BERTimbau mantém 80,8%: os vetores pré-treinados generalizam melhor para quem escreve diferente.
- **Negação atrapalha todas as representações:** no TF-IDF, a acurácia cai de 95,2% sem negação para 87,8% com negação.
- **Na tela**, a aba "Analisar crítica" usa o TF-IDF, que treina na hora e mostra as palavras que mais pesaram. Os exemplos da equipe incluem uma negação ("Não é um filme ruim…", lida como negativa) e uma ironia ("Ótimo… Genial.", lida como positiva).

## 7c. Entidades nomeadas e relações (Aula 9)

Documento: [docs/8-entidades-e-relacoes.md](docs/8-entidades-e-relacoes.md) · Código: [`entities/`](backend/src/app/entities/)

O notebook da aula aplicado às 428 sinopses, com o mesmo modelo (spaCy `pt_core_news_sm`) e as mesmas regras: **dependências → NER → relações → grafo**.

| | Resultado |
|---|---|
| NER | 1.671 menções. Comparando com os **créditos do TMDB**, 73,7% das pessoas creditadas saem como PER, e 81,6% das PER têm nome dos créditos |
| Relações | 1.435 triplas sujeito → relação → objeto; 88 delas pela regra a mais de coordenação ("nasceu … e estudou …") |

- **O NER encontra os nomes, mas erra a categoria:** "Maximus" e "Mathilda" viram lugares, e "Forrest Gump", MISC. O modelo foi treinado em notícias.
- **Correferência é o maior limite:** 35% das triplas têm "ele", "ela" ou "que" como sujeito, como o "Ela" do grafo da Marie Curie no notebook.
- **No site:** a ficha de cada filme mostra a sinopse com as entidades marcadas por cor, as pessoas e os lugares, e as triplas.

## 7d. Unidade 4: LLMs e RAG

Documento: [docs/9-tecnicas-avancadas.md](docs/9-tecnicas-avancadas.md) · Código: [`llm/`](backend/src/app/llm/), [`rag/`](backend/src/app/rag/) · ADRs [0029](docs/adr/0029-base-de-llm-por-api-gratuita.md) a [0034](docs/adr/0034-paginas-do-site-e-sobre-o-projeto.md)

Três técnicas com LLM (Gemini por API gratuita, com o Groq de reserva), **cada uma comparada com o que já existia**, inclusive onde não houve ganho:

| Técnica | Comparação | Resultado |
|---|---|---|
| **Interpretação da consulta** | Regras léxicas × LLM, em 50 frases anotadas | Acerto exato de 94% (few-shot) contra 44%; nenhum filtro inventado (regras: 11). Na busca, ganho pequeno: MAP de 0,627 → 0,640 |
| **Sentimento** | TF-IDF × BERTimbau × LLM, nas mesmas 200 críticas | Sem treino, o LLM teve F1 de 91,5% nas 200 críticas (reserva no Groq), contra 88,0% do BERTimbau e 79,1% do TF-IDF; erro da nota de 1,04 contra 1,53 |
| **Perguntas com RAG** | Busca híbrida × filmes citados pelo LLM, nas 20 consultas anotadas | Precisão dos citados de 0,90 a 0,95 contra 0,57; recusou as 5 perguntas sem resposta e as 3 tentativas de injeção; sem os trechos de crítica, recusou as 10 de opinião |

- **O que só o LLM faz:** responder "o que acharam de Oppenheimer?" juntando sinopse e críticas, com citações que abrem a ficha do filme.
- **Onde não melhorou:** separar o tema da frase pelo LLM não melhorou a busca. No sentimento, o few-shot não superou o zero-shot e gasta 60% mais tokens.
- **Custo:** cota gratuita, segundos de latência e respostas que variam. Por isso o site cai para as regras e para respostas gravadas quando o LLM falha.
- **Publicação:** Hugging Face Spaces (Docker, CPU gratuita), um processo servindo a API e as páginas, com limite de chamadas de LLM por visitante e orçamento diário ([ADR 0033](docs/adr/0033-publicacao-no-hugging-face-spaces.md)).

## 8. Roteiro da demonstração

> **Antes da apresentação:** abra o link público uns 10 minutos antes, porque o Space dorme sem visitas e leva cerca de 1 minuto para acordar. O indicador no topo deve ficar verde, com o número de filmes do catálogo (5.458). Reservas: a página "Sobre" estática e o site rodando localmente ([rodar-o-site.md](docs/tecnico/rodar-o-site.md)). Os filmes dos exemplos abaixo vieram do catálogo de outubro; com o catálogo publicado, alguns podem mudar de posição.

No link público (*a preencher depois da publicação ([passos](deploy/space/README.md))*) ou localmente, em <http://127.0.0.1:5500>:

**Cabeçalho e "Sobre o projeto"**

Mostrar o título, os autores e o link "Sobre o projeto": o quadro de técnicas (seção 6), os gráficos da Unidade 4 (seção 7) e as seis questões (seção 8).

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

**Aba "Perguntar (RAG)"**

| Clicar ou digitar | O que mostrar |
|---|---|
| "Tem algum filme sobre luto e sobre lidar com a perda de alguém?" | A resposta cita os filmes com marcas F…, que abrem a ficha; o bloco "De onde veio a resposta" mostra os 8 filmes e os trechos de crítica |
| "O que as pessoas acharam de Oppenheimer?" | Pergunta de opinião: a resposta vem dos trechos das críticas, com as notas dos autores |
| "Quais filmes falam sobre curling?" | Sem resposta no catálogo: o LLM recusa em vez de inventar |

**Aba "Analisar crítica"**

Clicar em "Usar um exemplo" até chegar à negação ("Não é um filme ruim…") e depois em **"Comparar com IA"**: o TF-IDF lê "ruim" como negativo; o LLM devolve a polaridade com uma justificativa, para discutir negação ao vivo.

**Aba "Classificar sinopse"**

1. Clicar em **"Usar um exemplo"**: sinopses reais do corpus, uma por gênero, com o gênero previsto e as barras de probabilidade.
2. Escrever uma frase própria, por exemplo "um robô doméstico ganha consciência e passa a ameaçar a família". O modelo pode errar, o que é bom para discutir o limite de 66% de F1 e a dificuldade com frases curtas.

## 9. Como garantimos que os resultados são confiáveis

Documentos: [docs/tecnico/validacao.md](docs/tecnico/validacao.md) · [docs/adr/](docs/adr/README.md)

- **Reprodutível:** toda etapa grava numa pasta nova com um manifesto de hashes. Refazendo com as mesmas entradas, os arquivos saem idênticos byte a byte. Um comando `verify` confere tudo.
- **Sem vazamento na avaliação:** na classificação, vocabulário, pesos e regularização são aprendidos só com o treino de cada dobra. Na busca, os relevantes foram marcados antes de rodar os algoritmos.
- **Testado:** 250 testes automatizados, sem rede (o LLM é substituído por dublês), mais lint e checagem de tipos, rodando no CI do GitHub.
- **Anotado antes de rodar:** frases, críticas sorteadas e perguntas do RAG foram commitadas antes da primeira chamada ao LLM, e as respostas brutas ficam gravadas para reavaliar sem gastar cota.
- **Decisões registradas:** 34 ADRs explicam cada escolha, as alternativas descartadas e as consequências.

## 10. Limitações e próximos passos

- **Catálogo do site:** a busca, a recomendação e as perguntas do site procuram em cerca de 5.500 filmes populares de 18 gêneros. A qualidade delas foi **medida só na amostra de 428**, porque anotar milhares de filmes à mão é inviável. No catálogo, a busca fica mais ruidosa: em "filme de cobra", aparecem filmes em que "Cobra" é nome de personagem.
- **Rótulos aproximados:** os gêneros do TMDB restritos a quatro opções apagam outros gêneros, como ação e romance, e geram parte dos "erros".
- **Avaliação da equipe:** as 20 consultas da busca foram escritas e julgadas por nós; a recomendação é avaliada por gênero, não por usuários.
- **Busca:**
  - não há nota mínima de corte, então a página sempre traz 20 filmes;
  - palavras de pedido ("quero", "me indica", "filme sobre") são removidas antes da busca por tema, e acentos que faltam voltam ("saude" → "saúde"); formas fora da lista continuam pesando, e temas abstratos, como saúde mental, trazem resultados mais misturados que temas concretos;
  - as regras tratam "família" como o gênero Família: "família aterrorizada por espíritos" filtra só filmes familiares.

- **LLM:** depende de cota gratuita; as respostas variam mesmo com temperatura 0; a fidelidade do RAG frase a frase depende do julgamento humano.
- **Próximos passos:** correferência antes das relações, avaliação com usuários reais, reordenação com *cross-encoder*, ajuste fino do BERTimbau, LLM local quantizado e uso dos pôsteres (multimodal).

---

**Onde está cada coisa:** veja a tabela de tarefas e a estrutura do repositório no [README](README.md).
