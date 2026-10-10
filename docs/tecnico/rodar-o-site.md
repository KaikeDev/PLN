# Como rodar o site

Guia do zero até o site aberto no navegador. O site tem duas partes, e cada uma roda num terminal:

| Parte | O que faz | Onde roda |
|---|---|---|
| **API** (back-end) | Busca filmes no TMDB, carrega os modelos e responde às telas | <http://127.0.0.1:8000> |
| **Telas** (front-end) | As páginas que você abre no navegador | <http://127.0.0.1:5500> |

Na **primeira vez**, siga os passos 1 a 5. **Nas próximas**, basta o passo 5.

## Antes de começar

- **Git**, para clonar o repositório.
- **uv**, o gerenciador de Python do projeto ([instalação](https://docs.astral.sh/uv/getting-started/installation/)). Ele instala sozinho o Python 3.14 e todas as bibliotecas.
- **Token do TMDB:** crie uma conta em <https://www.themoviedb.org>, vá em *Configurações → API* e copie o **"Token de leitura da API"**, o texto longo que começa com `eyJ`.
- **Internet e espaço em disco:** a primeira instalação baixa as bibliotecas (PyTorch, spaCy) e o modelo MiniLM, alguns GB no total.

> Todos os comandos abaixo rodam **dentro da pasta `backend`**, num terminal (PowerShell, Prompt de Comando ou o terminal do VS Code).

## Passo 1 — Colocar o token

Na pasta `backend`, copie `.env.example` para um arquivo novo chamado **`.env`** e cole o token depois do `=`:

```
TMDB_BEARER_TOKEN=eyJhbGciOi...
```

O `.env` fica só no seu computador: o Git o ignora. Não coloque o token em nenhum outro arquivo.

## Passo 2 — Instalar

```bash
cd backend
uv sync --frozen --extra semantico --extra jev --extra entidades
```

Os três extras:
- `semantico`: modelos da busca por tema, dos filmes parecidos e da classificação;
- `jev`: SDK do Jev;
- `entidades`: spaCy, para as entidades e relações.

Para conferir a instalação, rode os testes. Eles devem terminar com `OK`:

```bash
uv run --frozen python -m unittest discover -s tests
```

## Passo 3 — Gerar o catálogo do site (cerca de 8 minutos, uma vez só)

A busca por tema e os filmes parecidos procuram num catálogo de cerca de 5.500 filmes, que **não vem no repositório**. Gere-o com três comandos:

```bash
uv run --frozen python -m app.corpus collect --config ../config/coleta/coleta_site.json --output ../data/coleta/site_2026-10-05
uv run --frozen python -m app.corpus process --input ../data/coleta/site_2026-10-05 --output ../data/preparacao/site_2026-10-05 --stopwords ../config/coleta/stopwords_pt.txt
uv run --frozen --extra semantico python -m app.representations build --input ../data/preparacao/site_2026-10-05 --output ../data/representacoes/site_2026-10-05 --config ../config/representacoes/vetorizacao_site.json
```

Sem o catálogo, o site funciona, mas a busca por tema e os filmes parecidos usam só os 428 filmes da amostra, e aparece uma faixa amarela no topo.

> Se um comando disser que a pasta de saída já existe, aquele passo já foi feito. Pule para o próximo.

## Passo 4 — Preparar as críticas (segundos, uma vez só)

A aba "Analisar crítica" treina o modelo com as críticas que vêm no repositório, mas elas precisam ser preparadas antes:

```bash
uv run --frozen python -m app.sentiment process --input ../data/coleta/criticas_2026-10-10 --output ../data/preparacao/criticas_2026-10-10 --stopwords ../config/coleta/stopwords_pt.txt
```

## Passo 5 — Ligar o site (toda vez)

**Terminal 1: a API.** Na pasta `backend`:

```bash
uv run --frozen --extra semantico --extra jev --extra entidades uvicorn app.main:app --host 127.0.0.1
```

Espere aparecer `Application startup complete.`, o que leva de 20 a 40 segundos. Nesse tempo, a API carrega o catálogo e o modelo de sentença, treina o classificador de gênero e o de sentimento e carrega o spaCy. **Deixe este terminal aberto.**

**Terminal 2: as telas.** Abra outro terminal, também na pasta `backend`:

```bash
uv run --frozen python -m http.server 5500 --directory ../frontend
```

**Deixe este terminal aberto também.** Agora abra **<http://127.0.0.1:5500>** no navegador.

O indicador no canto superior direito deve ficar verde, com "servidor online · 5.525 filmes". Para desligar, aperte **Ctrl + C** em cada terminal.

## O que testar em cada tela

| Onde | O que fazer | Precisa de |
|---|---|---|
| Aba **"Buscar filmes"** | Digite um título ("Matrix"), preferências ("uma comédia recente") ou um tema ("astronautas perdidos no espaço") | Token do TMDB; catálogo (passo 3) para a busca por tema |
| **Ficha do filme** (clique num filme) | Veja **"Personagens, lugares e relações"** e **"Filmes parecidos"** | Extra `entidades`; catálogo (passo 3) |
| Aba **"Classificar sinopse"** | Cole uma sinopse ou clique em "Usar um exemplo" | Extra `semantico` |
| Aba **"Analisar crítica"** | Escreva uma opinião sobre um filme ou clique em "Usar um exemplo" | Críticas preparadas (passo 4) |

A documentação interativa da API, com todas as rotas, fica em <http://127.0.0.1:8000/docs>.

## Problemas comuns

| O que aparece | O que fazer |
|---|---|
| Indicador vermelho, "servidor offline (rode o uvicorn)" | A API não está rodando ou ainda está carregando: veja o terminal 1 e espere `Application startup complete.` |
| "Defina TMDB_BEARER_TOKEN" | Falta o `.env` com o token (passo 1), ou ele foi salvo fora da pasta `backend` |
| Faixa amarela "Catálogo do site não gerado" | Rode o passo 3 e reinicie a API |
| "Análise de sentimento indisponível" | Rode o passo 4 e reinicie a API |
| "Entidades e relações indisponíveis" ou "Busca por sinopse indisponível" | Faltou um extra no `uv sync` (passo 2) ou no comando da API |
| A tela não mudou depois de uma atualização do projeto | Recarregue sem cache: **Ctrl + F5** |
| "Address already in use" / porta em uso | Já há uma API ou um servidor de telas aberto; feche o terminal antigo ou aperte Ctrl + C nele |
| `uv` dá "Acesso negado" ao instalar | Feche a API (Ctrl + C) e tente de novo; o Windows trava os arquivos enquanto ela roda |
| Windows bloqueia o `python.exe` ("Controle de Aplicativo") | O Controle Inteligente de Aplicativos do Windows impede o ambiente de rodar; na máquina de desenvolvimento ele foi desativado |

Outros comandos (refazer cada etapa, conferir os dados entregues) estão em [como-executar.md](como-executar.md).
