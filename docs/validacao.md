# Validação técnica

Execução em 12/09/2026, Python 3.14.7, ambiente instalado com `uv sync --frozen` a partir de `backend/uv.lock`.

## Verificações concluídas

| Verificação | Resultado e alcance |
|---|---|
| Testes automatizados | 16 testes aprovados: os 5 originais, 6 para o corpus e 5 para pesquisa/integração de parâmetros. Dados controlados; sem rede. |
| Coleta real | 26 chamadas bem-sucedidas ao TMDB: 1 mapa de gêneros, 24 páginas de descoberta e 1 detalhe do ID 603. Manifesto com estado `complete`, 481 ocorrências, 430 IDs e 51 duplicatas removidas. |
| Processamento real | 430 IDs em seis representações, 428 sinopses válidas e 2 ausentes conservadas. |
| Integridade | 13 arquivos verificados por hash e alinhamento dos IDs entre representações e metadados. |
| Repetição offline | Nova pasta processada a partir da mesma amostra: os 13 arquivos de conteúdo ficaram idênticos byte a byte. O manifesto muda para registrar a nova execução. |
| API em execução | HTTP 200 para saúde, detalhes de Matrix e pesquisa por título/preferências. [Saídas resumidas](api_smoke.json). |

A API foi iniciada com Uvicorn e consultada via HTTP local, com acesso real ao TMDB. Matrix apareceu no modo título; a preferência por Drama, sem Terror, entre 2015 e 2019 retornou resultados com a interpretação esperada. Esse teste comprova essas chamadas, não uma avaliação geral da linguagem natural.

## Comandos reproduzíveis

Em `backend`:

```bash
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python -m app.corpus verify --input ../data/processed/tmdb_2026-09-12
uv run --frozen python -m app.corpus process --input ../data/raw/tmdb_2026-09-12 --output ../data/processed/reproducao --stopwords ../config/stopwords_pt.txt
```

A pasta `reproducao` deve ser nova. Os testes exercitam paginação, duplicidade, ausência de texto, negação, integridade, repetição determinística, recusa a sobrescrita e falhas de coleta sem vazamento da credencial. Os testes auxiliares verificam prioridade de título exato, limites de período, mapeamento para descoberta e ausência de filtro positivo para qualidade negada.

## Limites da validação

O teste original imprime “100% (12/12)” para campos selecionados de cinco frases. Isso não é acurácia geral do assistente, nem medida de recuperação por sinopse. O projeto não executa reconhecimento de nomes próprios, stemming, lematização ou vetorização. A interface não passou por avaliação visual em navegador nesta revisão; suas chamadas foram verificadas na API. O bônus e a nota final dependem da avaliação do professor.
