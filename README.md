# API de Filmes (TMDB)

Camada de conexao com a API do [TMDB](https://developer.themoviedb.org/reference/intro/getting-started)
exposta via FastAPI.

## Como rodar

```bash
pip install -r requirements.txt
cp -n .env.example .env     # -n = nao sobrescreve um .env ja preenchido
                            # depois preencha o TMDB_BEARER_TOKEN
uvicorn app.main:app --reload
```

Docs interativas: http://127.0.0.1:8000/docs

Com o backend no ar, tem uma telinha simples em `../frontend/` para buscar e
ver detalhes de filmes sem precisar do `/docs`:

```bash
cd ../frontend
python -m http.server 5500
```

Depois abra http://127.0.0.1:5500. O backend ja libera CORS para qualquer
origem (`CORSMiddleware` em `main.py`), entao funciona com qualquer servidor
estatico.

Sem servidor, direto no terminal:

```bash
python teste.py
python teste.py "cidade de deus"
```

## Estrutura

```
src/app/
├── main.py                    # cria a instancia FastAPI e inclui o api_router
├── core/
│   └── config.py               # le o .env (token, idioma, timeout)
├── api/
│   ├── router.py                # agrega os routers de rotas
│   └── routes/
│       ├── health.py            # GET /saude
│       └── filmes.py            # GET /busca, GET /filmes/{id}
├── services/
│   └── tmdb/
│       ├── client.py            # sessao HTTP: auth, retry, requisicao bruta
│       └── filmes.py            # regras de dominio: busca, detalhes, similares...
└── exceptions/
    └── tmdb.py                  # TMDBError
```

| camada            | papel                                                              |
|-------------------|---------------------------------------------------------------------|
| `api/routes/`     | endpoints FastAPI: validam entrada e traduzem erros em HTTP          |
| `services/tmdb/`  | integracao com o TMDB (transporte em `client.py`, dominio em `filmes.py`) |
| `exceptions/`     | erros da aplicacao, independentes do transporte HTTP                 |
| `core/config.py`  | configuracao lida do `.env`                                          |

`services/tmdb/filmes.py` e o ponto de entrada que a futura camada de PLN vai
consumir para responder perguntas em linguagem natural (ver "Proximos passos").

## Endpoints

| metodo | rota               | o que faz                                      |
|--------|--------------------|------------------------------------------------|
| GET    | `/busca?q=matrix`  | busca filmes por titulo (`&pagina=`, `&ano=`)  |
| GET    | `/filmes/{id}`     | ficha completa, com elenco e equipe            |
| GET    | `/saude`           | healthcheck                                    |

## Proximos passos

A camada de PLN (interpretar a pergunta do usuario e gerar a resposta em
linguagem natural) entra depois, consumindo as funcoes de
`app/services/tmdb/filmes.py`.


## Referências 

https://developer.themoviedb.org/docs/getting-started

https://www.themoviedb.org/
