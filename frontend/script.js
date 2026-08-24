// Tela simples para testar a API de Filmes (TMDB) sem depender do /docs.
// Ajuste API_BASE se o backend estiver rodando em outra porta/host.
const API_BASE = "http://127.0.0.1:8000";
const TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w200";
const SEM_POSTER = "https://placehold.co/200x300?text=Sem+imagem";

const elStatus = document.getElementById("status");
const elForm = document.getElementById("form-busca");
const elTitulo = document.getElementById("campo-titulo");
const elAno = document.getElementById("campo-ano");
const elMensagem = document.getElementById("mensagem");
const elResultados = document.getElementById("resultados");
const elModal = document.getElementById("modal");
const elModalCorpo = document.getElementById("modal-corpo");
const elFecharModal = document.getElementById("fechar-modal");

// TMDB e' um servico de terceiros: nunca confiar em titulo/sinopse/nomes
// como HTML seguro antes de jogar no DOM.
function escaparHtml(texto) {
  const div = document.createElement("div");
  div.textContent = texto ?? "";
  return div.innerHTML;
}

async function verificarSaude() {
  try {
    const resposta = await fetch(`${API_BASE}/saude`);
    if (!resposta.ok) throw new Error();
    elStatus.textContent = "servidor online";
    elStatus.className = "status status--ok";
  } catch {
    elStatus.textContent = "servidor offline (rode o uvicorn)";
    elStatus.className = "status status--erro";
  }
}

async function buscarFilmes(titulo, ano) {
  const params = new URLSearchParams({ q: titulo });
  if (ano) params.set("ano", ano);

  const resposta = await fetch(`${API_BASE}/busca?${params}`);
  const dados = await resposta.json();

  if (!resposta.ok) {
    throw new Error(dados.detail || "Falha ao buscar filmes.");
  }
  return dados.resultados;
}

async function buscarDetalhes(filmeId) {
  const resposta = await fetch(`${API_BASE}/filmes/${filmeId}`);
  const dados = await resposta.json();

  if (!resposta.ok) {
    throw new Error(dados.detail || "Falha ao carregar o filme.");
  }
  return dados;
}

function renderizarResultados(filmes) {
  elResultados.innerHTML = "";

  if (filmes.length === 0) {
    elMensagem.textContent = "Nenhum filme encontrado.";
    return;
  }

  for (const filme of filmes) {
    const card = document.createElement("article");
    card.className = "card";
    card.addEventListener("click", () => abrirDetalhes(filme.id));

    const poster = filme.poster_path
      ? `${TMDB_IMAGE_BASE}${filme.poster_path}`
      : SEM_POSTER;
    const ano = (filme.release_date || "").slice(0, 4) || "?";

    const titulo = escaparHtml(filme.title);
    card.innerHTML = `
      <img src="${poster}" alt="Poster de ${titulo}" loading="lazy" />
      <div class="card__corpo">
        <p class="card__titulo">${titulo}</p>
        <p class="card__meta">${ano} · ⭐ ${(filme.vote_average ?? 0).toFixed(1)}</p>
      </div>
    `;
    elResultados.appendChild(card);
  }
}

async function abrirDetalhes(filmeId) {
  elModalCorpo.innerHTML = "<p>Carregando...</p>";
  elModal.classList.remove("oculto");

  try {
    const filme = await buscarDetalhes(filmeId);
    const poster = filme.poster_path
      ? `${TMDB_IMAGE_BASE}${filme.poster_path}`
      : SEM_POSTER;
    const generos = (filme.genres || [])
      .map((g) => `<span class="tag">${escaparHtml(g.name)}</span>`)
      .join("");
    const elenco = (filme.credits?.cast || [])
      .slice(0, 6)
      .map((p) => escaparHtml(p.name))
      .join(", ");
    const titulo = escaparHtml(filme.title);
    const overview = escaparHtml(filme.overview) || "Sem sinopse disponivel.";

    elModalCorpo.innerHTML = `
      <div class="detalhe">
        <img src="${poster}" alt="Poster de ${titulo}" />
        <div class="detalhe__info">
          <h2>${titulo} (${(filme.release_date || "").slice(0, 4) || "?"})</h2>
          <div class="detalhe__generos">${generos}</div>
          <p>${overview}</p>
          ${elenco ? `<p class="elenco"><strong>Elenco:</strong> ${elenco}</p>` : ""}
        </div>
      </div>
    `;
  } catch (erro) {
    elModalCorpo.innerHTML = `<p class="mensagem">${escaparHtml(erro.message)}</p>`;
  }
}

elForm.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  elMensagem.textContent = "";
  elResultados.innerHTML = "";

  const titulo = elTitulo.value.trim();
  const ano = elAno.value.trim();

  try {
    const filmes = await buscarFilmes(titulo, ano);
    renderizarResultados(filmes);
  } catch (erro) {
    elMensagem.textContent = erro.message;
  }
});

elFecharModal.addEventListener("click", () => elModal.classList.add("oculto"));
elModal.addEventListener("click", (evento) => {
  if (evento.target === elModal) elModal.classList.add("oculto");
});

verificarSaude();
