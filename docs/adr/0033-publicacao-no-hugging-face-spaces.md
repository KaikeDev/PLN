# 0033. Publicação no Hugging Face Spaces: contêiner Docker, mesma origem, proxy e limites (Unidade 4)

- Estado: Aceita
- Data: 2026-11-01
- Substitui parcialmente: [ADR 0002](0002-credencial-e-exposicao-da-api.md), no item 4 (exposição só em `127.0.0.1`)

## Contexto

O item 4 do enunciado da Unidade 4 pede um **link público** da aplicação web. Até aqui, o site só rodava na máquina de quem o desenvolve:

- dois processos (a API em `127.0.0.1:8000` e as telas em `http.server` na porta 5500), com o endereço da API fixo no HTML e na CSP;
- a API presa a `127.0.0.1` por decisão de segurança (ADR 0002), porque repassa chamadas ao TMDB e, agora, aos LLMs com as chaves do servidor;
- no Linux, o `uv.lock` instalava o PyTorch com CUDA (rodas `nvidia-*`, vários GB), inúteis num servidor sem GPU;
- o catálogo do site, com cerca de 5.500 filmes (ADR 0024; 5.458 sinopses na coleta de 01/11/2026 publicada), é gerado na máquina e fica fora do Git;
- o limite por IP usa `request.client.host`. Atrás de um proxy, todos os visitantes teriam o IP do proxy e dividiriam o mesmo limite.

A API carrega o MiniLM, o spaCy e os classificadores na memória, cerca de 2 GB. Isso descarta as hospedagens gratuitas com 512 MB e as funções *serverless*.

## Decisão

- **Hospedagem: Hugging Face Spaces, Docker, CPU gratuita.** São 16 GB de memória, segredos por Space e um link estável (`https://huggingface.co/spaces/<conta>/<nome>`). O Space dorme quando fica sem visitas e acorda em cerca de 1 minuto; a tela mostra que o servidor está acordando.
- **Mesma origem.** Com `SERVE_FRONTEND=true`, a API serve também `frontend/` (`StaticFiles` em `/`, montado **depois** das rotas, para não sombrear `/pesquisa` e as demais). São um processo e um link, sem CORS em produção, com CSP `connect-src 'self'`. O modo local de dois terminais continua igual: `serve_frontend` é falso por padrão.
- **`0.0.0.0` só no contêiner, atrás do proxy.** O `uvicorn` roda com `--proxy-headers --forwarded-allow-ips "*"`: o contêiner só recebe tráfego pelo proxy do Space, então `request.client.host` passa a ser o IP real do visitante (`X-Forwarded-For`). Um único processo (`--workers 1`), porque os limites, o cache e o orçamento ficam em memória.
- **Três camadas contra abuso de cota:**
  1. o limite geral por IP (`RATE_LIMIT_PER_MINUTE`, 60 por minuto, ADR 0002);
  2. um limite próprio por IP para as rotas que sempre chamam o LLM, `/pergunta` e `/sentimento/llm` (`LLM_RATE_LIMIT_PER_MINUTE`, 5 por minuto);
  3. o orçamento diário global por propósito (ADR 0029), abaixo da cota gratuita.

  A interpretação da consulta em `/pesquisa` fica só no limite geral: ela tem cache, prazo de 4 s e reserva nas regras (ADR 0030).
- **PyTorch CPU no Linux.** `[[tool.uv.index]]` explícito para `https://download.pytorch.org/whl/cpu` e `[tool.uv.sources]` com `sys_platform == 'linux'`. O `torch` entra como dependência direta do extra `semantico`, fixado em `==2.14.0`, a mesma versão que o Windows já usava. No Linux, o lock passa a `2.14.0+cpu`, que tem roda para cp314, e as rodas `nvidia-*`, `cuda-*` e `triton` saem. No Windows e no macOS, nada muda.
- **Catálogo via dataset do Hugging Face, numa revisão fixada.** As três pastas `site_2026-10-05` (`coleta`, `preparacao` e `representacoes`, com os manifestos) vão para um dataset público, com a atribuição ao TMDB. O build baixa o **hash do commit** do dataset, que `deploy/space/stage.sh` grava no `Dockerfile`, e roda `verify` nas três pastas; um hash divergente quebra o build. Com `SKIP_CATALOG=1` (CI), a imagem sai sem o catálogo, e a API cai para a amostra de 428 filmes, com a faixa amarela.
- **Imagem (`deploy/space/Dockerfile`):**
  - usuário não root com uid 1000;
  - `uv sync --frozen --no-dev --extra semantico --extra entidades`, sem o extra `jev`;
  - MiniLM baixado no build, na revisão de `config/representacoes/vetorizacao_semantica.json`, e `HF_HUB_OFFLINE=1` na execução;
  - só as pastas de `data/` que a API lê;
  - críticas preparadas no build.
- **Segredos.** `TMDB_BEARER_TOKEN`, `GEMINI_API_KEY` e `GROQ_API_KEY` são segredos do Space, lidos como variáveis de ambiente na execução. Nunca vão em `ARG`, `ENV` ou camada da imagem. A pasta enviada é montada com `git archive HEAD`, que só leva arquivos versionados: nenhum `.env` entra.
- **Envio manual.** O workflow `deploy-space.yml` (`workflow_dispatch`) monta a pasta e a envia com `huggingface_hub.upload_folder`, usando o segredo `HF_TOKEN` do GitHub. O comando equivalente está em `deploy/space/README.md`. O CI constrói a imagem sem o catálogo na `main` e nos pull requests, para pegar quebras de dependência.

## O que muda em relação à ADR 0002

| ADR 0002 | Agora |
|---|---|
| A API roda com `--host 127.0.0.1`; o bind em localhost é o controle de acesso | Continua assim no modo local. No contêiner, `0.0.0.0` atrás do proxy do Space, e o controle passa a ser os limites por IP, o orçamento diário e as contas gratuitas sem cartão |
| O CORS lista as origens da interface local | Continua para o modo local; em produção não há requisição entre origens |
| Limite por IP da conexão | O mesmo código, com o IP do visitante vindo de `X-Forwarded-For` (proxy confiável), mais o limite das rotas de LLM |

Credencial só em cabeçalho, `SecretStr`, erros sem URL e o `.gitignore` continuam como na ADR 0002. A revogação do token exposto no commit `a09a21c` passa a ser **pré-requisito** para divulgar o link.

## Alternativas consideradas

- **Render ou Railway gratuitos:** 512 MB não bastam para o MiniLM e o spaCy.
- **Vercel ou Netlify (*serverless*):** limite de tamanho de função e arranque a frio a cada chamada, com os modelos carregados de novo.
- **GitHub Pages:** só serve arquivos estáticos (Modalidade A). Fica como reserva para a página "Sobre" (spec 05).
- **Dois serviços (telas estáticas + API) com CORS:** dois links, CSP com o domínio da API e CORS em produção, sem ganho.
- **Gerar o catálogo no build com o token do TMDB:** cerca de 8 minutos por build, o resultado muda com o ranking do TMDB e o token teria de ser segredo de build. O dataset com revisão fixada é reprodutível e verificável.
- **Streamlit ou Gradio:** descartariam a interface e os testes da API.
- **`slowapi` ou Redis para o limite:** um único processo basta, como na ADR 0002.

## Consequências

- O site tem link público, e os visitantes não instalam nada.
- O primeiro acesso depois de um tempo parado espera o Space acordar (cerca de 1 minuto). No dia da Mostra, o link deve ser aberto uns 10 minutos antes.
- `X-Forwarded-For` só é confiável porque o contêiner não é alcançável fora do proxy do Space. Rodando a imagem em outro lugar, sem proxy, `--forwarded-allow-ips "*"` deixaria o visitante escolher o próprio IP e contornar o limite por IP. Nesse caso, o orçamento diário global continua valendo.
- O catálogo é redistribuído num dataset público, com a atribuição ao TMDB e o aviso de uso acadêmico.
- A imagem depende de três serviços externos na execução (TMDB, Gemini e Groq), e de dois no build (PyPI ou o índice do PyTorch, e o Hugging Face). Sem o TMDB, a busca por título e a ficha falham com 502; o resto continua funcionando.
- A memória em uso, o arranque frio e o tamanho da imagem são medidos no Space e registrados em `docs/tecnico/validacao.md`.
