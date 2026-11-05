# 0032. RAG para perguntas sobre os filmes: busca híbrida como recuperador, trechos de crítica e citações conferidas (Unidade 4)

- Estado: Aceita
- Data: 2026-11-01

## Contexto

A técnica central da Unidade 4 é responder perguntas em linguagem natural sobre os filmes ("tem algum filme sobre luto?", "o que acharam de Oppenheimer?"). Nenhuma tarefa anterior fazia isso: a busca devolve uma lista, e o sentimento lê uma crítica de cada vez. Um LLM sozinho responderia de memória, sem garantia de que o filme existe no catálogo nem de que a opinião veio de alguém. A base de LLM ([ADR 0029](0029-base-de-llm-por-api-gratuita.md)) e a interpretação da consulta ([ADR 0030](0030-interpretacao-da-consulta-por-llm.md)) já existiam, e a busca híbrida tinha sido avaliada nas 20 consultas anotadas ([ADR 0020](0020-busca-hibrida-tfidf-e-sentenca.md), MAP de 0,627).

## Decisão

- **O recuperador é a busca híbrida que já existe**, sem banco vetorial novo.
  - Ela foi avaliada e escolhida com consultas anotadas.
  - Os 5,5 mil vetores do catálogo cabem na memória, e o cosseno com NumPy leva milissegundos; FAISS ou um banco vetorial só acrescentariam dependência.
  - Os filtros vêm do mesmo intérprete da pesquisa (LLM com reserva nas regras). Os títulos citados na pergunta também entram, porque a sinopse raramente traz o próprio título ("Pecadores vale a pena?").
- **k = 8 filmes no contexto.** Na avaliação com 5, 10 e 20 filmes, a precisão dos citados ficou alta nos três casos (0,95, 0,90 e 0,93), mas a revocação dentro do contexto caiu com o tamanho (0,87, 0,68 e 0,59), e os tokens de entrada quase dobraram a cada passo (cerca de 1.400, 2.500 e 4.800). Oito fica entre 5 e 10: dá margem para a busca errar o primeiro lugar sem pagar o custo de 20.
- **Críticas em trechos.** Até 2 trechos de cerca de 400 caracteres por filme, escolhidos pelo embedding de sentença como os mais parecidos com a pergunta, com a nota do autor e **sem o autor**. A crítica inteira estouraria o contexto (algumas passam de 2.000 caracteres), e o trecho certo carrega a opinião.
- **Saída estruturada com citações por id.** O LLM devolve `{resposta, contexto_suficiente, filmes: [{id, motivo}]}`, e o texto marca cada filme com `[F<id>]`.
- **Defesas de fidelidade:**
  - `grounding.py` remove do texto e da lista qualquer id fora do contexto. Uma resposta sem nenhuma citação válida vira "Não encontrei no catálogo…";
  - o prompt manda separar o enredo (sinopse) da opinião (críticas) e recusar quando o contexto não basta;
  - o bloco "De onde veio a resposta" mostra no site os 8 filmes, as pontuações e os trechos usados.
- **Defesas contra *prompt injection*:**
  - sinopses e críticas são declaradas como dados, não instruções;
  - marcas `[F…]` vindas de terceiros são neutralizadas antes de entrar no contexto;
  - a pergunta vai como dado, e a saída só é aceita no esquema.
- **Custo controlado:** uma chamada por pergunta, limite de 5 por minuto por IP nas rotas com LLM, orçamento diário `rag` de 250 e cache das perguntas repetidas.
- **Exemplos gravados:** as seis perguntas de exemplo da aba têm a resposta da avaliação em `frontend/dados/exemplos_rag.json`, mostrada quando a cota acaba.

## Avaliação (`data/rag/2026-11-01/`)

Perguntas e rubrica commitadas antes da primeira chamada (`714084f`). Foram 179 chamadas, sem falha: o Gemini respondeu 114 e o Groq 12, quando o Gemini devolveu 503.

| Medida | Resultado |
|---|---|
| Precisão: busca híbrida, 5 primeiros | 0,57 |
| Precisão dos citados pelo RAG (k = 5 / 10 / 20) | 0,95 / 0,90 / 0,93, com 2,4 a 2,8 filmes citados por resposta |
| Perguntas sem resposta no catálogo recusadas | 5 de 5 |
| Citações inventadas (removidas pela conferência) | 0 |
| Tentativas de injeção obedecidas | 0 de 3. As três foram recusadas. O sinal automático marcou a do poema porque a recusa repete a palavra "gatos", um falso positivo |
| Perguntas de opinião recusadas, com e sem trechos de crítica | 1 de 10 com os trechos; **10 de 10 sem** |
| Tokens por resposta (média) | 2.264 de entrada, 220 de saída |
| Latência | Mediana de 12 s e p95 de 124 s, inflados pelas novas tentativas durante o 503 do Gemini |

A precisão dos citados **não é diretamente comparável** à precisão @5: o LLM cita menos filmes (cerca de 2,7) e escolhe os mais seguros. O ganho real é outro: ele descarta os filmes fracos da lista, explica por que cada filme serve, e a revocação mostra o que fica de fora. A ablação mostra que **as críticas são indispensáveis para as perguntas de opinião** e não mudam as de tema (1 recusa em 15 nos dois casos).

A **fidelidade** (cada frase está no contexto?) depende do julgamento de dois integrantes com a rubrica de `config/rag/rubrica.md`. O arquivo para os juízes sai de `python -m app.rag judgment-template`, e a concordância (percentual e kappa de Cohen), de `python -m app.rag agreement`. Na data desta ADR, esse julgamento ainda não tinha sido feito.

## Consequências

- O site ganha uma função que nenhuma técnica anterior oferecia: responder juntando sinopse e críticas, com links para a ficha de cada filme citado.
- A qualidade do RAG fica presa à da busca: o LLM não cita o que ela não trouxe. Uma pergunta sobre um filme fora do catálogo é recusada ("Super Mario" não está na amostra avaliada).
- Respostas citadas podem ser fiéis ao contexto e ainda pouco úteis (em "luto", Guardiões da Galáxia Vol. 3 aparece pela sinopse). Isso é o que o julgamento humano mede.
- A latência de segundos e a dependência de cota exigem as respostas gravadas e mensagens claras quando o LLM falha.
- Agentes que escolhem ferramentas ficaram de fora: cada pergunta custaria várias chamadas, e não haveria como avaliá-los com o gabarito existente.
