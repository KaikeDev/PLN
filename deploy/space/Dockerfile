# Imagem do site no Hugging Face Spaces (Docker, CPU gratuita), ADR 0033.
#
# O contexto do build é a pasta montada por `deploy/space/stage.sh`, com `backend/`, `config/`, `frontend/` e só as
# pastas de `data/` que a API lê. Chaves (TMDB, Gemini, Groq) NUNCA entram aqui: são segredos do Space, lidos como
# variáveis de ambiente na execução. Sem o catálogo (`--build-arg SKIP_CATALOG=1`, usado no CI), a API cai para a
# amostra de 428 filmes, com a faixa amarela.

# 1. Python 3.14 com o uv.
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# 2. Usuário não root com uid 1000 (exigência do Spaces) e cache do Hugging Face dentro de /app.
RUN useradd --create-home --uid 1000 user && mkdir -p /app && chown user:user /app
USER user
ENV HOME=/home/user \
    HF_HOME=/app/.cache/huggingface \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH=/app/backend/.venv/bin:$PATH
WORKDIR /app/backend

# 3. Dependências travadas, sem o grupo dev e sem o extra jev, que o site não usa. No Linux, o PyTorch vem do
#    índice CPU (pyproject.toml). O spaCy `pt_core_news_sm` é instalado como roda pelo extra `entidades`.
COPY --chown=user backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --frozen --no-dev --no-install-project --extra semantico --extra entidades

# 4. MiniLM na revisão fixada em config/representacoes/vetorizacao_semantica.json, baixado no build: o arranque não
#    depende da rede do Hugging Face.
COPY --chown=user config/representacoes/vetorizacao_semantica.json /app/config/representacoes/vetorizacao_semantica.json
RUN python -c "import json; from huggingface_hub import snapshot_download; spec = next(r for r in json.load(open('/app/config/representacoes/vetorizacao_semantica.json', encoding='utf-8'))['representations'] if r['name'] == 'sentenca_minilm'); print(snapshot_download(spec['model'], revision=spec['revision']))"

# 5. Catálogo do site (cerca de 5,5 mil filmes com sinopse) do dataset público, numa revisão fixada (hash do commit do dataset).
#    stage.sh grava a revisão abaixo; um hash divergente quebra o build no passo 6.
ARG SKIP_CATALOG=0
ARG CATALOG_REPO=
ARG CATALOG_REVISION=
ENV CATALOG=site_2026-10-05
RUN if [ "$SKIP_CATALOG" = "1" ]; then \
      echo "Catálogo do site ignorado (SKIP_CATALOG=1): a API vai usar a amostra avaliada"; \
    else \
      test -n "$CATALOG_REPO" || { echo "Defina CATALOG_REPO (ou SKIP_CATALOG=1)" >&2; exit 1; }; \
      echo "$CATALOG_REVISION" | grep -Eq '^[0-9a-f]{40}$' || { echo "CATALOG_REVISION deve ser o hash completo do commit do dataset" >&2; exit 1; }; \
      python -c "import sys; from huggingface_hub import snapshot_download; snapshot_download(sys.argv[1], repo_type='dataset', revision=sys.argv[2], local_dir='/app/data', allow_patterns=[f'{stage}/{sys.argv[3]}/*' for stage in ('coleta', 'preparacao', 'representacoes')])" "$CATALOG_REPO" "$CATALOG_REVISION" "$CATALOG"; \
      rm -rf /app/data/.cache; \
    fi

# 6. Código, configurações, telas e só os dados que a API lê: a amostra avaliada e as críticas. Depois, instala o
#    projeto (editável, para que app.settings ache /app/config e /app/data) e confere os hashes do catálogo.
COPY --chown=user backend/src ./src
COPY --chown=user config /app/config
COPY --chown=user frontend /app/frontend
COPY --chown=user data/coleta/tmdb_2026-09-12 /app/data/coleta/tmdb_2026-09-12
COPY --chown=user data/preparacao/tmdb_2026-09-12 /app/data/preparacao/tmdb_2026-09-12
COPY --chown=user data/representacoes/tmdb_2026-09-12 /app/data/representacoes/tmdb_2026-09-12
COPY --chown=user data/coleta/criticas_2026-10-10 /app/data/coleta/criticas_2026-10-10
RUN uv sync --frozen --no-dev --extra semantico --extra entidades
RUN python -c "from pathlib import Path; from app.corpus.verification import verify_raw; verify_raw(Path('/app/data/coleta/tmdb_2026-09-12'))" \
    && python -m app.corpus verify --input /app/data/preparacao/tmdb_2026-09-12 \
    && python -m app.representations verify --input /app/data/representacoes/tmdb_2026-09-12 \
    && python -m app.sentiment verify --input /app/data/coleta/criticas_2026-10-10 \
    && if [ "$SKIP_CATALOG" != "1" ]; then \
      python -c "import sys; from pathlib import Path; from app.corpus.verification import verify_raw; verify_raw(Path(sys.argv[1]))" "/app/data/coleta/$CATALOG" \
      && python -m app.corpus verify --input "/app/data/preparacao/$CATALOG" \
      && python -m app.representations verify --input "/app/data/representacoes/$CATALOG"; \
    fi

# 7. Críticas preparadas (passo 4 de docs/tecnico/rodar-o-site.md), em segundos.
RUN python -m app.sentiment process --input /app/data/coleta/criticas_2026-10-10 --output /app/data/preparacao/criticas_2026-10-10 --stopwords /app/config/coleta/stopwords_pt.txt

# 8. Um processo, porta 7860, atrás do proxy do Space: --proxy-headers para que o limite por IP veja o visitante.
#    A API serve também as telas (mesma origem) e não acessa a rede do Hugging Face na execução.
ENV SERVE_FRONTEND=true \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PYTHONUNBUFFERED=1
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*", "--workers", "1"]
