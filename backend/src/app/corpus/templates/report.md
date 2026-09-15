# Evidências da coleta e das transformações

Resultados calculados sobre a amostra real do TMDB. Nenhum filme foi descartado por falta de sinopse.

- Estado da coleta: **$status**.
- Registros recebidos: $records_received; filmes únicos: $unique_movies; duplicatas removidas: $duplicates_removed.
- Sinopses válidas: $valid_overviews; ausentes: $missing_overviews ($missing_overviews_percent%).
- Extensão média original: $mean_characters caracteres; mediana: $median_characters.
- Textos alterados na limpeza: $changed_by_cleaning.

## Comparação das representações

Cálculos lexicais sobre as mesmas sinopses preenchidas. Tokens de pontuação não entram nesta tabela. TTR = tipos distintos / tokens. O original preserva maiúsculas; a normalização altera essa contagem.

| Representação | Tokens | Tipos | TTR | Média por sinopse | Mediana |
|---|---:|---:|---:|---:|---:|$representation_rows

## Recortes da amostra

Grupos podem se sobrepor: um mesmo filme pode ter sido retornado por vários gêneros. A soma dos grupos não é o total de filmes únicos. Matrix foi incluído adicionalmente como caso didático solicitado pelo professor.

| Recorte de coleta | Filmes | Sinopses válidas | Tokens filtrados | Tipos |
|---|---:|---:|---:|---:|$slice_rows

## Exemplos rastreáveis

As seis representações mantêm o mesmo ID. A versão filtrada é uma alternativa experimental; não é considerada superior antes da avaliação de recuperação.

$examples## Limitações

A coleta é intencional, usa ranking de popularidade e mínimo de votos; não representa todo o catálogo. O parâmetro pt-BR solicita a tradução, mas não comprova automaticamente o idioma de cada sinopse. original_language descreve a obra. Não foram medidas proporções de nomes próprios nem desempenho de recomendação. Vetorização, stemming e lematização permanecem para experiências posteriores.

Os arquivos originais, configurações, hashes e manifestos permitem repetir as transformações offline. Repetir a coleta online pode produzir outra amostra, pois o TMDB é atualizado.

## Fonte

Dados: The Movie Database (TMDB), https://www.themoviedb.org/. Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB. As condições da fonte se aplicam aos dados; as métricas e transformações são da equipe.
