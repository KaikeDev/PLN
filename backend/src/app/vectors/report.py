"""Relatório Markdown gerado somente a partir dos resultados calculados.

Cada análise escreve a própria seção por meio de `Analysis.report_section`, que delega às funções
de apresentação deste módulo. `make_report` só adiciona introdução, limitações e fonte; incluir uma
nova análise não exige alterar este arquivo.
"""

from collections.abc import Sequence
from typing import Protocol

from app.vectors.context import AnalysisContext


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
        "Gêneros de coleta são rótulos aproximados da amostragem, não julgamentos de relevância.",
        "",
    ]
    for analysis in analyses:
        if analysis.name in results:
            lines += analysis.report_section(results[analysis.name], context)
    lines += [
        "## Limitações",
        "",
        "BoW e TF-IDF só comparam termos idênticos após a preparação. Word2vec aproxima palavras usadas em contextos parecidos, mas a média apaga ordem e negação. "
        "Embeddings contextuais dependem do texto usado no treino do modelo e truncam sinopses longas. "
        "A concordância de gênero e as métricas de clustering usam os recortes de coleta como aproximação; filmes com vários gêneros são ambíguos. "
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


def neighbors_section(results: dict, context: AnalysisContext) -> list[str]:
    names = context.representation_names
    k = context.config.neighbors_k
    lines = [
        "## Similaridade do cosseno",
        "",
        f"Para cada sinopse foram buscados os {k} vizinhos de maior cosseno. A concordância é a fração desses vizinhos com ao menos um gênero de coleta em comum; "
        "a referência é essa fração calculada sobre todos os demais filmes, ou seja, o esperado sem usar o texto. "
        "Nas representações lexicais a explicação lista termos idênticos; no word2vec, pares de palavras próximas (≈); o modelo contextual não é explicável por palavras.",
        "",
        f"| Representação | Concordância de gênero @{k} | Referência | Filmes avaliados |",
        "|---|---:|---:|---:|",
    ]
    for name in names:
        row = results[name]
        lines.append(
            f"| {name} | {_number(row['genre_agreement_at_k'])} | {_number(row['genre_agreement_baseline'])} | {row['documents_evaluated']} |"
        )
    lines.append("")
    for index, movie_id in enumerate(context.config.example_ids):
        lines += [f"### Vizinhos de {context.corpus.by_id[movie_id].title} ({movie_id})", ""]
        for name in names:
            neighbors = results[name]["examples"][index]["neighbors"][:3]
            described = "; ".join(_titled(item) for item in neighbors) or "nenhum vizinho com cosseno positivo"
            lines.append(f"- **{name}**: {described}")
        lines.append("")
    return lines


def clustering_section(results: dict, context: AnalysisContext) -> list[str]:
    names = context.representation_names
    lines = [
        "## Clustering",
        "",
        f"K-Means com k = {context.config.clusters}. ARI, NMI e pureza comparam os clusters com o gênero de coleta dos filmes que vieram de um único gênero; "
        "a silhueta usa distância do cosseno e não depende de rótulos. Os termos descritivos vêm da média TF-IDF (sem stopwords) dos membros de cada cluster, "
        "o mesmo vocabulário para todas as representações.",
        "",
        "| Representação | ARI | NMI | Pureza | Silhueta | Filmes rotulados | Tamanhos |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for name in names:
        row = results[name]
        sizes = ", ".join(str(cluster["size"]) for cluster in row["clusters"])
        lines.append(
            f"| {name} | {_number(row['adjusted_rand_index'])} | {_number(row['normalized_mutual_information'])} | {_number(row['purity'])} | "
            f"{_number(row['silhouette_cosine'])} | {row['labeled_documents']} | {sizes} |"
        )
    for name in names:
        lines += ["", f"### {name}", ""]
        for cluster in results[name]["clusters"]:
            genres = ", ".join(f"{genre} {count}" for genre, count in list(cluster["genres"].items())[:4]) or "sem gênero"
            lines.append(f"- Cluster {cluster['cluster']} ({cluster['size']} filmes; {genres}): {', '.join(cluster['descriptive_terms'])}")
    return [*lines, ""]


def projection_section(results: dict, context: AnalysisContext) -> list[str]:
    names = context.representation_names
    lines = [
        "## Projeção em duas dimensões",
        "",
        "TruncatedSVD reduz as dimensões a dois componentes para inspeção visual (nas matrizes lexicais, é a LSA). "
        "Variância explicada baixa indica que o plano mostra só parte da estrutura; distâncias no gráfico não substituem o cosseno original. "
        "Sem centralização, o primeiro componente tende a seguir a direção média das sinopses e pode explicar menos variância que o segundo.",
        "",
        "| Representação | Variância componente 1 | Variância componente 2 | Gráfico |",
        "|---|---:|---:|---|",
    ]
    for name in names:
        first, second = results[name]["explained_variance_ratio"]
        lines.append(f"| {name} | {first:.2%} | {second:.2%} | [{name}.projection.svg]({name}.projection.svg) |")
    return [*lines, ""]


def word_neighbors_section(results: dict, context: AnalysisContext) -> list[str]:
    names = context.representation_names
    supported = [name for name in names if results[name]["supported"]]
    if not supported or not context.config.probe_words:
        return []
    lines = [
        "## Palavras vizinhas (word2vec)",
        "",
        "Palavras do vocabulário do corpus com maior cosseno em relação a cada palavra de sondagem. Direções próximas indicam contextos de uso parecidos, "
        "não sinonímia garantida.",
        "",
    ]
    for name in supported:
        lines += [f"### {name}", ""]
        for word, neighbors in results[name]["words"].items():
            described = (
                ", ".join(f"{neighbor} ({score:.2f})" for neighbor, score in neighbors)
                if neighbors is not None
                else "fora do vocabulário do modelo"
            )
            lines.append(f"- **{word}**: {described}")
        lines.append("")
    return lines


def retrieval_section(results: dict, context: AnalysisContext) -> list[str]:
    names = context.representation_names
    if not context.queries:
        return []
    k = context.config.neighbors_k
    lines = [
        "## Consultas anotadas",
        "",
        "A consulta passa pelas mesmas regras de preparação da entrada de cada representação e vira um vetor no mesmo espaço. "
        "A posição é a do primeiro filme anotado como relevante entre os filmes com cosseno positivo.",
        "",
        f"| Representação | MRR | Acerto @{k} |",
        "|---|---:|---:|",
    ]
    lines += [
        f"| {name} | {_number(results[name]['mean_reciprocal_rank'])} | {_number(results[name]['hit_rate_at_k'])} |" for name in names
    ]
    for index, query in enumerate(context.queries):
        lines += ["", f"### {query.id}: “{query.text}”", ""]
        if query.note:
            lines += [query.note, ""]
        lines += [
            "| Representação | Posição do relevante | Fora do vocabulário | Por que o relevante foi aproximado | Primeiros resultados |",
            "|---|---:|---|---|---|",
        ]
        for name in names:
            item = results[name]["queries"][index]
            rank = min((r["rank"] for r in item["relevant"] if r["rank"] is not None), default=None)
            oov = ", ".join(item["out_of_vocabulary"]) or "—"
            explanation = "; ".join(", ".join(r["explanation"]) for r in item["relevant"] if r["explanation"]) or "—"
            top = "; ".join(f"{result['title']} ({result['score']:.3f})" for result in item["top"][:3])
            top = top or ("vetor nulo" if item["null_vector"] else "nenhum filme com cosseno positivo")
            lines.append(f"| {name} | {rank if rank is not None else 'não recuperado'} | {oov} | {explanation} | {top} |")
    return [*lines, ""]


def _titled(item: dict) -> str:
    explanation = f": {', '.join(item['explanation'])}" if item["explanation"] else ""
    return f"{item['title']} ({item['score']:.3f}{explanation})"


def _number(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"
