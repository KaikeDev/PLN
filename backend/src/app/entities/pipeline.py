"""Orquestra NER e relações nas sinopses: corpus verificado → spaCy → entidades, triplas, conferência → evidências.

Segue as regras das outras etapas (ADR 0009): tudo é calculado em memória antes de criar a pasta de saída, que
nunca é sobrescrita, e o manifesto guarda hashes, versões e tempos. Com o mesmo modelo e a mesma versão do spaCy,
os arquivos de conteúdo são idênticos byte a byte.
"""

import platform
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np

from app.entities.credits import verify_credits
from app.entities.evaluation import check_film, name_words, summarize
from app.entities.extraction import dependencies, entities, is_pronoun, load_model, relations
from app.entities.report import make_report
from app.representations.corpus import ProcessedCorpus
from app.shared.artifacts import create_output, json_text, jsonl_text, read_jsonl, sha256, source_identity, write_json, write_text
from app.shared.manifest import MANIFEST_NAME, hash_files, read_manifest, verify_hashes
from app.shared.validation import read_config_json, require_bool, require_ids, require_int, require_object

ALIGNED = ("entities.jsonl", "relations.jsonl", "credits_check.jsonl")
LIBRARIES = ("spacy", "pt-core-news-sm")


@dataclass(frozen=True)
class EntitiesConfig:
    """Modelo spaCy, etapa de texto, regra de coordenação, filmes de exemplo e tamanho da amostra para conferência manual."""

    model: str
    stage: str
    coordination: bool
    example_ids: tuple[int, ...]
    review_sample: int
    random_state: int
    top: int


def load_config(path: Path) -> EntitiesConfig:
    """Lê e valida a configuração de NER e relações."""
    data = require_object(
        read_config_json(path),
        "configuração de entidades",
        required={"model", "stage", "coordination", "example_ids", "review_sample", "random_state", "top"},
        optional={"description"},
    )
    if data["model"] != "pt_core_news_sm":
        raise ValueError("model deve ser pt_core_news_sm, o modelo da Aula 9 instalado pelo extra entidades")
    if data["stage"] != "02_clean.jsonl":
        raise ValueError("stage deve ser 02_clean.jsonl: o spaCy precisa do texto com maiúsculas e pontuação")
    return EntitiesConfig(
        model=data["model"],
        stage=data["stage"],
        coordination=require_bool(data["coordination"], "coordination"),
        example_ids=require_ids(data["example_ids"], "example_ids"),
        review_sample=require_int(data["review_sample"], "review_sample", 0, 500),
        random_state=require_int(data["random_state"], "random_state", 0, 2**32 - 1),
        top=require_int(data["top"], "top", 1, 50),
    )


def build(processed: Path, credits: Path, output: Path, config_path: Path) -> dict:
    """Entidades e relações de todas as sinopses, conferência com os créditos e relatório, numa pasta nova."""
    if output.exists():
        raise FileExistsError(f"A pasta de saída já existe: {output}")
    config = load_config(config_path)
    corpus = ProcessedCorpus.load(processed)
    verify_credits(credits)
    cast = {row["movie_id"]: row["cast"] for row in read_jsonl(credits / "credits.jsonl")}
    texts = corpus.texts(config.stage)
    nlp = load_model(config.model)
    started = time.perf_counter()
    docs = list(nlp.pipe(texts))
    seconds = round(time.perf_counter() - started, 3)

    entity_rows: list[dict] = []
    relation_rows: list[dict] = []
    check_rows: list[dict] = []
    examples: list[dict] = []
    all_triples = []
    sentences = sentences_with_triple = 0
    for document, doc in zip(corpus.documents, docs, strict=True):
        found = entities(doc)
        triples = relations(doc, coordination=config.coordination)
        sentence_texts = [sentence.text for sentence in doc.sents]
        sentences += len(sentence_texts)
        sentences_with_triple += len({triple.sentence for triple in triples})
        entity_rows.append({"id": document.id, "title": document.title, "entidades": found})
        relation_rows.append({"id": document.id, "title": document.title, "triplas": [asdict(triple) for triple in triples]})
        check_rows.append({"id": document.id, "title": document.title, **check_film(doc, name_words(cast.get(document.id, [])))})
        all_triples += [(document, triple, sentence_texts[triple.sentence - 1]) for triple in triples]
        if document.id in config.example_ids:
            first = next(iter(doc.sents))
            examples.append(
                {
                    "id": document.id,
                    "title": document.title,
                    "texto": doc.text,
                    "dependencias_primeira_sentenca": dependencies(first),
                    "entidades": found,
                    "triplas": [asdict(triple) for triple in triples],
                }
            )

    labels = Counter(entity["categoria"] for row in entity_rows for entity in row["entidades"])
    by_label: dict[str, Counter] = {}
    for row in entity_rows:
        for entity in row["entidades"]:
            by_label.setdefault(entity["categoria"], Counter())[entity["entidade"]] += 1
    rules = Counter(triple.rule for _, triple, _ in all_triples)
    statistics = {
        "sinopses": len(docs),
        "sentencas": sentences,
        "sentencas_com_tripla": sentences_with_triple,
        "entidades": sum(labels.values()),
        "entidades_por_categoria": dict(sorted(labels.items())),
        "entidades_mais_frequentes": {label: counter.most_common(config.top) for label, counter in sorted(by_label.items())},
        "triplas": len(all_triples),
        "triplas_por_regra": dict(sorted(rules.items())),
        "triplas_regras_do_notebook": len(all_triples) - rules.get("coordenacao", 0),
        "relacoes_mais_frequentes": Counter(triple.relation for _, triple, _ in all_triples).most_common(config.top),
        "triplas_com_duas_entidades": sum(t.subject_is_entity and t.object_is_entity for _, t, _ in all_triples),
        "sujeitos_pronomes": sum(is_pronoun(t.subject) for _, t, _ in all_triples),
        "segundos_spacy": seconds,
    }
    credits_summary = summarize(check_rows)
    rng = np.random.default_rng(config.random_state)
    chosen = sorted(rng.choice(len(all_triples), size=min(config.review_sample, len(all_triples)), replace=False).tolist())
    review = [
        {
            "id": all_triples[i][0].id,
            "title": all_triples[i][0].title,
            "sentenca": all_triples[i][2],
            **asdict(all_triples[i][1]),
            "correta": None,
        }
        for i in chosen
    ]
    files = {
        "config.json": json_text(asdict(config)),
        "entities.jsonl": jsonl_text(entity_rows),
        "relations.jsonl": jsonl_text(relation_rows),
        "credits_check.jsonl": jsonl_text(check_rows),
        "statistics.json": json_text(statistics),
        "credits_summary.json": json_text(credits_summary),
        "examples.json": json_text(examples),
        "review_sample.json": json_text(review),
    }
    files["report.md"] = make_report(statistics, credits_summary, check_rows, examples, config)

    create_output(output)
    for filename, content in files.items():
        write_text(output / filename, content)
    write_json(
        output / MANIFEST_NAME,
        {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "source_processed_manifest_sha256": corpus.manifest_sha256,
            "source_credits_manifest_sha256": sha256(credits / "manifest.json"),
            "config_sha256": sha256(config_path),
            "model": config.model,
            "source_identity": source_identity(),
            "python": platform.python_version(),
            "libraries": _library_versions(),
            "seconds": seconds,
            "files": hash_files(output),
        },
    )
    verify(output)
    return {"synopses": len(docs), "entities": statistics["entidades"], "triples": statistics["triplas"], "output": str(output)}


def verify(output: Path) -> dict:
    """Confere os hashes do manifesto e se entidades, relações e conferência cobrem as mesmas sinopses, na mesma ordem."""
    manifest = read_manifest(output)
    verify_hashes(output, manifest["files"])
    orders = []
    for filename in ALIGNED:
        if filename not in manifest["files"]:
            raise ValueError(f"Arquivo fora da lista verificada: {filename}")
        orders.append([row["id"] for row in read_jsonl(output / filename)])
    if any(order != orders[0] for order in orders):
        raise ValueError("Entidades, relações e conferência desalinhadas")
    return {"status": "ok", "synopses": len(orders[0]), "files_verified": len(manifest["files"])}


def _library_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in LIBRARIES:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    return versions
