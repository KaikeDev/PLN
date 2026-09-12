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
│       └── filmes.py            # GET /pesquisa, /busca, /descobrir, /filmes/{id}...
├── services/
│   ├── tmdb/
│   │   ├── client.py            # sessao HTTP: auth, retry, requisicao bruta
│   │   └── filmes.py            # regras de dominio: busca, detalhes, similares...
│   └── pln/
│       ├── normalizacao.py      # minusculas, sem acento, tokenizacao
│       ├── lexico.py            # dicionarios humor/genero e qualidade
│       ├── periodo.py           # regex de decada/ano/termos relativos
│       ├── negacao.py           # janela de negacao sobre generos
│       ├── generos_cache.py     # cache do mapa id<->nome de generos do TMDB
│       ├── extrator.py          # orquestra tudo -> FiltrosExtraidos
│       └── pesquisa.py          # decide busca por titulo vs. descoberta por filtro
└── exceptions/
    └── tmdb.py                  # TMDBError
```

| camada            | papel                                                              |
|-------------------|---------------------------------------------------------------------|
| `api/routes/`     | endpoints FastAPI: validam entrada e traduzem erros em HTTP          |
| `services/tmdb/`  | integracao com o TMDB (transporte em `client.py`, dominio em `filmes.py`) |
| `services/pln/`   | entende texto livre e traduz em filtros do TMDB (ver "Camada de PLN") |
| `exceptions/`     | erros da aplicacao, independentes do transporte HTTP                 |
| `core/config.py`  | configuracao lida do `.env`                                          |

## Endpoints

| metodo | rota                     | o que faz                                                        |
|--------|--------------------------|-------------------------------------------------------------------|
| GET    | `/pesquisa?q=...`        | texto livre (titulo ou descricao) — entende linguagem natural e decide entre `/busca` e `/descobrir` por baixo dos panos |
| GET    | `/busca?q=matrix`        | busca filmes por titulo (`&pagina=`, `&ano=`)                    |
| GET    | `/descobrir`             | busca por filtros: genero, nota, periodo (`&generos=`, `&nota_minima=`, `&votos_minimos=`, `&lancado_apos=`, `&ordenar_por=`...) |
| GET    | `/filmes/{id}`           | ficha completa, com elenco e equipe                              |
| GET    | `/filmes/{id}/similares` | filmes parecidos com o indicado                                  |
| GET    | `/pessoas?nome=`         | busca pessoas (ator, diretor...) por nome                        |
| GET    | `/generos`               | mapa id -> nome dos generos (para resolver `with_genres`)        |
| GET    | `/saude`                 | healthcheck                                                      |

## Camada de PLN

`services/pln/` interpreta frases livres como *"queria um filme descontraído
com boa avaliação que não seja muito antigo"* e traduz isso nos parametros de
`/descobrir` (genero, nota minima, periodo), sem exigir nenhum campo extra na
UI — o mesmo campo de busca (`frontend/index.html`) atende titulo e descricao.

Tudo em Python puro (regex, `unicodedata`, `dataclasses`, stdlib), sem spaCy/
transformers: o projeto esta fixado em Python 3.14 e essas libs (e os modelos
`pt_core_news`) ainda nao instalam nessa versao. Tecnicas aplicadas: normalizacao
de texto, casamento lexico (humor/adjetivo -> genero), extracao de expressoes
temporais via regex, e uma heuristica de janela para negacao ("nao quero
terror"). Se o texto nao gerar nenhum filtro descritivo, cai no comportamento
antigo de busca por titulo (`/busca`) — preserva "matrix", "cidade de deus" etc.

Testes/avaliacao: `backend/tests/test_extrator.py` (via `unittest`, sem
dependencia nova) tem casos anotados manualmente e imprime a acuracia por slot
(genero incluido/excluido, nota, periodo).

```bash
python -m unittest backend/tests/test_extrator.py -v
```


## Referências 

https://developer.themoviedb.org/docs/getting-started

https://www.themoviedb.org/
