#!/usr/bin/env bash
# Monta a pasta enviada ao Hugging Face Space (e usada pelo `docker build` do CI) só com o necessário (ADR 0033).
#
# Uso, na raiz do repositório:  bash deploy/space/stage.sh <pasta-de-saida> [<dataset-do-catalogo> <revisao>]
#   ex.: bash deploy/space/stage.sh build/space conta/sinopses-catalogo-site 3f2a...  (hash completo do commit do dataset)
#
# Copia apenas arquivos versionados (`git archive HEAD`): nada de `.env`, `.venv` ou caches entra na pasta,
# e alterações não commitadas ficam de fora. A revisão do dataset do catálogo fica gravada no Dockerfile da
# pasta, junto com o nome do dataset, para que o build do Space baixe sempre a mesma versão; sem eles, o build exige
# SKIP_CATALOG=1 (é o que o CI faz).
set -euo pipefail

output="${1:?informe a pasta de saída}"
repo="${2:-}"
revision="${3:-}"
root="$(git rev-parse --show-toplevel)"

if [ -e "$output" ]; then
  echo "A pasta de saída já existe: $output" >&2
  exit 2
fi
mkdir -p "$output"

git -C "$root" archive HEAD \
  backend/pyproject.toml backend/uv.lock backend/README.md backend/src \
  config frontend \
  data/coleta/tmdb_2026-09-12 data/preparacao/tmdb_2026-09-12 data/representacoes/tmdb_2026-09-12 \
  data/coleta/criticas_2026-10-10 \
  | tar -x -C "$output"

cp "$root/deploy/space/README.md" "$output/README.md"
cp "$root/deploy/space/.dockerignore" "$output/.dockerignore"
if [ -n "$repo" ]; then
  if ! [[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || ! [[ "$revision" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Informe o dataset como conta/nome e a revisão como o hash completo do commit (40 caracteres hexadecimais)" >&2
    exit 2
  fi
  sed -e "s|^ARG CATALOG_REPO=.*|ARG CATALOG_REPO=$repo|" -e "s|^ARG CATALOG_REVISION=.*|ARG CATALOG_REVISION=$revision|" \
    "$root/deploy/space/Dockerfile" > "$output/Dockerfile"
else
  cp "$root/deploy/space/Dockerfile" "$output/Dockerfile"
fi

echo "Pasta do Space em $output ($(find "$output" -type f | wc -l) arquivos)"
