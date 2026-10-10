"use strict";

const API_BASE = document.querySelector('meta[name="api-base"]').content.replace(/\/$/, "");
const TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w200";
const SEM_POSTER = "sem-poster.svg";
const POSTER_PATH = /^\/[\w.-]+$/;
const ELENCO_EXIBIDO = 6;

const elStatus = document.getElementById("status");
const elAvisoCatalogo = document.getElementById("aviso-catalogo");
const elForm = document.getElementById("form-busca");
const elTitulo = document.getElementById("campo-titulo");
const elModo = document.getElementById("modo-busca");
const elAno = document.getElementById("campo-ano");
const elMensagem = document.getElementById("mensagem");
const elResultados = document.getElementById("resultados");
const elModal = document.getElementById("modal");
const elModalCorpo = document.getElementById("modal-corpo");
const elFecharModal = document.getElementById("fechar-modal");
const elFormClassificacao = document.getElementById("form-classificacao");
const elSinopse = document.getElementById("campo-sinopse");
const elMensagemClassificacao = document.getElementById("mensagem-classificacao");
const elResultadoClassificacao = document.getElementById("resultado-classificacao");
const elContadorSinopse = document.getElementById("contador-sinopse");
const elExemploSinopse = document.getElementById("exemplo-sinopse");
const elBotaoClassificar = document.getElementById("botao-classificar");
const elFormSentimento = document.getElementById("form-sentimento");
const elCritica = document.getElementById("campo-critica");
const elMensagemSentimento = document.getElementById("mensagem-sentimento");
const elResultadoSentimento = document.getElementById("resultado-sentimento");
const elContadorCritica = document.getElementById("contador-critica");
const elExemploCritica = document.getElementById("exemplo-critica");
const elBotaoAnalisar = document.getElementById("botao-analisar");
const LIMITE_CRITICA = 5000;
const EXEMPLOS_CRITICA = [
  {
    tipo: "elogio direto",
    texto: "Que filme maravilhoso! A fotografia é deslumbrante, as atuações são excelentes e a trilha sonora emociona do começo ao fim. Saí do cinema querendo ver de novo.",
  },
  {
    tipo: "crítica negativa",
    texto: "Uma perda de tempo. O roteiro é confuso, os diálogos são fracos e o final é previsível. Fiquei entediado na metade e não recomendo.",
  },
  {
    tipo: "negações",
    texto: "Não é um filme ruim. Não chega a ser uma obra-prima, mas não decepciona, e o elenco não deixa a desejar.",
  },
  {
    tipo: "ironia",
    texto: "Ótimo, mais uma continuação que ninguém pediu, com as mesmas piadas de sempre e duas horas e meia de explosões. Genial.",
  },
];
let proximoExemploCritica = 0;
let exemploCriticaAtual = null;
const elAbas = Array.from(document.querySelectorAll('[role="tab"]'));
const LIMITE_SINOPSE = 1000;
const EXEMPLOS = [
  {
    titulo: "Invocação do Mal",
    texto: "Harrisville, Rhode Island, Estados Unidos, 1968. Os investigadores paranormais Ed e Lorraine Warren trabalham para ajudar uma família aterrorizada por uma presença sombria em sua fazenda. Forçados a confrontar uma entidade poderosa, os Warrens se vêem presos no caso mais aterrorizante de suas vidas. Baseado numa história real.",
  },
  {
    titulo: "Se Beber, Não Case!",
    texto: "Dois dias antes de seu casamento, Doug e três amigos vão de carro até Las Vegas para uma louca e memorável despedida de solteiro. Quando os três padrinhos acordam na manhã seguinte, eles não conseguem se lembrar de nada e notam que Doug desapareceu. Com pouco tempo de sobra, os amigos tentam refazer a noite anterior e encontrar Doug para que possam levá-lo de volta a Los Angeles a tempo de chegar ao altar.",
  },
  {
    titulo: "Um Sonho de Liberdade",
    texto: "Em 1946, Andy Dufresne, um banqueiro jovem e bem sucedido, tem a sua vida radicalmente modificada ao ser condenado por um crime que nunca cometeu, o homicídio de sua esposa e do amante dela. Ele é mandado para uma prisão que é o pesadelo de qualquer detento, a Penitenciária Estadual de Shawshank, no Maine. Lá ele irá cumprir a pena perpétua.",
  },
  {
    titulo: "Perdido em Marte",
    texto: "O astronauta Mark Watney é enviado a uma missão em Marte. Após uma severa tempestade ele é dado como morto, abandonado pelos colegas e acorda sozinho no misterioso planeta com escassos suprimentos, sem saber como reencontrar os companheiros ou retornar à Terra.",
  },
];
let proximoExemplo = 0;
let aberturaAtual = 0;
let exemploAtual = null;

function elemento(tag, { classe, texto, atributos = {} } = {}, filhos = []) {
  const el = document.createElement(tag);
  if (classe) el.className = classe;
  if (texto !== undefined) el.textContent = texto;
  for (const [nome, valor] of Object.entries(atributos)) el.setAttribute(nome, valor);
  el.append(...filhos);
  return el;
}

function urlPoster(caminho) {
  return typeof caminho === "string" && POSTER_PATH.test(caminho) ? `${TMDB_IMAGE_BASE}${caminho}` : SEM_POSTER;
}

function anoDe(data) {
  const ano = String(data ?? "").slice(0, 4);
  return /^\d{4}$/.test(ano) ? ano : "?";
}

function nota(valor) {
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero.toFixed(1) : "0.0";
}

async function obterJson(caminho, mensagemPadrao) {
  const resposta = await fetch(`${API_BASE}${caminho}`, { headers: { accept: "application/json" } });
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const detalhe = typeof dados.detail === "string" ? dados.detail : mensagemPadrao;
    throw new Error(detalhe);
  }
  return dados;
}

async function verificarSaude() {
  try {
    const dados = await obterJson("/saude", "offline");
    const catalogo = dados.catalogo;
    const filmes = Number.isInteger(catalogo?.filmes) ? catalogo.filmes.toLocaleString("pt-BR") : null;
    if (catalogo?.origem === "amostra_avaliada") {
      elStatus.textContent = `servidor online · só a amostra (${filmes} filmes)`;
      elStatus.className = "status status--aviso";
      elAvisoCatalogo.hidden = false;
    } else {
      elStatus.textContent = filmes ? `servidor online · ${filmes} filmes` : "servidor online";
      elStatus.className = "status status--ok";
      elAvisoCatalogo.hidden = true;
    }
  } catch {
    elStatus.textContent = "servidor offline (rode o uvicorn)";
    elStatus.className = "status status--erro";
  }
}

async function buscarFilmes(texto, ano, modo) {
  const params = new URLSearchParams({ q: texto, modo });
  if (ano) params.set("ano", ano);
  const dados = await obterJson(`/pesquisa?${params}`, "Falha ao buscar filmes.");
  const aviso = typeof dados.interpretacao?.aviso === "string" ? dados.interpretacao.aviso : "";
  return { filmes: Array.isArray(dados.resultados) ? dados.resultados : [], aviso };
}

function classificarSinopse(texto) {
  return obterJson(`/classificacao?${new URLSearchParams({ texto })}`, "Falha ao classificar a sinopse.");
}

function porcentagem(valor) {
  const numero = Number(valor);
  return Number.isFinite(numero) ? `${Math.round(numero * 100)}%` : "?";
}

function classeGenero(nome) {
  const slug = String(nome ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z]+/g, "-")
    .replace(/^-|-$/g, "");
  return `genero--${slug}`;
}

function renderizarClassificacao(dados) {
  const generos = Array.isArray(dados.generos) ? dados.generos : [];
  if (generos.length === 0) {
    elMensagemClassificacao.textContent = "A classificação não devolveu gêneros.";
    return;
  }
  const [primeiro] = generos;
  const destaque = elemento("div", { classe: `destaque ${classeGenero(primeiro.genero)}` }, [
    elemento("div", {}, [
      elemento("span", { classe: "destaque__rotulo", texto: "Gênero previsto" }),
      elemento("span", { classe: "destaque__genero", texto: String(primeiro.genero) }),
    ]),
    elemento("span", { classe: "destaque__valor", texto: porcentagem(primeiro.probabilidade) }),
  ]);
  const barras = elemento(
    "ul",
    { classe: "barras", atributos: { "aria-label": "Probabilidade de cada gênero" } },
    generos.map((item) =>
      elemento("li", { classe: `barra ${classeGenero(item.genero)}` }, [
        elemento("span", { texto: String(item.genero) }),
        elemento("progress", { atributos: { max: "1", value: String(Number(item.probabilidade) || 0), "aria-label": `Probabilidade de ${item.genero}` } }),
        elemento("span", { classe: "barra__valor", texto: porcentagem(item.probabilidade) }),
      ]),
    ),
  );
  const filhos = [destaque, barras];
  if (exemploAtual) {
    filhos.unshift(elemento("p", { classe: "resultado__exemplo", texto: `Exemplo: sinopse de “${exemploAtual}”, que faz parte do corpus de treino.` }));
  }
  elResultadoClassificacao.replaceChildren(...filhos);
}

function analisarCritica(texto) {
  return obterJson(`/sentimento?${new URLSearchParams({ texto })}`, "Falha ao analisar a crítica.");
}

function decimal(valor, casas = 1) {
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero.toFixed(casas).replace(".", ",") : "?";
}

function listaPalavras(titulo, palavras, classe) {
  const itens = Array.isArray(palavras) ? palavras : [];
  return elemento("div", { classe: "palavras" }, [
    elemento("span", { classe: "palavras__titulo", texto: titulo }),
    itens.length
      ? elemento("ul", { classe: "palavras__lista" }, itens.map((item) => elemento("li", { classe: `palavra ${classe}`, texto: String(item.palavra) })))
      : elemento("span", { classe: "palavras__vazio", texto: "nenhuma" }),
  ]);
}

function renderizarSentimento(dados) {
  const positivo = dados.polaridade === "positivo";
  const classe = positivo ? "sentimento--positivo" : "sentimento--negativo";
  const chance = positivo ? Number(dados.probabilidade_positiva) : 1 - Number(dados.probabilidade_positiva);
  const destaque = elemento("div", { classe: `destaque ${classe}` }, [
    elemento("div", {}, [
      elemento("span", { classe: "destaque__rotulo", texto: "Sentimento previsto" }),
      elemento("span", { classe: "destaque__genero", texto: positivo ? "Positivo" : "Negativo" }),
    ]),
    elemento("span", { classe: "destaque__valor", texto: porcentagem(chance) }),
  ]);
  const barras = elemento("ul", { classe: "barras", atributos: { "aria-label": "Probabilidade e nota prevista" } }, [
    elemento("li", { classe: "barra sentimento--positivo" }, [
      elemento("span", { texto: "Chance de positivo" }),
      elemento("progress", { atributos: { max: "1", value: String(Number(dados.probabilidade_positiva) || 0), "aria-label": "Probabilidade de ser positiva" } }),
      elemento("span", { classe: "barra__valor", texto: porcentagem(dados.probabilidade_positiva) }),
    ]),
    elemento("li", { classe: "barra sentimento--nota" }, [
      elemento("span", { texto: "Nota prevista" }),
      elemento("progress", { atributos: { max: "10", value: String(Number(dados.nota_prevista) || 0), "aria-label": "Nota prevista de 0 a 10" } }),
      elemento("span", { classe: "barra__valor", texto: decimal(dados.nota_prevista) }),
    ]),
  ]);
  const filhos = [destaque, barras];
  if ((dados.palavras_positivas ?? []).length || (dados.palavras_negativas ?? []).length) {
    filhos.push(
      elemento("div", { classe: "palavras-grupo" }, [
        listaPalavras("Puxaram para positivo", dados.palavras_positivas, "sentimento--positivo"),
        listaPalavras("Puxaram para negativo", dados.palavras_negativas, "sentimento--negativo"),
      ]),
    );
  }
  if (exemploCriticaAtual) {
    filhos.unshift(elemento("p", { classe: "resultado__exemplo", texto: `Exemplo escrito pela equipe (${exemploCriticaAtual}), fora das críticas de treino.` }));
  }
  elResultadoSentimento.replaceChildren(...filhos);
}

function atualizarContadorCritica() {
  elContadorCritica.textContent = `${elCritica.value.length} / ${LIMITE_CRITICA}`;
}

function atualizarContador() {
  elContadorSinopse.textContent = `${elSinopse.value.length} / ${LIMITE_SINOPSE}`;
}

function selecionarAba(aba) {
  for (const outra of elAbas) {
    const ativa = outra === aba;
    outra.classList.toggle("aba--ativa", ativa);
    outra.setAttribute("aria-selected", String(ativa));
    outra.tabIndex = ativa ? 0 : -1;
    document.getElementById(outra.getAttribute("aria-controls")).hidden = !ativa;
  }
}

function buscarDetalhes(filmeId) {
  return obterJson(`/filmes/${encodeURIComponent(filmeId)}`, "Falha ao carregar o filme.");
}

function criarCard(filme) {
  const titulo = filme.title ?? "Sem título";
  const card = elemento("article", { classe: "card", atributos: { tabindex: "0" } }, [
    elemento("img", { atributos: { src: urlPoster(filme.poster_path), alt: `Pôster de ${titulo}`, loading: "lazy" } }),
    elemento("div", { classe: "card__corpo" }, [
      elemento("p", { classe: "card__titulo", texto: titulo }),
      elemento("p", { classe: "card__meta", texto: `${anoDe(filme.release_date)} · ⭐ ${nota(filme.vote_average)}` }),
    ]),
  ]);
  const abrir = () => abrirDetalhes(filme.id);
  card.addEventListener("click", abrir);
  card.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter" || evento.key === " ") {
      evento.preventDefault();
      abrir();
    }
  });
  return card;
}

function renderizarResultados({ filmes, aviso }) {
  elResultados.replaceChildren(...filmes.filter((filme) => Number.isInteger(filme.id)).map(criarCard));
  if (filmes.length === 0) elMensagem.textContent = aviso ? `${aviso}.` : "Nenhum filme encontrado.";
}

function criarDetalhe(filme) {
  const titulo = filme.title ?? "Sem título";
  const generos = (filme.genres ?? []).map((genero) => elemento("span", { classe: "tag", texto: genero.name }));
  const elenco = (filme.credits?.cast ?? []).slice(0, ELENCO_EXIBIDO).map((pessoa) => pessoa.name).join(", ");
  const info = elemento("div", { classe: "detalhe__info" }, [
    elemento("h2", { texto: `${titulo} (${anoDe(filme.release_date)})` }),
    elemento("div", { classe: "detalhe__generos" }, generos),
    elemento("p", { texto: filme.overview || "Sem sinopse disponível." }),
  ]);
  if (elenco) {
    info.append(elemento("p", { classe: "elenco" }, [elemento("strong", { texto: "Elenco:" }), ` ${elenco}`]));
  }
  return elemento("div", { classe: "detalhe" }, [
    elemento("img", { atributos: { src: urlPoster(filme.poster_path), alt: `Pôster de ${titulo}` } }),
    info,
  ]);
}

const CATEGORIAS = [
  { rotulo: "PER", nome: "Pessoas" },
  { rotulo: "LOC", nome: "Lugares" },
  { rotulo: "ORG", nome: "Organizações" },
  { rotulo: "MISC", nome: "Outros" },
];
const LIMITE_ENTIDADES = 2000;

function buscarEntidades(texto) {
  return obterJson(`/entidades?${new URLSearchParams({ texto })}`, "Falha ao extrair entidades e relações.");
}

function textoMarcado(texto, entidades) {
  const partes = [];
  let posicao = 0;
  for (const entidade of [...entidades].sort((a, b) => a.inicio - b.inicio)) {
    if (!Number.isInteger(entidade.inicio) || !Number.isInteger(entidade.fim) || entidade.inicio < posicao || entidade.fim > texto.length) continue;
    partes.push(texto.slice(posicao, entidade.inicio));
    partes.push(
      elemento("mark", { classe: `entidade entidade--${String(entidade.categoria).toLowerCase()}`, atributos: { title: String(entidade.categoria) } }, [
        texto.slice(entidade.inicio, entidade.fim),
        elemento("span", { classe: "entidade__rotulo", texto: String(entidade.categoria) }),
      ]),
    );
    posicao = entidade.fim;
  }
  partes.push(texto.slice(posicao));
  return elemento("p", { classe: "entidades__texto" }, partes);
}

function gruposEntidades(entidades) {
  return elemento(
    "div",
    { classe: "entidades__grupos" },
    CATEGORIAS.map(({ rotulo, nome }) => {
      const nomes = [...new Set(entidades.filter((entidade) => entidade.categoria === rotulo).map((entidade) => String(entidade.texto)))];
      return elemento("div", { classe: "palavras" }, [
        elemento("span", { classe: "palavras__titulo", texto: nome }),
        nomes.length
          ? elemento("ul", { classe: "palavras__lista" }, nomes.map((texto) => elemento("li", { classe: `palavra entidade--${rotulo.toLowerCase()}`, texto })))
          : elemento("span", { classe: "palavras__vazio", texto: "nenhum" }),
      ]);
    }),
  );
}

function listaRelacoes(relacoes) {
  if (!relacoes.length) return elemento("p", { classe: "parecidos__aviso", texto: "Nenhuma relação extraída pelas regras." });
  return elemento(
    "ul",
    { classe: "relacoes" },
    relacoes.map((tripla) =>
      elemento("li", { classe: "relacao" }, [
        elemento("span", { classe: "relacao__argumento", texto: String(tripla.sujeito) }),
        elemento("span", { classe: "relacao__verbo", texto: `— ${tripla.relacao} →` }),
        elemento("span", { classe: "relacao__argumento", texto: String(tripla.objeto) }),
      ]),
    ),
  );
}

async function carregarEntidades(sinopse, secao, abertura) {
  const titulo = elemento("h3", { texto: "Personagens, lugares e relações" });
  const corpo = elemento("p", { classe: "parecidos__aviso", texto: "Lendo a sinopse..." });
  secao.replaceChildren(titulo, corpo);
  const texto = String(sinopse ?? "").trim();
  if (!texto) {
    corpo.textContent = "Sem sinopse para analisar.";
    return;
  }
  try {
    const dados = await buscarEntidades(texto.slice(0, LIMITE_ENTIDADES));
    if (abertura !== aberturaAtual) return;
    const entidades = Array.isArray(dados.entidades) ? dados.entidades : [];
    const relacoes = Array.isArray(dados.relacoes) ? dados.relacoes : [];
    corpo.replaceWith(
      textoMarcado(texto.slice(0, LIMITE_ENTIDADES), entidades),
      gruposEntidades(entidades),
      elemento("h4", { classe: "entidades__subtitulo", texto: "Relações (sujeito — relação → objeto)" }),
      listaRelacoes(relacoes),
      elemento("p", { classe: "parecidos__aviso", texto: `Pelo spaCy ${dados.modelo}, com as regras de dependência da Aula 9. São previsões do modelo: confira com a sinopse.` }),
    );
  } catch (erro) {
    if (abertura === aberturaAtual) corpo.textContent = erro.message;
  }
}

function buscarParecidos(filmeId) {
  return obterJson(`/filmes/${encodeURIComponent(filmeId)}/parecidos`, "Falha ao buscar filmes parecidos.");
}

function criarParecido(filme) {
  const titulo = filme.title ?? "Sem título";
  const card = elemento("button", { classe: "parecido", atributos: { type: "button", title: `Abrir ${titulo}` } }, [
    elemento("img", { atributos: { src: urlPoster(filme.poster_path), alt: "", loading: "lazy" } }),
    elemento("span", { classe: "parecido__titulo", texto: titulo }),
    elemento("span", { classe: "parecido__meta", texto: `${anoDe(filme.release_date)} · ${porcentagem(filme.pontuacao)} parecido` }),
  ]);
  card.addEventListener("click", () => abrirDetalhes(filme.id));
  return card;
}

async function carregarParecidos(filmeId, secao, abertura) {
  const corpo = elemento("p", { classe: "parecidos__aviso", texto: "Procurando filmes com sinopse parecida..." });
  secao.replaceChildren(elemento("h3", { texto: "Filmes parecidos" }), corpo);
  try {
    const dados = await buscarParecidos(filmeId);
    if (abertura !== aberturaAtual) return;
    const filmes = Array.isArray(dados.parecidos) ? dados.parecidos.filter((filme) => Number.isInteger(filme.id)) : [];
    if (!dados.na_amostra) {
      corpo.textContent = "Este filme não está no catálogo de sinopses do site, então não há recomendações para ele.";
      return;
    }
    corpo.replaceWith(
      elemento("div", { classe: "parecidos__lista" }, filmes.map(criarParecido)),
      elemento("p", { classe: "parecidos__aviso", texto: `Pela sinopse, com o embedding de sentença (${dados.representacao}). A porcentagem é a similaridade do cosseno.` }),
    );
  } catch (erro) {
    if (abertura === aberturaAtual) corpo.textContent = erro.message;
  }
}

async function abrirDetalhes(filmeId) {
  const abertura = ++aberturaAtual;
  elModalCorpo.replaceChildren(elemento("p", { texto: "Carregando..." }));
  elModal.classList.remove("oculto");
  elFecharModal.focus();
  try {
    const filme = await buscarDetalhes(filmeId);
    if (abertura !== aberturaAtual) return;
    const secaoEntidades = elemento("section", { classe: "parecidos entidades", atributos: { "aria-label": "Personagens, lugares e relações" } });
    const secaoParecidos = elemento("section", { classe: "parecidos", atributos: { "aria-label": "Filmes parecidos" } });
    elModalCorpo.replaceChildren(criarDetalhe(filme), secaoEntidades, secaoParecidos);
    elModalCorpo.parentElement.scrollTop = 0;
    carregarEntidades(filme.overview, secaoEntidades, abertura);
    carregarParecidos(filmeId, secaoParecidos, abertura);
  } catch (erro) {
    if (abertura === aberturaAtual) elModalCorpo.replaceChildren(elemento("p", { classe: "mensagem", texto: erro.message }));
  }
}

function fecharModal() {
  elModal.classList.add("oculto");
}

elForm.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  elMensagem.textContent = "";
  elResultados.replaceChildren();
  try {
    renderizarResultados(await buscarFilmes(elTitulo.value.trim(), elAno.value.trim(), elModo.value));
  } catch (erro) {
    elMensagem.textContent = erro.message;
  }
});

elFormClassificacao.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  elMensagemClassificacao.textContent = "";
  elResultadoClassificacao.replaceChildren();
  elBotaoClassificar.disabled = true;
  elBotaoClassificar.textContent = "Classificando...";
  try {
    renderizarClassificacao(await classificarSinopse(elSinopse.value.trim()));
  } catch (erro) {
    elMensagemClassificacao.textContent = erro.message;
  } finally {
    elBotaoClassificar.disabled = false;
    elBotaoClassificar.textContent = "Classificar";
  }
});

elSinopse.addEventListener("input", () => {
  exemploAtual = null;
  atualizarContador();
});

elExemploSinopse.addEventListener("click", () => {
  const exemplo = EXEMPLOS[proximoExemplo];
  proximoExemplo = (proximoExemplo + 1) % EXEMPLOS.length;
  elSinopse.value = exemplo.texto;
  exemploAtual = exemplo.titulo;
  atualizarContador();
  elResultadoClassificacao.replaceChildren();
  elMensagemClassificacao.textContent = "";
  elSinopse.focus();
});

elFormSentimento.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  elMensagemSentimento.textContent = "";
  elResultadoSentimento.replaceChildren();
  elBotaoAnalisar.disabled = true;
  elBotaoAnalisar.textContent = "Analisando...";
  try {
    renderizarSentimento(await analisarCritica(elCritica.value.trim()));
  } catch (erro) {
    elMensagemSentimento.textContent = erro.message;
  } finally {
    elBotaoAnalisar.disabled = false;
    elBotaoAnalisar.textContent = "Analisar";
  }
});

elCritica.addEventListener("input", () => {
  exemploCriticaAtual = null;
  atualizarContadorCritica();
});

elExemploCritica.addEventListener("click", () => {
  const exemplo = EXEMPLOS_CRITICA[proximoExemploCritica];
  proximoExemploCritica = (proximoExemploCritica + 1) % EXEMPLOS_CRITICA.length;
  elCritica.value = exemplo.texto;
  exemploCriticaAtual = exemplo.tipo;
  atualizarContadorCritica();
  elResultadoSentimento.replaceChildren();
  elMensagemSentimento.textContent = "";
  elCritica.focus();
});

for (const aba of elAbas) {
  aba.addEventListener("click", () => selecionarAba(aba));
  aba.addEventListener("keydown", (evento) => {
    if (evento.key !== "ArrowRight" && evento.key !== "ArrowLeft") return;
    const passo = evento.key === "ArrowRight" ? 1 : -1;
    const proxima = elAbas[(elAbas.indexOf(aba) + passo + elAbas.length) % elAbas.length];
    selecionarAba(proxima);
    proxima.focus();
  });
}

elFecharModal.addEventListener("click", fecharModal);
elModal.addEventListener("click", (evento) => {
  if (evento.target === elModal) fecharModal();
});
document.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape") fecharModal();
});

verificarSaude();
