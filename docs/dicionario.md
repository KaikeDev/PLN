# Dicionário de dados

A unidade principal é um filme identificado pelo inteiro `id` do TMDB. O título não é chave: obras diferentes podem ser homônimas. JSON e JSONL preservam listas, tipos numéricos e valores null sem convertê-los em texto.

## Dados brutos

| Arquivo | Estrutura e significado |
|---|---|
| `responses/NNN.json` | Resposta JSON de cada chamada, sem campos de autenticação. Mantém inclusive metadados de paginação e repetições entre consultas. A serialização é formatada, não uma cópia dos bytes HTTP. |
| `movies.jsonl` | Uma linha por filme; primeira ocorrência recebida de cada ID, conservada sem transformação de campos. |
| `genres.json` | Mapa de gêneros retornado por `/genre/movie/list`, com `genres[] = {id, name}`. |
| `memberships.json` | Objeto com chaves de ID em texto e listas de recortes que retornaram o filme, por exemplo `genre_878_1980_1999`. |
| `config.json` | Cópia dos parâmetros da coleta. |
| `manifest.json` | Estado da execução, horários UTC, endpoint, parâmetros não secretos, arquivo e hash de cada resposta, erros, contagens e hashes dos dados/configuração/código. |

Campos principais das respostas de filmes:

| Campo | Tipo | Significado e tratamento |
|---|---|---|
| `id` | Inteiro | Identificador obrigatório; usado para deduplicação e relacionamentos. |
| `title` | Texto | Título retornado conforme idioma solicitado; mantido como recebido. |
| `original_title` | Texto | Título original da obra; mantido como recebido. |
| `overview` | Texto, null ou ausente | Sinopse. Null, vazio e somente espaços contam como ausência. Nenhum filme é excluído por isso. |
| `original_language` | Texto | Idioma original da obra; não identifica automaticamente o idioma da sinopse. |
| `release_date` | Texto | Data esperada no formato AAAA-MM-DD; vazio/ausente gera grupo `unknown` na distribuição temporal. |
| `genre_ids` | Lista de inteiros | IDs retornados pela descoberta; filmes podem ter vários gêneros. |
| `genres` | Lista de objetos | Detalhes podem retornar `{id, name}`; na exportação é convertido para `genre_ids`. |
| `vote_average` | Número | Nota agregada na fonte; não é texto de avaliação nem rótulo de sentimento. |
| `vote_count` | Inteiro | Quantidade de votos; usado como critério de seleção na coleta. |
| Demais campos | Conforme a resposta | Conservados no bruto; não entram no processamento de sinopses nesta etapa. |

## Representações processadas

| Arquivo/campo | Tipo | Regra |
|---|---|---|
| `id`, em todos os arquivos JSONL | Inteiro | Mesma ordem e mesmos IDs em todas as seis representações e nos metadados. |
| `01_original.jsonl` → `text` | Texto ou null | Copia `overview`; campo ausente vira null. O JSON bruto permite distinguir ausência da chave e null. |
| `02_clean.jsonl` → `text` | Texto ou null | Limpeza de marcações, URLs, caracteres de controle e espaços; Unicode NFC. |
| `03_normalized.jsonl` → `text` | Texto ou null | `casefold` sobre a versão limpa; mantém acentos. |
| `04_tokens.jsonl` → `tokens` | Lista de textos | Tokenização com pontuação; usa a expressão documentada no manifesto. |
| `05_without_punctuation.jsonl` → `tokens` | Lista de textos | Mantém tokens com pelo menos uma letra ou dígito. |
| `06_without_stopwords.jsonl` → `tokens` | Lista de textos | Aplica a lista versionada; conserva não, nem, nunca e sem. |
| `07_bag_of_words.json` | Objeto JSON | Vetorização numélica Bag of Words (frequências de termos, vocabulário e vetores esparsos por filme). |
| `metadata.jsonl` | Objeto por linha | `id`, `title`, `original_title`, `original_language`, `release_date`, `genre_ids`, `vote_average`, `vote_count`, `overview_missing`. |
| `overview_missing` | Booleano | True quando a sinopse original é null, ausente, vazia ou só contém espaços. |
| `stopwords_used.json` | Lista de textos | Lista efetivamente aplicada, normalizada e sem as exceções de negação. |
| `examples.json` | Lista de objetos | Filme, título e as seis representações para inspeção direta. |
| `statistics.json` | Objeto | Contagens, extensão, vocabulário, frequências e medidas por recorte. |
| `manifest.json` | Objeto | Identidade das entradas, regras, versão do Python e SHA-256 dos arquivos gerados. |

Textos ausentes geram listas vazias nas etapas tokenizadas. As métricas de extensão e vocabulário usam apenas as sinopses originalmente preenchidas; as contagens de filmes e ausência usam toda a base. Títulos ficam nos metadados e não passam pelo filtro de stopwords.

## Definições das medidas

- Registros recebidos: ocorrências de filmes em respostas de descoberta e detalhes; respostas da lista de gêneros não entram nessa contagem.
- Duplicatas removidas: registros recebidos menos IDs únicos. É a quantidade de ocorrências repetidas, não a quantidade de filmes que têm repetição.
- TTR: número de tokens distintos dividido pelo total de tokens. Não significa porcentagem de palavras que aparecem uma única vez.
- Média/mediana de tokens: calculadas por sinopse válida, excluindo tokens isolados de pontuação. O original mantém maiúsculas; a normalização pode reduzir tipos sem reduzir a contagem de tokens.
- Frequências por gênero e recorte não são categorias mutuamente exclusivas; suas somas podem superar o total de filmes.
- Hash SHA-256 detecta alteração em relação ao manifesto. Não é assinatura digital e não impede a alteração conjunta do arquivo e do manifesto.
