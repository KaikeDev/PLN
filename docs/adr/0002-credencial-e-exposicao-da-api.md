# 0002 — Credencial do TMDB, configuração e exposição da API local

- Estado: Aceita
- Data: 2026-09-14

## Contexto

A interface estática chama a API local, que chama o TMDB com a credencial do servidor. Na revisão de 14/09/2026 foram encontrados:

- `backend/.env` com credenciais reais versionado no commit `a09a21c` e enviado ao GitHub.
- Dois `.env.example` com nomes de variáveis diferentes dos lidos pelo código, o que fazia idioma e timeout serem ignorados sem aviso.
- Um comentário afirmando que o CORS protegia o token. CORS só restringe leitura de respostas por navegadores; `curl`, scripts e outras máquinas da rede não são afetados.
- Nenhum limite de requisições nem de tamanho da consulta.
- Fallback para `api_key` na query string, que pode aparecer em logs.

## Decisão

1. **Credencial**: apenas `TMDB_BEARER_TOKEN`, enviado no cabeçalho `Authorization`. A chave `api_key` na URL deixou de ser aceita.
2. **Configuração**: `app.settings.Settings` (pydantic-settings) lê variáveis de ambiente e `backend/.env`, resolvido pelo caminho do pacote e não pelo diretório atual. Valores inválidos falham na leitura. O token é `SecretStr`. Existe um único modelo, `backend/.env.example`.
3. **Inicialização**: a API falha ao iniciar sem token. A coleta falha antes de criar a pasta de saída.
4. **Exposição**: a API é documentada para rodar com `--host 127.0.0.1`. O CORS lista só as origens da interface (`CORS_ORIGINS`) e aceita apenas `GET`, sem cabeçalhos extras.
5. **Abuso de cota**: limite de `RATE_LIMIT_PER_MINUTE` requisições por IP em janela deslizante de 60 s, com resposta 429 e `Retry-After`. `/saude` fica fora do limite. A consulta tem no máximo 200 caracteres.
6. **Erros**: mensagens repassadas ao cliente só contêm status HTTP ou tipo da exceção, nunca URL ou cabeçalhos.
7. **Repositório**: `.env`, bytecode e caches ficam no `.gitignore` e foram removidos do índice.

## Alternativas consideradas

- Autenticação da API local (chave própria): exagerada para uma demonstração local e exigiria expor outra credencial ao navegador.
- `slowapi`/Redis para limite de taxa: dependência a mais; o limite em memória basta para um processo local.
- Reescrever o histórico do Git: não substitui a revogação da credencial e exige force-push coordenado. Fica a critério da equipe.

## Consequências

- **Ação obrigatória:** revogar e regenerar o token e a chave expostos no painel do TMDB.
- Quem usava `TMDB_API_KEY` precisa configurar `TMDB_BEARER_TOKEN` (disponível na mesma página do TMDB).
- O limite de taxa vale por processo; com várias réplicas, seria preciso um armazenamento compartilhado.
