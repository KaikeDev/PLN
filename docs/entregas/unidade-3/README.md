# Trabalho da Unidade 3

| Arquivo | O que é |
|---|---|
| [PLN_2026_2_Trabalho_Unidade_3.docx](PLN_2026_2_Trabalho_Unidade_3.docx) | Respostas às questões 1 a 6 do enunciado, com figuras, tabelas, exemplos e trechos de código |
| [PLN_2026_2_Trabalho_Unidade_3.pdf](PLN_2026_2_Trabalho_Unidade_3.pdf) | O mesmo documento em PDF, exportado pelo Word |
| [figuras/](figuras/) | As figuras do documento, em PNG |
| [resultados.json](resultados.json) | Números reunidos para o documento: top-5 e precisão @3 e @5 da busca; o classificador em dados novos |
| [coletar_resultados.py](coletar_resultados.py) | Gera `resultados.json` a partir dos dados do repositório |
| [gerar_documento.py](gerar_documento.py) | Gera as figuras e o `.docx` a partir dos resultados do repositório |

Os resultados de cada tarefa e o código estão nas pastas do projeto. A tabela de tarefas está no [README principal](../../../README.md).

## Como refazer

Em `backend`, depois de gerar o catálogo do site ([rodar-o-site.md](../../tecnico/rodar-o-site.md)):

```bash
uv run --frozen --extra semantico python ../docs/entregas/unidade-3/coletar_resultados.py
uv run --frozen --no-sync --with python-docx --with matplotlib python ../docs/entregas/unidade-3/gerar_documento.py
```

`python-docx` e `matplotlib` entram só no ambiente temporário dessa execução. O PDF foi exportado pelo Microsoft Word a partir do `.docx`.

## Uso de IA generativa

O documento e os scripts foram produzidos com o Claude Opus 5.5 (Anthropic), pelo Claude Code; a seção "Uso de IA generativa" do documento traz o modelo e os prompts. A marcação inicial das 40 triplas de relações (`config/entidades/conferencia_relacoes.json`) também foi feita pelo assistente.
