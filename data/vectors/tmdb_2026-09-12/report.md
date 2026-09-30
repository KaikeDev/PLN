# Evidências das representações vetoriais

Representações calculadas sobre 428 sinopses preenchidas de uma pasta processada com hashes verificados. As seções seguem as tarefas do ciclo de PLN aplicadas a cada representação: busca, recomendação, agrupamento e visualização; a classificação é a Etapa 3. Os rótulos de gênero são os `genre_ids` do TMDB restritos aos gêneros da coleta (Comédia, Drama, Ficção científica, Terror): servem de aproximação de relevância, não de julgamento humano.

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

## Busca: consultas anotadas

Busca é recuperação de informação: um texto de consulta vira um vetor no mesmo espaço das sinopses, que são ordenadas pelo cosseno. A consulta passa pelas mesmas regras de preparação da entrada de cada representação. A posição é a do primeiro filme anotado como relevante entre os filmes com cosseno positivo.

| Representação | MRR | Acerto @5 |
|---|---:|---:|
| bow_sem_pontuacao | 0.5072 | 0.5000 |
| bow_sem_stopwords | 0.5385 | 0.5000 |
| tfidf_sem_pontuacao | 0.5278 | 0.5000 |
| tfidf_sem_stopwords | 0.5455 | 0.5000 |
| word2vec_cbow | 0.5263 | 0.5000 |
| word2vec_skipgram | 0.6000 | 1.0000 |
| bert_base_pt | 0.3000 | 0.5000 |
| sentenca_minilm | 0.7500 | 1.0000 |

### matrix_literal: “programador conectado a um sistema de computadores”

Controle literal: todos os termos de conteúdo aparecem na sinopse coletada de Matrix.

| Representação | Posição do relevante | Fora do vocabulário | Por que o relevante foi aproximado | Primeiros resultados |
|---|---:|---|---|---|
| bow_sem_pontuacao | 1 | — | a, de, um, sistema, computadores | Matrix (0.461); Assim na Terra Como no Inferno (0.449); Contra o Tempo (0.429) |
| bow_sem_stopwords | 1 | — | sistema, computadores, conectado, programador | Matrix (0.350); Vingadores: Era de Ultron (0.090); O Enigma do Horizonte (0.087) |
| tfidf_sem_pontuacao | 1 | — | sistema, computadores, conectado, programador, a | Matrix (0.376); Vingadores: Era de Ultron (0.093); O Enigma do Horizonte (0.087) |
| tfidf_sem_stopwords | 1 | — | sistema, computadores, conectado, programador | Matrix (0.377); Vingadores: Era de Ultron (0.085); O Enigma do Horizonte (0.079) |
| word2vec_cbow | 1 | — | programador, conectado, sistema, computadores | Matrix (0.569); Free Guy: Assumindo o Controle (0.409); A Guerra dos Mundos (0.407) |
| word2vec_skipgram | 1 | — | conectado, sistema, programador, computadores | Matrix (0.573); Eu, Robô (0.455); O Jogo da Imitação (0.428) |
| bert_base_pt | 2 | — | — | A Guerra dos Mundos (0.631); Matrix (0.628); Operação Sombra (0.622) |
| sentenca_minilm | 1 | — | — | Matrix (0.371); Ghost in the Shell: O Fantasma do Futuro (0.352); O Jogo da Imitação (0.326) |

### matrix_simulacao: “filme sobre simulação da realidade”

Caso da orientação do professor: “simulação” não aparece literalmente na sinopse coletada de Matrix.

| Representação | Posição do relevante | Fora do vocabulário | Por que o relevante foi aproximado | Primeiros resultados |
|---|---:|---|---|---|
| bow_sem_pontuacao | 69 | simulação | da, realidade | Five Nights at Freddy's 2 (0.234); Hereditário (0.220); Resident Evil: Bem-Vindo a Raccoon City (0.186) |
| bow_sem_stopwords | 13 | simulação | realidade | O Dublê (0.333); Anaconda (0.243); Holocausto Canibal (0.229) |
| tfidf_sem_pontuacao | 18 | simulação | realidade, da | O Dublê (0.227); Anaconda (0.174); Vingadores: Guerra Infinita (0.173) |
| tfidf_sem_stopwords | 11 | simulação | realidade | O Dublê (0.284); Anaconda (0.198); Holocausto Canibal (0.193) |
| word2vec_cbow | 19 | — | realidade, simulação ≈ ilusão, filme ≈ sonho | Free Guy: Assumindo o Controle (0.584); O Dublê (0.555); Anaconda (0.554) |
| word2vec_skipgram | 5 | — | realidade, filme ≈ matrix, simulação ≈ artificial | Free Guy: Assumindo o Controle (0.565); Anaconda (0.540); O Dublê (0.540) |
| bert_base_pt | 10 | — | — | Uma Odisséia Chinesa: Parte Dois – Cinderela (0.609); Meninas Malvadas (0.563); Frankenstein (0.546) |
| sentenca_minilm | 2 | — | — | Free Guy: Assumindo o Controle (0.533); Matrix (0.484); A Entidade (0.423) |

## Recomendação: filmes parecidos

Recomendação por conteúdo: para cada filme, os 5 filmes de maior cosseno com a sinopse dele (item → item); para um perfil, os de maior cosseno com a média dos filmes de que a pessoa gostou. Sem avaliações de usuários, a relevância é aproximada pelos gêneros: a precisão @k é a fração dos recomendados com ao menos um gênero em comum, e a referência é essa fração sobre todos os demais filmes, o esperado de uma recomendação que ignora o texto. As recomendações de todos os filmes estão em `<representação>.recommendations.jsonl`. Nas representações lexicais a explicação lista termos idênticos; no word2vec, pares de palavras próximas (≈); o modelo contextual não é explicável por palavras.

| Representação | Precisão @5 | Referência | Ganho sobre a referência | Filmes avaliados |
|---|---:|---:|---:|---:|
| bow_sem_pontuacao | 0.4505 | 0.3791 | 0.0713 | 428 |
| bow_sem_stopwords | 0.5607 | 0.3791 | 0.1816 | 428 |
| tfidf_sem_pontuacao | 0.5696 | 0.3791 | 0.1905 | 428 |
| tfidf_sem_stopwords | 0.5780 | 0.3791 | 0.1989 | 428 |
| word2vec_cbow | 0.5575 | 0.3791 | 0.1784 | 428 |
| word2vec_skipgram | 0.6019 | 0.3791 | 0.2228 | 428 |
| bert_base_pt | 0.6355 | 0.3791 | 0.2564 | 428 |
| sentenca_minilm | 0.6257 | 0.3791 | 0.2466 | 428 |

### Quem gostou de Matrix (603)

Gêneros: Ficção científica.

- **bow_sem_pontuacao**: O Enigma de Outro Mundo (0.602: e, a, que, um, de); Um Sonho de Liberdade (0.599: e, a, que, de, um); Impacto Profundo (0.596: e, a, um, de, que)
- **bow_sem_stopwords**: Barbie (0.168: mundo, começa, descobre, está, real); Possessão (0.151: está, começa, descobre, estranhos, jovem); Madrugada dos Mortos (0.121: mundo, descobre, enquanto, está, real)
- **tfidf_sem_pontuacao**: Possessão (0.145: a, estranhos, e, que, está); Vingadores: Era de Ultron (0.134: sistema, artificial, o, que, da); Barbie (0.132: real, das, mundo, que, começa)
- **tfidf_sem_stopwords**: Barbie (0.086: real, mundo, começa, descobre, está); Vingadores: Era de Ultron (0.080: sistema, artificial); Coringa (0.078: thomas, mente)
- **word2vec_cbow**: Monstros S.A. (0.672: energia, mundo, pessoas ≈ crianças, thomas ≈ mike, sonho ≈ astro); O Incrível Hulk (0.669: está, conhece ≈ ama, vítima ≈ mulher, repete ≈ transforme, produzir ≈ explorar); Vingadores: Era de Ultron (0.667: artificial, sistema, cria ≈ gera, mundo ≈ planeta, conhece ≈ constrói)
- **word2vec_skipgram**: A Mosca (0.787: descobre ≈ percebe, pesadelos ≈ terríveis, começa ≈ vai, jovem ≈ homem, sempre ≈ não); O Máskara (0.738: enquanto, pessoas ≈ mulheres, usa ≈ usar, thomas ≈ carlyle, repete ≈ transforma); Círculo de Fogo (0.738: pessoas, começa ≈ começam, enquanto ≈ entretanto, misteriosos ≈ gigantescos, morpheus ≈ kaiju)
- **bert_base_pt**: A Hora do Pesadelo (0.913); Círculo de Fogo (0.908); A Mosca (0.907)
- **sentenca_minilm**: Contato (0.588); Monstros S.A. (0.584); A Hora do Pesadelo (0.577)

### Quem gostou de Forrest Gump: O Contador de Histórias (13)

Gêneros: Comédia, Drama.

- **bow_sem_pontuacao**: Os Bad Boys (0.438: de, do, e, da, a); A Guerra dos Mundos (0.436: de, do, um, e, o); Aos 14 (0.428: de, e, com, do, um)
- **bow_sem_stopwords**: Invocação do Mal 3: A Ordem do Demônio (0.136: caso, estados, história, unidos); Prenda-Me se For Capaz (0.128: anos, estados, história, unidos); Invocação do Mal (0.127: caso, estados, história, unidos)
- **tfidf_sem_pontuacao**: Sobrenatural: A Última Chave (0.131: infância, caso, de, do, com); Invocação do Mal 3: A Ordem do Demônio (0.126: estados, unidos, caso, história, de); Prenda-Me se For Capaz (0.126: estados, unidos, com, anos, história)
- **tfidf_sem_stopwords**: Sobrenatural: A Última Chave (0.103: infância, caso); Invocação do Mal 3: A Ordem do Demônio (0.086: estados, unidos, caso, história); Adeus, Minha Concubina (0.079: momentos, história, anos)
- **word2vec_cbow**: Prenda-Me se For Capaz (0.656: anos, história, estados, unidos, rapaz ≈ ladrão); Entrevista com o Vampiro (0.639: anos, rapaz ≈ homem, consegue ≈ precisa, história ≈ vida, intenções ≈ experiências); Terror em Silent Hill (0.638: anos, consegue ≈ vai, continua ≈ começa, rapaz ≈ carro, amor ≈ sofrimento)
- **word2vec_skipgram**: Prenda-Me se For Capaz (0.695: estados, anos, história, unidos, continua ≈ está); O Grande Lebowski (0.672: anos, vietnã, guerra, continua ≈ vai, consegue ≈ irá); Entrevista com o Vampiro (0.672: anos, rapaz ≈ homem, consegue ≈ precisa, história ≈ vida, jenny ≈ brad)
- **bert_base_pt**: O Grande Lebowski (0.911); Infidelidade (0.891); Diário de uma Paixão (0.889)
- **sentenca_minilm**: Prenda-Me se For Capaz (0.543); O Show de Truman: O Show da Vida (0.452); O Grande Lebowski (0.452)

### Quem gostou de Beleza Americana (14)

Gêneros: Drama.

- **bow_sem_pontuacao**: Contato (0.535: a, e, de, com, sua); Gladiador 2 (0.526: a, de, e, seu, o); O Fabuloso Destino de Amélie Poulain (0.515: a, de, e, sua, que)
- **bow_sem_stopwords**: Homem-Aranha: Sem Volta Para Casa (0.136: vida, ajuda, não, pede); Homem-Aranha: De Volta ao Lar (0.115: vida, não); WALL-E (0.110: vida, conhece)
- **tfidf_sem_pontuacao**: O Fabuloso Destino de Amélie Poulain (0.122: a, sente, sua, de, vida); O Profissional (0.122: vizinho, a, conhece, vida, de); Homem-Aranha: Sem Volta Para Casa (0.121: pede, vida, ajuda, mais, sua)
- **tfidf_sem_stopwords**: Homem-Aranha: Sem Volta Para Casa (0.067: pede, vida, ajuda, não); Barbie (0.064: beleza, começa, não); Thor: Amor e Trovão (0.062: jane, pede, ajuda)
- **word2vec_cbow**: Garota Exemplar (0.753: dia, começa, pai ≈ marido, amiga ≈ irmã, reconstruir ≈ descobrir); Da Magia à Sedução (0.730: momento, melhor, vida, volta, pai ≈ marido); Crepúsculo (0.728: volta, pai, amiga ≈ mãe, conhece ≈ sabe, masturba ≈ apaixonam)
- **word2vec_skipgram**: Garota Exemplar (0.808: começa, dia, pai ≈ marido, amiga ≈ irmã, jane ≈ margo); Da Magia à Sedução (0.796: melhor, vida, volta, momento, pai ≈ marido); 10 Coisas Que Eu Odeio em Você (0.795: dia, amiga ≈ irmã, pai ≈ namorado, conhece ≈ apaixona, impotente ≈ insuportável)
- **bert_base_pt**: Todo Mundo Quase Morto (0.925); Infidelidade (0.921); Diário de uma Paixão (0.915)
- **sentenca_minilm**: Infidelidade (0.532); Uma Noite Alucinante 2 (0.484); 365 Dias: Hoje (0.479)

### Perfil `ficcao_mente_realidade`: gostou de Matrix, A Origem, Brilho Eterno de uma Mente sem Lembranças

Gostou de ficção científica sobre mente, sonho e realidade.

Gêneros do perfil: Drama, Ficção científica.

| Representação | Precisão @5 | Primeiras recomendações |
|---|---:|---|
| bow_sem_pontuacao | 0.6000 | Fim dos Dias (0.627); Free Guy: Assumindo o Controle (0.626); O Fabuloso Destino de Amélie Poulain (0.622) |
| bow_sem_stopwords | 0.4000 | Divertida Mente 2 (0.124); Possessão (0.117); Duna: Parte Dois (0.112) |
| tfidf_sem_pontuacao | 0.4000 | Free Guy: Assumindo o Controle (0.171); Duna: Parte Dois (0.160); O Padre: Massacre no Dia de Ação de Graças (0.156) |
| tfidf_sem_stopwords | 0.8000 | Coringa (0.087); Divertida Mente 2 (0.081); Thor: Ragnarok (0.067) |
| word2vec_cbow | 0.4000 | O Incrível Hulk (0.754); Todo Mundo Quase Morto (0.742); O Máskara (0.741) |
| word2vec_skipgram | 0.8000 | O Incrível Hulk (0.807); Mad Max: Estrada da Fúria (0.804); Sua Culpa (0.802) |
| bert_base_pt | 0.4000 | A Hora do Pesadelo (0.937); Uma Noite Alucinante: A Morte do Demônio (0.936); O Incrível Hulk (0.935) |
| sentenca_minilm | 0.4000 | Contato (0.580); Gato de Botas (0.570); O Espetacular Homem-Aranha 2: A Ameaça de Electro (0.559) |

### Perfil `terror_sobrenatural`: gostou de Invocação do Mal, Hereditário, Sobrenatural: A Origem

Gostou de terror sobrenatural dentro de casa e da família.

Gêneros do perfil: Terror.

| Representação | Precisão @5 | Primeiras recomendações |
|---|---:|---|
| bow_sem_pontuacao | 0.2000 | Tropas Estelares (0.582); Casamento Sangrento (0.580); O Fabuloso Destino de Amélie Poulain (0.575) |
| bow_sem_stopwords | 0.2000 | Patos! (0.203); Parasita (0.196); Um Lugar Silencioso (0.182) |
| tfidf_sem_pontuacao | 0.8000 | Sobrenatural: A Última Chave (0.175); Invocação do Mal 4: O Último Ritual (0.174); Patos! (0.165) |
| tfidf_sem_stopwords | 0.8000 | Invocação do Mal 4: O Último Ritual (0.131); Um Lugar Silencioso (0.127); Sobrenatural: A Última Chave (0.115) |
| word2vec_cbow | 0.2000 | Da Magia à Sedução (0.774); Terror em Silent Hill (0.772); Patos! (0.771) |
| word2vec_skipgram | 0.4000 | Da Magia à Sedução (0.804); Terror em Silent Hill (0.801); Invocação do Mal 2 (0.800) |
| bert_base_pt | 1.0000 | Terror em Silent Hill (0.937); A Morte do Demônio (0.934); Constantine (0.931) |
| sentenca_minilm | 1.0000 | Invocação do Mal 2 (0.717); Invocação do Mal 4: O Último Ritual (0.684); A Morte do Demônio (0.644) |

### Perfil `animacao_familia`: gostou de Toy Story: Um Mundo de Aventuras, Up: Altas Aventuras, Monstros S.A.

Gostou de animações para toda a família.

Gêneros do perfil: Comédia.

| Representação | Precisão @5 | Primeiras recomendações |
|---|---:|---|
| bow_sem_pontuacao | 0.6000 | A Casa Monstro (0.666); O Fabuloso Destino de Amélie Poulain (0.648); Fim dos Dias (0.643) |
| bow_sem_stopwords | 1.0000 | Toy Story 3 (0.279); Toy Story 4 (0.198); Toy Story 2 (0.166) |
| tfidf_sem_pontuacao | 0.8000 | Toy Story 3 (0.272); Toy Story 2 (0.242); A Casa Monstro (0.212) |
| tfidf_sem_stopwords | 0.8000 | Toy Story 3 (0.248); Toy Story 2 (0.160); Toy Story 4 (0.139) |
| word2vec_cbow | 1.0000 | Zoopocalipse - Uma Aventura Animal (0.804); Toy Story 2 (0.801); A Casa Monstro (0.796) |
| word2vec_skipgram | 0.6000 | Uma Noite de Crime: Anarquia (0.822); Zoopocalipse - Uma Aventura Animal (0.822); A Casa Monstro (0.821) |
| bert_base_pt | 0.6000 | A Casa Monstro (0.955); 365 Dias: Hoje (0.949); Uma Noite de Crime: Anarquia (0.945) |
| sentenca_minilm | 0.2000 | O Gigante de Ferro (0.633); Os Caça-Fantasmas 2 (0.596); A Mosca (0.577) |

## Agrupamento (K-Means)

K-Means com k = 4, sem rótulos. ARI, NMI e pureza comparam os clusters com o gênero dos filmes que têm exatamente um gênero da coleta; a silhueta usa distância do cosseno e não depende de rótulos. Os termos descritivos vêm da média TF-IDF (sem stopwords) dos membros de cada cluster, o mesmo vocabulário para todas as representações. O gráfico de cada representação é a projeção da seção seguinte colorida pelo cluster encontrado.

| Representação | ARI | NMI | Pureza | Silhueta | Filmes rotulados | Tamanhos | Gráfico |
|---|---:|---:|---:|---:|---:|---|---|
| bow_sem_pontuacao | 0.0025 | 0.0131 | 0.3169 | 0.0327 | 325 | 120, 110, 85, 113 | [bow_sem_pontuacao.clusters.svg](bow_sem_pontuacao.clusters.svg) |
| bow_sem_stopwords | 0.0003 | 0.0138 | 0.2985 | 0.0060 | 325 | 140, 127, 112, 49 | [bow_sem_stopwords.clusters.svg](bow_sem_stopwords.clusters.svg) |
| tfidf_sem_pontuacao | 0.0011 | 0.0107 | 0.3138 | 0.0009 | 325 | 132, 73, 118, 105 | [tfidf_sem_pontuacao.clusters.svg](tfidf_sem_pontuacao.clusters.svg) |
| tfidf_sem_stopwords | 0.0244 | 0.0441 | 0.3508 | 0.0009 | 325 | 143, 99, 72, 114 | [tfidf_sem_stopwords.clusters.svg](tfidf_sem_stopwords.clusters.svg) |
| word2vec_cbow | 0.0600 | 0.0720 | 0.4031 | 0.0423 | 325 | 113, 96, 99, 120 | [word2vec_cbow.clusters.svg](word2vec_cbow.clusters.svg) |
| word2vec_skipgram | 0.0615 | 0.0797 | 0.4123 | 0.0621 | 325 | 122, 120, 85, 101 | [word2vec_skipgram.clusters.svg](word2vec_skipgram.clusters.svg) |
| bert_base_pt | 0.1442 | 0.1681 | 0.4892 | 0.0601 | 325 | 88, 106, 136, 98 | [bert_base_pt.clusters.svg](bert_base_pt.clusters.svg) |
| sentenca_minilm | 0.0869 | 0.1211 | 0.4462 | 0.0580 | 325 | 114, 136, 86, 92 | [sentenca_minilm.clusters.svg](sentenca_minilm.clusters.svg) |

### bow_sem_pontuacao

- Cluster 0 (120 filmes; Comédia 48, Drama 38, Ficção científica 34, Terror 34): ser, grupo, não, anos, jovem, depois, amigos, está, mundo, todos
- Cluster 1 (110 filmes; Ficção científica 38, Comédia 37, Drama 32, Terror 24): ser, está, agora, não, mundo, anos, dois, planeta, após, amigos
- Cluster 2 (85 filmes; Drama 31, Ficção científica 31, Terror 28, Comédia 21): dois, novo, família, jovem, cidade, após, não, nova, trás, passado
- Cluster 3 (113 filmes; Ficção científica 41, Drama 35, Terror 33, Comédia 30): está, família, casa, vida, não, após, começa, ser, morte, contra

### bow_sem_stopwords

- Cluster 0 (140 filmes; Drama 48, Ficção científica 44, Comédia 43, Terror 37): família, dois, jovem, casa, história, pai, mãe, relacionamento, futuro, jornada
- Cluster 1 (127 filmes; Terror 47, Ficção científica 42, Comédia 38, Drama 33): está, não, após, cidade, grupo, vírus, jovem, caminho, anos, encontrar
- Cluster 2 (112 filmes; Drama 39, Ficção científica 39, Comédia 37, Terror 27): ser, vida, anos, ter, onde, não, andy, jovem, amigos, após
- Cluster 3 (49 filmes; Ficção científica 19, Comédia 18, Drama 16, Terror 8): tempo, mesmo, dia, preso, mundo, soldado, precisa, decide, terra, está

### tfidf_sem_pontuacao

- Cluster 0 (132 filmes; Ficção científica 55, Terror 40, Drama 39, Comédia 32): guerra, está, grupo, tempo, futuro, missão, terra, família, mundial, não
- Cluster 1 (73 filmes; Comédia 29, Drama 26, Terror 23, Ficção científica 16): não, ser, vida, anos, após, começa, mundo, depois, mãe, está
- Cluster 2 (118 filmes; Comédia 42, Drama 40, Ficção científica 33, Terror 27): família, ser, não, jovem, após, está, dois, anos, crime, casa
- Cluster 3 (105 filmes; Ficção científica 40, Comédia 33, Drama 31, Terror 29): está, mundo, fazer, deve, anos, agora, filho, casa, dois, descobre

### tfidf_sem_stopwords

- Cluster 0 (143 filmes; Ficção científica 51, Drama 48, Terror 43, Comédia 37): morte, família, após, jovem, depois, não, anos, agora, mundo, já
- Cluster 1 (99 filmes; Comédia 38, Drama 38, Ficção científica 27, Terror 18): dois, não, está, amor, juntos, vida, anos, durante, precisam, família
- Cluster 2 (72 filmes; Drama 31, Ficção científica 30, Comédia 16, Terror 12): ser, homem, passa, combater, vida, depois, alta, ferro, tecnologia, tony
- Cluster 3 (114 filmes; Terror 46, Comédia 45, Ficção científica 36, Drama 19): casa, está, amigos, enquanto, família, anos, cidade, após, grupo, única

### word2vec_cbow

- Cluster 0 (113 filmes; Drama 46, Comédia 44, Terror 43, Ficção científica 18): família, casa, anos, vida, não, está, começa, morte, dois, mãe
- Cluster 1 (96 filmes; Comédia 40, Ficção científica 38, Terror 31, Drama 11): dois, grupo, amigos, todos, antes, cidade, terra, planeta, robô, precisam
- Cluster 2 (99 filmes; Drama 41, Comédia 35, Ficção científica 22, Terror 20): ser, jovem, não, peter, vida, está, anos, andy, angeles, caso
- Cluster 3 (120 filmes; Ficção científica 66, Drama 38, Terror 25, Comédia 17): está, após, mundo, contra, grupo, ser, missão, guerra, planeta, ainda

### word2vec_skipgram

- Cluster 0 (122 filmes; Ficção científica 60, Terror 52, Comédia 27, Drama 19): está, grupo, dois, ter, após, não, missão, terra, vírus, depois
- Cluster 1 (120 filmes; Drama 54, Comédia 47, Terror 38, Ficção científica 15): família, casa, não, está, vida, anos, jovem, dois, mãe, enquanto
- Cluster 2 (85 filmes; Drama 45, Comédia 25, Ficção científica 15, Terror 11): polícia, ser, jovem, anos, guerra, história, policial, mundial, vida, angeles
- Cluster 3 (101 filmes; Ficção científica 54, Comédia 37, Drama 18, Terror 18): ser, precisa, peter, mundo, jovem, está, ainda, vilão, após, força

### bert_base_pt

- Cluster 0 (88 filmes; Terror 50, Ficção científica 45, Comédia 15, Drama 11): grupo, vírus, cidade, está, missão, terra, planeta, equipe, após, única
- Cluster 1 (106 filmes; Ficção científica 67, Comédia 39, Drama 10, Terror 10): peter, ser, precisa, mundo, está, vilão, planeta, após, agora, contra
- Cluster 2 (136 filmes; Comédia 61, Drama 54, Terror 43, Ficção científica 20): casa, não, família, está, anos, amigos, vida, dois, ser, jovem
- Cluster 3 (98 filmes; Drama 61, Comédia 21, Terror 16, Ficção científica 12): jovem, durante, ser, anos, polícia, guerra, dois, policial, história, após

### sentenca_minilm

- Cluster 0 (114 filmes; Terror 51, Drama 48, Comédia 38, Ficção científica 9): família, casa, dois, está, não, amigos, começa, vida, anos, morte
- Cluster 1 (136 filmes; Drama 60, Ficção científica 42, Comédia 38, Terror 20): ser, jovem, homem, vida, não, peter, está, mundo, durante, policial
- Cluster 2 (86 filmes; Ficção científica 63, Terror 25, Drama 14, Comédia 12): missão, grupo, planeta, terra, está, vírus, após, equipe, robô, não
- Cluster 3 (92 filmes; Comédia 48, Ficção científica 30, Terror 23, Drama 14): família, novo, anos, mundo, encontrar, não, casa, pai, amigos, agora

## Visualização: projeção em duas dimensões

TruncatedSVD reduz as dimensões a dois componentes para inspeção visual (nas matrizes lexicais, é a LSA). Variância explicada baixa indica que o plano mostra só parte da estrutura; distâncias no gráfico não substituem o cosseno original. Sem centralização, o primeiro componente tende a seguir a direção média das sinopses e pode explicar menos variância que o segundo. Cada representação tem dois gráficos com as mesmas coordenadas: um colorido pelo gênero e outro pelo cluster do K-Means. Comparar os dois mostra se os grupos encontrados sem rótulos seguem os gêneros.

| Representação | Variância componente 1 | Variância componente 2 | Por gênero | Por cluster |
|---|---:|---:|---|---|
| bow_sem_pontuacao | 1.40% | 4.07% | [bow_sem_pontuacao.projection.svg](bow_sem_pontuacao.projection.svg) | [bow_sem_pontuacao.clusters.svg](bow_sem_pontuacao.clusters.svg) |
| bow_sem_stopwords | 0.34% | 0.90% | [bow_sem_stopwords.projection.svg](bow_sem_stopwords.projection.svg) | [bow_sem_stopwords.clusters.svg](bow_sem_stopwords.clusters.svg) |
| tfidf_sem_pontuacao | 0.24% | 0.62% | [tfidf_sem_pontuacao.projection.svg](tfidf_sem_pontuacao.projection.svg) | [tfidf_sem_pontuacao.clusters.svg](tfidf_sem_pontuacao.clusters.svg) |
| tfidf_sem_stopwords | 0.13% | 0.50% | [tfidf_sem_stopwords.projection.svg](tfidf_sem_stopwords.projection.svg) | [tfidf_sem_stopwords.clusters.svg](tfidf_sem_stopwords.clusters.svg) |
| word2vec_cbow | 0.86% | 4.72% | [word2vec_cbow.projection.svg](word2vec_cbow.projection.svg) | [word2vec_cbow.clusters.svg](word2vec_cbow.clusters.svg) |
| word2vec_skipgram | 0.99% | 7.41% | [word2vec_skipgram.projection.svg](word2vec_skipgram.projection.svg) | [word2vec_skipgram.clusters.svg](word2vec_skipgram.clusters.svg) |
| bert_base_pt | 0.53% | 6.97% | [bert_base_pt.projection.svg](bert_base_pt.projection.svg) | [bert_base_pt.clusters.svg](bert_base_pt.clusters.svg) |
| sentenca_minilm | 1.31% | 5.75% | [sentenca_minilm.projection.svg](sentenca_minilm.projection.svg) | [sentenca_minilm.clusters.svg](sentenca_minilm.clusters.svg) |

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

BoW e TF-IDF só comparam termos idênticos após a preparação. Word2vec aproxima palavras usadas em contextos parecidos, mas tem um vetor por palavra (não distingue sentidos) e a média apaga ordem e negação. Transformers dependem do texto usado no treino do modelo; o BERT pré-treinado só com modelagem de linguagem mascarada não foi ajustado para comparar sentenças, e o modelo de sentença trunca sinopses longas. As sondas linguísticas são poucas frases escritas pela equipe: ilustram os conceitos da aula, não medem desempenho. A precisão da recomendação e as métricas de agrupamento usam os gêneros como aproximação de relevância: dois filmes do mesmo gênero não são necessariamente boas recomendações um para o outro, e filmes com vários gêneros são ambíguos. As consultas anotadas são poucas e a lista de relevantes é parcial, portanto servem como casos didáticos, não como avaliação estatística.

## Fonte

Dados: The Movie Database (TMDB), https://www.themoviedb.org/. Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB.
Modelos pré-treinados: conforme `model` e `revision` em `config.json`; word2vec do NILC (Hartmann et al., 2017).
