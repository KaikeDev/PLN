# Evidências das representações vetoriais

Representações calculadas sobre 428 sinopses preenchidas de uma pasta processada com hashes verificados. Gêneros de coleta são rótulos aproximados da amostragem, não julgamentos de relevância.

## Representações e dimensões

| Representação | Método | Entrada | Dimensões | Tipo | Densidade | Não nulos por sinopse |
|---|---|---|---:|---|---:|---:|
| bow_sem_pontuacao | bow | 05_without_punctuation.jsonl | 5988 | esparsa | 0.7889% | 47.24 |
| bow_sem_stopwords | bow | 06_without_stopwords.jsonl | 5921 | esparsa | 0.5491% | 32.51 |
| tfidf_sem_pontuacao | tfidf | 05_without_punctuation.jsonl | 5988 | esparsa | 0.7889% | 47.24 |
| tfidf_sem_stopwords | tfidf | 06_without_stopwords.jsonl | 5921 | esparsa | 0.5491% | 32.51 |
| word2vec_sem_stopwords | word2vec | 06_without_stopwords.jsonl | 300 | densa | 100.0000% | 300.00 |
| contextual_minilm | contextual | 02_clean.jsonl | 384 | densa | 100.0000% | 384.00 |

- **bow_sem_pontuacao**, termos de maior peso somado: de, a, e, o, que, um, uma, para, em, com
- **bow_sem_stopwords**, termos de maior peso somado: não, está, ser, após, anos, família, vida, jovem, dois, casa
- **tfidf_sem_pontuacao**, termos de maior peso somado: de, a, o, um, e, que, uma, para, em, do
- **tfidf_sem_stopwords**, termos de maior peso somado: está, não, ser, família, após, anos, vida, jovem, dois, mundo
- **word2vec_sem_stopwords**: 99.69% dos tokens existem no modelo; 5879 palavras distintas do corpus têm vetor; 0 sinopses sem nenhuma palavra conhecida.
- **contextual_minilm**: limite de 128 tokens do modelo; 40 sinopses foram truncadas.

## Similaridade do cosseno

Para cada sinopse foram buscados os 5 vizinhos de maior cosseno. A concordância é a fração desses vizinhos com ao menos um gênero de coleta em comum; a referência é essa fração calculada sobre todos os demais filmes, ou seja, o esperado sem usar o texto. Nas representações lexicais a explicação lista termos idênticos; no word2vec, pares de palavras próximas (≈); o modelo contextual não é explicável por palavras.

| Representação | Concordância de gênero @5 | Referência | Filmes avaliados |
|---|---:|---:|---:|
| bow_sem_pontuacao | 0.3696 | 0.3071 | 428 |
| bow_sem_stopwords | 0.4879 | 0.3071 | 428 |
| tfidf_sem_pontuacao | 0.5023 | 0.3071 | 428 |
| tfidf_sem_stopwords | 0.5164 | 0.3071 | 428 |
| word2vec_sem_stopwords | 0.5168 | 0.3071 | 428 |
| contextual_minilm | 0.5486 | 0.3071 | 428 |

### Vizinhos de Matrix (603)

- **bow_sem_pontuacao**: O Enigma de Outro Mundo (0.602: e, a, que, um, de); Um Sonho de Liberdade (0.599: e, a, que, de, um); Impacto Profundo (0.596: e, a, um, de, que)
- **bow_sem_stopwords**: Barbie (0.168: mundo, começa, descobre, está, real); Possessão (0.151: está, começa, descobre, estranhos, jovem); Madrugada dos Mortos (0.121: mundo, descobre, enquanto, está, real)
- **tfidf_sem_pontuacao**: Possessão (0.145: a, estranhos, e, que, está); Vingadores: Era de Ultron (0.134: sistema, artificial, o, que, da); Barbie (0.132: real, das, mundo, que, começa)
- **tfidf_sem_stopwords**: Barbie (0.086: real, mundo, começa, descobre, está); Vingadores: Era de Ultron (0.080: sistema, artificial); Coringa (0.078: thomas, mente)
- **word2vec_sem_stopwords**: A Mosca (0.787: descobre ≈ percebe, pesadelos ≈ terríveis, começa ≈ vai, jovem ≈ homem, sempre ≈ não); O Máskara (0.738: enquanto, pessoas ≈ mulheres, usa ≈ usar, thomas ≈ carlyle, repete ≈ transforma); Círculo de Fogo (0.738: pessoas, começa ≈ começam, enquanto ≈ entretanto, misteriosos ≈ gigantescos, morpheus ≈ kaiju)
- **contextual_minilm**: Contato (0.588); Monstros S.A. (0.584); A Hora do Pesadelo (0.577)

### Vizinhos de Forrest Gump: O Contador de Histórias (13)

- **bow_sem_pontuacao**: Os Bad Boys (0.438: de, do, e, da, a); A Guerra dos Mundos (0.436: de, do, um, e, o); Aos 14 (0.428: de, e, com, do, um)
- **bow_sem_stopwords**: Invocação do Mal 3: A Ordem do Demônio (0.136: caso, estados, história, unidos); Prenda-Me se For Capaz (0.128: anos, estados, história, unidos); Invocação do Mal (0.127: caso, estados, história, unidos)
- **tfidf_sem_pontuacao**: Sobrenatural: A Última Chave (0.131: infância, caso, de, do, com); Invocação do Mal 3: A Ordem do Demônio (0.126: estados, unidos, caso, história, de); Prenda-Me se For Capaz (0.126: estados, unidos, com, anos, história)
- **tfidf_sem_stopwords**: Sobrenatural: A Última Chave (0.103: infância, caso); Invocação do Mal 3: A Ordem do Demônio (0.086: estados, unidos, caso, história); Adeus, Minha Concubina (0.079: momentos, história, anos)
- **word2vec_sem_stopwords**: Prenda-Me se For Capaz (0.695: estados, anos, história, unidos, continua ≈ está); O Grande Lebowski (0.672: anos, vietnã, guerra, continua ≈ vai, consegue ≈ irá); Entrevista com o Vampiro (0.672: anos, rapaz ≈ homem, consegue ≈ precisa, história ≈ vida, jenny ≈ brad)
- **contextual_minilm**: Prenda-Me se For Capaz (0.543); O Show de Truman: O Show da Vida (0.452); O Grande Lebowski (0.452)

### Vizinhos de Beleza Americana (14)

- **bow_sem_pontuacao**: Contato (0.535: a, e, de, com, sua); Gladiador 2 (0.526: a, de, e, seu, o); O Fabuloso Destino de Amélie Poulain (0.515: a, de, e, sua, que)
- **bow_sem_stopwords**: Homem-Aranha: Sem Volta Para Casa (0.136: vida, ajuda, não, pede); Homem-Aranha: De Volta ao Lar (0.115: vida, não); WALL-E (0.110: vida, conhece)
- **tfidf_sem_pontuacao**: O Fabuloso Destino de Amélie Poulain (0.122: a, sente, sua, de, vida); O Profissional (0.122: vizinho, a, conhece, vida, de); Homem-Aranha: Sem Volta Para Casa (0.121: pede, vida, ajuda, mais, sua)
- **tfidf_sem_stopwords**: Homem-Aranha: Sem Volta Para Casa (0.067: pede, vida, ajuda, não); Barbie (0.064: beleza, começa, não); Thor: Amor e Trovão (0.062: jane, pede, ajuda)
- **word2vec_sem_stopwords**: Garota Exemplar (0.808: começa, dia, pai ≈ marido, amiga ≈ irmã, jane ≈ margo); Da Magia à Sedução (0.796: melhor, vida, volta, momento, pai ≈ marido); 10 Coisas Que Eu Odeio em Você (0.795: dia, amiga ≈ irmã, pai ≈ namorado, conhece ≈ apaixona, impotente ≈ insuportável)
- **contextual_minilm**: Infidelidade (0.532); Uma Noite Alucinante 2 (0.484); 365 Dias: Hoje (0.479)

## Clustering

K-Means com k = 4. ARI, NMI e pureza comparam os clusters com o gênero de coleta dos filmes que vieram de um único gênero; a silhueta usa distância do cosseno e não depende de rótulos. Os termos descritivos vêm da média TF-IDF (sem stopwords) dos membros de cada cluster, o mesmo vocabulário para todas as representações.

| Representação | ARI | NMI | Pureza | Silhueta | Filmes rotulados | Tamanhos |
|---|---:|---:|---:|---:|---:|---|
| bow_sem_pontuacao | 0.0034 | 0.0126 | 0.3016 | 0.0327 | 378 | 120, 110, 85, 113 |
| bow_sem_stopwords | 0.0022 | 0.0098 | 0.3042 | 0.0060 | 378 | 140, 127, 112, 49 |
| tfidf_sem_pontuacao | 0.0022 | 0.0115 | 0.3016 | 0.0009 | 378 | 132, 73, 118, 105 |
| tfidf_sem_stopwords | 0.0216 | 0.0348 | 0.3333 | 0.0009 | 378 | 143, 99, 72, 114 |
| word2vec_sem_stopwords | 0.0582 | 0.0748 | 0.3968 | 0.0621 | 378 | 122, 120, 85, 101 |
| contextual_minilm | 0.0797 | 0.1077 | 0.4365 | 0.0580 | 378 | 114, 136, 86, 92 |

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

### word2vec_sem_stopwords

- Cluster 0 (122 filmes; Terror 52, Ficção científica 47, Comédia 24, Drama 16): está, grupo, dois, ter, após, não, missão, terra, vírus, depois
- Cluster 1 (120 filmes; Drama 46, Comédia 38, Terror 38, Ficção científica 11): família, casa, não, está, vida, anos, jovem, dois, mãe, enquanto
- Cluster 2 (85 filmes; Drama 45, Comédia 25, Ficção científica 15, Terror 11): polícia, ser, jovem, anos, guerra, história, policial, mundial, vida, angeles
- Cluster 3 (101 filmes; Ficção científica 47, Comédia 32, Terror 18, Drama 13): ser, precisa, peter, mundo, jovem, está, ainda, vilão, após, força

### contextual_minilm

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
| word2vec_sem_stopwords | 0.99% | 7.41% | [word2vec_sem_stopwords.projection.svg](word2vec_sem_stopwords.projection.svg) |
| contextual_minilm | 1.31% | 5.75% | [contextual_minilm.projection.svg](contextual_minilm.projection.svg) |

## Palavras vizinhas (word2vec)

Palavras do vocabulário do corpus com maior cosseno em relação a cada palavra de sondagem. Direções próximas indicam contextos de uso parecidos, não sinonímia garantida.

### word2vec_sem_stopwords

- **simulação**: demonstração (0.53), simular (0.53), ferramenta (0.46), processamento (0.41), computador (0.41), dinâmica (0.41), plataforma (0.40), máquina (0.40), rotineira (0.39), rotina (0.39)
- **realidade**: verdade (0.55), visão (0.54), percepção (0.53), situação (0.49), natureza (0.48), ilusão (0.48), história (0.47), dinâmica (0.46), intuição (0.43), utopia (0.43)
- **robô**: androide (0.65), andróide (0.64), monstro (0.64), alienígena (0.63), boneco (0.59), ciborgue (0.59), demônio (0.55), ultron (0.55), avatar (0.55), teletransporte (0.55)
- **fantasma**: monstro (0.66), demônio (0.58), vampiro (0.57), lobisomem (0.56), herói (0.53), assassino (0.53), vilão (0.53), supervilão (0.53), dragão (0.52), misterioso (0.52)
- **amor**: ciúme (0.62), ódio (0.57), paixão (0.54), sonho (0.53), deus (0.53), felicidade (0.52), desejo (0.52), prazer (0.52), eterna (0.50), alma (0.49)
- **guerra**: batalha (0.53), sangrenta (0.50), guerras (0.49), revolta (0.48), pós-guerra (0.45), rebelião (0.44), carnificina (0.43), ex-combatente (0.43), conflito (0.42), horrores (0.40)

## Consultas anotadas

A consulta passa pelas mesmas regras de preparação da entrada de cada representação e vira um vetor no mesmo espaço. A posição é a do primeiro filme anotado como relevante entre os filmes com cosseno positivo.

| Representação | MRR | Acerto @5 |
|---|---:|---:|
| bow_sem_pontuacao | 0.5072 | 0.5000 |
| bow_sem_stopwords | 0.5385 | 0.5000 |
| tfidf_sem_pontuacao | 0.5278 | 0.5000 |
| tfidf_sem_stopwords | 0.5455 | 0.5000 |
| word2vec_sem_stopwords | 0.6000 | 1.0000 |
| contextual_minilm | 0.7500 | 1.0000 |

### matrix_literal: “programador conectado a um sistema de computadores”

Controle literal: todos os termos de conteúdo aparecem na sinopse coletada de Matrix.

| Representação | Posição do relevante | Fora do vocabulário | Por que o relevante foi aproximado | Primeiros resultados |
|---|---:|---|---|---|
| bow_sem_pontuacao | 1 | — | a, de, um, sistema, computadores | Matrix (0.461); Assim na Terra Como no Inferno (0.449); Contra o Tempo (0.429) |
| bow_sem_stopwords | 1 | — | sistema, computadores, conectado, programador | Matrix (0.350); Vingadores: Era de Ultron (0.090); O Enigma do Horizonte (0.087) |
| tfidf_sem_pontuacao | 1 | — | sistema, computadores, conectado, programador, a | Matrix (0.376); Vingadores: Era de Ultron (0.093); O Enigma do Horizonte (0.087) |
| tfidf_sem_stopwords | 1 | — | sistema, computadores, conectado, programador | Matrix (0.377); Vingadores: Era de Ultron (0.085); O Enigma do Horizonte (0.079) |
| word2vec_sem_stopwords | 1 | — | conectado, sistema, programador, computadores | Matrix (0.573); Eu, Robô (0.455); O Jogo da Imitação (0.428) |
| contextual_minilm | 1 | — | — | Matrix (0.371); Ghost in the Shell: O Fantasma do Futuro (0.352); O Jogo da Imitação (0.326) |

### matrix_simulacao: “filme sobre simulação da realidade”

Caso da orientação do professor: “simulação” não aparece literalmente na sinopse coletada de Matrix.

| Representação | Posição do relevante | Fora do vocabulário | Por que o relevante foi aproximado | Primeiros resultados |
|---|---:|---|---|---|
| bow_sem_pontuacao | 69 | simulação | da, realidade | Five Nights at Freddy's 2 (0.234); Hereditário (0.220); Resident Evil: Bem-Vindo a Raccoon City (0.186) |
| bow_sem_stopwords | 13 | simulação | realidade | O Dublê (0.333); Anaconda (0.243); Holocausto Canibal (0.229) |
| tfidf_sem_pontuacao | 18 | simulação | realidade, da | O Dublê (0.227); Anaconda (0.174); Vingadores: Guerra Infinita (0.173) |
| tfidf_sem_stopwords | 11 | simulação | realidade | O Dublê (0.284); Anaconda (0.198); Holocausto Canibal (0.193) |
| word2vec_sem_stopwords | 5 | — | realidade, filme ≈ matrix, simulação ≈ artificial | Free Guy: Assumindo o Controle (0.565); Anaconda (0.540); O Dublê (0.540) |
| contextual_minilm | 2 | — | — | Free Guy: Assumindo o Controle (0.533); Matrix (0.484); A Entidade (0.423) |

## Limitações

BoW e TF-IDF só comparam termos idênticos após a preparação. Word2vec aproxima palavras usadas em contextos parecidos, mas a média apaga ordem e negação. Embeddings contextuais dependem do texto usado no treino do modelo e truncam sinopses longas. A concordância de gênero e as métricas de clustering usam os recortes de coleta como aproximação; filmes com vários gêneros são ambíguos. As consultas anotadas são poucas e a lista de relevantes é parcial, portanto servem como casos didáticos, não como avaliação estatística.

## Fonte

Dados: The Movie Database (TMDB), https://www.themoviedb.org/. Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB.
Modelos pré-treinados: conforme `model` e `revision` em `config.json`; word2vec do NILC (Hartmann et al., 2017).
