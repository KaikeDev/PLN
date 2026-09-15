# 0011 — Formatos legíveis e modelos pré-treinados com revisão fixada

- Estado: Aceita
- Data: 2026-09-14

## Contexto

Os arquivos de configuração e as saídas são lidos de volta pelos pipelines. Formatos como pickle executam código ao carregar. Modelos do Hugging Face podem mudar entre versões ou trazer código remoto.

## Decisão

- **Configurações e saídas**: somente JSON/JSONL, com limite de tamanho de 1 MB para configurações. Campos desconhecidos, booleanos no lugar de inteiros e nomes fora de `[a-z0-9_]` são recusados (`app.shared.validation`).
- **Caminhos**: a etapa de entrada vem de uma lista fixa (`app.corpus.contracts`); a configuração nunca informa caminhos livres.
- **Matrizes**: exportadas como JSON legível; nenhum modelo é salvo com pickle ou joblib.
- **Modelos pré-treinados**: identificador `organização/modelo` e `revision` com hash de commit de 40 caracteres, carregados com `trust_remote_code=False`. As bibliotecas ficam no extra opcional `semantico`.
- **SVG**: todo texto vindo dos dados é escapado.

## Alternativas consideradas

- Arquivos `.npz`/pickle: menores e mais rápidos, mas não legíveis e, no caso do pickle, inseguros.
- Revisão `main` dos modelos: resultados poderiam mudar sem aviso.

## Consequências

- As saídas são maiores; o comando `query` reconstrói o espaço a partir dos dados verificados.
- BoW e TF-IDF funcionam sem o extra `semantico`, e o CI não baixa modelos.
