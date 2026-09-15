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
  return Array.isArray(dados.resultados) ? dados.resultados : [];
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

function renderizarResultados(filmes) {
  elResultados.replaceChildren(...filmes.filter((filme) => Number.isInteger(filme.id)).map(criarCard));
  if (filmes.length === 0) elMensagem.textContent = "Nenhum filme encontrado.";
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

async function abrirDetalhes(filmeId) {
  elModalCorpo.replaceChildren(elemento("p", { texto: "Carregando..." }));
  elModal.classList.remove("oculto");
  elFecharModal.focus();
  try {
    elModalCorpo.replaceChildren(criarDetalhe(await buscarDetalhes(filmeId)));
  } catch (erro) {
    elModalCorpo.replaceChildren(elemento("p", { classe: "mensagem", texto: erro.message }));
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

elFecharModal.addEventListener("click", fecharModal);
elModal.addEventListener("click", (evento) => {
  if (evento.target === elModal) fecharModal();
});
document.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape") fecharModal();
});

verificarSaude();
