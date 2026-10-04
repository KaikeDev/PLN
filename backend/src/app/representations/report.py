"""Relatório Markdown gerado somente a partir dos resultados calculados.

Cada análise escreve a própria seção por meio de `Analysis.report_section`, que delega às funções
de apresentação deste módulo. `make_report` só adiciona introdução, limitações e fonte; incluir uma
nova análise não exige alterar este arquivo.
"""

from collections.abc import Sequence
from typing import Protocol

from app.representations.context import AnalysisContext


class ReportedAnalysis(Protocol):
    """O que o relatório precisa de uma análise."""

    name: str

    def report_section(self, results: dict, context: AnalysisContext) -> list[str]: ...


def make_report(results: dict, context: AnalysisContext, analyses: Sequence[ReportedAnalysis]) -> str:
    """Relatório completo: introdução, uma seção por análise executada, limitações e fonte."""
    lines = [
        "# Evidências das representações vetoriais",
        "",
        f"Representações calculadas sobre {len(context.corpus.documents)} sinopses preenchidas de uma pasta processada com hashes verificados. "
        "As seções seguem as tarefas do ciclo de PLN aplicadas a cada representação: busca, recomendação, agrupamento e visualização; "
        "a classificação é a Etapa 3. Os rótulos de gênero são os `genre_ids` do TMDB restritos aos gêneros da coleta "
        f"({', '.join(context.corpus.genre_labels(context.corpus.collection_genres))}): "
        "servem de aproximação de relevância, não de julgamento humano.",
        "",
    ]
    for analysis in analyses:
        if analysis.name in results:
            lines += analysis.report_section(results[analysis.name], context)
    lines += [
        "## Limitações",
        "",
        "BoW e TF-IDF só comparam termos idênticos após a preparação. Word2vec aproxima palavras usadas em contextos parecidos, mas tem um vetor por palavra "
        "(não distingue sentidos) e a média apaga ordem e negação. Transformers dependem do texto usado no treino do modelo; o BERT pré-treinado só com "
        "modelagem de linguagem mascarada não foi ajustado para comparar sentenças, e o modelo de sentença trunca sinopses longas. "
        "As sondas linguísticas são poucas frases escritas pela equipe: ilustram os conceitos da aula, não medem desempenho. "
        "A precisão da recomendação e as métricas de agrupamento usam os gêneros como aproximação de relevância: dois filmes do mesmo gênero "
        "não são necessariamente boas recomendações um para o outro, e filmes com vários gêneros são ambíguos. "
        "As consultas anotadas são poucas e a lista de relevantes é parcial, portanto servem como casos didáticos, não como avaliação estatística.",
        "",
        "## Fonte",
        "",
        "Dados: The Movie Database (TMDB), https://www.themoviedb.org/. Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB.",
        "Modelos pré-treinados: conforme `model` e `revision` em `config.json`; word2vec do NILC (Hartmann et al., 2017).",
        "",
    ]
    return "\n".join(lines)


def dimensions_section(results: dict, context: AnalysisContext) -> list[str]:
    names = context.representation_names
    lines = [
        "## Representações e dimensões",
        "",
        "| Representação | Método | Entrada | Dimensões | Tipo | Densidade | Não nulos por sinopse |",
        "|---|---|---|---:|---|---:|---:|",
    ]
    for name in names:
        row = results[name]
        kind = "esparsa" if row["sparse"] else "densa"
        lines.append(
            f"| {name} | {row['method']} | {row['stage']} | {row['dimensions']} | {kind} | {row['density']:.4%} | {row['mean_nonzero_per_document']:.2f} |"
        )
    lines.append("")
    for name in names:
        row = results[name]
        if "top_terms" in row:
            lines.append(f"- **{name}**, termos de maior peso somado: {', '.join(term for term, _ in row['top_terms'])}")
        if "token_coverage" in row:
            lines.append(
                f"- **{name}**: {row['token_coverage']:.2%} dos tokens existem no modelo; {row['corpus_words_in_model']} palavras distintas do corpus têm vetor; "
                f"{row['documents_without_known_words']} sinopses sem nenhuma palavra conhecida."
            )
        if "truncated_documents" in row and row["max_tokens"]:
            lines.append(
                f"- **{name}**: limite de {row['max_tokens']} tokens do modelo; {row['truncated_documents']} sinopses foram truncadas."
            )
    return [*lines, ""]


def word_neighbors_section(results: dict, context: AnalysisContext) -> list[str]:
    names = context.representation_names
    supported = [name for name in names if results[name]["supported"]]
    if not supported or not (context.config.probe_words or context.probes.word_pairs):
        return []
    lines = [
        "## Hipótese distribucional: palavras vizinhas (word2vec)",
        "",
        "“Conheceremos uma palavra pela companhia que ela mantém” (Firth). O word2vec aprende um vetor por palavra prevendo contextos: "
        "o CBOW prevê a palavra central a partir das vizinhas; o skip-gram prevê as vizinhas a partir da palavra central. "
        "Palavras usadas em contextos parecidos terminam com direções próximas, o que indica uso semelhante, não sinonímia garantida.",
        "",
    ]
    pairs = context.probes.word_pairs
    if pairs:
        lines += [
            "| Par de palavras | " + " | ".join(supported) + " |",
            "|---|" + "---:|" * len(supported),
        ]
        for index, (left, right) in enumerate(pairs):
            scores = [number(results[name]["pairs"][index][2], 3, "fora do vocabulário") for name in supported]
            lines.append(f"| {left} × {right} | " + " | ".join(scores) + " |")
        lines.append("")
    for name in supported:
        if not results[name]["words"]:
            continue
        lines += [f"### {name}: palavras do corpus mais próximas", ""]
        for word, neighbors in results[name]["words"].items():
            described = (
                ", ".join(f"{neighbor} ({score:.2f})" for neighbor, score in neighbors)
                if neighbors is not None
                else "fora do vocabulário do modelo"
            )
            lines.append(f"- **{word}**: {described}")
        lines.append("")
    return lines


def sentence_pairs_section(results: dict, context: AnalysisContext) -> list[str]:
    pairs = context.probes.sentence_pairs
    if not pairs:
        return []
    names = context.representation_names
    lines = [
        "## Similaridade lexical não é similaridade semântica",
        "",
        "Pares de frases da aula, fora do corpus. Cada frase passa pelas mesmas regras de preparação da entrada de cada representação. "
        "Nas lexicais, só palavras presentes no vocabulário das sinopses contam; termos ausentes zeram a contribuição. "
        "Compare cada coluna consigo mesma: um BERT pré-treinado sem ajuste para sentenças tende a dar cossenos altos a quase qualquer par "
        "(anisotropia), então importa a diferença entre pares próximos e distantes, não o valor absoluto.",
        "",
        "| Par | Esperado | " + " | ".join(names) + " |",
        "|---|---|" + "---:|" * len(names),
    ]
    for index, pair in enumerate(pairs):
        cells = []
        for name in names:
            item = results[name]["pairs"][index]
            cells.append("vetor nulo" if item["null_vector"] else f"{item['cosine']:.3f}")
        lines.append(f"| {pair.id} | {pair.expected} | " + " | ".join(cells) + " |")
    lines.append("")
    for index, pair in enumerate(pairs):
        lines += [f"### {pair.id}", "", f"- A: “{pair.left}”", f"- B: “{pair.right}”"]
        if pair.note:
            lines.append(f"- {pair.note}")
        for name in names:
            item = results[name]["pairs"][index]
            if item["explanation"]:
                lines.append(f"- **{name}** aproxima por: {', '.join(item['explanation'])}")
        lines.append("")
    return lines


def word_senses_section(results: dict, context: AnalysisContext) -> list[str]:
    senses = context.probes.word_senses
    supported = [name for name in context.representation_names if results[name]["supported"]]
    if not senses or not supported:
        return []
    lines = [
        "## Polissemia: embeddings estáticos × contextuais",
        "",
        "Vetor da mesma palavra em frases com sentidos iguais e diferentes. No word2vec o vetor é único por palavra, "
        "então os cossenos são sempre 1 e a diferença é zero. Nos transformers o vetor da palavra depende da frase: "
        "espera-se cosseno maior entre usos com o mesmo sentido. BoW e TF-IDF também não distinguem sentidos: a palavra é sempre a mesma coluna.",
        "",
    ]
    for index, item in enumerate(senses):
        lines += [
            f"### “{item.word}”",
            "",
            *[f"{position + 1}. ({entry.sense}) {entry.text}" for position, entry in enumerate(item.contexts)],
            "",
            "| Representação | Família | Mesmo sentido | Sentidos diferentes | Diferença |",
            "|---|---|---:|---:|---:|",
        ]
        for name in supported:
            row = results[name]["words"][index]
            if not row["found"]:
                lines.append(f"| {name} | {results[name]['family']} | palavra fora do vocabulário | — | — |")
                continue
            lines.append(
                f"| {name} | {results[name]['family']} | {number(row['same_sense_mean'], 3)} | "
                f"{number(row['different_sense_mean'], 3)} | {number(row['gap'], 3)} |"
            )
        lines.append("")
    return lines


FAMILY_LABELS = {"lexical": "lexical (contagem)", "static": "estática (word2vec)", "contextual": "contextual (transformer)"}


def synthesis_section(results: dict, context: AnalysisContext) -> list[str]:
    names = context.representation_names
    lines = [
        "## Síntese comparativa",
        "",
        "Propriedades medidas nesta execução, no formato da síntese da aula. Parâmetros aprendidos indicam o custo de memória do modelo; "
        "o tempo de construção de cada representação fica em `manifest.json` (`build_seconds`), porque varia entre máquinas.",
        "",
        "| Representação | Família | Esparsa | Dimensões | Dimensão = vocabulário | Aprendida | Palavra depende do contexto | Interpretável por palavras | Parâmetros |",
        "|---|---|---|---:|---|---|---|---|---:|",
    ]
    for name in names:
        row = results[name]
        parameters = f"{row['parameters'] / 1e6:.1f} mi" if row["parameters"] else "—"
        lines.append(
            f"| {name} | {FAMILY_LABELS.get(row['family'], row['family'])} | {_yes(row['sparse'])} | {row['dimensions']} | "
            f"{_yes(row['dimensions_are_vocabulary'])} | {_yes(row['learned'])} | {_yes(row['word_depends_on_context'])} | "
            f"{_yes(row['interpretable_by_words'])} | {parameters} |"
        )
    lines += [
        "",
        "A proximidade vetorial passa a refletir melhor a proximidade semântica quando a representação incorpora distribuição, contexto e "
        "treinamento em larga escala; em troca, o custo aumenta e a interpretação direta por palavras diminui. As técnicas coexistem: "
        "a escolha depende da tarefa, e as consultas anotadas deste projeto ainda são poucas para decidir.",
        "",
    ]
    return lines


def _yes(value: bool) -> str:
    return "sim" if value else "não"


def titled(item: dict) -> str:
    explanation = f": {', '.join(item['explanation'])}" if item["explanation"] else ""
    return f"{item['title']} ({item['score']:.3f}{explanation})"


def number(value: float | None, digits: int = 4, missing: str = "—") -> str:
    return missing if value is None else f"{value:.{digits}f}"
