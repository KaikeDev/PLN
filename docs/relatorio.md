UNIVERSIDADE REGIONAL DE BLUMENAU
CENTRO DE CIÊNCIAS EXATAS E NATURAIS
CURSO DE CIÊNCIA DA COMPUTAÇÃO

Disciplina: Processamento de Linguagem Natural (2026/2)

# Etapa Prática 1 — Coleta e preparação de dados textuais

Equipe: Kaike Ventura Tuerpe, Luana Nitsche, Pedro Henrique Ortunio e Thiago Bodnar

Repositório: https://github.com/KaikeDev/PLN
Branch da entrega: codex/etapa1-corpus-transformacoes

## 1 Base de dados textuais

Peso na rubrica: 0,4. O projeto prepara sinopses de filmes para comparar técnicas de processamento de linguagem natural e, posteriormente, apoiar a recuperação de obras por conteúdo. A fonte principal é a API do The Movie Database (TMDB), que fornece textos associados a identificadores, títulos, gêneros e outros metadados. A aplicação de consulta a filmes é uma demonstração auxiliar desse projeto.

A orientação do professor reforçou que cada transformação deve gerar uma representação identificável dos mesmos dados. Por isso, a entrega conserva o corpus original, cinco representações derivadas e os arquivos necessários para reproduzir o processamento. A escolha da técnica mais adequada à recuperação será feita em uma etapa posterior; a redução do número de tokens não é tomada como evidência de melhor resultado.

### Justificativa da escolha

O TMDB permite relacionar o conteúdo das sinopses a filmes concretos, mantendo títulos e identificadores para inspeção. Sinopses apresentam descrições de personagens, acontecimentos e contextos, enquanto os metadados permitem definir recortes comparáveis. O parâmetro pt-BR solicita textos localizados, mas a presença de uma sinopse não comprova automaticamente que ela esteja em português; essa cobertura requer inspeção própria.

A coleta real produziu 430 filmes únicos, com 428 sinopses preenchidas e 2 ausentes. Os dados estão organizados em arquivos JSON e JSONL. Perguntas de teste e regras de interpretação permanecem separadas do corpus de filmes, evitando confundir exemplos escritos pela equipe com textos recebidos do TMDB.

## 2 Amostragem e caracterização

A amostra foi coletada em 12/09/2026, entre 21:08:39 e 21:09:01 UTC. Foram cruzados quatro gêneros — Drama, Comédia, Terror e Ficção científica — com três intervalos de lançamento: 1980–1999, 2000–2014 e 2015–2025. Para cada um dos 12 recortes foram solicitadas duas páginas, ordenadas por popularidade, com mínimo de 50 votos e exclusão de conteúdo adulto. Esses limites são escolhas operacionais da experiência.

A execução realizou 26 chamadas bem-sucedidas: uma lista de gêneros, 24 páginas de descoberta e uma consulta de detalhes de Matrix, ID 603, incluída para acompanhar o exemplo citado pelo professor. O total de 481 ocorrências foi deduplicado por ID, conservando a primeira ocorrência de cada filme e registrando todos os recortes nos quais ele apareceu. O manifesto indica coleta completa.

| Medida | Resultado |
| --- | --- |
| Ocorrências recebidas / duplicatas removidas | 481 / 51 |
| Filmes únicos / sinopses preenchidas | 430 / 428 |
| Sinopses ausentes | 2 de 430 — 0,47% |
| Extensão original média / mediana | 347,44 / 327 caracteres |
| Tokens lexicais por sinopse — média / mediana | 58,44 / 54 |
| Idiomas originais distintos das obras | 15 |
| Sinopses alteradas pela limpeza | 4 |

### Abrangência e limites

O conjunto inclui filmes de cinco décadas e obras com 15 idiomas originais. Há 386 obras com idioma original inglês, o que evidencia concentração da amostra. A ordenação por popularidade e o mínimo de votos favorecem obras mais conhecidas; os grupos possuem gêneros sobrepostos. Portanto, o conjunto é uma amostra intencional e não representa estatisticamente todo o catálogo do TMDB.

As medidas de comprimento e vocabulário usam as 428 sinopses originalmente preenchidas. As medidas de ausência usam todos os 430 filmes. “Tipos” significa tokens distintos, e a razão tipo/token é calculada pela divisão entre tipos e ocorrências. Não foram estimadas proporções de nomes próprios nem usados os percentuais sem cálculo apresentados na versão inicial do trabalho.

## 3 Organização e dicionário dos dados

A unidade do corpus é o filme, identificado pelo campo id. Títulos iguais não indicam necessariamente duplicidade. O diretório data/raw/tmdb_2026-09-12 conserva respostas, configuração, registros deduplicados e proveniência; data/processed/tmdb_2026-09-12 reúne representações, metadados e resultados. O dicionário completo está em docs/dicionario.md.

| Campo ou arquivo | Tipo e significado |
| --- | --- |
| id | Inteiro obrigatório; chave que relaciona o filme entre todas as etapas. |
| title / original_title | Textos preservados nos metadados; não recebem remoção de stopwords. |
| overview | Texto, null ou ausente no bruto. Vazio e somente espaços também contam como ausência. |
| original_language | Código do idioma original da obra; não é o idioma comprovado da sinopse. |
| release_date | Data como texto AAAA-MM-DD; ausência é identificada na distribuição temporal. |
| genre_ids / genres | Lista de IDs na descoberta ou objetos nos detalhes; a exportação unifica em genre_ids. |
| vote_average / vote_count | Nota agregada e quantidade de votos; não constituem avaliações textuais ou rótulos de sentimento. |
| text | Texto correspondente à representação original, limpa ou normalizada; pode ser null. |
| tokens | Lista de textos nas três etapas tokenizadas; lista vazia para sinopse ausente. |
| overview_missing | Booleano nos metadados, calculado sobre a sinopse original. |
| memberships.json | Relaciona cada ID aos recortes de coleta que retornaram o filme. |
| manifest.json | Horários, configuração, estado, hashes e identificação dos arquivos e do código. |

Todas as etapas conservam a mesma ordem e os mesmos 430 IDs. Um filme sem sinopse permanece disponível para consultas por título e metadados, embora não contribua às métricas lexicais. As respostas JSON guardam o conteúdo recebido, incluindo repetições e paginação; a serialização local é formatada e não reproduz necessariamente os bytes da resposta HTTP.

Os manifestos registram hashes SHA-256 para detectar divergências em relação aos arquivos salvos. Essa verificação oferece rastreabilidade, mas não é assinatura digital: a alteração conjunta de um arquivo e de seu manifesto exige outro controle para ser detectada.

## 4 Script de coleta e reprodução

Peso na rubrica: 0,3. O projeto utiliza Python 3.14, com dependências registradas em pyproject.toml e fixadas em uv.lock. O módulo app.corpus.collect executa a amostragem a partir de config/coleta.json, consulta as páginas previstas, consolida os filmes por ID e registra as respostas e a situação de cada chamada. O acesso HTTP reutiliza a integração requests do projeto.

O transporte aplica timeout padrão de 10 segundos e até três novas tentativas para GET diante de HTTP 429, 500, 502, 503 e 504, com backoff. Há ainda intervalo configurado de 0,3 segundo entre chamadas. As credenciais são lidas do ambiente ou de .env local, ignorado pelo Git; não entram em dados, relatórios ou manifestos. Erros são registrados por tipo e status, sem mensagens que possam revelar autenticação.

### Executar uma nova coleta

Dentro da pasta backend, instalar o ambiente e configurar a credencial local do TMDB. Os comandos abaixo usam diretórios novos para evitar substituição dos dados entregues.

```bash
uv sync --frozen
uv run --frozen python -m app.corpus collect --config ../config/coleta.json --output ../data/raw/nova_coleta
```

Quando uma página falha, o recorte correspondente é interrompido e os demais são tentados. Os dados já recebidos são preservados e o estado da coleta fica parcial. O comando retorna código de saída 2 nessa situação; uma coleta completa retorna 0. A versão atual não executa retomada automática nem atualização periódica.

### Repetir o processamento sem rede

```bash
uv run --frozen python -m app.corpus process --input ../data/raw/tmdb_2026-09-12 --output ../data/processed/reproducao --stopwords ../config/stopwords_pt.txt
```

```bash
uv run --frozen python -m app.corpus verify --input ../data/processed/reproducao
```

O processamento usa somente os arquivos locais e dispensa a credencial. A pasta de saída deve ser inexistente. Os arquivos de conteúdo podem ser reproduzidos com as mesmas entradas e regras; o manifesto registra a nova execução. Repetir a coleta online pode gerar outra amostra porque o catálogo e o ranking mudam. O README apresenta os comandos e links diretos para cada item da rubrica.

## 5 Limpeza e preparação dos textos

Peso na rubrica: 0,3. As transformações são aplicadas às sinopses coletadas. O texto bruto continua disponível, e cada etapa gera uma nova representação identificada pelo ID do filme. A comparação posterior pode escolher uma etapa intermediária, sem ser obrigada a usar o resultado mais transformado.

| Representação | Procedimento |
| --- | --- |
| 01_original.jsonl | Cópia da sinopse sem alteração. O JSON bruto também é conservado. |
| 02_clean.jsonl | Tratamento de HTML, URLs, caracteres de controle e espaços; normalização Unicode NFC. |
| 03_normalized.jsonl | Conversão por casefold, preservando a acentuação. |
| 04_tokens.jsonl | Tokenização por expressão regular; conserva a pontuação em tokens separados. |
| 05_without_punctuation.jsonl | Retém tokens com pelo menos uma letra ou dígito; preserva números. |
| 06_without_stopwords.jsonl | Aplica a lista conservadora versionada; mantém não, nem, nunca e sem. |

A tokenização reconhece sequências de caracteres de palavra, com apóstrofos ou hífens internos, e sinais de pontuação separados. A expressão e as regras ficam registradas no manifesto. A filtragem não é aplicada aos títulos. A lista de stopwords é própria da experiência, não pretende esgotar todas as palavras funcionais do português e permanece disponível para comparação e ajustes.

### Exemplo observado em Matrix

Na sinopse de Matrix, “Thomas Anderson”, “Morpheus” e “Trinity” permanecem na versão original. Na representação normalizada passam para minúsculas, mas seus tokens continuam na versão filtrada. Isso permite inspecionar o efeito da transformação sobre nomes conhecidos sem alegar que foi executado reconhecimento automático de entidades.

O trecho original “Thomas conhece os misteriosos Morpheus e Trinity” produz, após normalização e filtragem, “thomas”, “conhece”, “misteriosos”, “morpheus”, “trinity”. A presença dos nomes nesse exemplo não garante preservação de todos os nomes do corpus. Os exemplos completos e as seis versões estão em examples.json na pasta processada.

A palavra “simulação” não aparece literalmente na sinopse recebida de Matrix; aparecem expressões como “sistema inteligente e artificial” e “ilusão de um mundo real”. A observação do professor, portanto, orienta uma futura avaliação de recuperação por assunto. O pipeline atual não afirma resolver essa correspondência semântica.

## 6 Comparação das representações e recortes

| Representação | Tokens | Tipos | TTR |
| --- | --- | --- | --- |
| Original | 25.013 | 6.261 | 0,2503 |
| Normalizada sem pontuação | 25.013 | 5.988 | 0,2394 |
| Sem stopwords | 14.769 | 5.921 | 0,4009 |

A normalização reduziu a quantidade de tipos ao reunir diferenças de caixa, mantendo o total de tokens lexicais. A retirada de stopwords eliminou 10.244 ocorrências, cerca de 40,95% desse total. O aumento de TTR na versão filtrada é consequência da mudança do denominador e da remoção de termos frequentes; não demonstra melhora na recomendação.

A comparação dos recortes usa o mesmo processamento. Cada grupo contém 40 filmes retornados pelas páginas consultadas; alguns filmes aparecem em mais de um grupo. A tabela mostra a quantidade de sinopses válidas e a média de tokens após filtragem.

| Gênero | Período | Sinopses | Média |
| --- | --- | --- | --- |
| Drama | 1980–1999 | 40 | 32,90 |
| Drama | 2000–2014 | 40 | 34,98 |
| Drama | 2015–2025 | 40 | 32,90 |
| Terror | 1980–1999 | 39 | 38,36 |
| Terror | 2000–2014 | 40 | 36,25 |
| Terror | 2015–2025 | 40 | 30,28 |
| Comédia | 1980–1999 | 39 | 35,92 |
| Comédia | 2000–2014 | 40 | 38,20 |
| Comédia | 2015–2025 | 40 | 30,18 |
| Ficção científica | 1980–1999 | 40 | 39,98 |
| Ficção científica | 2000–2014 | 40 | 34,40 |
| Ficção científica | 2015–2025 | 40 | 29,08 |

Ficção científica no recorte de 1980–1999 apresentou média de 39,98 tokens filtrados por sinopse, contra 29,08 em 2015–2025. Essa diferença descreve os grupos selecionados, sem permitir uma conclusão geral sobre todos os filmes desses períodos. Comédia e Terror no recorte mais antigo possuem uma sinopse ausente cada. As demais distribuições e frequências estão em statistics.json.

## 7 Validação e próximos passos

O ambiente foi instalado com uv sync --frozen e validado em Python 3.14.7. Os 16 testes automatizados passaram: cinco do extrator original, seis do corpus e cinco da pesquisa auxiliar. Os testes do corpus verificam paginação, deduplicação, textos ausentes, preservação de negações, integridade, reprodução determinística, recusa de sobrescrita e registro de falhas sem credenciais.

Na amostra real, a verificação confirmou seis etapas alinhadas com 430 filmes e os hashes de 13 arquivos de conteúdo. Uma segunda execução offline produziu esses 13 arquivos idênticos byte a byte; somente o manifesto muda para descrever a nova execução. As evidências e comandos estão em docs/validacao.md.

### Consulta auxiliar e limites dos testes

A API foi iniciada com Uvicorn e consultada por HTTP com acesso real ao TMDB. Saúde, detalhes de Matrix e pesquisas por título e preferências retornaram HTTP 200. O serviço de descoberta foi conectado, e o modo automático passou a priorizar títulos exatos antes dos gatilhos de gênero. A interface também oferece modo explícito de título para ambiguidades. Essa aplicação ainda não usa representações vetoriais das sinopses.

O teste original que imprime 100% mede 12 campos selecionados em cinco frases anotadas. Esse resultado não representa acurácia geral do assistente, qualidade da recuperação ou desempenho em perguntas inéditas. As heurísticas de negação e de períodos continuam limitadas, com convenções documentadas em docs/decisoes.md.

### Bônus e continuação da atividade

A entrega demonstra comparação entre recortes amostrais e coleta automatizada em um comando. Esses recursos correspondem a possibilidades de bônus da rubrica, cuja concessão depende do professor. Não foram executados stemming, lematização ou agendamento periódico. Não foram incorporados IMDb, MovieLens, reviews de usuários ou outros corpora.

A próxima etapa é definir consultas e filmes relevantes de referência, vetorizar representações comparáveis e avaliar a recuperação com o mesmo conjunto de testes. Stemming e lematização, se experimentados, devem gerar variantes independentes. A escolha final deve considerar a preservação da informação e a qualidade da recuperação, inclusive casos como Matrix associado a simulação, e não apenas a redução do vocabulário.

### Materiais utilizados

FURB. PLN 2026/2 — Template — Avaliação Prática 1. Rubrica fornecida para a atividade.
Orientação do professor em vídeo de 31/08/2026, com transcrição fornecida pela equipe.
The Movie Database. API e catálogo. https://www.themoviedb.org/ e https://developer.themoviedb.org/docs/getting-started. Coleta em 12/09/2026.
Repositório da equipe. https://github.com/KaikeDev/PLN.

Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB. Os dados permanecem sujeitos às condições da fonte.
