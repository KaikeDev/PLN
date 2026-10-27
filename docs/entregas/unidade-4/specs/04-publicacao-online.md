# Spec 04 — Publicação online: Docker no Hugging Face Spaces

**Depende de:** nada (começar já, com o site atual) · **ADR:** 0033, que substitui parcialmente a 0002 · **Esforço:** 2 dias

## Objetivo

Um **link público e estável** para o site, exigido pelo item 4 do enunciado. Os visitantes da Mostra usam todas as abas sem instalar nada, e as chaves ficam protegidas.

## Arquitetura de publicação

```
Visitante ──HTTPS──► Hugging Face Space (contêiner Docker, CPU gratuita)
                       └─ uvicorn (1 processo, porta 7860, --proxy-headers)
                            ├─ /            → frontend/ (arquivos estáticos, mesma origem)
                            ├─ /pesquisa, /filmes, /classificacao, /sentimento, /entidades, /pergunta, /saude
                            ├─ MiniLM + spaCy + classificadores (carregados na inicialização)
                            └─ chamadas de saída: TMDB · Gemini · Groq  (chaves = segredos do Space)
```

**Por que mesma origem:** um processo e um link, sem CORS em produção e com CSP `connect-src 'self'`. O modo local de dois terminais (porta 5500) continua funcionando.

## Mudanças no código

| Arquivo | Mudança |
|---|---|
| `backend/src/app/main.py` | Se `settings.serve_frontend` for verdadeiro, montar `StaticFiles(directory=frontend, html=True)` em `/`, **depois** das rotas da API, para não sombrear `/pesquisa` e as demais |
| `backend/src/app/settings.py` | `serve_frontend: bool = False`; `frontend_dir: Path`; limites das rotas de LLM (`llm_rate_limit_per_minute = 5`) |
| `frontend/index.html` | `<meta name="api-base" content="">`, onde vazio significa mesma origem. CSP: `connect-src 'self' http://127.0.0.1:8000 http://localhost:8000` |
| `frontend/script.js` | `API_BASE` vazio usa caminhos relativos. Mensagem de "servidor acordando" quando `/saude` demora (o Space dorme) |
| `backend/pyproject.toml` | PyTorch **CPU** no Linux: `[[tool.uv.index]] name="pytorch-cpu" url="https://download.pytorch.org/whl/cpu" explicit=true` e `[tool.uv.sources] torch = [{ index = "pytorch-cpu", marker = "sys_platform == 'linux'" }]`. Regerar o `uv.lock` e conferir que os `nvidia-*` saíram. **Verificar antes se existe a roda do PyTorch CPU para cp314 na versão travada**; se não existir, travar a versão mais nova que tenha |
| `backend/src/app/api/rate_limit.py` | Sem mudança de lógica: com `--proxy-headers`, `request.client.host` passa a ser o IP real do visitante. Acrescentar o teste com `X-Forwarded-For` |

## Dados do catálogo (5.525 filmes, fora do Git)

**Escolha:** gerar **uma vez** localmente (3 comandos de `rodar-o-site.md`) e publicar as três pastas (`coleta/`, `preparacao/` e `representacoes/site_2026-10-05`, com os manifestos) num **Dataset público do Hugging Face** com o aviso de atribuição ao TMDB. O build baixa uma **revisão fixada** (hash do commit do dataset) e roda `verify` nas três pastas; um hash divergente quebra o build.

**Alternativa** (se o grupo preferir não redistribuir o catálogo): gerar no build com o token do TMDB como segredo de build. Custos: cerca de 8 minutos por build, e o resultado muda com o ranking do TMDB.

**Reserva:** sem o catálogo, a API já cai para a amostra de 428 filmes, com a faixa amarela. Mesmo assim, o site publicado funciona (o enunciado permite amostra menor desde que explicitada).

## `Dockerfile` (em `deploy/space/`)

Passos, nesta ordem, para aproveitar o cache de camadas:

1. `FROM` a imagem do uv com Python 3.14 slim.
2. Usuário não root (uid 1000, exigência do Spaces) e `HF_HOME=/app/.cache/huggingface`.
3. Copiar `pyproject.toml` e `uv.lock` e rodar `uv sync --frozen --no-dev --extra semantico --extra entidades`. Sem o extra `jev`, que o site não usa.
4. **Baixar o MiniLM na revisão fixada** durante o build (o arranque não depende da rede do Hugging Face).
5. Baixar o dataset do catálogo e rodar `verify`.
6. Copiar `backend/src`, `config/`, `frontend/` e só as pastas de `data/` que a API lê: a amostra (`coleta`, `preparacao` e `representacoes/tmdb_2026-09-12`) e as críticas.
7. `python -m app.sentiment process …` para preparar as críticas (segundos; o passo 4 de `rodar-o-site.md`).
8. `CMD uvicorn app.main:app --host 0.0.0.0 --port 7860 --proxy-headers --forwarded-allow-ips "*" --workers 1`, com `SERVE_FRONTEND=true`.

Tamanho esperado: 2 a 3 GB. A memória em uso deve ficar bem abaixo dos 16 GB; **medir** e registrar.

## Segredos e envio

- Segredos do Space: `TMDB_BEARER_TOKEN`, `GEMINI_API_KEY` e `GROQ_API_KEY`. **Nunca** com `ARG` ou `ENV` no Dockerfile, nem em camadas da imagem.
- `deploy/space/README.md` traz o cabeçalho YAML do Space (`sdk: docker`, `app_port: 7860`, título e licença) e o link para o repositório do GitHub.
- Envio: o workflow `.github/workflows/deploy-space.yml`, **manual** (`workflow_dispatch`), monta uma pasta só com o necessário e a envia com `huggingface_hub.upload_folder`, usando o segredo `HF_TOKEN` do GitHub. Documentar também o comando manual equivalente.

## Antes de divulgar o link

- [ ] **Confirmar que o token do TMDB exposto no commit `a09a21c` (ADR 0002) foi revogado** no painel do TMDB. O histórico do repositório continua público.
- [ ] Contas dos provedores com a cota **gratuita**, sem cartão vinculado, ou com limite de gasto zero. Assim, abuso nenhum gera cobrança.
- [ ] `git ls-files -ci --exclude-standard` vazio e nenhum `.env` no Space.

## Robustez para o dia da Mostra

| Situação | O que acontece | Preparação |
|---|---|---|
| O Space dormiu | A primeira visita espera cerca de 1 minuto | Abrir o link uns 10 minutos antes; a tela mostra "servidor acordando…" |
| A cota do LLM acabou | Interpretação cai para as regras; "Perguntar" e "Comparar com IA" mostram os exemplos gravados | Orçamento abaixo da cota (spec 00) |
| O TMDB fora do ar | A busca por título e a ficha falham com 502; a busca por tema, a classificação, o sentimento e as entidades continuam (dados locais) | — |
| O Space inteiro fora do ar | — | **Reserva 1:** página "Sobre" estática no GitHub Pages (spec 05). **Reserva 2:** vídeo curto da demonstração no README. **Reserva 3:** rodar localmente (`rodar-o-site.md`) |

## Testes e verificações

- `test_api.py`: com `serve_frontend=True`, `/` devolve o `index.html`, as rotas da API continuam respondendo JSON e um caminho inexistente dá 404.
- `test_api.py`: o limite por IP respeita `X-Forwarded-For` quando o proxy é confiável.
- CI: `docker build` do `deploy/space/Dockerfile` **sem** baixar o dataset (`--build-arg SKIP_CATALOG=1`), para pegar quebras de dependência. Se demorar demais, só no workflow manual.
- `docs/tecnico/api_smoke.json`: atualizar o teste de fumaça para rodar também contra a URL pública (`python -m app … smoke --base-url https://…`).

## Critérios de aceite

- [ ] O link `https://huggingface.co/spaces/<conta>/<nome>` abre o site, com o indicador verde e "5.525 filmes".
- [ ] Todas as abas funcionam no link público, de um celular e de um computador.
- [ ] A memória em uso, o tempo de arranque frio e o tamanho da imagem estão medidos e registrados em `docs/tecnico/validacao.md`.
- [ ] O modo local de dois terminais continua funcionando sem mudança nos comandos.
- [ ] ADR 0033: por que o Hugging Face Spaces, mesma origem, `0.0.0.0` com proxy e limites, PyTorch CPU, catálogo via dataset, e o que muda em relação à ADR 0002.
