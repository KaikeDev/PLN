# 0024 — Catálogo maior para a busca e a recomendação do site

- Estado: Aceita
- Data: 2026-10-05

## Contexto

A busca por tema ([ADR 0020](0020-busca-hibrida-tfidf-e-sentenca.md)) e os filmes parecidos ([ADR 0023](0023-recomendacao-no-site.md)) só conheciam os 428 filmes da amostra da Etapa 1, de quatro gêneros. Uma busca como "filme de cobra" encontrava só três sinopses sobre o tema. A amostra foi pensada para **avaliar** as técnicas, porque as consultas anotadas exigem ler todas as sinopses. Ela não foi pensada como catálogo de um site.

## Decisão

- **Dois papéis, duas bases:**
  - a **amostra avaliada** (`tmdb_2026-09-12`, 428 sinopses) continua sendo a base de todas as medidas e escolhas: consultas anotadas, métricas, classificação e Jev;
  - o **catálogo do site** (`site_2026-10-05`) é só o conjunto em que a busca por tema e os filmes parecidos procuram.
- **Coleta do catálogo** pelo mesmo pipeline da Etapa 1, com [`config/coleta/coleta_site.json`](../../config/coleta/coleta_site.json):
  - 18 gêneros do TMDB (todos menos "Filme para TV") × os mesmos 3 períodos;
  - 10 páginas por combinação, ordenadas por popularidade, com pelo menos 50 votos;
  - resultado: 10.312 registros recebidos, 5.853 filmes únicos e 5.525 sinopses em português.
- **Vetores calculados uma vez:** [`config/representacoes/vetorizacao_site.json`](../../config/representacoes/vetorizacao_site.json) constrói só as duas representações da busca (TF-IDF sem stopwords e embedding de sentença), com especificações idênticas às da amostra. A API lê os vetores das sinopses do arquivo e carrega o modelo só para codificar as consultas; assim, inicia sem recodificar milhares de sinopses.
- **Mesmos algoritmos e pesos:** 0,3 × TF-IDF + 0,7 × embedding de sentença e os mesmos filtros das regras. Nenhum parâmetro foi reajustado no catálogo.
- **Classificador da tela** continua treinado nas 325 sinopses de um gênero da amostra avaliada, cujo desempenho foi medido ([ADR 0021](0021-classificacao-na-tela.md)).
- **Fora do Git:** o catálogo ocupa dezenas de MB e pode ser refeito com três comandos ([como executar](../tecnico/como-executar.md#catálogo-do-site)). Sem ele, a API usa a amostra avaliada e registra um aviso.
- **Modelo compartilhado:** o embedding de sentença é carregado uma vez e usado pela busca, pela recomendação e pelo classificador.

## Alternativas consideradas

- **Ampliar a própria amostra:** invalidaria as 20 consultas anotadas e todas as métricas entregues, e anotar milhares de sinopses à mão é inviável.
- **Buscar no TMDB ao vivo e reordenar:** cobriria o catálogo inteiro, mas a API do TMDB não busca por tema, e cada busca dependeria de chamadas externas.
- **Versionar o catálogo no Git:** facilitaria a reprodução, mas acrescentaria dezenas de MB de dados derivados. A coleta é refeita em poucos minutos, embora possa trazer filmes um pouco diferentes, porque o ranking do TMDB muda.
- **Treinar o classificador no catálogo:** daria mais exemplos de treino, mas sem uma medida de desempenho comparável à da amostra.

## Consequências

- **Mais filmes encontrados:** a busca por tema e os filmes parecidos passam de 428 para 5.525 sinopses, de 18 gêneros.
- **Qualidade não medida no catálogo:** as consultas anotadas valem só para a amostra. Com mais filmes, há mais candidatos parecidos, que podem ajudar ou atrapalhar o ranking.
- **Viés de popularidade:** o catálogo continua formado pelos filmes mais populares de cada gênero e período.
