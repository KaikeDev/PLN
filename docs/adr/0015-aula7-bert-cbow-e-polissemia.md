# 0015 — BERT contextual, CBOW × skip-gram e sondas de polissemia (Aula 7)

- Estado: Aceita
- Data: 2026-09-21

## Contexto

A Aula 7 (Word2Vec e embeddings modernos) pede para:

- explicar a hipótese distribucional;
- distinguir CBOW de skip-gram;
- diferenciar embeddings estáticos de contextuais diante da polissemia;
- comparar BoW, TF-IDF, word2vec e embeddings modernos quanto a informação, custo, interpretabilidade e aplicações.

A Etapa 2 já tinha BoW, TF-IDF, word2vec skip-gram e um modelo de sentenças, mas não tinha um BERT contextual, a variante CBOW nem uma forma de medir a polissemia. Os exemplos da aula (“cachorro/bola” × “cão/brinquedo”, “banco” financeiro × “banco” da praça) não estão no corpus.

## Decisão

- **BERT contextual:** `neuralmind/bert-base-portuguese-cased` (BERTimbau base, licença MIT, 768 dimensões), revisão `94d69c95…`. Ele é carregado pelo mesmo método `contextual` do modelo de sentenças, com *mean pooling* dos vetores dos tokens; o que muda é o modelo configurado, não o código. Os pesos só existem em `pytorch_model.bin`, lido com `torch.load(weights_only=True)` e `trust_remote_code=False` (ADR 0011).
- **Embedding de sentença:** o antigo `contextual_minilm` passa a se chamar `sentenca_minilm`, deixando explícita a distinção da aula entre “contextuais” (BERT pré-treinado com linguagem mascarada) e “embeddings semânticos de textos” (modelo ajustado para similaridade de sentenças).
- **CBOW × skip-gram:** acrescenta-se `pt-mteb/average_pt_nilc_word2vec_cbow_s300` (NILC, 300 dimensões, revisão `0d556458…`) ao skip-gram já usado. Os dois têm o mesmo corpus de treino e a mesma dimensão, então a comparação isola a arquitetura.
- **Vetor da palavra no contexto:** `Representation.word_in_context(texto, palavra)`.
  - No word2vec, devolve o mesmo vetor em qualquer frase.
  - Nos transformers, roda o modelo e faz a média das subpalavras da ocorrência, localizadas pelos deslocamentos de caracteres do tokenizador.
  - BoW e TF-IDF não implementam: a palavra é sempre a mesma coluna.
- **Sondas linguísticas:** ficam em `config/sondas_semanticas.json`, separadas do corpus e das consultas, e são validadas por `app.vectors.probes`. São pares de frases com relação esperada, pares de palavras e palavras polissêmicas com frases rotuladas por sentido (no mínimo dois sentidos; a palavra precisa aparecer em cada frase).
- **Novas análises:**
  - `sentence_pairs`: cosseno e explicação por par de frases.
  - `word_senses`: média de cosseno entre usos do mesmo sentido, média entre sentidos diferentes e a diferença entre elas.
  - `synthesis`: família, esparsidade, dimensões, se é aprendida, se depende do contexto, interpretabilidade e parâmetros.
  - `word_neighbors` passa a incluir os pares de palavras.
- **Custo:** a quantidade de parâmetros aprendidos entra no relatório. O tempo de construção de cada representação vai para `manifest.json` (`build_seconds`) e não para os arquivos de conteúdo, preservando o determinismo (ADR 0009).

## Alternativas consideradas

- **Treinar word2vec no próprio corpus** (gensim): mostraria o treinamento de ponta a ponta, mas 25 mil tokens são insuficientes para vetores úteis e acrescentaria uma dependência. Usar CBOW e skip-gram pré-treinados sobre o mesmo corpus de treino compara as arquiteturas com qualidade.
- **Usar o vetor do token `[CLS]` do BERT:** sem ajuste fino, é pior que a média dos tokens para similaridade.
- **Um método separado `bert`:** duplicaria `ContextualSpace` sem diferença de comportamento.
- **Carregar o BERT só com `transformers`:** o sentence-transformers já aplica a revisão fixada, o `trust_remote_code=False` e o *mean pooling*, e expõe o modelo subjacente para os vetores por token.

## Consequências

- **Tempo e disco:** o build completo baixa cerca de 3,1 GB de modelos na primeira vez e leva perto de 1,5 minuto numa CPU comum. O CI continua sem o extra `semantico` (ADR 0013); os testes usam dublês que implementam `word_vectors` e `parameters`.
- **Anisotropia:** sem ajuste para sentenças, o BERT dá cossenos altos a quase qualquer par e tem MRR baixo nas consultas. O relatório orienta a comparar diferenças entre pares, não valores absolutos.
- **Alcance das sondas:** são poucas frases escritas pela equipe. Ilustram os conceitos da aula e não substituem uma avaliação com consultas anotadas.
