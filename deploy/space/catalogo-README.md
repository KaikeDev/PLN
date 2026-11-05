---
license: other
language:
  - pt
pretty_name: Catálogo do site - sinopses de filmes do TMDB
---

# Catálogo do site: sinopses de filmes do TMDB (site_2026-10-05)

Catálogo de 5.458 filmes com sinopse (coleta de 01/11/2026) usado **só na demonstração** do projeto de PLN 2026/2 (FURB): busca por tema, filmes parecidos e RAG no site publicado. As métricas do projeto foram medidas na amostra avaliada de 428 filmes, que está no repositório; este catálogo não tem gabarito.

Pastas, cada uma com o seu `manifest.json` e os hashes SHA-256 conferidos pelo `verify` do projeto:

- `coleta/site_2026-10-05`: respostas da API do TMDB e `movies.jsonl`;
- `preparacao/site_2026-10-05`: as seis etapas de preparação do texto;
- `representacoes/site_2026-10-05`: vetores das sinopses usados pela busca.

Código, configuração da coleta e documentação: <https://github.com/KaikeDev/PLN>.

## Fonte e atribuição

Dados fornecidos por [The Movie Database (TMDB)](https://www.themoviedb.org/) via [API TMDB](https://developer.themoviedb.org/docs/getting-started). Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB. Os dados preservam as condições de uso da fonte; a redistribuição para a atividade acadêmica não concede uma nova licença sobre sinopses, imagens ou catálogo.
