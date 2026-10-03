# 0020 — Busca do site por tema: TF-IDF + embedding de sentença, com os filtros das regras

- Estado: Aceita
- Data: 2026-09-29

## Contexto

A busca do site entendia título e preferências por regras (gênero, período, nota, negação), mas descartava o tema. Em "quero um filme de ação sobre máquinas", ela reconhecia "ação" e ignorava "máquinas", devolvendo os filmes de ação mais populares do TMDB. O projeto já tinha oito representações das sinopses (Etapa 2 e Aula 7), mas só duas consultas anotadas, ambas sobre Matrix, o que não bastava para escolher uma delas.

## Decisão

- **Avaliação antes da escolha:** `config/consultas.json` passou de 2 para 20 consultas, escritas como um usuário digitaria. A equipe fechou os relevantes lendo as 428 sinopses antes de rodar qualquer ranking. A análise `retrieval` ganhou a precisão média (MAP) e a precisão @5, que consideram todos os relevantes, e não só o primeiro, como o MRR e o acerto @5.
- **Resultado de cada representação** (20 consultas):

  | Representação | MAP | MRR | Acerto @5 |
  |---|---:|---:|---:|
  | `sentenca_minilm` | 0,560 | 0,879 | 100% |
  | `tfidf_sem_pontuacao` | 0,460 | 0,844 | 95% |
  | `tfidf_sem_stopwords` | 0,446 | 0,880 | 95% |
  | `bow_sem_stopwords` | 0,375 | 0,765 | 90% |
  | `word2vec_skipgram` | 0,356 | 0,592 | 80% |
  | `word2vec_cbow` | 0,333 | 0,557 | 75% |
  | `bert_base_pt` | 0,295 | 0,489 | 75% |
  | `bow_sem_pontuacao` | 0,188 | 0,357 | 45% |

- **Combinação escolhida:** 0,3 × `tfidf_sem_stopwords` + 0,7 × `sentenca_minilm` (MAP de 0,613, MRR de 0,912, acerto @5 de 100%).
  - Antes da soma, o cosseno de cada representação é dividido pelo maior cosseno dela na consulta, porque o TF-IDF esparso e o embedding denso têm escalas diferentes.
  - Os pesos ficam em `config/busca.json`; a combinação, em `app.vectors.hybrid`; e o comando `python -m app.vectors hybrid --queries` refaz a comparação.
- **Integração com as regras:** o novo modo `sinopse` ordena os filmes da amostra pela combinação e aplica os mesmos filtros da descoberta, aos campos do TMDB de cada filme: gêneros incluídos e excluídos, período, ano, nota e votos. O modo `auto` passa a usar essa ordem:
  1. título exato;
  2. sinopse, se encontrar filmes;
  3. descoberta no TMDB;
  4. busca por título.
- **Execução:** a API carrega o índice uma vez, na inicialização, a partir da amostra entregue:
  - verifica as pastas bruta e processada e confere que a processada veio da bruta;
  - usa as mesmas especificações e revisões de modelo de `vetorizacao_semantica.json`.

  Sem o extra `semantico` ou com falha no carregamento, a API sobe assim mesmo, e o modo `sinopse` responde "Busca por sinopse indisponível".

## Alternativas consideradas

- **Só o `sentenca_minilm`:** era o melhor sozinho, mas perde nas consultas com palavra-chave forte. Em "zumbis", o MAP foi de 0,34, contra 0,62 do TF-IDF.
- **Fusão por posição (RRF, k = 60):** não tem pesos a ajustar, mas deu MAP de 0,573. A soma ponderada aproveita o tamanho do cosseno e não só a posição.
- **Acrescentar o `word2vec_skipgram`** (0,2 / 0,3 / 0,5): MAP de 0,617 e MRR de 0,950, praticamente iguais à escolhida, ao custo de mais um modelo de cerca de 1,1 GB no servidor.
- **BERTimbau ou CBOW na combinação:** sozinhos ficaram abaixo do TF-IDF e não melhoraram a soma ponderada.
- **Pesos escolhidos pelo maior MAP** (0,2 / 0,8, MAP de 0,622): com 20 consultas, as diferenças abaixo de 0,01 são ruído. Qualquer peso do TF-IDF entre 0,2 e 0,4 dá MAP de 0,60 a 0,62; 0,3 fica no meio dessa faixa.
- **Jev para ordenar:** exigiria uma chamada paga por filme a cada busca.

## Consequências

- **Risco de pesos ajustados às consultas:** foi controlado sorteando 500 vezes metade das consultas para escolher o peso e medindo na outra metade. A combinação superou o `sentenca_minilm` sozinho em 95% das divisões, com ganho médio de 0,05 no MAP. Consulta a consulta, a combinação melhora 13 das 20 e piora 4.
- **Alcance:** a busca por tema só cobre os 428 filmes com sinopse da amostra. Filmes fora dela continuam acessíveis pelo título e pela descoberta.
- **Custo:** a API passa a depender do torch e do modelo de sentença (cerca de 0,5 GB) e demora alguns segundos a mais para iniciar.
- **Limites:** consultas sobre tom, como "comédia romântica leve" (MAP de 0,12), continuam fracas no ranking; os filtros de gênero das regras compensam em parte. As consultas foram escritas e julgadas pela equipe e são poucas; não são uma avaliação com usuários.
