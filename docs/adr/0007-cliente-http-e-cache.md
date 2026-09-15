# 0007 — Cliente HTTP síncrono, sessão por thread, retry e cache em memória

- Estado: Aceita
- Data: 2026-09-14

## Contexto

As rotas do FastAPI são síncronas e rodam num pool de threads. Havia uma única `requests.Session` global, criada no import e compartilhada entre threads, sem garantia de segurança. O mapa de gêneros ficava num cache global sem expiração, e o modo automático repetia a consulta da primeira página ao paginar.

## Decisão

- **Cliente**: `TMDBClient` com `requests`, uma sessão por thread (`threading.local`), fechadas no encerramento da aplicação. Timeout configurável (padrão 10 s).
- **Retry**: até 3 tentativas para GET, backoff exponencial com fator 0,5, para HTTP 429, 500, 502, 503 e 504.
- **Cache** (`CachedMovieCatalog`, Decorator): gêneros por 24 h; buscas por título por 5 min, até 256 entradas (LRU). A descoberta não usa cache, porque os filtros variam muito. Tudo protegido por lock.

## Alternativas consideradas

- `httpx.AsyncClient` com rotas assíncronas: exigiria reescrever rotas e a lógica de retry por status, que o `httpx` não oferece pronta.
- Cache externo (Redis): desnecessário para um processo local.

## Consequências

- O cache é por processo e pode servir resultados de até 5 minutos atrás.
- A coleta (`app.corpus.collect`) usa o mesmo cliente, portanto a mesma política de retry.
