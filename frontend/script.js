"use strict";

const API_BASE = document.querySelector('meta[name="api-base"]').content.replace(/\/$/, "");
const TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w200";
const SEM_POSTER = "sem-poster.svg";
const POSTER_PATH = /^\/[\w.-]+$/;
const ELENCO_EXIBIDO = 6;

const elStatus = document.getElementById("status");
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
    await obterJson("/saude", "offline");
    elStatus.textContent = "servidor online";
    elStatus.className = "status status--ok";
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
      corpo.textContent = "Este filme não está entre os 428 da amostra do projeto, então não há recomendações para ele.";
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
    const secaoParecidos = elemento("section", { classe: "parecidos", atributos: { "aria-label": "Filmes parecidos" } });
    elModalCorpo.replaceChildren(criarDetalhe(filme), secaoParecidos);
    elModalCorpo.parentElement.scrollTop = 0;
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
