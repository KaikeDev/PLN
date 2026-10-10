# 7. Análise de sentimentos

Aplica a análise de sentimentos da Aula 9 a **críticas de filmes**: ler o texto de uma crítica e prever se ela é **positiva ou negativa** e **qual nota** o autor deu ao filme. Decisões na [ADR 0026](adr/0026-analise-de-sentimentos.md).

| Parte | Resultado | Onde |
|---|---|---|
| Dados | 1.859 críticas em português do TMDB, de 1.634 filmes, cada uma com a nota do próprio autor | [`data/coleta/criticas_2026-10-10/`](../data/coleta/criticas_2026-10-10/) |
| Polaridade | F1 macro de **0,867** (BERTimbau) e 0,856 (TF-IDF), contra 0,415 de chutar sempre "positivo" | [relatório](../data/sentimento/criticas_2026-10-10/report.md) |
| Nota de 0 a 10 | Erro médio de **1,33 ponto** (BERTimbau), contra 1,98 de chutar a média | [relatório](../data/sentimento/criticas_2026-10-10/report.md) |
| Na tela do site | Aba "Analisar crítica": sentimento, nota prevista e palavras que mais pesaram | [`sentiment/live.py`](../backend/src/app/sentiment/live.py) |

## Por que críticas, e não sinopses

Uma sinopse descreve o filme e não dá opinião, então não tem sentimento a medir. Já as críticas do TMDB (`/movie/{id}/reviews`) vêm com a **nota que o autor deu ao filme**: texto e rótulo no mesmo objeto, um conjunto supervisionado pronto, **sem anotação manual**.

| Nota do autor | Rótulo | Críticas |
|---|---|---:|
| 0 a 4 | negativa | 414 |
| 5 a 6 | fora da polaridade (só na previsão da nota) | 437 |
| 7 a 10 | positiva | 1.008 |

## Como os dados foram montados

1. **Coleta:** as críticas em português dos 5.853 filmes do catálogo do site. Foram 5.853 chamadas e cerca de 6 minutos, e vieram 2.008 críticas de 1.710 filmes. O autor vira um **código anônimo**; nome, usuário e avatar não são gravados.
2. **Preparação**, com as mesmas seis etapas de texto da Etapa 1. A limpeza **preserva as negações** ("não", "nem", "nunca", "sem"), importantes para o sentimento.
   - **Críticas bilíngues:** 187 críticas têm uma seção "**Português**" e outra "**English**"; só a parte em português é usada.
   - **Ficam de fora:** 107 críticas sem nota, 24 em outro idioma e 18 curtas demais (menos de 30 caracteres).
3. **Experimento:** as 8 representações da Etapa 2 com os mesmos classificadores da classificação de gêneros.
   - **Polaridade:** regressão logística com classes balanceadas.
   - **Nota:** regressão Ridge.
   - **Validação:** cruzada em 5 dobras, com **as críticas de um mesmo filme sempre na mesma dobra**, para o modelo não acertar pelo nome do filme.
4. **Textos longos:** uma crítica tem mediana de 339 palavras, e o MiniLM lê só 128 tokens. Os transformers leem a crítica **em partes** e tiram a média dos vetores, para não perder o veredito, que costuma vir no fim.

## Resultados

### Polaridade

| Representação | F1 macro | Acurácia | F1 negativo | F1 positivo |
|---|---:|---:|---:|---:|
| referência: sempre "positivo" | 0,415 | 0,709 | 0,000 | 0,830 |
| **BERTimbau** | **0,867** | **0,887** | **0,816** | 0,918 |
| TF-IDF sem stopwords | 0,856 | 0,885 | 0,790 | **0,921** |
| TF-IDF sem pontuação | 0,847 | 0,878 | 0,778 | 0,916 |
| BoW sem stopwords | 0,830 | 0,861 | 0,756 | 0,903 |
| MiniLM (embedding de sentença) | 0,820 | 0,844 | 0,754 | 0,886 |
| BoW sem pontuação | 0,809 | 0,844 | 0,727 | 0,891 |
| word2vec skip-gram | 0,800 | 0,826 | 0,729 | 0,871 |
| word2vec CBOW | 0,793 | 0,820 | 0,719 | 0,867 |

### Nota prevista

| Representação | Erro médio (pontos) | Spearman | A até 1 ponto da nota real |
|---|---:|---:|---:|
| referência: média do treino | 1,98 | 0,00 | 30,6% |
| **BERTimbau** | **1,33** | **0,73** | **44,5%** |
| TF-IDF sem pontuação | 1,36 | 0,69 | 43,4% |
| TF-IDF sem stopwords | 1,37 | 0,69 | 43,8% |
| MiniLM | 1,41 | 0,68 | 42,5% |
| word2vec CBOW | 1,52 | 0,62 | 38,9% |

### O que os números mostram

- **TF-IDF quase empata com o BERTimbau.** Em críticas, as palavras de opinião ("excelente", "gostei", "mau", "pior", "desinteressante") já carregam boa parte do sentimento. Ao contrário da busca e da classificação de gêneros, o BERTimbau aqui é o melhor: lendo a crítica inteira, ele capta frases como "funciona razoavelmente, mas…".
- **Um autor escreveu 67% das críticas.** O teste mais revelador treina sem esse autor e testa nele:

  | Representação | Treino sem o autor principal → teste nele (F1 macro) |
  |---|---:|
  | BERTimbau | **0,808** |
  | word2vec skip-gram | 0,749 |
  | MiniLM | 0,736 |
  | TF-IDF sem stopwords | 0,507 |

  O TF-IDF decora o vocabulário de quem mais escreve e cai quase ao acaso com outra pessoa; os vetores pré-treinados generalizam muito melhor.
- **Negação atrapalha todos.** As críticas com "não", "nem", "nunca" ou "sem" têm acurácia menor: 87,8% contra 95,2% no TF-IDF. O BERTimbau é o que menos sofre: 88,4% contra 91,1%.
- **Erros com mais convicção** vêm de críticas curtas ou de tom misto. *Parasita*, com nota 10, tem a crítica "Um bom filme não precisa de milhões investidos", e o BERTimbau previu negativo com 99,5%.

## Na tela do site

A aba **"Analisar crítica"** usa o **TF-IDF sem stopwords**, ajustado com as 1.422 críticas da polaridade. Ela mostra:

- o **sentimento previsto** e a probabilidade;
- a **nota prevista**, de 0 a 10;
- as **palavras do texto que mais puxaram** para cada lado (peso do modelo × valor no TF-IDF).

O BERTimbau é 0,011 melhor no F1, mas levou **39 minutos** para codificar as críticas, contra menos de 1 segundo do TF-IDF; com ele, a API demoraria esse tempo para iniciar. O TF-IDF também permite mostrar as palavras que decidiram.

Os quatro exemplos da tela foram **escritos pela equipe** e mostram os desafios da aula:

| Exemplo | Previsão | O que mostra |
|---|---|---|
| "Que filme maravilhoso! A fotografia é deslumbrante…" | positivo, 99,7%; nota 9,3 | Caso fácil |
| "Uma perda de tempo. O roteiro é confuso…" | negativo; nota 4,5 | Caso fácil |
| "Não é um filme ruim. Não chega a ser uma obra-prima, mas não decepciona…" | **negativo**; nota 4,9 | **Negação:** "não" e "ruim" pesam contra, mesmo negando o defeito |
| "Ótimo, mais uma continuação que ninguém pediu… Genial." | **positivo**, 95,5% | **Ironia:** "ótimo" e "genial" enganam o modelo |

## Como executar

Em `backend`:

```bash
# 1. coleta (TMDB_BEARER_TOKEN; cerca de 6 minutos; precisa do catálogo do site)
uv run --frozen python -m app.sentiment collect --movies ../data/preparacao/site_2026-10-05 --config ../config/sentimento/coleta_criticas.json --output ../data/coleta/criticas_<data>
# 2. preparação, sem rede (segundos); a pasta preparada fica fora do Git e é usada pelo site
uv run --frozen python -m app.sentiment process --input ../data/coleta/criticas_2026-10-10 --output ../data/preparacao/criticas_2026-10-10 --stopwords ../config/coleta/stopwords_pt.txt
# 3. experimento com as 8 representações (cerca de 45 minutos; 39 deles no BERTimbau)
uv run --frozen --extra semantico python -m app.sentiment build --input ../data/preparacao/criticas_2026-10-10 --output ../data/sentimento/<nova_pasta> --config ../config/sentimento/sentimento.json
# conferir qualquer uma das três pastas
uv run --frozen python -m app.sentiment verify --input ../data/sentimento/criticas_2026-10-10
```

A coleta entregue (`data/coleta/criticas_2026-10-10`) e o experimento (`data/sentimento/criticas_2026-10-10`) estão no Git. A preparação é refeita com o passo 2; sem ela, a aba "Analisar crítica" responde "Análise de sentimento indisponível".

## Onde está no código

| Parte | Arquivo |
|---|---|
| Coleta das críticas | [backend/src/app/sentiment/collect.py](../backend/src/app/sentiment/collect.py) |
| Filtro, seções bilíngues e etapas de texto | [backend/src/app/sentiment/process.py](../backend/src/app/sentiment/process.py) |
| Transformers em partes | [backend/src/app/sentiment/encoders.py](../backend/src/app/sentiment/encoders.py) |
| Experimento, dobras por filme, teste entre autores | [backend/src/app/sentiment/pipeline.py](../backend/src/app/sentiment/pipeline.py), [evaluation.py](../backend/src/app/sentiment/evaluation.py) |
| Modelo da tela e rota `/sentimento` | [backend/src/app/sentiment/live.py](../backend/src/app/sentiment/live.py), [backend/src/app/api/routes/sentiment.py](../backend/src/app/api/routes/sentiment.py) |
| Configurações | [config/sentimento/](../config/sentimento/) |

## Limitações

- **A nota é do autor, não do texto.** Quem dá 4 pode escrever elogios, e quem dá 8 pode listar defeitos. Parte dos "erros" é esse descompasso.
- **Um autor domina a base:** 67% das críticas. A validação cruzada mede sobretudo o estilo dele; o teste entre autores mostra quanto o resultado cai com outras pessoas.
- **Negação e ironia** não têm tratamento específico. A tela mostra os dois casos.
- **Base pequena e desequilibrada:** há poucas críticas em português no TMDB, e 71% das críticas da polaridade são positivas.
