# 0009 — Saídas imutáveis, determinísticas e verificáveis por manifesto

- Estado: Aceita
- Data: 2026-09-14 (imutabilidade e manifesto desde a Etapa 1; quebra de linha LF nesta data)

## Contexto

A disciplina exige localizar e repetir cada transformação. Uma coleta online muda com o tempo, então a amostra salva é a referência. Na revisão, os arquivos gerados no Windows saíam com CRLF e os gerados em Linux com LF: "idêntico byte a byte" só valia no mesmo sistema operacional, e o `core.autocrlf` do Git poderia alterar arquivos com hash registrado.

## Decisão

- **Imutabilidade**: toda execução grava numa pasta nova; uma pasta existente causa erro. Na Etapa 2, tudo é calculado em memória antes de criar a pasta, para não deixar saída parcial.
- **Manifesto**: SHA-256 de cada arquivo, identidade do código e dos templates (`source_identity`), versões de Python e bibliotecas e hashes das entradas. `verify` recusa nomes com caminho e detecta alterações.
- **Determinismo**: JSON indentado e JSONL em UTF-8, sem escapar acentos, sempre com LF (`app.shared.artifacts.write_text`). Ordenações têm desempate explícito e sementes aleatórias são fixas.
- **Git**: `.gitattributes` marca `data/**` como `-text`, para que o Git nunca converta quebras de linha de arquivos com hash.
- **Textos de relatório**: o texto fixo do relatório da Etapa 1 fica em `app/corpus/templates/report.md`, também coberto pela identidade do código.

## Alternativas consideradas

- Sobrescrever a última execução: mais simples, mas perde rastreabilidade.
- Assinatura digital: exigiria gestão de chaves; o hash basta para detectar alterações acidentais.

## Consequências

- O hash não impede a alteração conjunta de um arquivo e do manifesto.
- Reprocessar `data/raw/tmdb_2026-09-12` reproduz byte a byte `data/processed/tmdb_2026-09-12`, exceto o manifesto, em qualquer sistema operacional.
- `data/vectors/tmdb_2026-09-12` foi gerado no Windows antes desta decisão (CRLF). Continua verificável, mas uma nova execução gera LF e, portanto, outros bytes.
