"""Orquestra a Etapa 2: corpus verificado → representações → análises → evidências rastreáveis.

Tudo é validado, calculado e serializado em memória antes de a pasta de saída ser criada; assim uma
falha não deixa resultado parcial. O manifesto registra hashes, versões das bibliotecas (None quando o
extra semântico não está instalado) e a identidade do código e das entradas.
"""

import platform
import time
from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from app.shared.artifacts import (
    create_output,
    json_text,
    jsonl_text,
    read_json_array,
    read_jsonl,
    sha256,
    source_identity,
    write_json,
    write_text,
)
from app.shared.manifest import MANIFEST_NAME, hash_files, read_manifest, require_plain_filename, verify_hashes
from app.vectors.analyses import DEFAULT_ANALYSES, Analysis
from app.vectors.config import ExperimentConfig, QuerySpec, RepresentationSpec, load_config, load_queries
from app.vectors.context import AnalysisContext
from app.vectors.corpus import ProcessedCorpus
from app.vectors.methods import METHODS, Method
from app.vectors.probes import ProbeSet, load_probes
from app.vectors.report import make_report
from app.vectors.space import TFIDF, Representation

LIBRARIES = ("numpy", "scipy", "scikit-learn", "torch", "transformers", "sentence-transformers")
DESCRIPTOR = RepresentationSpec("referencia_tfidf", "tfidf", "06_without_stopwords.jsonl")


def prepare(
    processed: Path, config_path: Path, queries_path: Path | None = None, methods: Mapping[str, Method] = METHODS
) -> tuple[ProcessedCorpus, ExperimentConfig, tuple[QuerySpec, ...]]:
    """Valida configuração, consultas e corpus antes de qualquer cálculo ou download de modelo."""
    config = load_config(config_path, methods)
    queries = load_queries(queries_path) if queries_path else ()
    corpus = ProcessedCorpus.load(processed)
    referenced = {*config.example_ids, *(movie_id for query in queries for movie_id in query.relevant_ids)}
    if missing := sorted(referenced - corpus.by_id.keys()):
        raise ValueError(f"IDs sem sinopse no corpus processado: {missing}")
    if config.clusters >= len(corpus.documents):
        raise ValueError(f"clusters deve ser menor que o número de sinopses ({len(corpus.documents)})")
    return corpus, config, queries


def build(
    processed: Path,
    output: Path,
    config_path: Path,
    queries_path: Path | None = None,
    probes_path: Path | None = None,
    analyses: tuple[Analysis, ...] = DEFAULT_ANALYSES,
    methods: Mapping[str, Method] = METHODS,
) -> dict:
    """Constrói todas as representações e análises da configuração numa pasta nova e verifica o resultado.

    `probes_path` aponta para as sondas linguísticas da Aula 7 (opcional). O tempo de construção de cada
    representação vai para o manifesto, e não para os arquivos de conteúdo, porque varia entre execuções.
    """
    if output.exists():
        raise FileExistsError(f"A pasta de saída já existe: {output}")
    corpus, config, queries = prepare(processed, config_path, queries_path, methods)
    probes = load_probes(probes_path) if probes_path else ProbeSet()
    context = AnalysisContext(corpus, config, TFIDF.build(DESCRIPTOR, corpus, config), queries, probes)
    representations: list[Representation] = []
    build_seconds: dict[str, float] = {}
    for spec in config.representations:
        started = time.perf_counter()
        representations.append(methods[spec.method].build(spec, corpus, config))
        build_seconds[spec.name] = round(time.perf_counter() - started, 3)
    results = {analysis.name: {rep.spec.name: analysis.run(rep, context) for rep in representations} for analysis in analyses}

    files = {
        "config.json": json_text(asdict(config)),
        "documents.json": json_text([{"id": d.id, "title": d.title, "genres": sorted(d.genres)} for d in corpus.documents]),
    }
    if queries:
        files["queries_config.json"] = json_text([asdict(query) for query in queries])
    if probes_path:
        files["probes_config.json"] = json_text(asdict(probes))
    row_files = []
    for representation in representations:
        for suffix, payload in representation.export().items():
            filename = f"{representation.spec.name}.{suffix}"
            if isinstance(payload, list):
                files[filename] = jsonl_text(payload)
                row_files.append(filename)
            else:
                files[filename] = json_text(payload)
    for analysis in analyses:
        files[f"{analysis.name}.json"] = json_text(results[analysis.name])
        for representation in representations:
            files.update(analysis.artifacts(representation, results[analysis.name][representation.spec.name], context))
    files["report.md"] = make_report(results, context, analyses)
    if unsafe := sorted(name for name in files if Path(name).name != name or name == MANIFEST_NAME):
        raise ValueError(f"Nomes de arquivo inválidos gerados pelas análises: {unsafe}")

    create_output(output)
    for filename, content in files.items():
        write_text(output / filename, content)
    manifest = {
        "schema_version": 2,
        "created_at": datetime.now(UTC).isoformat(),
        "source_processed_manifest_sha256": corpus.manifest_sha256,
        "config_sha256": sha256(config_path),
        "queries_sha256": sha256(queries_path) if queries_path else None,
        "probes_sha256": sha256(probes_path) if probes_path else None,
        "source_identity": source_identity(),
        "python": platform.python_version(),
        "libraries": _library_versions(),
        "representations": [asdict(spec) for spec in config.representations],
        "analyses": [analysis.name for analysis in analyses],
        "row_files": row_files,
        "build_seconds": build_seconds,
        "files": hash_files(output),
    }
    write_json(output / MANIFEST_NAME, manifest)
    verify(output)
    return {"documents": len(corpus.documents), "representations": [spec.name for spec in config.representations], "output": str(output)}


def verify(output: Path) -> dict:
    """Confere hashes do manifesto e o alinhamento de cada arquivo de vetores com `documents.json`."""
    manifest = read_manifest(output)
    verify_hashes(output, manifest["files"])
    ids = [document["id"] for document in read_json_array(output / "documents.json")]
    for filename in manifest["row_files"]:
        require_plain_filename(filename)
        if filename not in manifest["files"]:
            raise ValueError(f"Arquivo de vetores fora da lista verificada: {filename!r}")
        if [row["id"] for row in read_jsonl(output / filename)] != ids:
            raise ValueError(f"Vetores desalinhados dos documentos: {filename}")
    return {
        "status": "ok",
        "documents": len(ids),
        "representations": len(manifest["representations"]),
        "files_verified": len(manifest["files"]),
    }


def build_one(
    processed: Path, config_path: Path, name: str, methods: Mapping[str, Method] = METHODS
) -> tuple[ProcessedCorpus, Representation]:
    """Constrói uma única representação da configuração (usado pelo comando `query`)."""
    corpus, config, _ = prepare(processed, config_path, methods=methods)
    specs = {spec.name: spec for spec in config.representations}
    if name not in specs:
        raise ValueError(f"Representação desconhecida; use uma de {sorted(specs)}")
    return corpus, methods[specs[name].method].build(specs[name], corpus, config)


def _library_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in LIBRARIES:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    return versions
