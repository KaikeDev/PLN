# Evidências das representações vetoriais

Representações calculadas sobre 428 sinopses preenchidas de uma pasta processada com hashes verificados. Gêneros de coleta são rótulos aproximados da amostragem, não julgamentos de relevância.

## Representações e dimensões

| Representação | Método | Entrada | Dimensões | Tipo | Densidade | Não nulos por sinopse |
|---|---|---|---:|---|---:|---:|
| bow_sem_pontuacao | bow | 05_without_punctuation.jsonl | 5988 | esparsa | 0.7889% | 47.24 |
| bow_sem_stopwords | bow | 06_without_stopwords.jsonl | 5921 | esparsa | 0.5491% | 32.51 |
| tfidf_sem_pontuacao | tfidf | 05_without_punctuation.jsonl | 5988 | esparsa | 0.7889% | 47.24 |
| tfidf_sem_stopwords | tfidf | 06_without_stopwords.jsonl | 5921 | esparsa | 0.5491% | 32.51 |
| word2vec_cbow | word2vec | 06_without_stopwords.jsonl | 300 | densa | 100.0000% | 300.00 |
| word2vec_skipgram | word2vec | 06_without_stopwords.jsonl | 300 | densa | 100.0000% | 300.00 |
| bert_base_pt | contextual | 02_clean.jsonl | 768 | densa | 100.0000% | 768.00 |
| sentenca_minilm | contextual | 02_clean.jsonl | 384 | densa | 100.0000% | 384.00 |

- **bow_sem_pontuacao**, termos de maior peso somado: de, a, e, o, que, um, uma, para, em, com
- **bow_sem_stopwords**, termos de maior peso somado: não, está, ser, após, anos, família, vida, jovem, dois, casa
- **tfidf_sem_pontuacao**, termos de maior peso somado: de, a, o, um, e, que, uma, para, em, do
- **tfidf_sem_stopwords**, termos de maior peso somado: está, não, ser, família, após, anos, vida, jovem, dois, mundo
- **word2vec_cbow**: 99.69% dos tokens existem no modelo; 5879 palavras distintas do corpus têm vetor; 0 sinopses sem nenhuma palavra conhecida.
- **word2vec_skipgram**: 99.69% dos tokens existem no modelo; 5879 palavras distintas do corpus têm vetor; 0 sinopses sem nenhuma palavra conhecida.
- **bert_base_pt**: limite de 512 tokens do modelo; 0 sinopses foram truncadas.
- **sentenca_minilm**: limite de 128 tokens do modelo; 40 sinopses foram truncadas.

## Similaridade do cosseno

Para cada sinopse foram buscados os 5 vizinhos de maior cosseno. A concordância é a fração desses vizinhos com ao menos um gênero de coleta em comum; a referência é essa fração calculada sobre todos os demais filmes, ou seja, o esperado sem usar o texto. Nas representações lexicais a explicação lista termos idênticos; no word2vec, pares de palavras próximas (≈); o modelo contextual não é explicável por palavras.

| Representação | Concordância de gênero @5 | Referência | Filmes avaliados |
|---|---:|---:|---:|
| bow_sem_pontuacao | 0.3696 | 0.3071 | 428 |
| bow_sem_stopwords | 0.4879 | 0.3071 | 428 |
| tfidf_sem_pontuacao | 0.5023 | 0.3071 | 428 |
| tfidf_sem_stopwords | 0.5164 | 0.3071 | 428 |
| word2vec_cbow | 0.4701 | 0.3071 | 428 |
| word2vec_skipgram | 0.5168 | 0.3071 | 428 |
| bert_base_pt | 0.5523 | 0.3071 | 428 |
| sentenca_minilm | 0.5486 | 0.3071 | 428 |

### Vizinhos de Matrix (603)

- **bow_sem_pontuacao**: O Enigma de Outro Mundo (0.602: e, a, que, um, de); Um Sonho de Liberdade (0.599: e, a, que, de, um); Impacto Profundo (0.596: e, a, um, de, que)
- **bow_sem_stopwords**: Barbie (0.168: mundo, começa, descobre, está, real); Possessão (0.151: está, começa, descobre, estranhos, jovem); Madrugada dos Mortos (0.121: mundo, descobre, enquanto, está, real)
- **tfidf_sem_pontuacao**: Possessão (0.145: a, estranhos, e, que, está); Vingadores: Era de Ultron (0.134: sistema, artificial, o, que, da); Barbie (0.132: real, das, mundo, que, começa)
- **tfidf_sem_stopwords**: Barbie (0.086: real, mundo, começa, descobre, está); Vingadores: Era de Ultron (0.080: sistema, artificial); Coringa (0.078: thomas, mente)
- **word2vec_cbow**: Monstros S.A. (0.672: energia, mundo, pessoas ≈ crianças, thomas ≈ mike, sonho ≈ astro); O Incrível Hulk (0.669: está, conhece ≈ ama, vítima ≈ mulher, repete ≈ transforme, produzir ≈ explorar); Vingadores: Era de Ultron (0.667: artificial, sistema, cria ≈ gera, mundo ≈ planeta, conhece ≈ constrói)
- **word2vec_skipgram**: A Mosca (0.787: descobre ≈ percebe, pesadelos ≈ terríveis, começa ≈ vai, jovem ≈ homem, sempre ≈ não); O Máskara (0.738: enquanto, pessoas ≈ mulheres, usa ≈ usar, thomas ≈ carlyle, repete ≈ transforma); Círculo de Fogo (0.738: pessoas, começa ≈ começam, enquanto ≈ entretanto, misteriosos ≈ gigantescos, morpheus ≈ kaiju)
- **bert_base_pt**: A Hora do Pesadelo (0.913); Círculo de Fogo (0.908); A Mosca (0.907)
- **sentenca_minilm**: Contato (0.588); Monstros S.A. (0.584); A Hora do Pesadelo (0.577)

### Vizinhos de Forrest Gump: O Contador de Histórias (13)

- **bow_sem_pontuacao**: Os Bad Boys (0.438: de, do, e, da, a); A Guerra dos Mundos (0.436: de, do, um, e, o); Aos 14 (0.428: de, e, com, do, um)
- **bow_sem_stopwords**: Invocação do Mal 3: A Ordem do Demônio (0.136: caso, estados, história, unidos); Prenda-Me se For Capaz (0.128: anos, estados, história, unidos); Invocação do Mal (0.127: caso, estados, história, unidos)
- **tfidf_sem_pontuacao**: Sobrenatural: A Última Chave (0.131: infância, caso, de, do, com); Invocação do Mal 3: A Ordem do Demônio (0.126: estados, unidos, caso, história, de); Prenda-Me se For Capaz (0.126: estados, unidos, com, anos, história)
- **tfidf_sem_stopwords**: Sobrenatural: A Última Chave (0.103: infância, caso); Invocação do Mal 3: A Ordem do Demônio (0.086: estados, unidos, caso, história); Adeus, Minha Concubina (0.079: momentos, história, anos)
- **word2vec_cbow**: Prenda-Me se For Capaz (0.656: anos, história, estados, unidos, rapaz ≈ ladrão); Entrevista com o Vampiro (0.639: anos, rapaz ≈ homem, consegue ≈ precisa, história ≈ vida, intenções ≈ experiências); Terror em Silent Hill (0.638: anos, consegue ≈ vai, continua ≈ começa, rapaz ≈ carro, amor ≈ sofrimento)
- **word2vec_skipgram**: Prenda-Me se For Capaz (0.695: estados, anos, história, unidos, continua ≈ está); O Grande Lebowski (0.672: anos, vietnã, guerra, continua ≈ vai, consegue ≈ irá); Entrevista com o Vampiro (0.672: anos, rapaz ≈ homem, consegue ≈ precisa, história ≈ vida, jenny ≈ brad)
- **bert_base_pt**: O Grande Lebowski (0.911); Infidelidade (0.891); Diário de uma Paixão (0.889)
- **sentenca_minilm**: Prenda-Me se For Capaz (0.543); O Show de Truman: O Show da Vida (0.452); O Grande Lebowski (0.452)

### Vizinhos de Beleza Americana (14)

- **bow_sem_pontuacao**: Contato (0.535: a, e, de, com, sua); Gladiador 2 (0.526: a, de, e, seu, o); O Fabuloso Destino de Amélie Poulain (0.515: a, de, e, sua, que)
- **bow_sem_stopwords**: Homem-Aranha: Sem Volta Para Casa (0.136: vida, ajuda, não, pede); Homem-Aranha: De Volta ao Lar (0.115: vida, não); WALL-E (0.110: vida, conhece)
- **tfidf_sem_pontuacao**: O Fabuloso Destino de Amélie Poulain (0.122: a, sente, sua, de, vida); O Profissional (0.122: vizinho, a, conhece, vida, de); Homem-Aranha: Sem Volta Para Casa (0.121: pede, vida, ajuda, mais, sua)
- **tfidf_sem_stopwords**: Homem-Aranha: Sem Volta Para Casa (0.067: pede, vida, ajuda, não); Barbie (0.064: beleza, começa, não); Thor: Amor e Trovão (0.062: jane, pede, ajuda)
- **word2vec_cbow**: Garota Exemplar (0.753: dia, começa, pai ≈ marido, amiga ≈ irmã, reconstruir ≈ descobrir); Da Magia à Sedução (0.730: momento, melhor, vida, volta, pai ≈ marido); Crepúsculo (0.728: volta, pai, amiga ≈ mãe, conhece ≈ sabe, masturba ≈ apaixonam)
- **word2vec_skipgram**: Garota Exemplar (0.808: começa, dia, pai ≈ marido, amiga ≈ irmã, jane ≈ margo); Da Magia à Sedução (0.796: melhor, vida, volta, momento, pai ≈ marido); 10 Coisas Que Eu Odeio em Você (0.795: dia, amiga ≈ irmã, pai ≈ namorado, conhece ≈ apaixona, impotente ≈ insuportável)
- **bert_base_pt**: Todo Mundo Quase Morto (0.925); Infidelidade (0.921); Diário de uma Paixão (0.915)
- **sentenca_minilm**: Infidelidade (0.532); Uma Noite Alucinante 2 (0.484); 365 Dias: Hoje (0.479)

## Clustering

K-Means com k = 4. ARI, NMI e pureza comparam os clusters com o gênero de coleta dos filmes que vieram de um único gênero; a silhueta usa distância do cosseno e não depende de rótulos. Os termos descritivos vêm da média TF-IDF (sem stopwords) dos membros de cada cluster, o mesmo vocabulário para todas as representações.

| Representação | ARI | NMI | Pureza | Silhueta | Filmes rotulados | Tamanhos |
|---|---:|---:|---:|---:|---:|---|
| bow_sem_pontuacao | 0.0034 | 0.0126 | 0.3016 | 0.0327 | 378 | 120, 110, 85, 113 |
| bow_sem_stopwords | 0.0022 | 0.0098 | 0.3042 | 0.0060 | 378 | 140, 127, 112, 49 |
| tfidf_sem_pontuacao | 0.0022 | 0.0115 | 0.3016 | 0.0009 | 378 | 132, 73, 118, 105 |
| tfidf_sem_stopwords | 0.0216 | 0.0348 | 0.3333 | 0.0009 | 378 | 143, 99, 72, 114 |
| word2vec_cbow | 0.0568 | 0.0681 | 0.4048 | 0.0423 | 378 | 113, 96, 99, 120 |
| word2vec_skipgram | 0.0582 | 0.0748 | 0.3968 | 0.0621 | 378 | 122, 120, 85, 101 |
| bert_base_pt | 0.1224 | 0.1476 | 0.4709 | 0.0601 | 378 | 88, 106, 136, 98 |
| sentenca_minilm | 0.0797 | 0.1077 | 0.4365 | 0.0580 | 378 | 114, 136, 86, 92 |

### bow_sem_pontuacao

- Cluster 0 (120 filmes; Comédia 43, Drama 34, Terror 34, Ficção científica 27): ser, grupo, não, anos, jovem, depois, amigos, está, mundo, todos
- Cluster 1 (110 filmes; Ficção científica 35, Comédia 33, Drama 30, Terror 24): ser, está, agora, não, mundo, anos, dois, planeta, após, amigos
- Cluster 2 (85 filmes; Terror 28, Drama 27, Ficção científica 22, Comédia 17): dois, novo, família, jovem, cidade, após, não, nova, trás, passado
- Cluster 3 (113 filmes; Ficção científica 36, Terror 33, Drama 29, Comédia 26): está, família, casa, vida, não, após, começa, ser, morte, contra

### bow_sem_stopwords

- Cluster 0 (140 filmes; Comédia 40, Drama 40, Ficção científica 37, Terror 37): família, dois, jovem, casa, história, pai, mãe, relacionamento, futuro, jornada
- Cluster 1 (127 filmes; Terror 47, Ficção científica 33, Comédia 31, Drama 31): está, não, após, cidade, grupo, vírus, jovem, caminho, anos, encontrar
- Cluster 2 (112 filmes; Drama 34, Ficção científica 33, Comédia 32, Terror 27): ser, vida, anos, ter, onde, não, andy, jovem, amigos, após
- Cluster 3 (49 filmes; Ficção científica 17, Comédia 16, Drama 15, Terror 8): tempo, mesmo, dia, preso, mundo, soldado, precisa, decide, terra, está

### tfidf_sem_pontuacao

- Cluster 0 (132 filmes; Ficção científica 47, Terror 40, Drama 35, Comédia 28): guerra, está, grupo, tempo, futuro, missão, terra, família, mundial, não
- Cluster 1 (73 filmes; Comédia 23, Terror 23, Drama 22, Ficção científica 13): não, ser, vida, anos, após, começa, mundo, depois, mãe, está
- Cluster 2 (118 filmes; Comédia 38, Drama 37, Terror 27, Ficção científica 26): família, ser, não, jovem, após, está, dois, anos, crime, casa
- Cluster 3 (105 filmes; Ficção científica 34, Comédia 30, Terror 29, Drama 26): está, mundo, fazer, deve, anos, agora, filho, casa, dois, descobre

### tfidf_sem_stopwords

- Cluster 0 (143 filmes; Drama 46, Terror 43, Ficção científica 41, Comédia 34): morte, família, após, jovem, depois, não, anos, agora, mundo, já
- Cluster 1 (99 filmes; Comédia 35, Drama 33, Ficção científica 23, Terror 18): dois, não, está, amor, juntos, vida, anos, durante, precisam, família
- Cluster 2 (72 filmes; Drama 27, Ficção científica 27, Comédia 15, Terror 12): ser, homem, passa, combater, vida, depois, alta, ferro, tecnologia, tony
- Cluster 3 (114 filmes; Terror 46, Comédia 35, Ficção científica 29, Drama 14): casa, está, amigos, enquanto, família, anos, cidade, após, grupo, única

### word2vec_cbow

- Cluster 0 (113 filmes; Terror 43, Drama 38, Comédia 35, Ficção científica 14): família, casa, anos, vida, não, está, começa, morte, dois, mãe
- Cluster 1 (96 filmes; Comédia 36, Terror 31, Ficção científica 30, Drama 10): dois, grupo, amigos, todos, antes, cidade, terra, planeta, robô, precisam
- Cluster 2 (99 filmes; Drama 40, Comédia 32, Ficção científica 20, Terror 20): ser, jovem, não, peter, vida, está, anos, andy, angeles, caso
- Cluster 3 (120 filmes; Ficção científica 56, Drama 32, Terror 25, Comédia 16): está, após, mundo, contra, grupo, ser, missão, guerra, planeta, ainda

### word2vec_skipgram

- Cluster 0 (122 filmes; Terror 52, Ficção científica 47, Comédia 24, Drama 16): está, grupo, dois, ter, após, não, missão, terra, vírus, depois
- Cluster 1 (120 filmes; Drama 46, Comédia 38, Terror 38, Ficção científica 11): família, casa, não, está, vida, anos, jovem, dois, mãe, enquanto
- Cluster 2 (85 filmes; Drama 45, Comédia 25, Ficção científica 15, Terror 11): polícia, ser, jovem, anos, guerra, história, policial, mundial, vida, angeles
- Cluster 3 (101 filmes; Ficção científica 47, Comédia 32, Terror 18, Drama 13): ser, precisa, peter, mundo, jovem, está, ainda, vilão, após, força

### bert_base_pt

- Cluster 0 (88 filmes; Terror 50, Ficção científica 33, Comédia 11, Drama 8): grupo, vírus, cidade, está, missão, terra, planeta, equipe, após, única
- Cluster 1 (106 filmes; Ficção científica 59, Comédia 35, Terror 10, Drama 9): peter, ser, precisa, mundo, está, vilão, planeta, após, agora, contra
- Cluster 2 (136 filmes; Comédia 52, Drama 47, Terror 43, Ficção científica 16): casa, não, família, está, anos, amigos, vida, dois, ser, jovem
- Cluster 3 (98 filmes; Drama 56, Comédia 21, Terror 16, Ficção científica 12): jovem, durante, ser, anos, polícia, guerra, dois, policial, história, após

### sentenca_minilm

- Cluster 0 (114 filmes; Terror 51, Drama 41, Comédia 31, Ficção científica 4): família, casa, dois, está, não, amigos, começa, vida, anos, morte
- Cluster 1 (136 filmes; Drama 55, Ficção científica 38, Comédia 37, Terror 20): ser, jovem, homem, vida, não, peter, está, mundo, durante, policial
- Cluster 2 (86 filmes; Ficção científica 53, Terror 25, Comédia 12, Drama 12): missão, grupo, planeta, terra, está, vírus, após, equipe, robô, não
- Cluster 3 (92 filmes; Comédia 39, Ficção científica 25, Terror 23, Drama 12): família, novo, anos, mundo, encontrar, não, casa, pai, amigos, agora

## Projeção em duas dimensões

TruncatedSVD reduz as dimensões a dois componentes para inspeção visual (nas matrizes lexicais, é a LSA). Variância explicada baixa indica que o plano mostra só parte da estrutura; distâncias no gráfico não substituem o cosseno original. Sem centralização, o primeiro componente tende a seguir a direção média das sinopses e pode explicar menos variância que o segundo.

| Representação | Variância componente 1 | Variância componente 2 | Gráfico |
|---|---:|---:|---|
| bow_sem_pontuacao | 1.40% | 4.07% | [bow_sem_pontuacao.projection.svg](bow_sem_pontuacao.projection.svg) |
| bow_sem_stopwords | 0.34% | 0.90% | [bow_sem_stopwords.projection.svg](bow_sem_stopwords.projection.svg) |
| tfidf_sem_pontuacao | 0.24% | 0.62% | [tfidf_sem_pontuacao.projection.svg](tfidf_sem_pontuacao.projection.svg) |
| tfidf_sem_stopwords | 0.13% | 0.50% | [tfidf_sem_stopwords.projection.svg](tfidf_sem_stopwords.projection.svg) |
| word2vec_cbow | 0.86% | 4.72% | [word2vec_cbow.projection.svg](word2vec_cbow.projection.svg) |
| word2vec_skipgram | 0.99% | 7.41% | [word2vec_skipgram.projection.svg](word2vec_skipgram.projection.svg) |
| bert_base_pt | 0.53% | 6.97% | [bert_base_pt.projection.svg](bert_base_pt.projection.svg) |
| sentenca_minilm | 1.31% | 5.75% | [sentenca_minilm.projection.svg](sentenca_minilm.projection.svg) |

## Hipótese distribucional: palavras vizinhas (word2vec)

“Conheceremos uma palavra pela companhia que ela mantém” (Firth). O word2vec aprende um vetor por palavra prevendo contextos: o CBOW prevê a palavra central a partir das vizinhas; o skip-gram prevê as vizinhas a partir da palavra central. Palavras usadas em contextos parecidos terminam com direções próximas, o que indica uso semelhante, não sinonímia garantida.

| Par de palavras | word2vec_cbow | word2vec_skipgram |
|---|---:|---:|
| gato × cachorro | 0.566 | 0.646 |
| cão × cachorro | 0.749 | 0.754 |
| bola × brinquedo | 0.114 | 0.086 |
| leite × água | 0.173 | 0.195 |
| banco × empréstimo | 0.245 | 0.358 |
| banco × praça | 0.117 | 0.076 |
| gato × financiamento | 0.077 | -0.031 |

### word2vec_cbow: palavras do corpus mais próximas

- **simulação**: demonstração (0.53), máquina (0.49), ferramenta (0.47), invenção (0.46), rotina (0.43), aventura (0.43), pesquisa (0.42), réplica (0.42), visão (0.41), mistura (0.40)
- **realidade**: verdade (0.63), história (0.59), natureza (0.52), tragédia (0.51), trama (0.49), situação (0.49), farsa (0.47), vida (0.47), visão (0.47), atmosfera (0.47)
- **robô**: monstro (0.66), demônio (0.57), androide (0.56), lobisomem (0.55), ciborgue (0.54), macaco (0.54), ogro (0.53), esquilo (0.53), boneco (0.53), filhote (0.53)
- **fantasma**: monstro (0.62), assassino (0.57), vampiro (0.55), demônio (0.53), lobisomem (0.52), justiceiro (0.52), dragão (0.50), ciborgue (0.50), vilão (0.50), fugitivo (0.50)
- **amor**: ciúme (0.62), ódio (0.58), desejo (0.56), prazer (0.55), sonho (0.53), desespero (0.51), sofrimento (0.51), coração (0.50), deus (0.50), marido (0.49)
- **guerra**: batalha (0.51), revolta (0.45), rebelião (0.44), turnê (0.41), guerras (0.39), expedição (0.39), dominação (0.38), luta (0.37), pós-guerra (0.37), cruzada (0.36)
- **banco**: tesouro (0.39), governo (0.36), fundo (0.34), mercado (0.33), hospital (0.32), laboratório (0.32), bloco (0.32), corretor (0.30), setor (0.30), empresário (0.30)
- **cachorro**: cão (0.75), filhote (0.63), garoto (0.63), macaquinho (0.60), macaco (0.59), esquilo (0.58), bebê (0.58), rapaz (0.58), monstro (0.57), babuíno (0.57)

### word2vec_skipgram: palavras do corpus mais próximas

- **simulação**: demonstração (0.53), simular (0.53), ferramenta (0.46), processamento (0.41), computador (0.41), dinâmica (0.41), plataforma (0.40), máquina (0.40), rotineira (0.39), rotina (0.39)
- **realidade**: verdade (0.55), visão (0.54), percepção (0.53), situação (0.49), natureza (0.48), ilusão (0.48), história (0.47), dinâmica (0.46), intuição (0.43), utopia (0.43)
- **robô**: androide (0.65), andróide (0.64), monstro (0.64), alienígena (0.63), boneco (0.59), ciborgue (0.59), demônio (0.55), ultron (0.55), avatar (0.55), teletransporte (0.55)
- **fantasma**: monstro (0.66), demônio (0.58), vampiro (0.57), lobisomem (0.56), herói (0.53), assassino (0.53), vilão (0.53), supervilão (0.53), dragão (0.52), misterioso (0.52)
- **amor**: ciúme (0.62), ódio (0.57), paixão (0.54), sonho (0.53), deus (0.53), felicidade (0.52), desejo (0.52), prazer (0.52), eterna (0.50), alma (0.49)
- **guerra**: batalha (0.53), sangrenta (0.50), guerras (0.49), revolta (0.48), pós-guerra (0.45), rebelião (0.44), carnificina (0.43), ex-combatente (0.43), conflito (0.42), horrores (0.40)
- **banco**: tesouro (0.44), central (0.43), fundo (0.40), corretora (0.39), caixa (0.38), crédito (0.38), reservas (0.34), governo (0.32), sachs (0.31), banqueiro (0.29)
- **cachorro**: cão (0.75), filhote (0.69), gato (0.65), esquilo (0.59), garoto (0.59), bandido (0.57), hipopótamo (0.57), boneco (0.56), ladrão (0.56), porquinho (0.56)

## Similaridade lexical não é similaridade semântica

Pares de frases da aula, fora do corpus. Cada frase passa pelas mesmas regras de preparação da entrada de cada representação. Nas lexicais, só palavras presentes no vocabulário das sinopses contam; termos ausentes zeram a contribuição. Compare cada coluna consigo mesma: um BERT pré-treinado sem ajuste para sentenças tende a dar cossenos altos a quase qualquer par (anisotropia), então importa a diferença entre pares próximos e distantes, não o valor absoluto.

| Par | Esperado | bow_sem_pontuacao | bow_sem_stopwords | tfidf_sem_pontuacao | tfidf_sem_stopwords | word2vec_cbow | word2vec_skipgram | bert_base_pt | sentenca_minilm |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| parafrase_cachorro | proximas | 0.224 | 0.000 | 0.021 | 0.000 | 0.487 | 0.537 | 0.789 | 0.677 |
| polissemia_banco | distantes | 0.224 | 1.000 | 0.762 | 1.000 | 0.465 | 0.463 | 0.594 | -0.033 |
| mesmo_sentido_banco | proximas | 0.671 | 0.707 | 0.647 | 0.665 | 0.558 | 0.582 | 0.841 | 0.623 |
| parafrase_filme | proximas | 0.213 | 0.000 | 0.029 | 0.000 | 0.457 | 0.548 | 0.787 | 0.605 |

### parafrase_cachorro

- A: “O cachorro perseguiu a bola.”
- B: “O cão correu atrás do brinquedo.”
- Baixa sobreposição lexical, sentido próximo.
- **bow_sem_pontuacao** aproxima por: o
- **tfidf_sem_pontuacao** aproxima por: o
- **word2vec_cbow** aproxima por: cachorro ≈ cão, perseguiu ≈ correu, bola ≈ brinquedo
- **word2vec_skipgram** aproxima por: cachorro ≈ cão, perseguiu ≈ correu, bola ≈ atrás

### polissemia_banco

- A: “O banco aprovou o financiamento.”
- B: “Ele sentou no banco da praça.”
- Compartilham a palavra “banco”, mas com sentidos diferentes.
- **bow_sem_pontuacao** aproxima por: banco
- **bow_sem_stopwords** aproxima por: banco
- **tfidf_sem_pontuacao** aproxima por: banco
- **tfidf_sem_stopwords** aproxima por: banco
- **word2vec_cbow** aproxima por: banco, aprovou ≈ sentou, financiamento ≈ praça
- **word2vec_skipgram** aproxima por: banco, aprovou ≈ sentou

### mesmo_sentido_banco

- A: “O banco aprovou o financiamento.”
- B: “O banco cobrou juros do empréstimo.”
- Controle: “banco” com o mesmo sentido (instituição financeira).
- **bow_sem_pontuacao** aproxima por: o, banco
- **bow_sem_stopwords** aproxima por: banco
- **tfidf_sem_pontuacao** aproxima por: banco, o
- **tfidf_sem_stopwords** aproxima por: banco
- **word2vec_cbow** aproxima por: banco, financiamento ≈ empréstimo, aprovou ≈ cobrou
- **word2vec_skipgram** aproxima por: banco, financiamento ≈ empréstimo, aprovou ≈ cobrou

### parafrase_filme

- A: “Um programador descobre que vive em uma realidade simulada.”
- B: “O mundo que ele conhece é uma ilusão criada por máquinas.”
- Paráfrase do tema de Matrix sem palavras de conteúdo em comum.
- **bow_sem_pontuacao** aproxima por: que, uma
- **tfidf_sem_pontuacao** aproxima por: uma, que
- **word2vec_cbow** aproxima por: vive ≈ conhece, realidade ≈ ilusão, simulada ≈ criada, programador ≈ máquinas, descobre ≈ mundo
- **word2vec_skipgram** aproxima por: descobre ≈ conhece, realidade ≈ ilusão, programador ≈ máquinas, simulada ≈ criada, vive ≈ mundo

## Polissemia: embeddings estáticos × contextuais

Vetor da mesma palavra em frases com sentidos iguais e diferentes. No word2vec o vetor é único por palavra, então os cossenos são sempre 1 e a diferença é zero. Nos transformers o vetor da palavra depende da frase: espera-se cosseno maior entre usos com o mesmo sentido. BoW e TF-IDF também não distinguem sentidos: a palavra é sempre a mesma coluna.

### “banco”

1. (instituição financeira) O banco aprovou o financiamento.
2. (instituição financeira) O banco cobrou juros do empréstimo.
3. (assento) Ele sentou no banco da praça.
4. (assento) As crianças pintaram o banco de madeira do jardim.

| Representação | Família | Mesmo sentido | Sentidos diferentes | Diferença |
|---|---|---:|---:|---:|
| word2vec_cbow | static | 1.000 | 1.000 | 0.000 |
| word2vec_skipgram | static | 1.000 | 1.000 | 0.000 |
| bert_base_pt | contextual | 0.823 | 0.545 | 0.278 |
| sentenca_minilm | contextual | 0.858 | 0.193 | 0.665 |

### “manga”

1. (fruta) Ela comeu uma manga madura no café da manhã.
2. (fruta) O suco de manga estava doce e gelado.
3. (parte da roupa) A manga da camisa rasgou no prego.
4. (parte da roupa) Ele dobrou a manga do casaco antes de lavar as mãos.

| Representação | Família | Mesmo sentido | Sentidos diferentes | Diferença |
|---|---|---:|---:|---:|
| word2vec_cbow | static | 1.000 | 1.000 | 0.000 |
| word2vec_skipgram | static | 1.000 | 1.000 | 0.000 |
| bert_base_pt | contextual | 0.887 | 0.663 | 0.224 |
| sentenca_minilm | contextual | 0.672 | 0.451 | 0.221 |

## Consultas anotadas

A consulta passa pelas mesmas regras de preparação da entrada de cada representação e vira um vetor no mesmo espaço. A posição é a do primeiro filme anotado como relevante entre os filmes com cosseno positivo. MRR e acerto só olham o primeiro relevante; a precisão média (MAP) considera a posição de todos, e a precisão @5 é a fração relevante dos 5 primeiros resultados.

| Representação | MRR | Acerto @5 | MAP | Precisão @5 |
|---|---:|---:|---:|---:|
| bow_sem_pontuacao | 0.3572 | 0.4500 | 0.1875 | 0.1400 |
| bow_sem_stopwords | 0.7652 | 0.9000 | 0.3751 | 0.3500 |
| tfidf_sem_pontuacao | 0.8444 | 0.9500 | 0.4603 | 0.4600 |
| tfidf_sem_stopwords | 0.8795 | 0.9500 | 0.4459 | 0.4400 |
| word2vec_cbow | 0.5575 | 0.7500 | 0.3328 | 0.3000 |
| word2vec_skipgram | 0.5923 | 0.8000 | 0.3559 | 0.3000 |
| bert_base_pt | 0.4894 | 0.7500 | 0.2953 | 0.2500 |
| sentenca_minilm | 0.8792 | 1.0000 | 0.5598 | 0.4900 |

### matrix_literal: “programador conectado a um sistema de computadores”

Controle literal: todos os termos de conteúdo aparecem na sinopse coletada de Matrix.

1 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 1 | 1 de 1 | 1.000 | — | a, de, um, sistema, computadores | Matrix (0.461); Assim na Terra Como no Inferno (0.449); Contra o Tempo (0.429) |
| bow_sem_stopwords | 1 | 1 de 1 | 1.000 | — | sistema, computadores, conectado, programador | Matrix (0.350); Vingadores: Era de Ultron (0.090); O Enigma do Horizonte (0.087) |
| tfidf_sem_pontuacao | 1 | 1 de 1 | 1.000 | — | sistema, computadores, conectado, programador, a | Matrix (0.376); Vingadores: Era de Ultron (0.093); O Enigma do Horizonte (0.087) |
| tfidf_sem_stopwords | 1 | 1 de 1 | 1.000 | — | sistema, computadores, conectado, programador | Matrix (0.377); Vingadores: Era de Ultron (0.085); O Enigma do Horizonte (0.079) |
| word2vec_cbow | 1 | 1 de 1 | 1.000 | — | programador, conectado, sistema, computadores | Matrix (0.569); Free Guy: Assumindo o Controle (0.409); A Guerra dos Mundos (0.407) |
| word2vec_skipgram | 1 | 1 de 1 | 1.000 | — | conectado, sistema, programador, computadores | Matrix (0.573); Eu, Robô (0.455); O Jogo da Imitação (0.428) |
| bert_base_pt | 2 | 1 de 1 | 0.500 | — | — | A Guerra dos Mundos (0.631); Matrix (0.628); Operação Sombra (0.622) |
| sentenca_minilm | 1 | 1 de 1 | 1.000 | — | — | Matrix (0.371); Ghost in the Shell: O Fantasma do Futuro (0.352); O Jogo da Imitação (0.326) |

### matrix_simulacao: “filme sobre simulação da realidade”

Caso da orientação do professor: “simulação” não aparece literalmente na sinopse coletada de Matrix.

1 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 69 | 0 de 1 | 0.014 | simulação | da, realidade | Five Nights at Freddy's 2 (0.234); Hereditário (0.220); Resident Evil: Bem-Vindo a Raccoon City (0.186) |
| bow_sem_stopwords | 13 | 0 de 1 | 0.077 | simulação | realidade | O Dublê (0.333); Anaconda (0.243); Holocausto Canibal (0.229) |
| tfidf_sem_pontuacao | 18 | 0 de 1 | 0.056 | simulação | realidade, da | O Dublê (0.227); Anaconda (0.174); Vingadores: Guerra Infinita (0.173) |
| tfidf_sem_stopwords | 11 | 0 de 1 | 0.091 | simulação | realidade | O Dublê (0.284); Anaconda (0.198); Holocausto Canibal (0.193) |
| word2vec_cbow | 19 | 0 de 1 | 0.053 | — | realidade, simulação ≈ ilusão, filme ≈ sonho | Free Guy: Assumindo o Controle (0.584); O Dublê (0.555); Anaconda (0.554) |
| word2vec_skipgram | 5 | 1 de 1 | 0.200 | — | realidade, filme ≈ matrix, simulação ≈ artificial | Free Guy: Assumindo o Controle (0.565); Anaconda (0.540); O Dublê (0.540) |
| bert_base_pt | 10 | 0 de 1 | 0.100 | — | — | Uma Odisséia Chinesa: Parte Dois – Cinderela (0.609); Meninas Malvadas (0.563); Frankenstein (0.546) |
| sentenca_minilm | 2 | 1 de 1 | 0.500 | — | — | Free Guy: Assumindo o Controle (0.533); Matrix (0.484); A Entidade (0.423) |

### acao_maquinas: “quero um filme de ação sobre máquinas”

Exemplo do site. Relevantes: filmes com gênero Ação no TMDB cuja sinopse trata de máquinas, robôs, ciborgues ou inteligência artificial.

11 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 37 | 0 de 11 | 0.023 | quero | um, de, máquinas | A Bruxa de Blair (0.428); Assim na Terra Como no Inferno (0.404); A Iniciação (0.386) |
| bow_sem_stopwords | 4 | 1 de 11 | 0.080 | quero | máquinas | O Dublê (0.272); Anaconda (0.198); Holocausto Canibal (0.187) |
| tfidf_sem_pontuacao | 2 | 2 de 11 | 0.135 | quero | máquinas, um, de | O Dublê (0.193); O Exterminador do Futuro (0.173); Anaconda (0.146) |
| tfidf_sem_stopwords | 2 | 2 de 11 | 0.136 | quero | máquinas | O Dublê (0.218); O Exterminador do Futuro (0.191); Matrix Reloaded (0.152) |
| word2vec_cbow | 9 | 0 de 11 | 0.066 | — | ação ≈ violência, filme ≈ robô, máquinas ≈ robôs, quero ≈ impede | O Dublê (0.395); Space Jam: O Jogo do Século (0.368); Meu Malvado Favorito (0.364) |
| word2vec_skipgram | 5 | 1 de 11 | 0.142 | — | filme ≈ robocop, ação ≈ policial, máquinas ≈ usar, quero ≈ senhor | O Dublê (0.493); A Serbian Film - Terror sem Limites (0.477); O Vingador do Futuro (0.449) |
| bert_base_pt | 14 | 0 de 11 | 0.048 | — | — | Anaconda (0.567); A Serbian Film - Terror sem Limites (0.555); Uma Odisséia Chinesa: Parte Dois – Cinderela (0.553) |
| sentenca_minilm | 1 | 4 de 11 | 0.585 | — | — | O Exterminador do Futuro (0.528); Eu, Robô (0.500); Blade Runner: O Caçador de Andróides (0.450) |

### robo_amizade: “robô que cria laços de amizade com uma criança ou com animais”

Tema afetivo com robôs; poucas sinopses usam “amizade” e “robô” juntas.

5 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 35 | 0 de 5 | 0.030 | — | com, de, que, cria, robô | Akira (0.445); O Lobo de Wall Street (0.423); A Garota da Fábrica de Caixas de Fósforos (0.418) |
| bow_sem_stopwords | 1 | 4 de 5 | 0.786 | — | robô | Operação Big Hero (0.167); Lilo & Stitch (0.163); Robô Selvagem (0.157) |
| tfidf_sem_pontuacao | 2 | 3 de 5 | 0.630 | — | robô, de | Lilo & Stitch (0.130); Operação Big Hero (0.127); Robô Selvagem (0.124) |
| tfidf_sem_stopwords | 1 | 4 de 5 | 0.786 | — | robô | Operação Big Hero (0.142); Lilo & Stitch (0.138); Robô Selvagem (0.117) |
| word2vec_cbow | 4 | 1 de 5 | 0.152 | — | animais, robô, laços ≈ relacionamentos, criança ≈ órfão, cria ≈ construindo | Lilo & Stitch (0.563); Alice: Subservience (0.536); Matrix (0.535) |
| word2vec_skipgram | 6 | 0 de 5 | 0.123 | — | robô, criança ≈ menino, amizade ≈ amigos, cria ≈ formam, animais ≈ postos | Lilo & Stitch (0.599); Matrix (0.592); Blade II: O Caçador de Vampiros (0.581) |
| bert_base_pt | 2 | 1 de 5 | 0.154 | — | — | Eu, Robô (0.714); Robô Selvagem (0.704); Círculo de Fogo (0.700) |
| sentenca_minilm | 1 | 2 de 5 | 0.465 | — | — | Robô Selvagem (0.635); Alice: Subservience (0.588); Operação Big Hero (0.575) |

### ia_rebelde: “inteligência artificial que se volta contra a humanidade”

Máquinas ou androides que se rebelam ou manipulam humanos.

7 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 14 | 0 de 7 | 0.054 | — | a, humanidade, que, se | O Chamado (0.350); Guerra Mundial Z (0.331); Os Infiltrados (0.322) |
| bow_sem_stopwords | 1 | 2 de 7 | 0.247 | — | artificial, inteligência | Alice: Subservience (0.205); Guerra Mundial Z (0.187); Planeta dos Macacos: A Origem (0.183) |
| tfidf_sem_pontuacao | 1 | 2 de 7 | 0.402 | — | artificial, inteligência, a | Alice: Subservience (0.219); Vingadores: Era de Ultron (0.199); Planeta dos Macacos: A Origem (0.151) |
| tfidf_sem_stopwords | 1 | 2 de 7 | 0.380 | — | artificial, inteligência | Alice: Subservience (0.231); Vingadores: Era de Ultron (0.190); Planeta dos Macacos: A Origem (0.138) |
| word2vec_cbow | 1 | 1 de 7 | 0.263 | — | artificial, inteligência, humanidade ≈ terra, volta ≈ acaba, contra ≈ salvar | Vingadores: Era de Ultron (0.544); Independence Day (0.496); Guerra Mundial Z (0.495) |
| word2vec_skipgram | 1 | 1 de 7 | 0.255 | — | artificial, inteligência, humanidade ≈ humana, contra ≈ proteger, volta ≈ acaba | Vingadores: Era de Ultron (0.626); Independence Day (0.580); Tropas Estelares (0.565) |
| bert_base_pt | 5 | 1 de 7 | 0.207 | — | — | Guerra Mundial Z (0.664); Velozes & Furiosos: Hobbs & Shaw (0.641); Alien³ (0.626) |
| sentenca_minilm | 1 | 5 de 7 | 0.862 | — | — | Eu, Robô (0.601); O Exterminador do Futuro (0.592); Blade Runner: O Caçador de Andróides (0.579) |

### viagem_no_tempo: “viagem no tempo para mudar o passado”

Inclui ciclos temporais em que o personagem volta ao mesmo momento para mudar o desfecho.

9 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 2 | 2 de 9 | 0.225 | — | no, para, passado, mudar, o | Deadpool 2 (0.365); Os 12 Macacos (0.351); Sobrenatural: A Porta Vermelha (0.345) |
| bow_sem_stopwords | 1 | 2 de 9 | 0.306 | — | passado, mudar | Os 12 Macacos (0.257); De Volta para o Futuro (0.231); Viúva Negra (0.164) |
| tfidf_sem_pontuacao | 1 | 2 de 9 | 0.342 | — | passado, mudar, no, para, o | Os 12 Macacos (0.251); De Volta para o Futuro (0.195); O Iluminado (0.138) |
| tfidf_sem_stopwords | 1 | 2 de 9 | 0.290 | — | passado, mudar | Os 12 Macacos (0.219); De Volta para o Futuro (0.174); Viúva Negra (0.117) |
| word2vec_cbow | 1 | 3 de 9 | 0.411 | — | viagem, tempo, mudar ≈ fazer, passado ≈ pais | De Volta para o Futuro (0.542); Os 12 Macacos (0.532); Era Uma Vez na América (0.514) |
| word2vec_skipgram | 1 | 3 de 9 | 0.472 | — | tempo, viagem, mudar ≈ fazer, passado ≈ ano | De Volta para o Futuro (0.566); Os 12 Macacos (0.533); Se Beber, Não Case! (0.501) |
| bert_base_pt | 1 | 1 de 9 | 0.368 | — | — | De Volta para o Futuro (0.627); Os Croods (0.618); Feitiço do Tempo (0.608) |
| sentenca_minilm | 1 | 2 de 9 | 0.413 | — | — | Crimes Temporais (0.476); De Volta para o Futuro II (0.466); 2012 (0.461) |

### invasao_alienigena: “alienígenas invadem e atacam a Terra”

Invasão ou guerra contra alienígenas; visitas pacíficas não contam.

5 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 15 | 0 de 5 | 0.061 | invadem | a, e, alienígenas, terra | A Chegada (0.464); Impacto Profundo (0.380); Cinquenta Tons de Liberdade (0.380) |
| bow_sem_stopwords | 1 | 1 de 5 | 0.390 | invadem | alienígenas, atacam, terra | Independence Day (0.261); Blade Runner: O Caçador de Andróides (0.229); Encontro Marcado (0.218) |
| tfidf_sem_pontuacao | 1 | 3 de 5 | 0.570 | invadem | atacam, alienígenas, terra, a | Independence Day (0.247); A Chegada (0.166); Tropas Estelares (0.147) |
| tfidf_sem_stopwords | 1 | 3 de 5 | 0.509 | invadem | atacam, alienígenas, terra | Independence Day (0.254); MIB - Homens de Preto (0.143); A Chegada (0.140) |
| word2vec_cbow | 3 | 1 de 5 | 0.151 | — | terra, alienígenas, atacam, invadem ≈ unem | X-Men: Dias de um Futuro Esquecido (0.557); Blade Runner: O Caçador de Andróides (0.527); Independence Day (0.501) |
| word2vec_skipgram | 2 | 1 de 5 | 0.172 | — | alienígenas, atacam, terra, invadem ≈ unem | X-Men: Dias de um Futuro Esquecido (0.679); Independence Day (0.615); Vida de Inseto (0.612) |
| bert_base_pt | 1 | 1 de 5 | 0.336 | — | — | Independence Day (0.678); X-Men: Dias de um Futuro Esquecido (0.659); Capitão América: Guerra Civil (0.657) |
| sentenca_minilm | 1 | 2 de 5 | 0.588 | — | — | Tropas Estelares (0.658); Independence Day (0.547); O Predador 2: A Caçada Continua (0.525) |

### casa_assombrada: “família aterrorizada por espíritos em uma casa assombrada”

Assombração de casa ou de família por espíritos; inclui a comédia em que fantasmas tentam assustar os novos moradores.

7 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 4 | 1 de 7 | 0.174 | — | uma, aterrorizada, em, família, por | Predador: Terras Selvagens (0.365); Um Lugar Silencioso (0.350); Os Croods (0.340) |
| bow_sem_stopwords | 1 | 3 de 7 | 0.487 | — | casa, assombrada | Os Outros (0.286); Sobrenatural (0.274); Hereditário (0.256) |
| tfidf_sem_pontuacao | 1 | 4 de 7 | 0.586 | — | assombrada, espíritos, casa, por, uma | Invocação do Mal 2 (0.256); Os Outros (0.190); Invocação do Mal (0.165) |
| tfidf_sem_stopwords | 1 | 4 de 7 | 0.626 | — | assombrada, espíritos, casa | Invocação do Mal 2 (0.247); Os Outros (0.193); Invocação do Mal (0.141) |
| word2vec_cbow | 6 | 0 de 7 | 0.134 | — | casa, família, aterrorizada ≈ lá, espíritos ≈ atormentam, assombrada ≈ renai | Parasita (0.707); Hereditário (0.647); A Bruxa (0.618) |
| word2vec_skipgram | 3 | 2 de 7 | 0.260 | — | casa, família, espíritos ≈ atormentam, aterrorizada ≈ renai, assombrada ≈ lá | Hereditário (0.675); Parasita (0.673); Sobrenatural (0.610) |
| bert_base_pt | 1 | 3 de 7 | 0.524 | — | — | Invocação do Mal (0.745); Invocação do Mal 2 (0.744); Um Lugar Silencioso (0.740) |
| sentenca_minilm | 4 | 2 de 7 | 0.370 | — | — | Um Lugar Silencioso (0.617); A Morte do Demônio (0.572); Hereditário (0.570) |

### possessao: “possessão demoníaca e exorcismo”

Personagens possuídos por demônios ou exorcistas.

7 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 28 | 0 de 7 | 0.021 | exorcismo | demoníaca, e, possessão | Uma Batalha Após a Outra (0.289); Cinquenta Tons de Liberdade (0.280); Operação Cupido (0.274) |
| bow_sem_stopwords | 1 | 1 de 7 | 0.143 | exorcismo | demoníaca, possessão | Invocação do Mal 3: A Ordem do Demônio (0.267); A Freira (0.108) |
| tfidf_sem_pontuacao | 1 | 1 de 7 | 0.157 | exorcismo | possessão, demoníaca, e | Invocação do Mal 3: A Ordem do Demônio (0.290); A Freira (0.117); Operação Cupido (0.023) |
| tfidf_sem_stopwords | 1 | 1 de 7 | 0.143 | exorcismo | possessão, demoníaca | Invocação do Mal 3: A Ordem do Demônio (0.316); A Freira (0.110) |
| word2vec_cbow | 5 | 1 de 7 | 0.132 | — | demoníaca, possessão, exorcismo ≈ assassinato | A Freira (0.558); Thor: Amor e Trovão (0.519); Sobrenatural: A Origem (0.507) |
| word2vec_skipgram | 7 | 0 de 7 | 0.093 | — | demoníaca ≈ maldição, exorcismo ≈ demônios, possessão ≈ possuídos | A Freira (0.622); Sobrenatural: A Origem (0.590); Thor: Amor e Trovão (0.587) |
| bert_base_pt | 12 | 0 de 7 | 0.061 | — | — | Neon Genesis Evangelion: O Fim do Evangelho (0.606); Van Helsing: O Caçador de Monstros (0.597); Shrek Para Sempre (0.577) |
| sentenca_minilm | 2 | 2 de 7 | 0.263 | — | — | Os Caça-Fantasmas 2 (0.541); Constantine (0.539); Invocação do Mal 3: A Ordem do Demônio (0.526) |

### zumbis: “sobreviventes em um mundo tomado por zumbis”

Inclui infectados e mutantes que agem como zumbis, mesmo quando a sinopse não usa a palavra “zumbi” (Extermínio, Eu Sou a Lenda).

9 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 1 | 1 de 9 | 0.215 | — | um, mundo, por, em, sobreviventes | Madrugada dos Mortos (0.414); Predador: Terras Selvagens (0.390); Os Croods (0.364) |
| bow_sem_stopwords | 1 | 1 de 9 | 0.260 | — | mundo, sobreviventes, tomado, zumbis | Madrugada dos Mortos (0.361); Barbie (0.200); Free Guy: Assumindo o Controle (0.186) |
| tfidf_sem_pontuacao | 1 | 5 de 9 | 0.762 | — | tomado, zumbis, sobreviventes, mundo, por | Madrugada dos Mortos (0.307); Extermínio (0.169); Guerra Mundial Z (0.119) |
| tfidf_sem_stopwords | 1 | 3 de 9 | 0.620 | — | tomado, zumbis, sobreviventes, mundo | Madrugada dos Mortos (0.291); Extermínio (0.152); Guerra Mundial Z (0.112) |
| word2vec_cbow | 1 | 2 de 9 | 0.287 | — | tomado, sobreviventes, zumbis, mundo | Madrugada dos Mortos (0.574); X-Men: Dias de um Futuro Esquecido (0.513); Extermínio (0.506) |
| word2vec_skipgram | 1 | 2 de 9 | 0.239 | — | mundo, tomado, sobreviventes, zumbis | Madrugada dos Mortos (0.649); X-Men: Dias de um Futuro Esquecido (0.635); Independence Day (0.597) |
| bert_base_pt | 3 | 1 de 9 | 0.242 | — | — | X-Men: Dias de um Futuro Esquecido (0.711); A Morte do Demônio: A Ascensão (0.707); Zumbilândia (0.706) |
| sentenca_minilm | 1 | 2 de 9 | 0.342 | — | — | Extermínio: A Evolução (0.619); Extermínio (0.592); Os Oito Odiados (0.569) |

### assassino_mascarado: “assassino mascarado persegue um grupo de adolescentes”

Slashers com jovens como vítimas; inclui a paródia Todo Mundo em Pânico.

6 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 5 | 1 de 6 | 0.146 | — | um, de, adolescentes, grupo | Assim na Terra Como no Inferno (0.412); Premonição 5 (0.406); A Longa Marcha: Caminhe ou Morra (0.395) |
| bow_sem_stopwords | 2 | 3 de 6 | 0.300 | — | adolescentes, assassino, grupo | A Longa Marcha: Caminhe ou Morra (0.224); Todo Mundo em Pânico (0.205); Premonição 5 (0.202) |
| tfidf_sem_pontuacao | 1 | 3 de 6 | 0.492 | — | adolescentes, assassino, grupo, de, um | Todo Mundo em Pânico (0.164); A Longa Marcha: Caminhe ou Morra (0.161); Sexta-Feira 13 (0.152) |
| tfidf_sem_stopwords | 1 | 3 de 6 | 0.514 | — | adolescentes, assassino, grupo | Todo Mundo em Pânico (0.153); A Longa Marcha: Caminhe ou Morra (0.151); Sexta-Feira 13 (0.132) |
| word2vec_cbow | 13 | 0 de 6 | 0.027 | — | assassino, adolescentes, grupo, persegue ≈ descobre, mascarado ≈ horror | A Hora do Pesadelo (0.612); Operação Big Hero (0.597); Batman Begins (0.596) |
| word2vec_skipgram | 13 | 0 de 6 | 0.045 | — | assassino, grupo, adolescentes, persegue ≈ descobre, mascarado ≈ horror | A Hora do Pesadelo (0.690); Deadpool 2 (0.663); Batman: O Cavaleiro das Trevas Ressurge (0.649) |
| bert_base_pt | 20 | 0 de 6 | 0.024 | — | — | Zumbilândia (0.727); Zootopia: Essa Cidade é o Bicho (0.721); O Predador 2: A Caçada Continua (0.714) |
| sentenca_minilm | 1 | 3 de 6 | 0.455 | — | — | Todo Mundo em Pânico (0.642); A Hora do Pesadelo (0.615); Pânico (0.583) |

### vampiros: “vampiros”

Consulta de uma palavra. Crepúsculo e Um Drink no Inferno ficam fora porque as sinopses coletadas não revelam os vampiros.

9 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 1 | 2 de 9 | 0.222 | — | vampiros | Blade II: O Caçador de Vampiros (0.155); Os Garotos Perdidos (0.088) |
| bow_sem_stopwords | 1 | 2 de 9 | 0.222 | — | vampiros | Blade II: O Caçador de Vampiros (0.229); Os Garotos Perdidos (0.126) |
| tfidf_sem_pontuacao | 1 | 2 de 9 | 0.222 | — | vampiros | Blade II: O Caçador de Vampiros (0.243); Os Garotos Perdidos (0.139) |
| tfidf_sem_stopwords | 1 | 2 de 9 | 0.222 | — | vampiros | Blade II: O Caçador de Vampiros (0.261); Os Garotos Perdidos (0.146) |
| word2vec_cbow | 2 | 1 de 9 | 0.126 | — | vampiros | X-Men: Dias de um Futuro Esquecido (0.555); Blade II: O Caçador de Vampiros (0.552); Vida de Inseto (0.517) |
| word2vec_skipgram | 2 | 1 de 9 | 0.159 | — | vampiros | X-Men: Dias de um Futuro Esquecido (0.622); Blade II: O Caçador de Vampiros (0.595); A Era do Gelo 3 (0.573) |
| bert_base_pt | 3 | 1 de 9 | 0.090 | — | — | Neon Genesis Evangelion: O Fim do Evangelho (0.308); Uma Odisséia Chinesa: Parte Dois – Cinderela (0.282); Blade Trinity (0.263) |
| sentenca_minilm | 1 | 3 de 9 | 0.561 | — | — | Entrevista com o Vampiro (0.601); Blade II: O Caçador de Vampiros (0.578); A Morte do Demônio: A Ascensão (0.543) |

### astronautas_perdidos: “astronautas perdidos no espaço lutando para sobreviver”

Tripulações ou astronautas isolados no espaço ou em outro planeta.

6 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 26 | 0 de 6 | 0.040 | perdidos | no, espaço, para | Sobrenatural: A Porta Vermelha (0.224); Debi & Lóide: Dois Idiotas em Apuros (0.216); Barbie (0.211) |
| bow_sem_stopwords | 3 | 1 de 6 | 0.150 | perdidos | astronautas | Jogos Mortais (0.107); Entre Montanhas (0.104); O Enigma do Horizonte (0.087) |
| tfidf_sem_pontuacao | 1 | 3 de 6 | 0.488 | perdidos | astronautas, para | O Enigma do Horizonte (0.100); Interestelar (0.098); Top Gun - Ases Indomáveis (0.096) |
| tfidf_sem_stopwords | 1 | 3 de 6 | 0.433 | perdidos | astronautas | O Enigma do Horizonte (0.103); Interestelar (0.095); Top Gun - Ases Indomáveis (0.091) |
| word2vec_cbow | 2 | 2 de 6 | 0.234 | — | sobreviver ≈ retornar, astronautas ≈ companheiros, perdidos ≈ escassos, espaço ≈ planeta, lutando ≈ morto | X-Men: Dias de um Futuro Esquecido (0.550); Perdido em Marte (0.502); Entre Montanhas (0.489) |
| word2vec_skipgram | 3 | 2 de 6 | 0.262 | — | astronautas ≈ astronauta, sobreviver ≈ retornar, perdidos ≈ escassos, lutando ≈ sozinho, espaço ≈ planeta | X-Men: Dias de um Futuro Esquecido (0.623); Entre Montanhas (0.594); Perdido em Marte (0.587) |
| bert_base_pt | 2 | 2 de 6 | 0.324 | — | — | X-Men: Dias de um Futuro Esquecido (0.658); Perdido em Marte (0.656); O Segredo do Abismo (0.653) |
| sentenca_minilm | 1 | 4 de 6 | 0.897 | — | — | Alien: Romulus (0.701); Interestelar (0.670); Perdido em Marte (0.656) |

### segunda_guerra: “soldados lutando na Segunda Guerra Mundial”

Combatentes na guerra; dramas da guerra sem soldados em combate (O Pianista, O Menino do Pijama Listrado) não contam.

6 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 1 | 3 de 6 | 0.552 | — | soldados, guerra, mundial, na, segunda | Dunkirk (0.234); Bastardos Inglórios (0.233); Uma Odisséia Chinesa: Parte Dois – Cinderela (0.218) |
| bow_sem_stopwords | 1 | 3 de 6 | 0.544 | — | soldados, guerra, mundial, segunda | Dunkirk (0.326); Corações de Ferro (0.307); Godzilla Minus One (0.293) |
| tfidf_sem_pontuacao | 1 | 3 de 6 | 0.538 | — | soldados, segunda, mundial, guerra, na | Dunkirk (0.252); Corações de Ferro (0.219); Godzilla Minus One (0.182) |
| tfidf_sem_stopwords | 1 | 3 de 6 | 0.544 | — | soldados, segunda, mundial, guerra | Dunkirk (0.255); Corações de Ferro (0.234); Godzilla Minus One (0.194) |
| word2vec_cbow | 2 | 4 de 6 | 0.488 | — | soldados, guerra, mundial, segunda, lutando ≈ lutar | 9º Pelotão (0.576); Corações de Ferro (0.567); Dunkirk (0.552) |
| word2vec_skipgram | 1 | 4 de 6 | 0.705 | — | mundial, soldados, guerra, segunda, lutando ≈ lutar | Corações de Ferro (0.682); Até o Último Homem (0.652); Bastardos Inglórios (0.642) |
| bert_base_pt | 1 | 4 de 6 | 0.769 | — | — | Dunkirk (0.693); Até o Último Homem (0.624); Corações de Ferro (0.602) |
| sentenca_minilm | 1 | 3 de 6 | 0.648 | — | — | Corações de Ferro (0.602); Dunkirk (0.550); 9º Pelotão (0.544) |

### comedia_romantica: “comédia romântica leve sobre um casal que se apaixona”

Romance como trama principal em tom de comédia.

6 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 21 | 0 de 6 | 0.033 | comédia, leve, romântica | que, um, apaixona, se | Madrugada dos Mortos (0.373); A Hora do Pesadelo (0.362); D-Tox (0.355) |
| bow_sem_stopwords | 7 | 0 de 6 | 0.024 | comédia, leve, romântica | apaixona | Invocação do Mal 4: O Último Ritual (0.136); Ted 2 (0.131); Acompanhante Perfeita (0.131) |
| tfidf_sem_pontuacao | 3 | 1 de 6 | 0.078 | comédia, leve, romântica | apaixona, que, um, se | Os Suspeitos (0.155); Five Nights at Freddy's 2 (0.146); 10 Coisas Que Eu Odeio em Você (0.144) |
| tfidf_sem_stopwords | 1 | 1 de 6 | 0.167 | comédia, leve, romântica | apaixona | 10 Coisas Que Eu Odeio em Você (0.138); Acompanhante Perfeita (0.098); Invocação do Mal 4: O Último Ritual (0.098) |
| word2vec_cbow | 8 | 0 de 6 | 0.109 | — | casal ≈ homem, apaixona ≈ transforma, leve ≈ elegante, comédia ≈ hollywood, romântica ≈ prostituta | Titanic (0.535); 9 Canções (0.535); A Centopéia Humana 2 (0.517) |
| word2vec_skipgram | 7 | 0 de 6 | 0.097 | — | apaixona, casal ≈ garoto, romântica ≈ bad-boy, comédia ≈ kat, leve ≈ insuportável | A Morte lhe Cai Bem (0.609); A Centopéia Humana 2 (0.597); Cisne Negro (0.574) |
| bert_base_pt | 4 | 2 de 6 | 0.255 | — | — | 9 Canções (0.719); A Iniciação (0.706); Possessão (0.700) |
| sentenca_minilm | 3 | 1 de 6 | 0.117 | — | — | Infidelidade (0.562); Cinquenta Tons de Liberdade (0.519); La La Land: Cantando Estações (0.509) |

### prisao_injusta: “homem preso injustamente sobrevivendo na prisão”

Vida dentro da prisão; filmes em que o personagem só sai da prisão não contam.

3 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 8 | 0 de 3 | 0.063 | injustamente | prisão | A Hora do Pesadelo (0.159); Rambo: Programado Para Matar (0.143); Meninas Malvadas (0.138) |
| bow_sem_stopwords | 2 | 1 de 3 | 0.181 | injustamente | prisão | Rambo: Programado Para Matar (0.229); Prisioneiro do Inferno (0.160); A Hora do Pesadelo (0.141) |
| tfidf_sem_pontuacao | 1 | 1 de 3 | 0.383 | injustamente | prisão | Prisioneiro do Inferno (0.133); Rambo: Programado Para Matar (0.133); Uma Batalha Após a Outra (0.124) |
| tfidf_sem_stopwords | 2 | 1 de 3 | 0.204 | injustamente | prisão | Rambo: Programado Para Matar (0.147); Prisioneiro do Inferno (0.145); Uma Batalha Após a Outra (0.132) |
| word2vec_cbow | 1 | 2 de 3 | 0.565 | — | prisão, homem ≈ detento, preso ≈ condenado, injustamente ≈ corruptos, sobrevivendo ≈ chegar | Prisioneiro do Inferno (0.611); A Outra História Americana (0.534); Um Sonho de Liberdade (0.529) |
| word2vec_skipgram | 1 | 2 de 3 | 0.681 | — | prisão, preso ≈ condenado, homem ≈ jovem, injustamente ≈ culposo, sobrevivendo ≈ chegar | Prisioneiro do Inferno (0.693); Um Sonho de Liberdade (0.630); A Outra História Americana (0.617) |
| bert_base_pt | 5 | 1 de 3 | 0.303 | — | — | Police Story: A Guerra das Drogas (0.608); O Demolidor (0.596); Os Bons Companheiros (0.594) |
| sentenca_minilm | 1 | 2 de 3 | 0.639 | — | — | Um Sonho de Liberdade (0.609); Jogos Mortais (0.494); À Espera de um Milagre (0.487) |

### mafia: “gângsteres e a máfia”

Crime organizado como tema central.

9 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 14 | 0 de 9 | 0.057 | — | a, e, máfia | Cinquenta Tons de Liberdade (0.424); Avatar: Fogo e Cinzas (0.420); O Exterminador do Futuro (0.417) |
| bow_sem_stopwords | 2 | 4 de 9 | 0.302 | — | máfia | 365 Dias: Hoje (0.243); Os Infiltrados (0.178); Os Bons Companheiros (0.141) |
| tfidf_sem_pontuacao | 2 | 4 de 9 | 0.322 | — | máfia, a, e | 365 Dias: Hoje (0.229); Os Infiltrados (0.175); Os Bons Companheiros (0.150) |
| tfidf_sem_stopwords | 2 | 4 de 9 | 0.302 | — | máfia | 365 Dias: Hoje (0.219); Os Infiltrados (0.166); Os Bons Companheiros (0.133) |
| word2vec_cbow | 1 | 3 de 9 | 0.393 | — | máfia, gângsteres ≈ aflitos | Os Infiltrados (0.537); 365 Dias: Hoje (0.502); Scarface (0.484) |
| word2vec_skipgram | 1 | 3 de 9 | 0.352 | — | gângsteres, máfia ≈ violência | Magnatas do Crime (0.538); 365 Dias: Hoje (0.495); Os Infiltrados (0.492) |
| bert_base_pt | 1 | 2 de 9 | 0.434 | — | — | Os Bons Companheiros (0.599); Magnatas do Crime (0.590); Zootopia: Essa Cidade é o Bicho (0.572) |
| sentenca_minilm | 1 | 3 de 9 | 0.353 | — | — | Magnatas do Crime (0.525); Os Bad Boys (0.516); Os Bons Companheiros (0.510) |

### mundo_falso: “personagem descobre que vive em um mundo falso”

Variação do caso Matrix: nenhuma das três sinopses usa as palavras “mundo falso”.

3 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 2 | 1 de 3 | 0.206 | falso | que, mundo, um, descobre, em | Os Croods (0.436); Free Guy: Assumindo o Controle (0.405); Matador de Aluguel (0.389) |
| bow_sem_stopwords | 1 | 1 de 3 | 0.417 | falso | mundo, descobre, personagem | Free Guy: Assumindo o Controle (0.371); Barbie (0.300); Madrugada dos Mortos (0.217) |
| tfidf_sem_pontuacao | 1 | 1 de 3 | 0.401 | falso | personagem, mundo, descobre, que, um | Free Guy: Assumindo o Controle (0.308); Barbie (0.154); Os Croods (0.140) |
| tfidf_sem_stopwords | 1 | 1 de 3 | 0.389 | falso | personagem, mundo, descobre | Free Guy: Assumindo o Controle (0.304); Barbie (0.156); Madrugada dos Mortos (0.104) |
| word2vec_cbow | 3 | 2 de 3 | 0.249 | — | personagem, descobre, mundo, falso ≈ entediante, vive ≈ precisa | Barbie (0.619); Cidade das Sombras (0.619); Free Guy: Assumindo o Controle (0.590) |
| word2vec_skipgram | 4 | 1 de 3 | 0.165 | — | mundo, descobre, personagem, falso ≈ único, vive ≈ vida | Cidade das Sombras (0.691); Barbie (0.679); Shrek Para Sempre (0.648) |
| bert_base_pt | 6 | 0 de 3 | 0.166 | — | — | Matador de Aluguel (0.765); Conflitos Internos (0.740); Barbie (0.738) |
| sentenca_minilm | 1 | 2 de 3 | 0.473 | — | — | Free Guy: Assumindo o Controle (0.649); Os Caça-Fantasmas 2 (0.564); Avatar (0.561) |

### enganar_a_morte: “jovens escapam de um acidente, mas a morte volta para buscá-los”

Série Premonição; parte das sinopses cita “Morte”, e outras só o pesadelo e o destino.

5 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 1 | 2 de 5 | 0.431 | buscá-los, escapam | a, de, um, acidente, para | Premonição 2 (0.497); O Profissional (0.486); Assim na Terra Como no Inferno (0.462) |
| bow_sem_stopwords | 1 | 2 de 5 | 0.584 | buscá-los, escapam | morte, acidente | Premonição 3 (0.279); Premonição 2 (0.231); Encontro Marcado (0.189) |
| tfidf_sem_pontuacao | 1 | 3 de 5 | 0.645 | buscá-los, escapam | acidente, morte, a, mas, um | Premonição 2 (0.253); Premonição 3 (0.250); Operação Sombra (0.173) |
| tfidf_sem_stopwords | 1 | 2 de 5 | 0.563 | buscá-los, escapam | morte, acidente | Premonição 3 (0.238); Premonição 2 (0.212); Operação Sombra (0.147) |
| word2vec_cbow | 1 | 4 de 5 | 0.818 | — | morte, acidente, jovens ≈ amigos, escapam ≈ tiveram, volta ≈ voltará | Premonição 2 (0.636); Premonição 3 (0.634); Premonição 5 (0.591) |
| word2vec_skipgram | 1 | 3 de 5 | 0.696 | — | morte, acidente, jovens ≈ estudantes, escapam ≈ enganam, buscá-los ≈ enganar | Premonição 3 (0.640); Premonição 2 (0.620); Terror em Silent Hill (0.589) |
| bert_base_pt | 2 | 3 de 5 | 0.462 | — | — | Sobrenatural (0.820); Premonição 2 (0.810); Premonição 6: Laços de Sangue (0.808) |
| sentenca_minilm | 1 | 3 de 5 | 0.665 | — | — | Premonição 3 (0.652); Premonição 2 (0.615); Premonição 5 (0.612) |

### dinossauros: “dinossauros recriados a partir de DNA”

Controle literal: as duas sinopses usam “dinossauros” e “DNA”/“genético”.

2 filme(s) relevante(s).

| Representação | Primeiro relevante | Relevantes no top 5 | AP | Fora do vocabulário | Por que o primeiro relevante foi aproximado | Primeiros resultados |
|---|---:|---:|---:|---|---|---|
| bow_sem_pontuacao | 6 | 0 de 2 | 0.183 | recriados | a, de, dinossauros, dna, partir | Casamento Sangrento (0.438); O Fabuloso Destino de Amélie Poulain (0.436); Sobrenatural: A Origem (0.430) |
| bow_sem_stopwords | 1 | 2 de 2 | 1.000 | recriados | dinossauros, dna, partir | Jurassic Park: O Parque dos Dinossauros (0.344); Jurassic World: Recomeço (0.209); Homem de Ferro (0.101) |
| tfidf_sem_pontuacao | 1 | 2 de 2 | 1.000 | recriados | dinossauros, dna, partir, a, de | Jurassic Park: O Parque dos Dinossauros (0.351); Jurassic World: Recomeço (0.245); Homem de Ferro (0.092) |
| tfidf_sem_stopwords | 1 | 2 de 2 | 1.000 | recriados | dinossauros, dna, partir | Jurassic Park: O Parque dos Dinossauros (0.357); Jurassic World: Recomeço (0.238); Alien: A Ressurreição (0.082) |
| word2vec_cbow | 1 | 2 de 2 | 1.000 | — | partir, dinossauros, dna, recriados ≈ extintos | Jurassic Park: O Parque dos Dinossauros (0.600); Jurassic World: Recomeço (0.555); Círculo de Fogo (0.505) |
| word2vec_skipgram | 1 | 2 de 2 | 1.000 | — | partir, dinossauros, dna, recriados ≈ extintos | Jurassic Park: O Parque dos Dinossauros (0.619); Jurassic World: Recomeço (0.574); Blade Runner: O Caçador de Andróides (0.551) |
| bert_base_pt | 1 | 1 de 2 | 0.538 | — | — | Jurassic Park: O Parque dos Dinossauros (0.627); Alien: A Ressurreição (0.621); Avatar (0.589) |
| sentenca_minilm | 1 | 2 de 2 | 1.000 | — | — | Jurassic World: Recomeço (0.724); Jurassic Park: O Parque dos Dinossauros (0.720); Alien: A Ressurreição (0.489) |

## Síntese comparativa

Propriedades medidas nesta execução, no formato da síntese da aula. Parâmetros aprendidos indicam o custo de memória do modelo; o tempo de construção de cada representação fica em `manifest.json` (`build_seconds`), porque varia entre máquinas.

| Representação | Família | Esparsa | Dimensões | Dimensão = vocabulário | Aprendida | Palavra depende do contexto | Interpretável por palavras | Parâmetros |
|---|---|---|---:|---|---|---|---|---:|
| bow_sem_pontuacao | lexical (contagem) | sim | 5988 | sim | não | não | sim | — |
| bow_sem_stopwords | lexical (contagem) | sim | 5921 | sim | não | não | sim | — |
| tfidf_sem_pontuacao | lexical (contagem) | sim | 5988 | sim | não | não | sim | — |
| tfidf_sem_stopwords | lexical (contagem) | sim | 5921 | sim | não | não | sim | — |
| word2vec_cbow | estática (word2vec) | não | 300 | não | sim | não | sim | 278.9 mi |
| word2vec_skipgram | estática (word2vec) | não | 300 | não | sim | não | sim | 278.9 mi |
| bert_base_pt | contextual (transformer) | não | 768 | não | sim | sim | não | 108.9 mi |
| sentenca_minilm | contextual (transformer) | não | 384 | não | sim | sim | não | 117.7 mi |

A proximidade vetorial passa a refletir melhor a proximidade semântica quando a representação incorpora distribuição, contexto e treinamento em larga escala; em troca, o custo aumenta e a interpretação direta por palavras diminui. As técnicas coexistem: a escolha depende da tarefa, e as consultas anotadas deste projeto ainda são poucas para decidir.

## Limitações

BoW e TF-IDF só comparam termos idênticos após a preparação. Word2vec aproxima palavras usadas em contextos parecidos, mas tem um vetor por palavra (não distingue sentidos) e a média apaga ordem e negação. Transformers dependem do texto usado no treino do modelo; o BERT pré-treinado só com modelagem de linguagem mascarada não foi ajustado para comparar sentenças, e o modelo de sentença trunca sinopses longas. As sondas linguísticas são poucas frases escritas pela equipe: ilustram os conceitos da aula, não medem desempenho. A concordância de gênero e as métricas de clustering usam os recortes de coleta como aproximação; filmes com vários gêneros são ambíguos. As consultas anotadas são poucas e a lista de relevantes é parcial, portanto servem como casos didáticos, não como avaliação estatística.

## Fonte

Dados: The Movie Database (TMDB), https://www.themoviedb.org/. Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB.
Modelos pré-treinados: conforme `model` e `revision` em `config.json`; word2vec do NILC (Hartmann et al., 2017).
