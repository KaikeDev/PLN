"""Processamento offline, estatísticas e inspeção da rastreabilidade."""
import json
import platform
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.corpus.io import create_output, read_jsonl, sha256, source_identity, write_json, write_jsonl
from app.corpus.transform import PRESERVED_NEGATIONS, TOKEN_PATTERN, TOKEN_RE, representations, word_token

STAGES = {
    "01_original.jsonl": "original", "02_clean.jsonl": "clean",
    "03_normalized.jsonl": "normalized", "04_tokens.jsonl": "tokens",
    "05_without_punctuation.jsonl": "words", "06_without_stopwords.jsonl": "filtered",
}


def lexical_metrics(documents: list[list[str]]) -> dict:
    counts = Counter(token for document in documents for token in document)
    total = sum(counts.values())
    lengths = [len(document) for document in documents]
    return {
        "documents": len(documents), "tokens": total, "types": len(counts),
        "type_token_ratio": len(counts) / total if total else 0,
        "mean_tokens": statistics.mean(lengths) if lengths else 0,
        "median_tokens": statistics.median(lengths) if lengths else 0,
        "most_frequent": counts.most_common(20),
    }


def verify_raw(raw: Path) -> dict:
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    if sha256(raw / "movies.jsonl") != manifest["movies_sha256"]:
        raise ValueError("movies.jsonl diverge do hash da coleta")
    for item in manifest["requests"]:
        if item["status"] == "ok" and sha256(raw / item["file"]) != item["sha256"]:
            raise ValueError(f"Resposta original alterada: {item['file']}")
    for filename, expected in manifest.get("artifact_sha256", {}).items():
        if sha256(raw / filename) != expected:
            raise ValueError(f"Arquivo da coleta alterado: {filename}")
    return manifest


def process(raw: Path, output: Path, stopwords_path: Path) -> dict:
    collection = verify_raw(raw)
    movies = read_jsonl(raw / "movies.jsonl")
    if not movies:
        raise ValueError("A amostra não contém filmes; execute a coleta antes do processamento")
    ids = [movie["id"] for movie in movies]
    if len(set(ids)) != len(ids) or any(type(i) is not int for i in ids):
        raise ValueError("IDs devem ser inteiros únicos")
    stopwords = {
        line.strip().casefold() for line in stopwords_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    } - PRESERVED_NEGATIONS
    stage_rows = {filename: [] for filename in STAGES}
    metadata, transformed = [], {}
    for movie in movies:
        overview = movie.get("overview")
        stages = {"original": overview, **representations(overview, stopwords)}
        transformed[movie["id"]] = stages
        for filename, key in STAGES.items():
            field = "text" if key in {"original", "clean", "normalized"} else "tokens"
            stage_rows[filename].append({"id": movie["id"], field: stages[key]})
        genre_ids = movie.get("genre_ids", [g["id"] for g in movie.get("genres", [])])
        metadata.append({
            "id": movie["id"], "title": movie.get("title"), "original_title": movie.get("original_title"),
            "original_language": movie.get("original_language"), "release_date": movie.get("release_date"),
            "genre_ids": genre_ids, "vote_average": movie.get("vote_average"), "vote_count": movie.get("vote_count"),
            "overview_missing": overview is None or not overview.strip(),
        })
    create_output(output)
    for filename, rows in stage_rows.items():
        write_jsonl(output / filename, rows)
    write_jsonl(output / "metadata.jsonl", metadata)
    write_json(output / "stopwords_used.json", sorted(stopwords))
    memberships = json.loads((raw / "memberships.json").read_text(encoding="utf-8"))
    genres = json.loads((raw / "genres.json").read_text(encoding="utf-8"))
    write_json(output / "memberships.json", memberships)
    write_json(output / "genres.json", genres)
    valid = [m for m in movies if m.get("overview") and m["overview"].strip()]
    original_documents = [[t for t in TOKEN_RE.findall(m["overview"]) if word_token(t)] for m in valid]
    filtered_documents = [transformed[m["id"]]["filtered"] for m in valid]
    missing = len(movies) - len(valid)
    stats = {
        "unique_movies": len(movies), "valid_overviews": len(valid), "missing_overviews": missing,
        "missing_overviews_percent": missing / len(movies) * 100,
        "mean_characters_original": statistics.mean(len(m["overview"]) for m in valid) if valid else 0,
        "median_characters_original": statistics.median(len(m["overview"]) for m in valid) if valid else 0,
        "original": lexical_metrics(original_documents),
        "normalized_without_punctuation": lexical_metrics([transformed[m["id"]]["words"] for m in valid]),
        "filtered": lexical_metrics(filtered_documents),
        "original_languages": dict(Counter(m.get("original_language") or "unknown" for m in movies)),
        "release_decades": dict(Counter((m.get("release_date") or "unknown")[:3]+"0" if (m.get("release_date") or "")[:4].isdigit() else "unknown" for m in movies)),
        "genre_memberships": dict(Counter(str(g) for m in metadata for g in m["genre_ids"])),
        "changed_by_cleaning": sum(m.get("overview") != transformed[m["id"]]["clean"] for m in movies),
        "slices": {},
    }
    for label in sorted({label for labels in memberships.values() for label in labels}):
        members = [m for m in movies if label in memberships.get(str(m["id"]), [])]
        docs = [transformed[m["id"]]["filtered"] for m in members if m.get("overview") and m["overview"].strip()]
        stats["slices"][label] = {"movies": len(members), "valid_overviews": len(docs), "filtered": lexical_metrics(docs)}
    write_json(output / "statistics.json", stats)
    example_ids = ([603] if 603 in ids else []) + [i for i in ids if i != 603][:2]
    examples = [{"id": i, "title": next(m["title"] for m in metadata if m["id"] == i), **transformed[i]} for i in example_ids]
    write_json(output / "examples.json", examples)
    from app.corpus.bow import generate_bow_dataset
    bow_data = generate_bow_dataset(output)
    write_json(output / "07_bag_of_words.json", bow_data)
    report = make_report(stats, collection, examples)
    (output / "report.md").write_text(report, encoding="utf-8")
    manifest = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "collection_status": collection["status"], "source_movies_sha256": sha256(raw / "movies.jsonl"),
        "collection_manifest_sha256": sha256(raw / "manifest.json"), "source_identity": source_identity(),
        "python": platform.python_version(), "normalization": "NFC na limpeza; casefold na representação normalizada; acentos preservados",
        "token_pattern": TOKEN_PATTERN, "preserved_negations": sorted(PRESERVED_NEGATIONS),
        "stopwords_source_sha256": sha256(stopwords_path), "stages": STAGES,
        "files": {p.name: sha256(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    write_json(output / "manifest.json", manifest)
    verify(output)
    return {"movies": len(movies), "valid_overviews": len(valid), "missing_overviews": missing, "output": str(output)}


def verify(output: Path) -> dict:
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    for filename, expected in manifest["files"].items():
        if sha256(output / filename) != expected:
            raise ValueError(f"Hash divergente: {filename}")
    stages = [read_jsonl(output / filename) for filename in manifest["stages"]]
    ids = [r["id"] for r in stages[0]]
    if len(ids) != len(set(ids)):
        raise ValueError("IDs duplicados")
    if any([row["id"] for row in stage] != ids for stage in stages):
        raise ValueError("IDs desalinhados entre as etapas")
    if [row["id"] for row in read_jsonl(output / "metadata.jsonl")] != ids:
        raise ValueError("Metadados desalinhados")
    return {"status": "ok", "movies": len(ids), "stages": len(stages), "files_verified": len(manifest["files"])}


def make_report(stats: dict, collection: dict, examples: list[dict]) -> str:
    lines = ["# Evidências da coleta e das transformações", "", "Resultados calculados sobre a amostra real do TMDB. Nenhum filme foi descartado por falta de sinopse.", "",
        f"- Estado da coleta: **{collection['status']}**.", f"- Registros recebidos: {collection['records_received']}; filmes únicos: {stats['unique_movies']}; duplicatas removidas: {collection['duplicates_removed']}.",
        f"- Sinopses válidas: {stats['valid_overviews']}; ausentes: {stats['missing_overviews']} ({stats['missing_overviews_percent']:.2f}%).",
        f"- Extensão média original: {stats['mean_characters_original']:.2f} caracteres; mediana: {stats['median_characters_original']:.2f}.",
        f"- Textos alterados na limpeza: {stats['changed_by_cleaning']}.", "", "## Comparação das representações", "",
        "Cálculos lexicais sobre as mesmas sinopses preenchidas. Tokens de pontuação não entram nesta tabela. TTR = tipos distintos / tokens. O original preserva maiúsculas; a normalização altera essa contagem.", "",
        "| Representação | Tokens | Tipos | TTR | Média por sinopse | Mediana |", "|---|---:|---:|---:|---:|---:|"]
    for key, label in [("original", "Original"), ("normalized_without_punctuation", "Normalizada sem pontuação"), ("filtered", "Sem stopwords")]:
        row = stats[key]
        lines.append(f"| {label} | {row['tokens']} | {row['types']} | {row['type_token_ratio']:.4f} | {row['mean_tokens']:.2f} | {row['median_tokens']:.2f} |")
    lines += ["", "## Recortes da amostra", "", "Grupos podem se sobrepor: um mesmo filme pode ter sido retornado por vários gêneros. A soma dos grupos não é o total de filmes únicos. Matrix foi incluído adicionalmente como caso didático solicitado pelo professor.", "",
        "| Recorte de coleta | Filmes | Sinopses válidas | Tokens filtrados | Tipos |", "|---|---:|---:|---:|---:|"]
    for label, value in stats["slices"].items():
        lines.append(f"| {label} | {value['movies']} | {value['valid_overviews']} | {value['filtered']['tokens']} | {value['filtered']['types']} |")
    lines += ["", "## Exemplos rastreáveis", "", "As seis representações mantêm o mesmo ID. A versão filtrada é uma alternativa experimental; não é considerada superior antes da avaliação de recuperação.", ""]
    for item in examples:
        lines += [f"### Filme {item['id']}", "", "```json", json.dumps(item, ensure_ascii=False, indent=2), "```", ""]
    lines += ["## Limitações", "", "A coleta é intencional, usa ranking de popularidade e mínimo de votos; não representa todo o catálogo. O parâmetro pt-BR solicita a tradução, mas não comprova automaticamente o idioma de cada sinopse. original_language descreve a obra. Não foram medidas proporções de nomes próprios nem desempenho de recomendação. Vetorização, stemming e lematização permanecem para experiências posteriores.", "",
        "Os arquivos originais, configurações, hashes e manifestos permitem repetir as transformações offline. Repetir a coleta online pode produzir outra amostra, pois o TMDB é atualizado.", "",
        "## Fonte", "", "Dados: The Movie Database (TMDB), https://www.themoviedb.org/. Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB. As condições da fonte se aplicam aos dados; as métricas e transformações são da equipe.", ""]
    return "\n".join(lines)
