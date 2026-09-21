# Decisões e limitações

As decisões estão registradas, com contexto, alternativas e consequências, nas [ADRs](adr/README.md). Esta página resume o que cada uma implica para a entrega.

## Escopo orientado pelo professor

Na orientação em vídeo de 31/08/2026, o professor pede representações sucessivas dos mesmos dados (00:00–00:46), comparação futura e vetorização (00:46–01:25) e um repositório navegável, com dados e transformações localizáveis no README (01:38–02:15). A implementação entrega o corpus, as representações vetoriais e as evidências; não afirma que a recomendação semântica esteja concluída.

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
| Código | Camadas com portas e adaptadores; identificadores em inglês e contrato em português; ruff, mypy e CI | [0004](adr/0004-arquitetura-em-camadas.md), [0008](adr/0008-idioma-do-codigo-e-do-contrato.md), [0013](adr/0013-ferramentas-de-qualidade.md) |

## Limitações

- A amostra tem viés de popularidade e de disponibilidade de metadados. O parâmetro `pt-BR` pede tradução, mas não comprova o idioma de cada sinopse.
- Não há reconhecimento automático de nomes próprios. A versão em minúsculas remove uma pista de identificação de nomes, por isso a versão original é preservada.
- Não há retomada automática da coleta: falhas parciais ficam no manifesto e a próxima execução usa outra pasta. Uma interrupção durante o processamento deixa a pasta sem manifesto completo, portanto inválida como entrega.
- A pesquisa auxiliar não interpreta toda a semântica da negação, títulos alternativos nem perguntas com contexto adicional. "Depois de X" é inclusivo por convenção do protótipo, a refinar em avaliação futura.
- As consultas anotadas da Etapa 2 são poucas e a lista de relevantes é parcial.

## Próximas experiências

Comparar representações com mais consultas e filmes relevantes anotados e selecionar a técnica pela qualidade da recuperação, não só pela redução de tokens ou pelo aumento de TTR. Não foram incorporadas bases externas, avaliações textuais de usuários nem modelos treinados pela equipe.
