# Decisões da Etapa Prática 1

## Escopo orientado pelo professor

Na orientação em vídeo de 31/08/2026, o professor pede representações sucessivas dos mesmos dados (00:00–00:46), comparação futura e vetorização (00:46–01:25), além de repositório navegável com dados e transformações localizáveis no README (01:38–02:15). Esta implementação entrega o corpus e as evidências; não afirma que a recomendação semântica esteja concluída.

## Amostra intencional

Selecionamos Drama (18), Comédia (35), Terror (27) e Ficção científica (878), cruzados com 1980–1999, 2000–2014 e 2015–2025. São duas páginas por recorte, ordenadas por popularidade, com pelo menos 50 votos e conteúdo adulto excluído. Os cortes e o limite de páginas são decisões de viabilidade da experiência, não exigências numéricas do professor. Incluímos o ID 603 como caso didático de Matrix. A amostra tem viés de popularidade e disponibilidade de metadados.

## Transformações comparáveis

As seis saídas mantêm todos os IDs. A limpeza e o `casefold` não substituem os textos originais. Acentos são preservados no corpus; a normalização sem acentos do extrator de perguntas é um fluxo auxiliar diferente. A lista de stopwords é conservadora e explicitamente versionada, sem pretensão de cobrir todas as palavras funcionais do português. Negação e números são conservados. Títulos não são filtrados.

Não há reconhecimento automático de nomes próprios. Por isso, preservamos a versão original e não aplicamos stemming ou lematização como padrão. A versão em minúsculas já remove uma pista de identificação de nomes. As variantes morfológicas podem ser acrescentadas separadamente, nunca aplicando stemming sobre os lemas ou usando a redução lexical como prova de melhor recuperação.

## Reprodutibilidade e falhas

A coleta online é variável; a amostra salva é a referência. Cada chamada bem-sucedida guarda JSON e hash. Erros guardam somente tipo e status, sem URLs com credenciais nem mensagens potencialmente secretas. O transporte possui timeout e até três retries com backoff para 429 e erros transitórios. A coleta aplica intervalo mínimo entre chamadas. Não há retomada automática: falhas parciais ficam no manifesto e a próxima execução usa outra pasta.

O processamento offline conserva resultados idênticos com os mesmos textos e regras. Horário e identidade da execução ficam em manifesto separado. No caso de interrupção durante a gravação do processamento, a ausência de manifesto completo impede validar a pasta como uma entrega íntegra; deve-se usar outra pasta na nova execução.

## Consulta auxiliar por regras

O serviço de descoberta e a rota `/pesquisa` foram conectados para remover a chamada a uma função inexistente. Em modo automático, títulos localizados/originais com correspondência exata têm prioridade sobre gatilhos de gênero. O modo explícito de título resolve ambiguidades restantes. Títulos alternativos e perguntas com contexto adicional ainda podem não ser reconhecidos.

A consulta usa regras: nota mínima 7 e 100 votos para boa avaliação, 8 e 200 para expressões mais fortes; recência de dez anos e antiguidade de 25. O código não deduz premiações a partir da nota. Uma janela local evita tratar algumas expressões de qualidade negadas como preferência positiva; não interpreta toda a semântica da negação. O tratamento de gêneros continua por janela de três tokens.

O limite inicial do ano explícito continua inclusivo: “depois de 2015” é tratado como a partir de 01/01/2015, mantendo a convenção do protótipo; “antes de 2020” termina em 31/12/2019. Essa convenção deve ser refinada em uma avaliação futura da linguagem. Ambos os limites são considerados, e um ano informado separadamente é intersectado com o período extraído.

## Próximas experiências

Comparar representações com as mesmas consultas e filmes relevantes anotados. Analisar recuperação de Matrix por temas, documentando a ausência literal de “simulação” na sinopse obtida. Selecionar a técnica pela qualidade da recuperação, não somente por redução de tokens ou aumento de TTR. Não foram incorporadas bases externas, avaliações textuais de usuários nem modelos treinados nesta etapa.
