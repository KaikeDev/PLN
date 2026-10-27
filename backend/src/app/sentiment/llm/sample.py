"""Críticas do experimento e a amostra equilibrada do sentimento com LLM.

As críticas vêm da pasta preparada (texto da etapa `02_clean`, a mesma que o BERTimbau leu) e a polaridade
vem do `documents.json` do experimento da Aula 9, que precisa listar as mesmas críticas na mesma ordem: assim
as predições gravadas do TF-IDF e do BERTimbau se referem exatamente às críticas sorteadas.

O sorteio é feito uma vez (`python -m app.sentiment llm-sample`) e gravado em
`config/sentimento/sentimento_llm_amostra.json`, que é commitado antes da primeira chamada. Para cada
polaridade, `do_autor_principal_por_polaridade` críticas são do autor que escreveu a maior parte do corpus e
o restante, dos demais. Um único gerador com a semente sorteia os estratos em ordem fixa, e as críticas saem em ordem de ID.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.corpus.verification import verify_processed
from app.representations.corpus import ProcessedCorpus
from app.sentiment.config import LABEL_NAMES
from app.sentiment.llm.prompt import SampleSettings
from app.sentiment.pipeline import verify as verify_experiment
from app.shared.artifacts import read_json_array, read_jsonl
from app.shared.language import NEGATION_MARKERS
from app.shared.validation import read_config_json, require_bool, require_object, require_unique

NEGATIVE_NAME, POSITIVE_NAME = LABEL_NAMES
CLEAN_STAGE = "02_clean.jsonl"
WORDS_STAGE = "05_without_punctuation.jsonl"


@dataclass(frozen=True)
class Review:
    """Crítica com polaridade: texto limpo, nota do autor e os dois estratos."""

    id: int
    review_id: str
    title: str
    rating: float
    polarity: str
    main_author: bool
    negation: bool
    text: str


@dataclass(frozen=True)
class Sample:
    """IDs do TMDB das críticas sorteadas e das repetidas no teste de estabilidade."""

    review_ids: tuple[str, ...]
    stability: tuple[str, ...]


def load_reviews(processed: Path, experiment: Path) -> dict[str, Review]:
    """Críticas com polaridade, indexadas pelo ID do TMDB; confere as duas pastas e o alinhamento entre elas."""
    verify_processed(processed)
    verify_experiment(experiment)
    corpus = ProcessedCorpus.load(processed)
    metadata = {row["id"]: row for row in read_jsonl(processed / "metadata.jsonl")}
    documents = read_json_array(experiment / "documents.json")
    if [metadata[number]["review_id"] for number in corpus.ids] != [document["review_id"] for document in documents]:
        raise ValueError("A pasta preparada e o experimento não têm as mesmas críticas na mesma ordem")
    authors = Counter(row["author_key"] for row in metadata.values())
    main_author = authors.most_common(1)[0][0]
    texts = dict(zip(corpus.ids, corpus.texts(CLEAN_STAGE), strict=True))
    words = dict(zip(corpus.ids, corpus.tokens(WORDS_STAGE), strict=True))
    return {
        document["review_id"]: Review(
            id=document["id"],
            review_id=document["review_id"],
            title=document["title"],
            rating=float(document["nota"]),
            polarity=document["polaridade"],
            main_author=metadata[document["id"]]["author_key"] == main_author,
            negation=any(word in NEGATION_MARKERS for word in words[document["id"]]),
            text=texts[document["id"]],
        )
        for document in documents
        if document["polaridade"] is not None
    }


def draw_sample(reviews: dict[str, Review], settings: SampleSettings) -> dict:
    """Amostra equilibrada por polaridade e por autor principal, no formato do arquivo de amostra."""
    rng = np.random.default_rng(settings.seed)
    picked: list[Review] = []
    for polarity in (NEGATIVE_NAME, POSITIVE_NAME):
        for main_author, size in (
            (True, settings.main_author_per_polarity),
            (False, settings.per_polarity - settings.main_author_per_polarity),
        ):
            stratum = sorted((r for r in reviews.values() if r.polarity == polarity and r.main_author == main_author), key=lambda r: r.id)
            if len(stratum) < size:
                raise ValueError(f"Estrato {polarity}/autor principal={main_author} tem {len(stratum)} críticas; pedidas {size}")
            picked += [stratum[index] for index in rng.choice(len(stratum), size=size, replace=False)]
    picked.sort(key=lambda review: review.id)
    stability = sorted(picked[index].review_id for index in rng.choice(len(picked), size=settings.stability, replace=False))
    return {
        "description": "Gerada por `python -m app.sentiment llm-sample` a partir de config/sentimento/sentimento_llm.json. Não editar à mão.",
        "semente": settings.seed,
        "estratos": {
            "negativo": sum(review.polarity == NEGATIVE_NAME for review in picked),
            "positivo": sum(review.polarity == POSITIVE_NAME for review in picked),
            "autor_principal": sum(review.main_author for review in picked),
            "com_negacao": sum(review.negation for review in picked),
            "cortadas": sum(len(review.text) > settings.max_chars for review in picked),
        },
        "criticas": [
            {"review_id": r.review_id, "polaridade": r.polarity, "autor_principal": r.main_author, "com_negacao": r.negation}
            for r in picked
        ],
        "estabilidade": stability,
    }


def load_sample(path: Path, reviews: dict[str, Review]) -> Sample:
    """Lê a amostra e confere que cada crítica existe e mantém a polaridade e os estratos gravados."""
    data = require_object(
        read_config_json(path), path.name, required={"semente", "estratos", "criticas", "estabilidade"}, optional={"description"}
    )
    items = data["criticas"]
    if not isinstance(items, list) or not items:
        raise ValueError(f"{path.name}: criticas deve ser uma lista não vazia")
    ids = []
    for position, value in enumerate(items):
        item = require_object(value, f"crítica {position}", required={"review_id", "polaridade", "autor_principal", "com_negacao"})
        review = reviews.get(item["review_id"])
        if review is None:
            raise ValueError(f"Crítica da amostra ausente do experimento: {item['review_id']}")
        recorded = (
            item["polaridade"],
            require_bool(item["autor_principal"], "autor_principal"),
            require_bool(item["com_negacao"], "com_negacao"),
        )
        if recorded != (review.polarity, review.main_author, review.negation):
            raise ValueError(f"Estratos da crítica {review.review_id} diferentes dos dados")
        ids.append(review.review_id)
    require_unique(ids, "Críticas repetidas na amostra")
    stability = data["estabilidade"]
    if not isinstance(stability, list) or not set(stability) <= set(ids):
        raise ValueError("estabilidade deve listar críticas da amostra")
    return Sample(tuple(ids), tuple(stability))
