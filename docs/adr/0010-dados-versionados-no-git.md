# 0010 — Amostra entregue versionada no Git

- Estado: Aceita
- Data: 2026-09-14

## Contexto

A avaliação pede um repositório navegável em que dados brutos, transformações e evidências sejam localizáveis pelo README. Os dados somam poucos megabytes. Os termos do TMDB se aplicam à redistribuição das sinopses.

## Decisão

Versionar no Git apenas a amostra oficial `tmdb_2026-09-12` em `data/raw`, `data/processed` e `data/vectors`. Reproduções locais ficam fora do repositório pelo `.gitignore`. Modelos pré-treinados e caches do Hugging Face nunca são versionados. Toda saída mantém a atribuição ao TMDB.

## Alternativas consideradas

- Git LFS ou DVC: úteis para volumes maiores, mas exigiriam instalação extra de quem avalia e quebrariam a navegação direta no GitHub.
- Publicar só os scripts: a coleta online não é reproduzível, porque o TMDB muda.

## Consequências

- Uma nova amostra oficial exige uma exceção explícita no `.gitignore`.
- Antes de tornar o repositório público ou reutilizar os dados fora da disciplina, é preciso conferir os termos e as exigências de atribuição do TMDB.
