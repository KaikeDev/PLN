# 0031. Sentimento por LLM zero-shot e few-shot comparado ao TF-IDF e ao BERTimbau (Unidade 4)

- Estado: Aceita
- Data: 2026-11-01

## Contexto

Na Aula 9, a polaridade e a nota das críticas do TMDB foram aprendidas com as oito representações. O F1 macro foi de 85,6% no TF-IDF e 86,7% no BERTimbau, com erro médio da nota de 1,37 e 1,33 ([ADR 0026](0026-analise-de-sentimentos.md)). Os limites conhecidos são negação, ironia e o autor principal, que escreveu 67% das críticas: treinado sem ele, o TF-IDF cai muito. Um LLM lê o texto inteiro sem treino e pode explicar a decisão, mas custa cota e latência e não é determinístico. A base de LLM já existia ([ADR 0029](0029-base-de-llm-por-api-gratuita.md)).

## Decisão

- **Mesmas críticas para todos os sistemas.** 200 críticas sorteadas com semente fixa e commitadas antes da primeira chamada (`1880036`): metade negativas, metade positivas, metade do autor principal. O TF-IDF e o BERTimbau entram com as **predições fora da dobra** da Aula 9, e nenhum sistema viu essas críticas no treino. O F1 deles é recalculado nessa amostra equilibrada; os números da Aula 9 valem para o conjunto completo, com 71% de positivas.
- **Três variantes de prompt no Gemini:** zero-shot, few-shot (quatro exemplos resolvidos, nenhum da amostra) e zero-shot sem justificativa. A **reserva** repete a variante do site no Groq. A saída é JSON com `polaridade` (enum), `nota` de 0 a 10 e `justificativa`. Críticas acima de 2.000 caracteres são cortadas no meio, igual para todas as variantes.
- **No site, o LLM fica ao lado do modelo treinado, sem substituí-lo:** o botão "Comparar com IA" na aba "Analisar crítica" (`GET /sentimento/llm`), com a variante few-shot, o limite de 5 chamadas por minuto por IP e o orçamento diário `sentimento`. O modelo treinado continua sendo a resposta principal: é instantâneo, não gasta cota e mostra as palavras que pesaram.

## Resultado (`data/sentimento/llm_2026-11-01/`)

Duas execuções somadas com `--reuse`. A primeira (`llm_2026-10-26`) e a segunda pararam na **cota diária do Gemini**. No fim, cada variante no Gemini respondeu 171 a 173 das 200 críticas, e a reserva no Groq respondeu as 200.

| Sistema | F1 macro | Erro médio da nota | Respondidas |
|---|---:|---:|---:|
| Chutar a média das notas | — | 2,83 | 200 |
| TF-IDF (fora da dobra) | 0,791 | 1,80 | 200 |
| BERTimbau (fora da dobra) | 0,880 | 1,53 | 200 |
| LLM zero-shot (Gemini) | 0,930 | 0,91 | 172 |
| LLM few-shot (Gemini) | 0,925 | 1,00 | 173 |
| LLM zero-shot sem justificativa (Gemini) | 0,930 | 0,94 | 171 |
| **LLM few-shot (Groq, reserva)** | **0,915** | **1,04** | **200** |

- **O LLM, sem treino, supera os dois modelos treinados.** A comparação completa é a da reserva, nas 200 críticas: F1 de 0,915 contra 0,880 do BERTimbau, e erro da nota de 1,04 contra 1,53. O ganho maior é na nota: o LLM fica a até 1 ponto da nota do autor em 74% das críticas, contra 41% do BERTimbau.
- **Generaliza entre autores.** Nas críticas dos demais autores, o TF-IDF cai para F1 de 0,70, e a reserva fica em 0,93.
- **O prompt pouco importa.** Zero-shot e few-shot ficam a menos de um ponto de F1 entre si, e a justificativa não muda a polaridade. O few-shot gasta cerca de 60% mais tokens de entrada (825 contra 521).
- **Onde o LLM erra:** críticas mistas em que a nota do autor é baixa, mas o texto é benevolente ("Um bom filme familiar, ainda que não seja brilhante", nota 4). Nesses casos, os modelos treinados acertam porque aprenderam o vocabulário do autor principal. Com a variante few-shot, só o LLM acertou 10 críticas, e só os modelos treinados acertaram 8.
- **Viés das falhas:** as respostas que faltaram no Gemini são todas de autores que não o principal, por causa da ordem da amostra. Por isso o número completo da comparação é o da reserva.
- **Não medidos:** a estabilidade (20 críticas repetidas) e os quatro casos da equipe dependiam do Gemini depois da cota e ficaram sem resposta. A mesma linha de comando com `--reuse ../data/sentimento/llm_2026-11-01` pede só o que faltou, quando a cota renovar.

## Consequências

- O quadro de técnicas registra um resultado de melhoria clara com LLM, medido de forma justa (mesmas críticas, predições fora da dobra).
- A variante do site continua few-shot, que é a avaliada nas 200 críticas pela reserva. O zero-shot teria o mesmo F1 com menos tokens; trocar exige uma nova avaliação da reserva.
- O LLM não vai para a resposta principal da aba: cada análise custaria uma chamada e segundos de espera, e a cota gratuita não cobre um site público. Ele fica como comparação, com a justificativa visível.
- A avaliação depende da cota do dia. As respostas brutas ficam gravadas, e o `llm-verify` no CI confere as duas pastas.
