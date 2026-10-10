"""Relatório Markdown gerado somente a partir dos resultados calculados do experimento de sentimentos."""

from app.classification.evaluation import BASELINE
from app.sentiment.config import SentimentConfig

POLARITY, RATING, MEAN_BASELINE = "polaridade", "nota", "media_do_treino"


def make_report(dataset: dict, config: SentimentConfig, results: dict, representations: dict, terms: dict, errors: dict) -> str:
    """Dados, polaridade, nota, negação, termos, erros mais confiantes e limitações."""
    polarity, rating = results[POLARITY], results[RATING]
    names = list(representations)
    best = max(names, key=lambda name: polarity[name]["f1_macro"])
    best_rating = min(names, key=lambda name: rating[name]["erro_absoluto_medio"])
    negative, positive = dataset["polarity"]["negativo"], dataset["polarity"]["positivo"]
    lines = [
        "# Análise de sentimentos das críticas",
        "",
        f"{dataset['reviews']} críticas em português do TMDB, de {dataset['movies']} filmes e {dataset['authors']} autores. "
        f"O rótulo é a nota que o próprio autor deu ao filme: **negativa** com nota ≤ {config.negative_max:g} ({negative} críticas) e "
        f"**positiva** com nota ≥ {config.positive_min:g} ({positive}). As {dataset['middle_excluded_from_polarity']} do meio ficam fora da polaridade, "
        "mas entram na previsão da nota.",
        "",
        f"Validação cruzada em {config.classification.folds} dobras, com as críticas de um mesmo filme sempre na mesma dobra. "
        "Polaridade: regressão logística com classes de peso balanceado, como na classificação de gêneros. Nota: regressão Ridge. "
        "Os transformers leem a crítica inteira, em partes que cabem no modelo, e tiram a média dos vetores.",
        "",
        "## Polaridade",
        "",
        "| Representação | F1 macro | Acurácia | F1 negativo | F1 positivo | F1 macro nas dobras |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in [BASELINE, *sorted(names, key=lambda name: -polarity[name]["f1_macro"])]:
        row = polarity[name]
        label = "referência: classe mais frequente" if name == BASELINE else f"`{name}`"
        folds = row["f1_macro_dobras"]
        lines.append(
            f"| {label} | {_n(row['f1_macro'])} | {_n(row['acuracia'])} | {_n(row['por_genero']['negativo']['f1'])} | "
            f"{_n(row['por_genero']['positivo']['f1'])} | {_n(folds['media'])} ± {_n(folds['desvio'])} |"
        )
    matrix = polarity[best]["matriz_confusao"]
    lines += [
        "",
        f"Melhor F1 macro: `{best}`. Matriz de confusão (linhas reais, colunas previstas, negativo e positivo): "
        f"{matrix[0][0]} e {matrix[0][1]} entre as negativas; {matrix[1][0]} e {matrix[1][1]} entre as positivas.",
        "",
        "## Nota prevista",
        "",
        "| Representação | Erro absoluto médio | Raiz do erro quadrático | Spearman | A até 1 ponto da nota |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in [MEAN_BASELINE, *sorted(names, key=lambda name: rating[name]["erro_absoluto_medio"])]:
        row = rating[name]
        label = "referência: média do treino" if name == MEAN_BASELINE else f"`{name}`"
        lines.append(
            f"| {label} | {_n(row['erro_absoluto_medio'])} | {_n(row['raiz_erro_quadratico'])} | {_n(row['spearman'])} | {_pct(row['ate_1_ponto'])} |"
        )
    lines += [
        "",
        f"Menor erro: `{best_rating}`, que erra a nota em {_n(rating[best_rating]['erro_absoluto_medio'])} ponto em média.",
        "",
        "## Entre autores",
        "",
        f"Um único autor escreveu {dataset['main_author_share']:.0%} das críticas. Polaridade treinando sem ele e testando nele, e o contrário (F1 macro):".replace(
            ".", ",", 0
        ),
        "",
        "| Representação | Treino sem o autor principal → teste nele | Treino só com ele → teste nos demais |",
        "|---|---:|---:|",
        *(
            f"| `{name}` | {_n(polarity[name]['entre_autores']['treino_sem_autor_principal']['f1_macro'])} | "
            f"{_n(polarity[name]['entre_autores']['treino_so_autor_principal']['f1_macro'])} |"
            for name in sorted(names, key=lambda name: -polarity[name]["f1_macro"])
        ),
        "",
        "## Negação",
        "",
        f'{dataset["with_negation"]} críticas da polaridade têm "não", "nem", "nunca" ou "sem". Acurácia com e sem esses marcadores:',
        "",
        "| Representação | Com negação | Sem negação |",
        "|---|---:|---:|",
        *(
            f"| `{name}` | {_pct(polarity[name]['negacao']['com']['acuracia'])} | {_pct(polarity[name]['negacao']['sem']['acuracia'])} |"
            for name in sorted(names, key=lambda name: -polarity[name]["f1_macro"])
        ),
        "",
    ]
    if terms:
        lexical = max(terms, key=lambda name: polarity[name]["f1_macro"])
        lines += [
            "## Termos de maior peso",
            "",
            f"Coeficientes de `{lexical}` num modelo ajustado com todas as críticas da polaridade (para interpretar, não para avaliar).",
            "",
            "| Negativo | Positivo |",
            "|---|---|",
            *(f"| {neg[0]} | {pos[0]} |" for neg, pos in zip(terms[lexical]["negativo"], terms[lexical]["positivo"], strict=True)),
            "",
        ]
    lines += ["## Erros mais confiantes", "", f"Críticas em que `{best}` errou com mais convicção:", ""]
    for row in errors[best]:
        lines.append(
            f"- **{row['title']}**, nota {row['nota']:g}: previsto {row['previsto'][0]} com {_pct(max(row['probabilidades'].values()))}. "
            f'"{row["trecho"]}"'
        )
    lines += [
        "",
        "## Limitações",
        "",
        '- **A nota é do autor, não do texto:** quem dá 4 pode escrever com elogios, e quem dá 8 pode listar defeitos. Parte dos "erros" é esse descompasso.',
        "- **Um autor domina a base:** a validação cruzada mede sobretudo o estilo desse autor; o teste entre autores mostra quanto o resultado se mantém para outras pessoas.",
        "- **Ironia** e opiniões implícitas não têm tratamento específico.",
        "- **Base do TMDB:** poucas críticas em português, escritas por usuários que publicam críticas, e mais positivas que negativas.",
        "",
    ]
    return "\n".join(lines)


def _n(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}".replace(".", ",")


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}".replace(".", ",")
