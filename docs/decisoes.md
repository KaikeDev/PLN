# Decisões e limitações

As decisões estão registradas, com contexto, alternativas e consequências, nas [ADRs](adr/README.md), e resumidas com as justificativas em [`adr.md`](../adr.md). Esta página resume o que cada uma implica para a entrega.

## Escopo orientado pelo professor

Na orientação em vídeo de 31/08/2026, o professor pede representações sucessivas dos mesmos dados (00:00–00:46), comparação futura e vetorização (00:46–01:25) e um repositório navegável, com dados e transformações localizáveis no README (01:38–02:15). Na Aula 8, o quadro organizou a disciplina em representações (BoW, TF-IDF, word2vec, BERT…) × tarefas (busca, recomendação, agrupamento com visualização e classificação). A implementação aplica cada representação às quatro tarefas ([ADR 0018](adr/0018-tarefas-do-ciclo-de-pln.md)). A recomendação é por conteúdo e é avaliada com os gêneros como aproximação de relevância, sem avaliações de usuários.

## Resumo

| Tema | Decisão | ADR |
|---|---|---|
| Amostra | Quatro gêneros × três períodos, 2 páginas por popularidade, ≥ 50 votos, sem adulto, Matrix (603) como semente | [0014](adr/0014-amostragem-intencional.md) |
| Transformações | Seis saídas com todos os IDs; acentos, números e negações preservados no corpus; sem stemming ou lematização por padrão | [0003](adr/0003-normalizacao-do-corpus-e-da-pesquisa.md) |
| Reprodutibilidade | Pasta nova a cada execução, manifesto SHA-256, saída determinística com LF; a amostra salva é a referência | [0009](adr/0009-saidas-imutaveis-e-verificaveis.md), [0010](adr/0010-dados-versionados-no-git.md) |
| Falhas de coleta | Timeout, até 3 retries com backoff para 429/5xx, intervalo entre chamadas; erros guardam só tipo e status | [0007](adr/0007-cliente-http-e-cache.md) |
| Credencial e API | Só Bearer em cabeçalho, API em localhost, CORS restrito, limite de requisições | [0002](adr/0002-credencial-e-exposicao-da-api.md) |
| Pesquisa auxiliar | Regras léxicas com limiares nomeados; título exato tem prioridade no modo automático | [0005](adr/0005-pesquisa-por-regras-lexicas.md), [0006](adr/0006-prioridade-de-titulo-exato.md) |
| Vetorização | Tokens da Etapa 1, cosseno com norma L2, K-Means com k = 4, SVD 2D, modelos com revisão fixa | [0011](adr/0011-formatos-e-modelos-seguros.md), [0012](adr/0012-parametros-do-experimento-vetorial.md) |
| Aula 7 | BERTimbau, word2vec CBOW × skip-gram, sondas de polissemia e síntese comparativa | [0015](adr/0015-aula7-bert-cbow-e-polissemia.md) |
| Classificação na tela | Regressão logística da Etapa 3 sobre o embedding de sentença, ajustada com as 325 sinopses de um gênero; `GET /classificacao` | [0021](adr/0021-classificacao-na-tela.md) |
| Aula 8 | Classificação de gêneros com as oito representações, classificadores alternativos e K-Means × classificador | [0017](adr/0017-aula8-classificacao-de-generos.md) |
| Tarefas | Busca, recomendação, agrupamento e visualização para cada representação; rótulos unificados; vetores densos reaproveitados | [0018](adr/0018-tarefas-do-ciclo-de-pln.md) |
| Busca por tema | 0,3 × TF-IDF sem stopwords + 0,7 × embedding de sentença, escolhida em 20 consultas anotadas; filtros das regras aplicados aos filmes da amostra | [0020](adr/0020-busca-hibrida-tfidf-e-sentenca.md) |
| Aula 8 | Gênero pelo Jev (Choice + um Noul por gênero, sem treino) × TF-IDF + regressão logística treinada fora da amostra; 120 filmes; respostas guardadas e reaproveitáveis | [0019](adr/0019-aula8-jev-classificacao-de-genero.md) |
| Repositório | Sem comentários fora de docstrings; `.gitignore` para segredos, modelos, dados não entregues e arquivos locais | [0001](adr/0001-registrar-decisoes-em-adrs.md), [0016](adr/0016-politica-do-gitignore.md) |
| Código | Camadas com portas e adaptadores; identificadores em inglês e contrato em português; ruff, mypy e CI | [0004](adr/0004-arquitetura-em-camadas.md), [0008](adr/0008-idioma-do-codigo-e-do-contrato.md), [0013](adr/0013-ferramentas-de-qualidade.md) |

## Limitações

- A amostra tem viés de popularidade e de disponibilidade de metadados. O parâmetro `pt-BR` pede tradução, mas não comprova o idioma de cada sinopse.
- Não há reconhecimento automático de nomes próprios. A versão em minúsculas remove uma pista de identificação de nomes, por isso a versão original é preservada.
- Não há retomada automática da coleta: falhas parciais ficam no manifesto e a próxima execução usa outra pasta. Uma interrupção durante o processamento deixa a pasta sem manifesto completo, portanto inválida como entrega.
- A pesquisa auxiliar não interpreta toda a semântica da negação, títulos alternativos nem perguntas com contexto adicional. "Depois de X" é inclusivo por convenção do protótipo, a refinar em avaliação futura.
- As 20 consultas anotadas foram escritas e julgadas pela equipe; servem para comparar representações, não como avaliação com usuários. A busca por tema cobre só os filmes da amostra.
- A recomendação é avaliada por gênero compartilhado: dois filmes do mesmo gênero não são necessariamente boas recomendações um para o outro. Não há avaliações de usuários para uma avaliação colaborativa.
- Na Aula 8, o rótulo de gênero são os `genre_ids` do TMDB restritos aos quatro gêneros, e muitos filmes têm gêneros fora dessas opções (ação, romance, suspense). O Jev foi refeito com esse rótulo ([ADR 0019](adr/0019-aula8-jev-classificacao-de-genero.md)). O Jev é um serviço externo e pago: uma nova execução depende da chave e pode usar outro modelo por trás do alias `jev-latest`. A redação das perguntas faz parte da tarefa.

## Próximas experiências

Comparar representações com mais consultas e filmes relevantes anotados e selecionar a técnica pela qualidade da busca e da recomendação, não só pela redução de tokens ou pelo aumento de TTR. Na Aula 8, testar outras redações das perguntas ao Jev, usar o Score quando houver um rótulo ordinal expresso no texto e revisar manualmente os casos de baixa confiança. Não foram incorporadas bases externas, avaliações textuais de usuários nem modelos treinados pela equipe.
