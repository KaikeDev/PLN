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

Sem servidor, direto no terminal:

```bash
python teste.py
python teste.py "cidade de deus"
```

## Estrutura

| arquivo         | papel                                                    |
|-----------------|----------------------------------------------------------|
| `app/config.py` | le o `.env` (token, idioma, timeout)                     |
| `app/tmdb.py`   | camada de requisicoes: sessao, auth, retry, erros        |
| `app/main.py`   | endpoints FastAPI                                        |
| `teste.py`      | testa a conexao sem subir o servidor                     |

## Endpoints

| metodo | rota               | o que faz                                      |
|--------|--------------------|------------------------------------------------|
| GET    | `/busca?q=matrix`  | busca filmes por titulo (`&pagina=`, `&ano=`)  |
| GET    | `/filmes/{id}`     | ficha completa, com elenco e equipe            |
| GET    | `/saude`           | healthcheck                                    |

## Proximos passos

A camada de PLN (interpretar a pergunta do usuario e gerar a resposta em
linguagem natural) entra depois, consumindo as funcoes de `app/tmdb.py`.
