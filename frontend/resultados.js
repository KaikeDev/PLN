"use strict";

// Números do projeto lidos de dados/resultados.json (gerado por docs/entregas/unidade-4/coletar_resultados.py, ADR 0034).
// Elementos com data-resultado="caminho.no.json" recebem o valor formatado por data-formato.

const RESULTADOS_URL = "dados/resultados.json";
let resultadosCarregados = null;

function valorEm(objeto, caminho) {
  return caminho.split(".").reduce((atual, chave) => (atual === null || atual === undefined ? undefined : atual[chave]), objeto);
}

function formatarNumero(valor, formato = "decimal3") {
  const numero = Number(valor);
  if (valor === null || valor === undefined || !Number.isFinite(numero)) return "—";
  const casas = (formato.match(/\d+$/) ?? ["0"])[0];
  if (formato.startsWith("pct")) return `${(numero * 100).toLocaleString("pt-BR", { minimumFractionDigits: Number(casas), maximumFractionDigits: Number(casas) })}%`;
  if (formato.startsWith("decimal")) return numero.toLocaleString("pt-BR", { minimumFractionDigits: Number(casas), maximumFractionDigits: Number(casas) });
  return Math.round(numero).toLocaleString("pt-BR");
}

function preencherResultados(dados, raiz = document) {
  for (const el of raiz.querySelectorAll("[data-resultado]")) {
    const valor = valorEm(dados, el.dataset.resultado);
    el.textContent = formatarNumero(valor, el.dataset.formato ?? "decimal3");
  }
}

async function carregarResultados() {
  if (resultadosCarregados) return resultadosCarregados;
  const resposta = await fetch(RESULTADOS_URL, { headers: { accept: "application/json" } });
  if (!resposta.ok) throw new Error("Resultados indisponíveis.");
  resultadosCarregados = await resposta.json();
  preencherResultados(resultadosCarregados);
  return resultadosCarregados;
}
