"""Relatório Markdown gerado somente a partir das previsões e métricas calculadas."""

from collections.abc import Mapping, Sequence

from app.jev.config import JevConfig

METHOD_LABELS = {"jev": "Jev", "tfidf_logreg": "TF-IDF + RL"}


def make_report(metrics: dict, rows: Sequence[dict], config: JevConfig, names: Mapping[str, str], models: Sequence[str]) -> str:
    """Relatório completo; `names` traduz a chave de cada gênero para o nome do TMDB."""
    jev, baseline = metrics["methods"]["jev"], metrics["methods"]["tfidf_logreg"]
    lines = [
        "# Classificação de gênero com o Jev",
        "",
        f"Amostra de {metrics['films']} sinopses: {config.sample_per_genre} de cada gênero único ({', '.join(names.values())}) "
        f"e {config.multi_genre_sample} com mais de um desses gêneros, sorteadas com semente {config.random_state}. "
        f"O Jev recebeu o texto da etapa `{config.stage}` com uma Choice (gênero principal) e um Noul por gênero, na mesma chamada; "
        f"não foi treinado com o corpus. O classificador de referência (TF-IDF da etapa `{config.baseline_stage}` + regressão logística) "
        "foi treinado com os filmes fora da amostra e avaliado nos mesmos filmes.",
        "",
        f"Filmes avaliados: {metrics['evaluated']} de {metrics['films']} ({metrics['failed']} falhas do Jev, fora de todas as métricas). "
        f"Modelo informado pela API: {', '.join(f'`{model}`' for model in models) or 'não informado'}. "
        "Os gêneros de referência são os recortes de coleta do TMDB, não um julgamento sobre a sinopse.",
        "",
        "## Resumo",
        "",
        f"| Métrica | {METHOD_LABELS['jev']} | {METHOD_LABELS['tfidf_logreg']} |",
        "|---|---:|---:|",
        _row("Choice: gênero principal entre os do filme (toda a amostra)", jev["choice"]["hit_rate"], baseline["choice"]["hit_rate"]),
        _row(
            f"Choice: acurácia nos {metrics['single_genre']} filmes de um gênero", jev["choice"]["accuracy"], baseline["choice"]["accuracy"]
        ),
        _row("Choice: F1 macro nos filmes de um gênero", jev["choice"]["macro_f1"], baseline["choice"]["macro_f1"]),
        _row("Por gênero: ROC AUC macro", jev["labels"]["macro_auc"], baseline["labels"]["macro_auc"]),
        _row(f"Por gênero: F1 macro com limiar {config.threshold}", jev["labels"]["macro_f1"], baseline["labels"]["macro_f1"]),
        _row("Por gênero: conjunto de gêneros exato", jev["labels"]["exact_match"], baseline["labels"]["exact_match"]),
        "",
        f"Os dois métodos escolhem o mesmo gênero principal em {metrics['choice_agreement']:.1%} dos filmes.",
        "",
        "## Choice por gênero (filmes de um gênero)",
        "",
        "| Gênero | Filmes | Precisão Jev | Revocação Jev | F1 Jev | Precisão RL | Revocação RL | F1 RL |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, name in names.items():
        a, b = jev["choice"]["per_genre"].get(key), baseline["choice"]["per_genre"].get(key)
        if a and b:
            lines.append(
                f"| {name} | {a['support']} | {a['precision']:.3f} | {a['recall']:.3f} | {a['f1']:.3f} | {b['precision']:.3f} | {b['recall']:.3f} | {b['f1']:.3f} |"
            )
    for method in ("jev", "tfidf_logreg"):
        lines += ["", *_confusion(metrics["methods"][method]["choice"]["confusion"], names, METHOD_LABELS[method])]
    lines += [
        "",
        "## Noul × regressão binária, por gênero (toda a amostra)",
        "",
        "Cada gênero é uma pergunta sim/não. A ROC AUC usa o valor contínuo (Noul ou probabilidade da regressão) e não depende do limiar; "
        f"o F1 usa o limiar {config.threshold}. Filmes com dois gêneros contam como positivos nos dois.",
        "",
        "| Gênero | Positivos | AUC Jev | AUC RL | F1 Jev | F1 RL |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key, name in names.items():
        a, b = jev["labels"]["per_genre"][key], baseline["labels"]["per_genre"][key]
        lines.append(f"| {name} | {a['positives']} | {_value(a['auc'])} | {_value(b['auc'])} | {a['f1']:.3f} | {b['f1']:.3f} |")
    confidence, consistency = metrics["jev_confidence"], metrics["jev_consistency"]
    lines += [
        "",
        "## Confiança e coerência do Jev",
        "",
        f"- Confiança média da Choice quando acerta: {_value(confidence['mean_when_hit'])}; quando erra: {_value(confidence['mean_when_miss'])}. "
        "Confiança mede a concentração das probabilidades, não a correção.",
        f"- A Choice coincide com o Noul mais alto em {consistency['choice_is_top_noul']:.1%} dos filmes, "
        f"e o Noul do gênero escolhido passa do limiar em {consistency['choice_noul_above_threshold']:.1%}.",
        "",
        "Casos de menor confiança:",
        "",
        "| Filme | Gêneros de coleta | Choice | Confiança | Probabilidades |",
        "|---|---|---|---:|---|",
    ]
    for case in confidence["lowest"]:
        spread = ", ".join(f"{names[key]} {value:.2f}" for key, value in case["choice_probabilities"].items())
        lines.append(
            f"| {_cell(case['title'])} | {_genres(case['gold'], names)} | {names[case['choice']]} | {case['confidence']:.2f} | {spread} |"
        )
    misses = [row for row in rows if row["jev"] is not None and row["jev"]["choice"] not in row["gold"]]
    lines += ["", "## Erros da Choice do Jev", ""]
    if misses:
        lines += ["| Filme | Gêneros de coleta | Jev | Confiança | TF-IDF + RL |", "|---|---|---|---:|---|"]
        for row in misses:
            lines.append(
                f"| {_cell(row['title'])} | {_genres(row['gold'], names)} | {names[row['jev']['choice']]} | "
                f"{_value(row['jev']['confidence'])} | {names[row['tfidf_logreg']['choice']]} |"
            )
    else:
        lines.append("Nenhum.")
    if failures := [row for row in rows if row["jev"] is None]:
        lines += ["", "## Falhas do Jev", ""]
        lines += [f"- {_cell(row['title'])} ({row['id']}): {_cell(row['error'])}" for row in failures]
    lines += [
        "",
        "## Limitações",
        "",
        "A amostra é pequena porque cada filme é uma chamada paga a uma API externa; as diferenças entre os métodos servem como ilustração, "
        "não como teste estatístico. O rótulo é o recorte de coleta, e muitos filmes pertencem a gêneros não avaliados (ação, romance, suspense), "
        "que ficam fora das opções. O Jev é acessado pelo alias mais recente: o modelo registrado acima pode mudar entre execuções, "
        "por isso as respostas brutas ficam em `responses.jsonl` e podem ser reavaliadas sem novas chamadas (`--reuse`). "
        "As perguntas e os critérios fazem parte da tarefa: outra redação pode mudar os resultados. "
        "O classificador de referência foi treinado só com os filmes deste corpus fora da amostra e não teve hiperparâmetros ajustados.",
        "",
        "## Fonte",
        "",
        "Dados: The Movie Database (TMDB), https://www.themoviedb.org/. Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB. "
        "Decisões estruturadas: Jev, da TypeSafe AI (https://docs.typesafe.ai/).",
        "",
    ]
    return "\n".join(lines)


def _confusion(confusion: dict | None, names: Mapping[str, str], method: str) -> list[str]:
    if confusion is None:
        return []
    labels = confusion["labels"]
    lines = [
        f"Matriz de confusão — {method} (linhas: gênero de coleta; colunas: previsto):",
        "",
        "| | " + " | ".join(names[key] for key in labels) + " |",
        "|---|" + "---:|" * len(labels),
    ]
    lines += [
        f"| {names[key]} | " + " | ".join(str(count) for count in row) + " |" for key, row in zip(labels, confusion["matrix"], strict=True)
    ]
    return lines


def _row(label: str, left: float | None, right: float | None) -> str:
    return f"| {label} | {_value(left)} | {_value(right)} |"


def _value(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def _genres(keys: Sequence[str], names: Mapping[str, str]) -> str:
    return ", ".join(names[key] for key in keys)


def _cell(text: str) -> str:
    """Texto vindo dos dados, sem quebrar a tabela Markdown."""
    return " ".join(str(text).split()).replace("|", "\\|")
