"""Reúne os números que a página "Sobre o projeto" mostra, lidos dos arquivos entregues em `data/` e `config/`.

Rode na raiz do repositório ou em `backend` (só usa a biblioteca padrão):

    python docs/entregas/unidade-4/coletar_resultados.py

Grava `frontend/dados/resultados.json`. Nenhum número da página é digitado à mão no HTML: o `script.js` lê este
arquivo, e `backend/tests/test_resultados.py` confere que ele bate com as fontes (ADR 0034). Fontes opcionais, como
o catálogo do site (fora do Git) e a avaliação do RAG, viram `null` quando a pasta não existe; nesse caso o valor
anterior do JSON é mantido, para que gerar o arquivo numa máquina sem o catálogo não apague o número.
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data"
CONFIG = REPO / "config"
OUTPUT = REPO / "frontend" / "dados" / "resultados.json"

SAMPLE = "tmdb_2026-09-12"
CATALOG = DATA / "preparacao" / "site_2026-10-05" / "statistics.json"
REVIEWS = DATA / "sentimento" / "criticas_2026-10-10"
INTERPRETATION = DATA / "interpretacao" / "frases_2026-10-26"
SENTIMENT_LLM = DATA / "sentimento" / "llm_2026-11-01"
RAG = DATA / "rag" / "2026-11-01"
RAG_JUDGMENTS = CONFIG / "rag" / "julgamentos.json"

REPRESENTATIONS = (
    "bow_sem_pontuacao",
    "bow_sem_stopwords",
    "tfidf_sem_pontuacao",
    "tfidf_sem_stopwords",
    "word2vec_cbow",
    "word2vec_skipgram",
    "bert_base_pt",
    "sentenca_minilm",
)
INTERPRETATION_EXAMPLES = ("par_me_faca_rir", "neg_menos_terror")
# posição do exemplo em cada lista de discordância de `metrics.json`, escolhida para a página
SENTIMENT_EXAMPLES = (("so_o_llm_acerta", 5), ("so_os_modelos_treinados_acertam", 1))
SENTIMENT_SYSTEMS = {
    "tfidf": "TF-IDF (Aula 9)",
    "bertimbau": "BERTimbau (Aula 9)",
    "zero_shot": "LLM zero-shot",
    "few_shot": "LLM few-shot",
    "zero_shot_sem_justificativa": "LLM zero-shot sem justificativa",
    "reserva": "LLM reserva (Groq)",
}
EXCERPT_CHARS = 280
LIBRARIES = ("fastapi", "uvicorn", "pydantic", "requests", "numpy", "scikit-learn", "torch", "transformers", "sentence-transformers", "spacy", "pt-core-news-sm")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def r(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(float(value), digits)


def short(text: str) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= EXCERPT_CHARS else text[: EXCERPT_CHARS - 1].rstrip() + "…"


def data() -> dict:
    statistics = read(DATA / "preparacao" / SAMPLE / "statistics.json")
    reviews = read(REVIEWS / "dataset.json")
    catalog = read(CATALOG)["valid_overviews"] if CATALOG.exists() else None
    return {
        "filmes_coletados": statistics["unique_movies"],
        "sinopses": statistics["valid_overviews"],
        "catalogo_do_site": catalog,
        "criticas": reviews["reviews"],
        "filmes_com_critica": reviews["movies"],
        "autores": reviews["authors"],
        "participacao_do_autor_principal": reviews["main_author_share"],
    }


def tasks_by_representation() -> dict:
    vectors = DATA / "representacoes" / SAMPLE
    retrieval = read(vectors / "retrieval.json")
    recommendation = read(vectors / "recommendation.json")
    clustering = read(vectors / "clustering.json")
    classification = read(DATA / "classificacao" / SAMPLE / "results.json")["multiclasse"]
    rows = [
        {
            "representacao": name,
            "busca_map": r(retrieval[name]["mean_average_precision"]),
            "recomendacao_precisao_5": r(recommendation[name]["precision_at_k"]),
            "agrupamento_ari": r(clustering[name]["adjusted_rand_index"]),
            "classificacao_f1": r(classification[name]["f1_macro"]),
        }
        for name in REPRESENTATIONS
    ]
    return {
        "referencia": {
            "recomendacao_precisao_5": r(recommendation[REPRESENTATIONS[0]]["baseline"]),
            "agrupamento_ari": 0,
            "classificacao_f1": r(classification["maioria"]["f1_macro"]),
        },
        "linhas": rows,
    }


def earlier_results() -> dict:
    effect = read(INTERPRETATION / "search_effect.json")["metricas"]
    sentiment = read(REVIEWS / "results.json")
    jev = read(DATA / "jev" / SAMPLE / "metrics.json")["methods"]["jev"]["choice"]
    classification = read(DATA / "classificacao" / SAMPLE / "results.json")["multiclasse"]
    credits = read(DATA / "entidades" / SAMPLE / "credits_summary.json")
    reviews = read(REVIEWS / "dataset.json")
    entities = read(DATA / "entidades" / SAMPLE / "statistics.json")
    return {
        "busca": {"map": r(effect["frase"]["map"]), "mrr": r(effect["frase"]["mrr"]), "precisao_5": r(effect["frase"]["precisao_at_k"])},
        "classificacao": {
            "melhor": "word2vec_skipgram",
            "melhor_f1": r(classification["word2vec_skipgram"]["f1_macro"]),
            "tela_f1": r(classification["sentenca_minilm"]["f1_macro"]),
            "jev_acuracia": r(jev["accuracy"]),
            "jev_filmes": read(DATA / "jev" / SAMPLE / "metrics.json")["evaluated"],
        },
        "sentimento": {
            "tfidf_f1": r(sentiment["polaridade"]["tfidf_sem_stopwords"]["f1_macro"]),
            "tfidf_acuracia": r(sentiment["polaridade"]["tfidf_sem_stopwords"]["acuracia"]),
            "bertimbau_f1": r(sentiment["polaridade"]["bert_base_pt"]["f1_macro"]),
            "tfidf_erro_nota": r(sentiment["nota"]["tfidf_sem_stopwords"]["erro_absoluto_medio"]),
            "bertimbau_erro_nota": r(sentiment["nota"]["bert_base_pt"]["erro_absoluto_medio"]),
            "media_erro_nota": r(sentiment["nota"]["media_do_treino"]["erro_absoluto_medio"]),
            "participacao_positivas": r(reviews["polarity"]["positivo"] / (reviews["polarity"]["positivo"] + reviews["polarity"]["negativo"])),
        },
        "entidades": {
            "revocacao_pessoas": r(credits["revocacao_per"]),
            "triplas": entities["triplas"],
            "sujeito_pronome": r(entities["sujeitos_pronomes"] / entities["triplas"]),
            "sinopses": entities["sinopses"],
        },
    }


def interpretation() -> dict:
    metrics = read(INTERPRETATION / "metrics.json")
    effect = read(INTERPRETATION / "search_effect.json")["metricas"]
    total = metrics["avaliacao"]["total"]
    systems = metrics["avaliacao"]["sistemas"]
    predictions = {row["id"]: row for row in lines(INTERPRETATION / "predictions.jsonl")}
    return {
        "frases": total["regras"]["frases"],
        "sistemas": {
            name: {key: total[name][key] for key in ("acerto_exato", "f1_generos", "acerto_periodo", "filtro_inventado", "falhas")}
            for name in systems
        },
        "por_categoria": {
            category: {name: values[name]["acerto_exato"] for name in systems} for category, values in metrics["avaliacao"]["por_categoria"].items()
        },
        "busca_map": {
            "sem_filtros": r(effect["frase"]["map"]),
            "filtros_das_regras": r(effect["frase_com_filtros_das_regras"]["map"]),
            "filtros_do_llm": r(effect["frase_com_filtros_do_llm"]["map"]),
        },
        "tokens_entrada_medio": {name: metrics["uso"][name]["tokens_entrada_medio"] for name in ("zero_shot", "few_shot")},
        "exemplos": [
            {
                "frase": predictions[key]["texto"],
                "esperado": predictions[key]["esperado"],
                "regras": predictions[key]["regras"]["filtros"],
                "llm": predictions[key]["few_shot"]["filtros"],
            }
            for key in INTERPRETATION_EXAMPLES
        ],
    }


def sentiment_llm() -> dict | None:
    if not SENTIMENT_LLM.exists():
        return None
    metrics = read(SENTIMENT_LLM / "metrics.json")
    evaluation = metrics["avaliacao"]
    rows = []
    for key, label in SENTIMENT_SYSTEMS.items():
        polarity = evaluation["polaridade"][key]
        rating = evaluation["nota"][key]
        rows.append(
            {
                "sistema": key,
                "nome": label,
                "f1_macro": polarity["f1_macro"],
                "acuracia": polarity["acuracia"],
                "respondidas": polarity.get("respondidas", evaluation["criticas"]),
                "erro_nota": rating["erro_absoluto_medio"],
            }
        )

    agreement = metrics["concordancia"]
    variant = agreement["variante"]
    predictions = {row["review_id"]: row for row in lines(SENTIMENT_LLM / "predictions.jsonl")}
    chosen = [agreement[key][position] for key, position in SENTIMENT_EXAMPLES if len(agreement[key]) > position]
    texts = {row["review_id"]: row["content"] for row in lines(DATA / "coleta" / "criticas_2026-10-10" / "reviews.jsonl") if row["review_id"] in chosen}

    def example(review_id: str) -> dict:
        row = predictions[review_id]
        return {
            "filme": row["titulo"],
            "nota_do_autor": row["nota_real"],
            "trecho": short(texts[review_id]),
            "llm": {key: row[variant][key] for key in ("polaridade", "nota", "justificativa")},
            "tfidf": {key: row["tfidf"][key] for key in ("polaridade", "nota")},
            "bertimbau": {key: row["bertimbau"][key] for key in ("polaridade", "nota")},
        }

    return {
        "criticas": evaluation["criticas"],
        "media_erro_nota": evaluation["nota"]["media_fora_da_amostra"]["erro_absoluto_medio"],
        "sistemas": rows,
        "por_estrato": {
            stratum: {key: values[key]["f1_macro"] for key in SENTIMENT_SYSTEMS if key in values}
            for stratum, values in evaluation["por_estrato"].items()
        },
        "variante_do_site": variant,
        "so_o_llm_acerta": len(agreement["so_o_llm_acerta"]),
        "so_os_modelos_acertam": len(agreement["so_os_modelos_treinados_acertam"]),
        "exemplos": [example(review_id) for review_id in chosen],
        "estabilidade": metrics["estabilidade"],
        "uso": {key: {k: v for k, v in value.items() if k != "falhas_por_motivo"} for key, value in metrics["uso"].items()},
    }


def rag() -> dict | None:
    if not (RAG / "metrics.json").exists():
        return None
    metrics = read(RAG / "metrics.json")
    ranking = metrics["ordenacao"]
    predictions = {row["id"]: row for row in lines(RAG / "predictions.jsonl")}
    judgments = read(RAG_JUDGMENTS) if RAG_JUDGMENTS.exists() else None
    examples = []
    for key in ("tema_luto", "sem_curling"):
        row = predictions.get(key)
        if row and not row["falha"]:
            examples.append({"pergunta": row["pergunta"], "resposta": short(row["resposta"]), "citados": [item["titulo"] for item in row["citados"]]})
    return {
        "busca_precisao_5": ranking["busca_hibrida_sozinha"]["precisao_at_5"],
        "contextos": [
            {
                "filmes": int(key[2:]),
                "precisao_dos_citados": item["precisao_dos_citados"],
                "revocacao_no_contexto": item["revocacao_no_contexto"],
                "citados_por_resposta": item["citados_por_resposta"],
                "tokens_entrada_medio": item["tokens_entrada_medio"],
                "falhas": item["falhas"],
            }
            for key, item in ranking.items()
            if key.startswith("k_")
        ],
        "perguntas": metrics["perguntas"],
        "sem_criticas": metrics["sem_criticas"],
        "uso": {key: value for key, value in metrics["uso"].items() if key != "falhas_por_motivo"},
        "exemplos": examples,
        "julgamentos": judgments.get("concordancia") if isinstance(judgments, dict) else None,
    }


def llm() -> dict:
    config = read(CONFIG / "llm" / "llm.json")
    return {
        "provedores": [{"nome": item["name"], "modelo": item["model"]} for item in config["providers"]],
        "temperatura": config["temperature"],
        "maximo_de_tokens": config["max_output_tokens"],
        "orcamento_diario": config["daily_budget"],
    }


def technologies() -> dict:
    vectors = read(CONFIG / "representacoes" / "vetorizacao_semantica.json")["representations"]
    lock = (REPO / "backend" / "uv.lock").read_text(encoding="utf-8")
    versions: dict[str, str] = {}
    for name, version in re.findall(r'^name = "([^"]+)"\nversion = "([^"+]+)', lock, re.MULTILINE):
        versions.setdefault(name, version)
    python = re.search(r'^requires-python = "([^"]+)"', (REPO / "backend" / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)
    return {
        "modelos": [{"representacao": item["name"], "modelo": item["model"], "revisao": item["revision"]} for item in vectors if "model" in item],
        "bibliotecas": {name: versions.get(name) for name in LIBRARIES},
        "python": python.group(1) if python else None,
    }


def board() -> list[dict]:
    """Quadro do item 1, copiado da tabela de `docs/9-tecnicas-avancadas.md` para a página mostrar o mesmo texto."""
    text = (REPO / "docs" / "9-tecnicas-avancadas.md").read_text(encoding="utf-8")
    section = text.split("## Quadro de técnicas", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.split("\n") if line.startswith("|")][2:]
    cells = [[cell.strip().replace("**", "") for cell in row.strip().strip("|").split("|")] for row in rows]
    return [{"tecnologia": first, "utilizada": second, "justificativa": third} for first, second, third in cells]


def project() -> dict:
    tests = sum(len(re.findall(r"^\s*def test_", path.read_text(encoding="utf-8"), re.MULTILINE)) for path in (REPO / "backend" / "tests").glob("test_*.py"))
    adrs = sum(1 for path in (REPO / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md"))
    return {"testes": tests, "adrs": adrs}


def collect(previous: dict | None = None) -> dict:
    previous = previous or {}
    result = {
        "dados": data(),
        "tarefas_representacoes": tasks_by_representation(),
        "unidades_anteriores": earlier_results(),
        "quadro": board(),
        "unidade_4": {"interpretacao": interpretation(), "sentimento": sentiment_llm(), "rag": rag()},
        "llm": llm(),
        "tecnologias": technologies(),
        "projeto": project(),
    }
    if result["dados"]["catalogo_do_site"] is None:
        result["dados"]["catalogo_do_site"] = previous.get("dados", {}).get("catalogo_do_site")
    return result


def main() -> None:
    previous = read(OUTPUT) if OUTPUT.exists() else None
    result = collect(previous)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{OUTPUT.relative_to(REPO)}: catálogo {result['dados']['catalogo_do_site']}, sentimento {'ok' if result['unidade_4']['sentimento'] else 'pendente'}, rag {'ok' if result['unidade_4']['rag'] else 'pendente'}")


if __name__ == "__main__":
    main()
