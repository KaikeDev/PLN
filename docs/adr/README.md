# Registros de decisões arquiteturais (ADRs)

Cada ADR registra uma decisão com contexto, alternativas e consequências, no formato [MADR](https://adr.github.io/madr/). Uma decisão substituída não é apagada: recebe o estado **Substituída por ADR NNNN**.

| ADR | Decisão | Estado |
|---|---|---|
| [0001](0001-registrar-decisoes-em-adrs.md) | Registrar decisões em ADRs | Aceita |
| [0002](0002-credencial-e-exposicao-da-api.md) | Credencial do TMDB, configuração e exposição da API local | Aceita |
| [0003](0003-normalizacao-do-corpus-e-da-pesquisa.md) | Normalizações distintas para corpus e pesquisa | Aceita |
| [0004](0004-arquitetura-em-camadas.md) | Arquitetura em camadas com portas e adaptadores | Aceita |
| [0005](0005-pesquisa-por-regras-lexicas.md) | Pesquisa auxiliar por regras léxicas e heurísticas explícitas | Aceita |
| [0006](0006-prioridade-de-titulo-exato.md) | Modo automático prioriza título exato da primeira página | Aceita |
| [0007](0007-cliente-http-e-cache.md) | Cliente HTTP síncrono, sessão por thread, retry e cache em memória | Aceita |
| [0008](0008-idioma-do-codigo-e-do-contrato.md) | Identificadores em inglês; contrato, mensagens e documentação em português | Aceita |
| [0009](0009-saidas-imutaveis-e-verificaveis.md) | Saídas imutáveis, determinísticas e verificáveis por manifesto | Aceita |
| [0010](0010-dados-versionados-no-git.md) | Amostra entregue versionada no Git | Aceita |
| [0011](0011-formatos-e-modelos-seguros.md) | Formatos legíveis e modelos pré-treinados com revisão fixada | Aceita |
| [0012](0012-parametros-do-experimento-vetorial.md) | Parâmetros do experimento vetorial | Aceita |
| [0013](0013-ferramentas-de-qualidade.md) | Ambiente, testes, lint, tipos e CI | Aceita |
| [0014](0014-amostragem-intencional.md) | Amostragem intencional da coleta | Aceita |
| [0015](0015-aula7-bert-cbow-e-polissemia.md) | BERT contextual, CBOW × skip-gram e sondas de polissemia (Aula 7) | Aceita |
| [0016](0016-politica-do-gitignore.md) | Política do `.gitignore` | Aceita |

O resumo de todas as decisões e das justificativas está em [`adr.md`](../../adr.md), na raiz do repositório.

Modelo para uma nova ADR: copie a estrutura de qualquer arquivo, use o próximo número, acrescente uma linha nesta tabela e uma entrada em `adr.md`.
