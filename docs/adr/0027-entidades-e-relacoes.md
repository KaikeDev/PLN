# 0027 — Entidades nomeadas e relações nas sinopses com o spaCy (Aula 9)

- Estado: Aceita
- Data: 2026-10-10

## Contexto

O notebook da Aula 9 encadeia parsing de dependências, NER e extração de relações com o spaCy `pt_core_news_sm` e regras sobre a árvore de dependências, e termina com um grafo e uma lista de limites. O projeto não tinha nenhum modelo que fizesse NER ou parsing: as oito representações só transformam texto em vetores.

## Decisão

- **Modelo da aula:** spaCy 3.8 e `pt_core_news_sm` 3.8.0, num extra opcional `entidades`. O modelo é instalado pela URL fixa da versão, registrada no `uv.lock` com hash. É a única dependência de modelo fora das representações do projeto, liberada pela equipe para esta tarefa.
- **Regras do notebook portadas sem mudança:** `analisar_dependencias`, `extrair_entidades`, `obter_sintagma`, `obter_argumento`, `normalizar_preposicao` e `extrair_relacoes`. Um teste confere as triplas das frases do notebook.
- **Uma regra a mais, separável:** verbos coordenados (`conj`) sem sujeito herdam o sujeito do verbo ao qual se coordenam (`coordination` na configuração). Cada tripla registra a regra, e o relatório separa as do notebook das novas.
- **Base:** as 428 sinopses da amostra avaliada, no texto limpo (`02_clean.jsonl`), que mantém maiúsculas e pontuação.
- **Referência automática do NER:** os créditos do TMDB (os 15 primeiros do elenco, ator e personagem), coletados em `data/coleta/creditos_2026-10-10`. Medimos:
  - a revocação de pessoas: menções creditadas marcadas como PER;
  - a precisão estimada, um piso: entidades PER com algum nome dos créditos.
- **Relações sem precisão afirmada:** 40 triplas sorteadas vão para `review_sample.json`, com o campo `correta` vazio, para conferência manual da equipe.
- **Grafo em Mermaid** no relatório, no lugar do NetworkX e do Matplotlib do notebook: o GitHub desenha o mesmo grafo dirigido sem mais dependências.
- **No site:** a rota `GET /entidades` analisa um texto na hora; a ficha do filme a chama com a sinopse.

## Alternativas consideradas

- **Regras manuais sem modelo** (maiúsculas e listas de nomes dos créditos): sem parsing, não há relações, e o NER seria só uma busca de nomes conhecidos.
- **NER com BERTimbau ajustado:** exigiria um conjunto anotado em BIO para treinar; a aula usa o spaCy pronto.
- **Stanza:** citado na aula, mas o notebook usa o spaCy, e trocar o modelo mudaria os resultados de referência.
- **Anotar as entidades à mão:** mais preciso, mas a equipe não anotou as 428 sinopses. Os créditos dão uma medida parcial sem anotação; a conferência manual das relações fica preparada.
- **Resolver correferência:** o `pt_core_news_sm` não tem esse componente, e a aula o deixa como limite.

## Consequências

- **NER:** 1.671 menções. Revocação de pessoas de 73,7%, com 98,5% das menções creditadas reconhecidas com alguma categoria; precisão estimada de PER de 81,6%. O erro típico é a categoria: personagens viram LOC ou MISC.
- **Relações:** 1.435 triplas, 88 delas pela regra de coordenação; 63,5% das sentenças têm ao menos uma. 35% das triplas têm um pronome como sujeito, e só 2,2% ligam duas entidades.
- **Dependência opcional:** sem o extra `entidades`, a API sobe sem a rota de entidades (503), e os testes que exigem o spaCy são pulados.
