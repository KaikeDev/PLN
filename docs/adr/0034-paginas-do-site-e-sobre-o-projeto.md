# 0034. Páginas do site: identificação, "Sobre o projeto" gerada dos dados e acessibilidade (Unidade 4)

- Estado: Aceita
- Data: 2026-11-01

## Contexto

Na Modalidade B, o enunciado da Unidade 4 pede que a própria página traga título, autores, problema, técnicas, exemplos, dados, metodologia, limitações, custos e instruções. Também pede as seis questões de avaliação crítica e o quadro de técnicas. O site era uma ferramenta sem contexto: o cabeçalho dizia "API de Filmes (TMDB)", e os números de cada técnica estavam digitados nos rodapés das abas, alguns já desatualizados (o MAP da busca, por exemplo). O avaliador da Mostra precisa entender o projeto sem abrir o repositório.

## Decisão

- **Identificação em todas as páginas.** O cabeçalho traz o título "Sinopses de filmes: do corpus ao LLM", os autores, a disciplina e uma frase de descrição. Ao lado ficam o indicador do servidor e os links para "Sobre o projeto" e para o repositório. O rodapé traz a atribuição ao TMDB e os links para o uso de IA, para os custos e para a ADR de publicação.
- **Abas na ordem da demonstração:** Buscar filmes, Perguntar (RAG), Classificar sinopse e Analisar crítica. Cada aba ganha um bloco recolhível, "Como usar e o que está por trás", com o que fazer, os exemplos, a técnica e o resultado medido.
- **"Sobre o projeto" é uma página separada (`frontend/sobre.html`)**, aberta por um link e não por uma quinta aba:
  - um link dentro de um `tablist` quebraria o padrão de acessibilidade das abas;
  - a mesma página serve sozinha como **reserva estática** (GitHub Pages ou arquivo local), porque só precisa de `dados/resultados.json`. Quando `/saude` não responde, ela avisa que é a versão estática.
- **As 13 seções da spec 05**, com as seis questões do item 3 em títulos próprios (8.1 a 8.6).
- **Nenhum número digitado à mão no HTML.**
  - `docs/entregas/unidade-4/coletar_resultados.py` lê `data/**` e `config/**` e grava `frontend/dados/resultados.json`. Ele só usa a biblioteca padrão.
  - As páginas preenchem os elementos `data-resultado="caminho.no.json"`.
  - `backend/tests/test_resultados.py` roda o coletor de novo e compara com o JSON commitado. Também confere que todo `data-resultado` das páginas aponta para um número existente.
  - O quadro de técnicas é copiado da tabela de `docs/9-tecnicas-avancadas.md`, para o repositório e a página terem o mesmo texto.
  - O catálogo do site fica fora do Git. Sem ele, o coletor mantém o valor anterior do JSON.
- **Gráficos em SVG gerados pelo `sobre.js`**, sem biblioteca. A CSP continua `script-src 'self'`, sem CDN:
  - barras horizontais de uma série, com o sistema medido na cor de destaque e as referências em cinza;
  - o valor escrito ao lado da barra e um `<title>` por barra, que serve de dica ao passar o mouse;
  - `role="img"` com um `aria-label` que traz todos os números, e a mesma informação numa tabela logo abaixo ("Ver como tabela").
- **Acessibilidade e erros:**
  - link "Pular para o conteúdo", `lang="pt-BR"`, foco visível e abas por setas, Home e End;
  - modal com foco preso, `Esc` para fechar e o foco devolvido ao elemento que o abriu;
  - entidades marcadas também com o rótulo (PER, LOC, ORG, MISC), e não só pela cor;
  - mensagens específicas para servidor acordando, cota de IA esgotada, TMDB fora do ar e limite de requisições;
  - meta: Lighthouse ≥ 90 em Acessibilidade e em Boas práticas; relatórios em `docs/tecnico/acessibilidade/`.

## Consequências

- Atualizar um resultado é rodar o coletor e commitar o JSON. O teste falha se alguém esquecer.
- O texto das seções continua escrito à mão. As afirmações qualitativas ("o few-shot não superou o zero-shot") precisam ser revistas quando uma avaliação é refeita.
- A página "Sobre" funciona sem a API. Os exemplos gravados do RAG (`dados/exemplos_rag.json`) também cobrem a aba "Perguntar" quando a cota acaba.
- No celular, os gráficos SVG encolhem com a largura da tela. A tabela equivalente continua legível.
