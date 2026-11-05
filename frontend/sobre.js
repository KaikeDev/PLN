"use strict";

// Página "Sobre o projeto" (ADR 0034): tabelas e gráficos de barras em SVG montados a partir de dados/resultados.json,
// sem biblioteca externa. Cada gráfico tem role="img", aria-label com os números e a tabela equivalente logo abaixo.

const SVG = "http://www.w3.org/2000/svg";
const NOMES_REPRESENTACAO = {
  bow_sem_pontuacao: "BoW sem pontuação",
  bow_sem_stopwords: "BoW sem stopwords",
  tfidf_sem_pontuacao: "TF-IDF sem pontuação",
  tfidf_sem_stopwords: "TF-IDF sem stopwords",
  word2vec_cbow: "word2vec CBOW",
  word2vec_skipgram: "word2vec skip-gram",
  bert_base_pt: "BERTimbau",
  sentenca_minilm: "Embedding de sentença (MiniLM)",
};
const NOMES_CURTOS = { word2vec_skipgram: "skip-gram", word2vec_cbow: "CBOW", bert_base_pt: "BERTimbau", sentenca_minilm: "MiniLM" };
const NOMES_INTERPRETACAO = { regras: "Regras léxicas", zero_shot: "LLM zero-shot", few_shot: "LLM few-shot (site)", reserva: "Few-shot com reserva" };
const NOMES_CATEGORIA = {
  explicita: "Explícita",
  parafrase: "Paráfrase",
  negacao: "Negação",
  periodo: "Período",
  armadilha_lexica: "Armadilha léxica",
  sem_filtro: "Sem filtro",
  tema: "Tema",
  opiniao: "Opinião",
  sem_resposta: "Sem resposta",
  injecao: "Injeção de prompt",
};

function el(tag, { classe, texto, atributos = {} } = {}, filhos = []) {
  const no = document.createElement(tag);
  if (classe) no.className = classe;
  if (texto !== undefined) no.textContent = texto;
  for (const [nome, valor] of Object.entries(atributos)) no.setAttribute(nome, valor);
  no.append(...filhos);
  return no;
}

function svg(tag, atributos = {}, filhos = []) {
  const no = document.createElementNS(SVG, tag);
  for (const [nome, valor] of Object.entries(atributos)) no.setAttribute(nome, String(valor));
  no.append(...filhos);
  return no;
}

function tabela({ legenda, colunas, linhas }) {
  const cabecalho = el("tr", {}, colunas.map((coluna) => el("th", { classe: coluna.num ? "num" : undefined, texto: coluna.titulo, atributos: { scope: "col" } })));
  const corpo = linhas.map((linha) =>
    el(
      "tr",
      {},
      colunas.map((coluna, indice) => {
        const valor = coluna.valor(linha);
        const celula = el(indice === 0 ? "th" : "td", { classe: [coluna.num ? "num" : "", coluna.melhor?.(linha) ? "melhor" : ""].join(" ").trim() || undefined });
        if (indice === 0) celula.setAttribute("scope", "row");
        celula.textContent = valor;
        return celula;
      }),
    ),
  );
  return el("div", { classe: "tabela-rolagem" }, [
    el("table", { classe: "tabela" }, [...(legenda ? [el("caption", { texto: legenda })] : []), el("thead", {}, [cabecalho]), el("tbody", {}, corpo)]),
  ]);
}

// Barras horizontais de uma só série: o valor medido em destaque e as referências em cinza.
function graficoBarras({ titulo, itens, maximo = 1, formato = "pct1", nomeValor = "Valor" }) {
  const largura = 640;
  const colunaRotulo = 250;
  const colunaValor = 64;
  const linha = 30;
  const altura = itens.length * linha + 8;
  const area = largura - colunaRotulo - colunaValor;
  const descricao = itens.map((item) => `${item.rotulo}: ${formatarNumero(item.valor, formato)}`).join("; ");
  const grafico = svg("svg", { viewBox: `0 0 ${largura} ${altura}`, role: "img", "aria-label": `${titulo}. ${descricao}` });
  grafico.append(svg("line", { class: "eixo-svg", x1: colunaRotulo, x2: colunaRotulo, y1: 0, y2: altura }));
  itens.forEach((item, indice) => {
    const y = indice * linha + 6;
    const valor = Number(item.valor);
    const comprimento = Number.isFinite(valor) ? Math.max(2, (Math.min(valor, maximo) / maximo) * area) : 0;
    const rotulo = svg("text", { class: "rotulo-svg", x: colunaRotulo - 8, y: y + 13, "text-anchor": "end" });
    rotulo.textContent = item.rotulo;
    const barra = svg("rect", { class: `barra-svg${item.referencia ? " barra-svg--referencia" : ""}`, x: colunaRotulo + 1, y: y + 2, width: comprimento, height: 16, rx: 4 }, [
      svg("title", {}, [document.createTextNode(`${item.rotulo}: ${formatarNumero(item.valor, formato)}`)]),
    ]);
    const texto = svg("text", { class: "valor-svg", x: colunaRotulo + comprimento + 8, y: y + 15 });
    texto.textContent = formatarNumero(item.valor, formato);
    grafico.append(rotulo, barra, texto);
  });
  const tabelaEquivalente = tabela({
    colunas: [
      { titulo: "Sistema", valor: (item) => item.rotulo },
      { titulo: nomeValor, num: true, valor: (item) => formatarNumero(item.valor, formato) },
    ],
    linhas: itens,
  });
  return el("figure", { classe: "grafico" }, [
    el("figcaption", { texto: titulo }),
    grafico,
    el("details", {}, [el("summary", { texto: "Ver como tabela" }), tabelaEquivalente]),
  ]);
}

function montar(id, ...filhos) {
  const alvo = document.getElementById(id);
  if (alvo) alvo.replaceChildren(...filhos);
}

function filtrosLegiveis(filtros) {
  const partes = [];
  if (filtros.generos?.length) partes.push(`gêneros: ${filtros.generos.join(", ")}`);
  if (filtros.generos_excluidos?.length) partes.push(`sem: ${filtros.generos_excluidos.join(", ")}`);
  if (filtros.lancado_depois) partes.push(`a partir de ${filtros.lancado_depois.slice(0, 4)}`);
  if (filtros.lancado_antes) partes.push(`até ${filtros.lancado_antes.slice(0, 4)}`);
  if (filtros.bem_avaliado) partes.push("bem avaliado");
  return partes.length ? partes.join(" · ") : "nenhum filtro";
}

function renderizarTarefas(dados) {
  const { linhas, referencia } = dados.tarefas_representacoes;
  const metricas = [
    { chave: "busca_map", titulo: "Busca: MAP", formato: "decimal3" },
    { chave: "recomendacao_precisao_5", titulo: "Recomendação: precisão @5", formato: "pct1" },
    { chave: "agrupamento_ari", titulo: "Agrupamento: ARI", formato: "decimal3" },
    { chave: "classificacao_f1", titulo: "Classificação: F1 macro", formato: "pct1" },
  ];
  const melhor = Object.fromEntries(metricas.map(({ chave }) => [chave, Math.max(...linhas.map((linha) => linha[chave]))]));
  const todas = [{ representacao: "Referência que ignora o texto", ...referencia, busca_map: null }, ...linhas];
  montar(
    "tabela-tarefas",
    tabela({
      legenda: "Uma métrica por célula, na amostra avaliada; em destaque, a melhor de cada tarefa.",
      colunas: [
        { titulo: "Representação", valor: (linha) => NOMES_REPRESENTACAO[linha.representacao] ?? linha.representacao },
        ...metricas.map(({ chave, titulo, formato }) => ({
          titulo,
          num: true,
          valor: (linha) => formatarNumero(linha[chave], formato),
          melhor: (linha) => linha.representacao in NOMES_REPRESENTACAO && linha[chave] === melhor[chave],
        })),
      ],
      linhas: todas,
    }),
  );
  const itens = [];
  for (const { chave, titulo, formato } of metricas) {
    const vencedora = linhas.find((linha) => linha[chave] === melhor[chave]);
    itens.push({ rotulo: `${titulo.split(":")[0]}: ${NOMES_CURTOS[vencedora.representacao] ?? NOMES_REPRESENTACAO[vencedora.representacao]}`, valor: melhor[chave], formato });
    if (referencia[chave] !== undefined && referencia[chave] !== null) itens.push({ rotulo: `${titulo.split(":")[0]}: referência`, valor: referencia[chave], referencia: true, formato });
  }
  montar(
    "grafico-tarefas",
    graficoBarras({
      titulo: "Melhor representação de cada tarefa contra a referência que ignora o texto (escala de 0 a 1)",
      itens,
      formato: "decimal3",
      nomeValor: "Métrica (0 a 1)",
    }),
  );
}

function renderizarInterpretacao(dados) {
  const interpretacao = dados.unidade_4.interpretacao;
  const sistemas = ["regras", "zero_shot", "few_shot"];
  montar(
    "grafico-interpretacao",
    graficoBarras({
      titulo: `Interpretação da frase: acerto exato dos filtros nas ${interpretacao.frases} frases anotadas`,
      itens: sistemas.map((nome) => ({ rotulo: NOMES_INTERPRETACAO[nome], valor: interpretacao.sistemas[nome].acerto_exato, referencia: nome === "regras" })),
      formato: "pct0",
      nomeValor: "Acerto exato",
    }),
  );
  montar(
    "tabela-interpretacao",
    tabela({
      legenda: "Acerto exato por categoria de frase e filtros inventados (filtro que a frase não pede).",
      colunas: [
        { titulo: "Categoria", valor: (linha) => linha.nome },
        ...sistemas.map((nome) => ({ titulo: NOMES_INTERPRETACAO[nome], num: true, valor: (linha) => linha[nome] })),
      ],
      linhas: [
        ...Object.entries(interpretacao.por_categoria).map(([categoria, valores]) => ({
          nome: NOMES_CATEGORIA[categoria] ?? categoria,
          ...Object.fromEntries(sistemas.map((nome) => [nome, formatarNumero(valores[nome], "pct0")])),
        })),
        { nome: "Filtros inventados", ...Object.fromEntries(sistemas.map((nome) => [nome, formatarNumero(interpretacao.sistemas[nome].filtro_inventado, "int")])) },
        { nome: "Tokens de entrada por frase", regras: "—", zero_shot: formatarNumero(interpretacao.tokens_entrada_medio.zero_shot, "int"), few_shot: formatarNumero(interpretacao.tokens_entrada_medio.few_shot, "int") },
      ],
    }),
  );
  montar(
    "exemplos-interpretacao",
    ...interpretacao.exemplos.map((exemplo) =>
      el("div", { classe: "exemplo-io" }, [
        el("p", {}, [el("strong", { texto: "Entrada: " }), `“${exemplo.frase}”`]),
        el("p", { texto: `Regras: ${filtrosLegiveis(exemplo.regras)}` }),
        el("p", { texto: `LLM few-shot: ${filtrosLegiveis(exemplo.llm)}` }),
        el("p", { classe: "fraco", texto: `Gabarito: ${filtrosLegiveis(exemplo.esperado)}` }),
      ]),
    ),
  );
}

function renderizarSentimento(dados) {
  const sentimento = dados.unidade_4.sentimento;
  if (!sentimento) {
    montar("grafico-sentimento", el("p", { classe: "fraco", texto: "Avaliação pendente." }));
    return;
  }
  const variante = sentimento.sistemas.find((item) => item.sistema === sentimento.variante_do_site);
  if (variante) document.getElementById("variante-sentimento").textContent = variante.nome.replace(/^LLM /, "");
  const sistemas = sentimento.sistemas.filter((item) => item.sistema !== "zero_shot_sem_justificativa");
  montar(
    "grafico-sentimento",
    graficoBarras({
      titulo: `Sentimento: F1 macro da polaridade nas ${sentimento.criticas} críticas equilibradas`,
      itens: sistemas.map((item) => ({ rotulo: item.nome, valor: item.f1_macro, referencia: item.sistema === "tfidf" || item.sistema === "bertimbau" })),
      formato: "pct1",
      nomeValor: "F1 macro",
    }),
  );
  const estratos = sentimento.por_estrato;
  montar(
    "tabela-sentimento",
    tabela({
      legenda: "Polaridade, nota e estratos. As métricas do LLM contam só as críticas que ele respondeu.",
      colunas: [
        { titulo: "Sistema", valor: (item) => item.nome },
        { titulo: "F1 macro", num: true, valor: (item) => formatarNumero(item.f1_macro, "pct1") },
        { titulo: "Erro médio da nota", num: true, valor: (item) => formatarNumero(item.erro_nota, "decimal2") },
        { titulo: "Com negação", num: true, valor: (item) => formatarNumero(estratos["com_negacao=true"]?.[item.sistema], "pct1") },
        { titulo: "Autor principal", num: true, valor: (item) => formatarNumero(estratos["autor_principal=true"]?.[item.sistema], "pct1") },
        { titulo: "Demais autores", num: true, valor: (item) => formatarNumero(estratos["autor_principal=false"]?.[item.sistema], "pct1") },
        { titulo: "Respondidas", num: true, valor: (item) => formatarNumero(item.respondidas, "int") },
      ],
      linhas: [...sentimento.sistemas, { nome: "Chutar a média das notas", sistema: "media", f1_macro: null, erro_nota: sentimento.media_erro_nota, respondidas: sentimento.criticas }],
    }),
  );
  montar(
    "exemplos-sentimento",
    ...sentimento.exemplos.map((exemplo) =>
      el("div", { classe: "exemplo-io" }, [
        el("p", {}, [el("strong", { texto: `${exemplo.filme} (nota do autor: ${formatarNumero(exemplo.nota_do_autor, "int")})` })]),
        el("p", { texto: `“${exemplo.trecho}”` }),
        el("p", { texto: `LLM: ${exemplo.llm.polaridade}, nota ${formatarNumero(exemplo.llm.nota, "decimal1")}. ${exemplo.llm.justificativa ?? ""}` }),
        el("p", { classe: "fraco", texto: `TF-IDF: ${exemplo.tfidf.polaridade}, nota ${formatarNumero(exemplo.tfidf.nota, "decimal1")} · BERTimbau: ${exemplo.bertimbau.polaridade}, nota ${formatarNumero(exemplo.bertimbau.nota, "decimal1")}` }),
      ]),
    ),
  );
}

function renderizarRag(dados) {
  const rag = dados.unidade_4.rag;
  if (!rag) {
    montar("grafico-rag", el("p", { classe: "fraco", texto: "Avaliação pendente: rode python -m app.rag eval (docs/tecnico/como-executar.md)." }));
    return;
  }
  montar(
    "grafico-rag",
    graficoBarras({
      titulo: "Precisão: filmes citados pelo RAG × 5 primeiros da busca híbrida, nas 20 consultas anotadas",
      itens: [
        { rotulo: "Busca híbrida, 5 primeiros", valor: rag.busca_precisao_5, referencia: true },
        ...rag.contextos.map((item) => ({ rotulo: `RAG, ${item.filmes} filmes no contexto`, valor: item.precisao_dos_citados })),
      ],
      formato: "pct0",
      nomeValor: "Precisão",
    }),
  );
  const perguntas = Object.entries(rag.perguntas).map(([categoria, item]) => ({ categoria, ...item }));
  montar(
    "tabela-rag",
    tabela({
      legenda: "Métricas automáticas nas perguntas de avaliação (com trechos de crítica no contexto).",
      colunas: [
        { titulo: "Categoria", valor: (item) => NOMES_CATEGORIA[item.categoria] ?? item.categoria },
        { titulo: "Perguntas", num: true, valor: (item) => item.perguntas },
        { titulo: "Respondidas", num: true, valor: (item) => item.respondidas },
        { titulo: "Recusou", num: true, valor: (item) => item.recusou },
        { titulo: "Citações inventadas (removidas)", num: true, valor: (item) => item.citacoes_inventadas },
        { titulo: "Filmes por resposta", num: true, valor: (item) => formatarNumero(item.citados_por_resposta, "decimal1") },
        { titulo: "Injeção obedecida (sinal automático)", num: true, valor: (item) => (item.injecao_obedecida === null ? "—" : item.injecao_obedecida) },
      ],
      linhas: perguntas,
    }),
    tabela({
      legenda: "Tamanho do contexto: mais filmes dão mais chance de achar o relevante, mas custam mais tokens.",
      colunas: [
        { titulo: "Filmes no contexto", valor: (item) => item.filmes },
        { titulo: "Precisão dos citados", num: true, valor: (item) => formatarNumero(item.precisao_dos_citados, "pct0") },
        { titulo: "Revocação no contexto", num: true, valor: (item) => formatarNumero(item.revocacao_no_contexto, "pct0") },
        { titulo: "Filmes por resposta", num: true, valor: (item) => formatarNumero(item.citados_por_resposta, "decimal1") },
        { titulo: "Tokens de entrada", num: true, valor: (item) => formatarNumero(item.tokens_entrada_medio, "int") },
        { titulo: "Falhas", num: true, valor: (item) => item.falhas },
      ],
      linhas: rag.contextos,
    }),
  );
  montar(
    "exemplos-rag",
    ...rag.exemplos.map((exemplo) =>
      el("div", { classe: "exemplo-io" }, [
        el("p", {}, [el("strong", { texto: "Pergunta: " }), `“${exemplo.pergunta}”`]),
        el("p", { texto: `Resposta: ${exemplo.resposta}` }),
        el("p", { classe: "fraco", texto: `Filmes citados: ${exemplo.citados.join(", ") || "nenhum"}` }),
      ]),
    ),
  );
}

function renderizarQuadro(dados) {
  montar(
    "quadro",
    tabela({
      legenda: "Quadro do item 1 do enunciado, igual ao de docs/9-tecnicas-avancadas.md.",
      colunas: [
        { titulo: "Tecnologia ou abordagem", valor: (linha) => linha.tecnologia },
        { titulo: "Utilizada?", valor: (linha) => linha.utilizada },
        { titulo: "Aplicação ou justificativa", valor: (linha) => linha.justificativa },
      ],
      linhas: dados.quadro ?? [],
    }),
  );
  document.querySelector("#quadro table")?.classList.add("quadro");
}

function renderizarTecnologias(dados) {
  const { modelos, bibliotecas, python } = dados.tecnologias;
  montar(
    "tabela-modelos",
    tabela({
      legenda: "Modelos pré-treinados, baixados do Hugging Face com a revisão fixada e rodando localmente (sem API).",
      colunas: [
        { titulo: "Representação", valor: (item) => NOMES_REPRESENTACAO[item.representacao] ?? item.representacao },
        { titulo: "Modelo", valor: (item) => item.modelo },
        { titulo: "Revisão", valor: (item) => item.revisao.slice(0, 10) },
      ],
      linhas: modelos,
    }),
  );
  montar(
    "tabela-bibliotecas",
    tabela({
      legenda: `Python ${python}. Versões travadas em backend/uv.lock.`,
      colunas: [
        { titulo: "Biblioteca", valor: ([nome]) => nome },
        { titulo: "Versão", valor: ([, versao]) => versao ?? "—" },
      ],
      linhas: Object.entries(bibliotecas),
    }),
  );
  const llm = dados.llm;
  montar(
    "tabela-llm",
    tabela({
      legenda: `Acesso por API gratuita, temperatura ${formatarNumero(llm.temperatura, "decimal1")}, na ordem de tentativa (config/llm/llm.json).`,
      colunas: [
        { titulo: "Uso", valor: ([uso]) => ({ interpretacao: "Interpretação da frase", sentimento: "Sentimento", rag: "Perguntas (RAG)" })[uso] ?? uso },
        { titulo: "Máximo de tokens de saída", num: true, valor: ([uso]) => formatarNumero(llm.maximo_de_tokens[uso], "int") },
        { titulo: "Orçamento diário do site", num: true, valor: ([uso]) => formatarNumero(llm.orcamento_diario[uso], "int") },
      ],
      linhas: Object.entries(llm.maximo_de_tokens),
    }),
  );
  montar("provedores-llm", document.createTextNode(llm.provedores.map((item) => `${item.nome} (${item.modelo})`).join(", depois ")));
}

async function verificarDemonstracao() {
  const aviso = document.getElementById("aviso-estatico");
  try {
    const base = location.port === "5500" ? `http://${location.hostname === "localhost" ? "localhost" : "127.0.0.1"}:8000` : "";
    const resposta = await fetch(`${base}/saude`, { headers: { accept: "application/json" } });
    if (!resposta.ok) throw new Error();
    const saude = await resposta.json();
    const filmes = saude.catalogo?.filmes;
    const status = document.getElementById("status");
    status.textContent = Number.isInteger(filmes) ? `demonstração online · ${filmes.toLocaleString("pt-BR")} filmes` : "demonstração online";
    status.className = "status status--ok";
  } catch {
    aviso.hidden = false;
    const status = document.getElementById("status");
    status.textContent = "versão estática";
    status.className = "status status--pendente";
  }
}

carregarResultados()
  .then((dados) => {
    renderizarTarefas(dados);
    renderizarQuadro(dados);
    renderizarInterpretacao(dados);
    renderizarSentimento(dados);
    renderizarRag(dados);
    renderizarTecnologias(dados);
  })
  .catch(() => {
    document.getElementById("erro-resultados").hidden = false;
  });
verificarDemonstracao();
