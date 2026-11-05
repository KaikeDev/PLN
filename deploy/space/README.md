---
title: Sinopses de filmes - do corpus ao LLM
emoji: 🎬
colorFrom: indigo
colorTo: yellow
sdk: docker
app_port: 7860
license: other
short_description: Busca, recomendação, classificação, sentimento e RAG em PT
---

# Sinopses de filmes: do corpus ao LLM

Site do projeto de PLN 2026/2 (FURB) de Kaike Ventura Tuerpe, Luana Nitsche, Pedro Henrique Ortunio e Thiago Bodnar: busca por título, preferências e tema nas sinopses, filmes parecidos, classificação de gênero, análise de sentimento de críticas, entidades e relações, e perguntas sobre os filmes respondidas por RAG.

Código, documentação e resultados: <https://github.com/KaikeDev/PLN>. A decisão de publicação está na [ADR 0033](https://github.com/KaikeDev/PLN/blob/main/docs/adr/0033-publicacao-no-hugging-face-spaces.md).

O Space dorme depois de um tempo sem visitas; a primeira visita depois disso espera cerca de 1 minuto enquanto o servidor acorda.

> Dados fornecidos por [The Movie Database (TMDB)](https://www.themoviedb.org/). Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB.

---

O restante deste arquivo é para quem mantém o site: como publicar e manter o Space. Este `README.md` é copiado para a raiz do Space por `deploy/space/stage.sh`, e o cabeçalho YAML acima é a configuração do Space.

## O que vai para o Space

`deploy/space/stage.sh` monta uma pasta só com arquivos versionados (`git archive HEAD`), sem `.env`, `.venv` nem caches:

| Na pasta | De onde vem |
|---|---|
| `Dockerfile` | `deploy/space/Dockerfile`, com o dataset e a revisão do catálogo gravados nos `ARG` |
| `README.md` | Este arquivo |
| `backend/` | `pyproject.toml`, `uv.lock`, `README.md` e `src/` |
| `config/`, `frontend/` | Inteiros |
| `data/` | Só o que a API lê: a amostra avaliada (`coleta`, `preparacao` e `representacoes` de `tmdb_2026-09-12`) e as críticas (`coleta/criticas_2026-10-10`). O catálogo do site vem do dataset (abaixo), e as críticas são preparadas no build |

## Plano

Spaces Docker exigem o plano PRO (US$ 9 por mês) na conta dona do Space; o hardware CPU Basic não tem custo por hora.

## Segredos do Space

Em *Settings → Variables and secrets → New secret* do Space, como **segredos** (nunca como variáveis públicas):

| Segredo | Para quê | Sem ele |
|---|---|---|
| `TMDB_BEARER_TOKEN` | Busca por título, ficha do filme | A API não sobe |
| `GEMINI_API_KEY` | LLM principal (interpretação da consulta, "Comparar com IA", "Perguntar") | Usa só o Groq |
| `GROQ_API_KEY` | LLM de reserva | Usa só o Gemini; sem nenhuma das duas, as funções com LLM respondem 503 e a busca cai para as regras |

O Space expõe os segredos como variáveis de ambiente **na execução**. O `Dockerfile` não usa nenhum deles em `ARG`, `ENV` ou `RUN`, então nenhuma chave fica em camada da imagem.

## Catálogo do site como dataset do Hugging Face

O catálogo (5.458 filmes com sinopse na coleta de 01/11/2026) é gerado uma vez com os três comandos do passo 3 de [`docs/tecnico/rodar-o-site.md`](https://github.com/KaikeDev/PLN/blob/main/docs/tecnico/rodar-o-site.md) e publicado num **dataset público**, com os manifestos. Na pasta `backend`, com um token de escrita do Hugging Face em `HF_TOKEN`:

```bash
uv run --no-sync python -c "
from huggingface_hub import HfApi
api = HfApi()
repo = 'CONTA/sinopses-catalogo-site'
api.create_repo(repo, repo_type='dataset', exist_ok=True)
for stage in ('coleta', 'preparacao', 'representacoes'):
    api.upload_folder(repo_id=repo, repo_type='dataset', folder_path=f'../data/{stage}/site_2026-10-05', path_in_repo=f'{stage}/site_2026-10-05')
api.upload_file(repo_id=repo, repo_type='dataset', path_or_fileobj='../deploy/space/catalogo-README.md', path_in_repo='README.md')
print(api.dataset_info(repo).sha)
"
```

O último número impresso é o **hash do commit do dataset**: é ele que se passa como revisão no envio do Space. O build baixa exatamente essa revisão e roda `verify` nas três pastas; um arquivo alterado quebra o build.

O `README.md` do dataset ([`catalogo-README.md`](catalogo-README.md)) traz a atribuição obrigatória ao TMDB e diz que o catálogo serve só à demonstração acadêmica.

## Envio do Space

**Pelo GitHub (recomendado):** *Actions → Publicar no Hugging Face Space → Run workflow*, com o id do Space (`CONTA/NOME`), o dataset e a revisão. O workflow precisa do segredo `HF_TOKEN` do repositório no GitHub (token de escrita do Hugging Face).

**Manual, equivalente ao workflow**, na raiz do repositório e com `HF_TOKEN` no ambiente:

```bash
bash deploy/space/stage.sh build/space CONTA/sinopses-catalogo-site <hash-do-commit-do-dataset>
python -m pip install "huggingface_hub>=0.34"
python -c "
from huggingface_hub import HfApi
api = HfApi()
api.create_repo('CONTA/NOME', repo_type='space', space_sdk='docker', exist_ok=True)
api.upload_folder(repo_id='CONTA/NOME', repo_type='space', folder_path='build/space', delete_patterns=['backend/**', 'config/**', 'frontend/**', 'data/**'])
"
```

O Space reconstrói a imagem a cada envio (alguns minutos). Para testar a imagem sem o catálogo: `docker build --build-arg SKIP_CATALOG=1 -t pln-space build/space`, e `docker run -p 7860:7860 --env-file backend/.env pln-space`.

## Antes de divulgar o link

- [ ] O token do TMDB exposto no commit `a09a21c` ([ADR 0002](https://github.com/KaikeDev/PLN/blob/main/docs/adr/0002-credencial-e-exposicao-da-api.md)) foi **revogado** no painel do TMDB; o histórico do repositório continua público.
- [ ] As contas do Gemini e do Groq estão no plano **gratuito**, sem cartão vinculado ou com limite de gasto zero: abuso nenhum gera cobrança.
- [ ] `git ls-files -ci --exclude-standard` não lista nada, e nenhum `.env` foi enviado ao Space.
- [ ] O site abre no link público com o indicador verde e "5.458 filmes" (o número do catálogo publicado).
