# Spec 05 — Páginas do site: identificação, "Sobre o projeto" e acessibilidade

**Depende de:** 01–03 para os números (a estrutura pode ser feita antes) · **ADR:** 0034 · **Esforço:** 2 dias

## Objetivo

Fazer o próprio site cumprir os itens B.1, B.2 e B.4 a B.6 e as seis questões do item 3. Hoje o site é uma ferramenta sem contexto: o cabeçalho diz "API de Filmes (TMDB)" e não traz autores, problema, metodologia nem limitações. O avaliador da Mostra precisa entender o projeto **sem abrir o repositório**.

## Estrutura do site

```
Cabeçalho: "Sinopses de filmes: do corpus ao LLM" · Kaike Ventura Tuerpe, Luana Nitsche, Pedro Henrique Ortunio, Thiago Bodnar · PLN 2026/2 · FURB
           [indicador do servidor] [link para o repositório]
Abas: Buscar filmes | Perguntar (RAG) | Classificar sinopse | Analisar crítica | Sobre o projeto
Rodapé: atribuição TMDB · "Uso de IA generativa" · link para o repositório e para a ADR de publicação
```

Cada aba funcional ganha, no topo, um bloco curto e **recolhível** "Como usar e o que está por trás", com:

- o que fazer (1 ou 2 frases) e exemplos clicáveis;
- a técnica de PLN, em 1 ou 2 frases, com link para a seção da página "Sobre";
- o resultado medido daquela técnica (ex.: "F1 macro de 66% na validação cruzada").

## Página "Sobre o projeto"

Uma seção por item, na ordem abaixo. Os números são **lidos de `frontend/dados/resultados.json`**, que um script gera a partir de `data/` (abaixo). Nenhum número é digitado à mão no HTML.

| # | Seção | Conteúdo | Atende |
|---|---|---|---|
| 1 | Problema | Encontrar, recomendar e entender filmes a partir do **texto** (sinopses e críticas), em português, sem avaliações de usuários | B.2 |
| 2 | Objetivos | Os da proposta inicial, mais os da Unidade 4 | B.1, item 3.1 |
| 3 | Dados | Amostra avaliada de **428 sinopses** (4 gêneros × 3 períodos), catálogo de **5.525** só para a demonstração, **1.859 críticas**. Dizer com todas as letras: "**as métricas foram medidas na amostra menor; o catálogo maior não tem gabarito**" | B.5, item 5 |
| 4 | Metodologia | Diagrama do pipeline em SVG inline: coleta → 6 preparações → 8 representações → tarefas → LLM. Uma linha por tarefa | B.2, B.5 |
| 5 | Resultados das unidades anteriores | A tabela "tarefas × representações" do README e um gráfico de barras (melhor representação por tarefa contra a referência que ignora o texto) | B.4 |
| 6 | Técnicas avançadas (Unidade 4) | O **quadro do item 1** (spec 06), com Sim/Não e justificativa | Item 1 |
| 7 | Resultados da Unidade 4 | Três comparações, cada uma com gráfico e 2 exemplos de entrada e saída: regras × LLM na interpretação; TF-IDF × BERTimbau × LLM no sentimento; busca híbrida × RAG, com a fidelidade | Item 1, B.4 |
| 8 | Avaliação crítica | **As seis questões do item 3, cada uma com título próprio** e resposta sustentada por número ou exemplo (abaixo) | Item 3 |
| 9 | Limitações | Técnicas e metodológicas: rótulos aproximados, consultas julgadas pela equipe, catálogo sem gabarito, correferência, viés de popularidade e do autor principal, não determinismo do LLM | B.5 |
| 10 | Custos e dependências externas | TMDB (token gratuito), Gemini e Groq (cota gratuita: o que acontece quando acaba), Hugging Face Spaces (dorme quando inativo), tamanho dos modelos e memória medida (spec 04) | B, último parágrafo |
| 11 | Tecnologias e modelos | Lista com versões: MiniLM (revisão), BERTimbau, word2vec NILC, spaCy `pt_core_news_sm`, scikit-learn, FastAPI, modelo exato e configurações do LLM (temperatura, máximo de tokens, provedor e acesso por API) | Item 5 |
| 12 | Uso de IA generativa | Fornecedor e modelo (Anthropic, Claude Opus 5.5, pelo Claude Code), principais usos (código, testes, documentação, páginas, primeira marcação de anotações revisada pela equipe) e principais prompts. Dizer o que foi **revisado pela equipe** | Item 5 |
| 13 | Referências | TMDB (com a atribuição obrigatória), artigos e modelos, bibliotecas e o repositório | Pôster 8, B.5 |

### As seis questões: o que cada resposta precisa conter

| Questão | Sustentar com |
|---|---|
| 1. Os objetivos foram alcançados? | Tabela "objetivo da proposta → status → evidência", sem esconder o que ficou parcial (ex.: recomendação avaliada por gênero, não por usuários) |
| 2. Quais técnicas foram mais adequadas? | A tabela tarefas × representações (nenhuma vence todas) e o vencedor de cada comparação da Unidade 4 |
| 3. LLMs trouxeram melhorias ou possibilidades novas? | Os números das specs 01, 02 e 03, **inclusive onde não melhorou**; e o que só o LLM faz (responder perguntas com citações, entender paráfrase) |
| 4. Limitações | A seção 9, com as mais importantes primeiro |
| 5. Como a qualidade foi verificada | Validação cruzada sem vazamento, consultas anotadas antes de rodar, julgamento duplo do RAG com concordância, mais de 148 testes, manifesto com hashes e `verify` no CI |
| 6. Aprimoramentos futuros | Concretos: correferência; avaliação com usuários reais; reordenação por *cross-encoder*; ajuste fino do BERTimbau; modelo local quantizado para tirar a dependência de cota; pôsteres (multimodal) |

## Gráficos e dados

- **`docs/entregas/unidade-4/coletar_resultados.py`** (no padrão da Unidade 3) lê `data/**/metrics.json`, `results.json` e os demais e grava `frontend/dados/resultados.json`. Um teste confere que cada número do JSON bate com o arquivo de origem.
- Gráficos em **SVG gerado no navegador pelo próprio `script.js`** a partir do JSON (barras simples, sem biblioteca externa). Assim a CSP fica `script-src 'self'` e não depende de CDN. Cada gráfico tem `role="img"`, `aria-label` com os números e uma tabela equivalente logo abaixo (acessível e imprimível).
- **Reserva estática:** a mesma página "Sobre" também funciona aberta sozinha (`frontend/sobre.html` e `dados/resultados.json`). Assim pode ir para o GitHub Pages como link de reserva (spec 04).

## Acessibilidade e funcionamento

- **Lighthouse** (Acessibilidade ≥ 90; Boas práticas ≥ 90) e **axe DevTools** sem erros críticos em cada aba. Gravar os relatórios em `docs/tecnico/acessibilidade/`.
- Navegação só por teclado: as abas com setas (o padrão `tablist` que já existe), foco visível, modal com foco preso e `Esc` para fechar.
- Contraste AA nas cores de entidades e nos selos; não depender só da cor (entidades marcadas também com o rótulo PER/LOC/ORG/MISC).
- Responsivo a partir de 360 px de largura, sem rolagem horizontal.
- `lang="pt-BR"`, textos alternativos nos pôsteres (o título do filme) e `aria-live` nas respostas (já existe em parte).
- Erros com mensagem útil: cota esgotada, servidor acordando, TMDB fora do ar.

## Testes

- `node --check` (já no CI) para os arquivos JS novos.
- Teste Python: `resultados.json` é coerente com os arquivos de origem (ver acima).
- Lista de verificação manual de cada aba, registrada em `docs/tecnico/validacao.md`, em celular e em computador, no link público.

## Critérios de aceite

- [ ] Título, autores, disciplina e descrição visíveis no topo de todas as abas.
- [ ] A página "Sobre" tem as 13 seções, com as seis questões em títulos próprios.
- [ ] Nenhum número digitado à mão: todos vêm de `resultados.json`, conferido por teste.
- [ ] Lighthouse e axe dentro das metas, com os relatórios salvos.
- [ ] A versão estática da página "Sobre" abre sem a API.
- [ ] ADR 0034: organização da página, números gerados de `data/`, gráficos sem biblioteca e a página estática de reserva.
