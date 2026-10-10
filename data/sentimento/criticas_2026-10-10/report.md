# Análise de sentimentos das críticas

1859 críticas em português do TMDB, de 1634 filmes e 86 autores. O rótulo é a nota que o próprio autor deu ao filme: **negativa** com nota ≤ 4 (414 críticas) e **positiva** com nota ≥ 7 (1008). As 437 do meio ficam fora da polaridade, mas entram na previsão da nota.

Validação cruzada em 5 dobras, com as críticas de um mesmo filme sempre na mesma dobra. Polaridade: regressão logística com classes de peso balanceado, como na classificação de gêneros. Nota: regressão Ridge. Os transformers leem a crítica inteira, em partes que cabem no modelo, e tiram a média dos vetores.

## Polaridade

| Representação | F1 macro | Acurácia | F1 negativo | F1 positivo | F1 macro nas dobras |
|---|---:|---:|---:|---:|---:|
| referência: classe mais frequente | 0,415 | 0,709 | 0,000 | 0,830 | 0,415 ± 0,000 |
| `bert_base_pt` | 0,867 | 0,887 | 0,816 | 0,918 | 0,867 ± 0,030 |
| `tfidf_sem_stopwords` | 0,856 | 0,885 | 0,790 | 0,921 | 0,856 ± 0,037 |
| `tfidf_sem_pontuacao` | 0,847 | 0,878 | 0,778 | 0,916 | 0,847 ± 0,042 |
| `bow_sem_stopwords` | 0,830 | 0,861 | 0,756 | 0,903 | 0,830 ± 0,031 |
| `sentenca_minilm` | 0,820 | 0,844 | 0,754 | 0,886 | 0,820 ± 0,013 |
| `bow_sem_pontuacao` | 0,809 | 0,844 | 0,727 | 0,891 | 0,809 ± 0,034 |
| `word2vec_skipgram` | 0,800 | 0,826 | 0,729 | 0,871 | 0,800 ± 0,024 |
| `word2vec_cbow` | 0,793 | 0,820 | 0,719 | 0,867 | 0,793 ± 0,016 |

Melhor F1 macro: `bert_base_pt`. Matriz de confusão (linhas reais, colunas previstas, negativo e positivo): 356 e 58 entre as negativas; 103 e 905 entre as positivas.

## Nota prevista

| Representação | Erro absoluto médio | Raiz do erro quadrático | Spearman | A até 1 ponto da nota |
|---|---:|---:|---:|---:|
| referência: média do treino | 1,979 | 2,400 | -0,007 | 30,6% |
| `bert_base_pt` | 1,334 | 1,653 | 0,732 | 44,5% |
| `tfidf_sem_pontuacao` | 1,363 | 1,703 | 0,692 | 43,4% |
| `tfidf_sem_stopwords` | 1,367 | 1,715 | 0,687 | 43,8% |
| `bow_sem_stopwords` | 1,398 | 1,758 | 0,683 | 43,9% |
| `bow_sem_pontuacao` | 1,402 | 1,767 | 0,673 | 43,0% |
| `sentenca_minilm` | 1,414 | 1,752 | 0,678 | 42,5% |
| `word2vec_skipgram` | 1,514 | 1,865 | 0,638 | 39,4% |
| `word2vec_cbow` | 1,522 | 1,885 | 0,624 | 38,9% |

Menor erro: `bert_base_pt`, que erra a nota em 1,334 ponto em média.

## Entre autores

Um único autor escreveu 67% das críticas. Polaridade treinando sem ele e testando nele, e o contrário (F1 macro):

| Representação | Treino sem o autor principal → teste nele | Treino só com ele → teste nos demais |
|---|---:|---:|
| `bert_base_pt` | 0,808 | 0,678 |
| `tfidf_sem_stopwords` | 0,507 | 0,716 |
| `tfidf_sem_pontuacao` | 0,474 | 0,673 |
| `bow_sem_stopwords` | 0,647 | 0,612 |
| `sentenca_minilm` | 0,736 | 0,644 |
| `bow_sem_pontuacao` | 0,538 | 0,582 |
| `word2vec_skipgram` | 0,749 | 0,536 |
| `word2vec_cbow` | 0,710 | 0,548 |

## Negação

1276 críticas da polaridade têm "não", "nem", "nunca" ou "sem". Acurácia com e sem esses marcadores:

| Representação | Com negação | Sem negação |
|---|---:|---:|
| `bert_base_pt` | 88,4% | 91,1% |
| `tfidf_sem_stopwords` | 87,8% | 95,2% |
| `tfidf_sem_pontuacao` | 87,0% | 94,5% |
| `bow_sem_stopwords` | 85,1% | 95,2% |
| `sentenca_minilm` | 83,6% | 91,1% |
| `bow_sem_pontuacao` | 83,2% | 94,5% |
| `word2vec_skipgram` | 81,4% | 92,5% |
| `word2vec_cbow` | 80,8% | 92,5% |

## Termos de maior peso

Coeficientes de `tfidf_sem_stopwords` num modelo ajustado com todas as críticas da polaridade (para interpretar, não para avaliar).

| Negativo | Positivo |
|---|---|
| mau | excelente |
| roteiro | bem |
| filme | gostei |
| não | terror |
| ideia | agradável |
| basicamente | melhores |
| nada | muitos |
| qualquer | sempre |
| pior | algumas |
| desinteressante | agora |
| sexo | sou |
| falta | fora |
| decente | excelentes |
| parece | bom |
| fazer | melhor |

## Erros mais confiantes

Críticas em que `bert_base_pt` errou com mais convicção:

- **Parasita**, nota 10: previsto negativo com 99,5%. "Um bom filme não precisa de milhões investidos"
- **No Limite do Amanhã**, nota 7: previsto negativo com 99,1%. "**Um filme eficaz, que funciona razoavelmente, mas que não deixa de parecer um pretexto para o CGI massivo.** Em anos recentes, parece que se convencionou de que basta uma quantidade insana de efeitos especiais para fazer um bom filme. Há imensos filmes que parecem desculpas ou pretextos para uma tonelada de efeitos, CGI e gráficos incríveis, sem grande conteúdo a dar-lhes uma base sólida. Este…"
- **A Hora do Mal**, nota 4: previsto positivo com 99,0%. "“Hora do Desaparecimento” parte de uma premissa sólida e inquietante, capaz de convocar medos coletivos e um suspense social que, à partida, prometia muito mais do que acaba por cumprir. A estrutura em capítulos, centrada em diferentes personagens, permite algum fôlego à narrativa e cria momentos de interesse genuíno, sobretudo quando esboça o impacto do mistério na comunidade. No entanto, a…"
- **Frankenstein de Mary Shelley**, nota 8: previsto negativo com 98,3%. "**Fiel ao livro, mas cheio de presunção.** Quando a jovem Mary Shelley escreveu "Frankenstein", ela estava longe de imaginar o impacto que isso teria. Há literalmente dezenas de filmes que abordam a história, mas o cinema nunca conseguiu fazer um filme que fosse fiel ao romance original. Este filme é o que mais se aproxima, embora também apresente mudanças. Muitas são muito positivas, mas algumas…"
- **Resgate 2**, nota 7: previsto negativo com 98,2%. "Chris Hemsworth deveria se aposentar de Thor e seguir fazendo isso |"
- **Diário de uma Paixão**, nota 4: previsto positivo com 97,2%. "**Mais um filme ultra-romântico com um amor proibido. O bom elenco e as boas actuações são interessantes, mas quase tudo o resto é comum.** Este é o típico romance dramático que sai da mente de Nicholas Sparks, o autor preferido das jovens adolescentes. A história conta o romance entre Noah, um jovem de origens humildes, e Allie, filha de pais ricos que não aprovam aquele namoro e decidem casá-la…"
- **Querida, Estiquei o Bebê**, nota 4: previsto positivo com 96,9%. "**Uma sequela bem orquestrada.** Este filme é a continuação do filme "Querida, Encolhi os Miúdos", um filme de grande sucesso. Aqui, a história continua, com a máquina ainda a funcionar da maneira errada. Desta vez, o filho mais novo do professor Szalinski foi ampliado para a altura de um gigante. E se um bebê normal dá trabalho aos pais, imagine um bebê gigantesco... O filme continua a fazer…"
- **Thunderbolts***, nota 8: previsto negativo com 96,2%. "Depois de anos a tropeçar na fracassada tentativa de explorar o Multiverso com argumentos rebuscados, sem muito sentido ou ambição, somando a uma overdose de novas personagens pobres, chatas e mal exploradas, a Marvel Studios acerta finalmente com Thunderbolts. E fá-lo de forma surpreendente: não ao tentar inovar, mas ao focar-se em contar uma boa história. Thunderbolts é o melhor filme da Marvel…"

## Limitações

- **A nota é do autor, não do texto:** quem dá 4 pode escrever com elogios, e quem dá 8 pode listar defeitos. Parte dos "erros" é esse descompasso.
- **Um autor domina a base:** a validação cruzada mede sobretudo o estilo desse autor; o teste entre autores mostra quanto o resultado se mantém para outras pessoas.
- **Ironia** e opiniões implícitas não têm tratamento específico.
- **Base do TMDB:** poucas críticas em português, escritas por usuários que publicam críticas, e mais positivas que negativas.
