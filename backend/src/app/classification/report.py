"""Relatório Markdown gerado somente a partir dos resultados calculados da classificação."""

import math
from dataclasses import dataclass

from app.classification.alternatives import ALTERNATIVES, TREES
from app.classification.config import ClassificationConfig
from app.classification.dataset import Task
from app.classification.evaluation import BASELINE

BASELINE_LABEL = "referência: gênero mais frequente"
LOGISTIC_LABEL = "Regressão logística"
SUPERSCRIPT = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


@dataclass(frozen=True)
class Findings:
    """Resultados calculados que o relatório apresenta, todos indexados pelo nome da representação.

    `results` é indexado primeiro pela tarefa; `clusters` e `alternatives` referem-se à tarefa multiclasse.
    """

    results: dict[str, dict[str, dict]]
    representations: dict[str, dict]
    terms: dict[str, dict]
    errors: dict[str, list]
    clusters: dict[str, dict]
    alternatives: dict[str, dict]


def make_report(tasks: tuple[Task, Task], config: ClassificationConfig, findings: Findings) -> str:
    """Relatório completo: tarefas, avaliações, agrupamento, outros classificadores, interpretação, custo, limitações e fonte."""
    multiclass, multilabel = tasks
    results, representations = findings.results, findings.representations
    best = max(representations, key=lambda name: results[multiclass.name][name]["f1_macro"])
    lines = [
        "# Classificação de gêneros a partir das sinopses",
        "",
        "Cada representação da Etapa 2 alimenta a mesma regressão logística, com classes de peso balanceado. "
        f"A regularização C é escolhida pela log loss entre {', '.join(_n(c) for c in config.regularization_grid)} em {config.inner_folds} dobras internas do próprio treino, "
        f"e o modelo é avaliado por validação cruzada em {config.folds} dobras externas (semente {config.random_state}), as mesmas para todas as representações. "
        "Toda métrica usa só previsões fora da dobra: cada sinopse é classificada por um modelo que não a viu no treino. "
        "Os rótulos são os gêneros atribuídos pelo TMDB (`genre_ids`) restritos aos gêneros da coleta.",
        "",
        *_tasks_section(tasks),
        *_multiclass_section(multiclass, results[multiclass.name], representations, best),
        *_grouping_section(multiclass, results[multiclass.name], findings.clusters),
        *_alternatives_section(results[multiclass.name], findings.alternatives, config),
        *_multilabel_section(multilabel, results[multilabel.name], representations),
        *_terms_section(findings.terms),
        *_errors_section(findings.errors[best], best),
        *_cost_section(representations),
        "## Limitações",
        "",
        f"A amostra é pequena ({len(multilabel.ids)} sinopses) e intencional (ADR 0014): os valores dependem das dobras, por isso o desvio entre dobras acompanha o F1. "
        "O gênero é atribuído ao filme, não à sinopse; uma sinopse curta pode não conter pistas do gênero. "
        "Os classificadores alternativos foram comparados só na tarefa multiclasse e só pelo gênero previsto; a floresta aleatória usa parâmetros fixos. "
        "O BERT e o modelo de sentença são usados como extratores de atributos congelados, sem ajuste fino. "
        "LLM com instrução e decisões tipadas (Jev) não foram avaliados: dependem de serviço externo e não seriam reproduzíveis nesta entrega.",
        "",
        "## Fonte",
        "",
        "Dados: The Movie Database (TMDB), https://www.themoviedb.org/. Este projeto utiliza a API do TMDB, mas não é endossado ou certificado pelo TMDB.",
        "",
    ]
    return "\n".join(lines)


def _tasks_section(tasks: tuple[Task, Task]) -> list[str]:
    multiclass, multilabel = tasks
    single = multiclass.targets.tolist()
    many = multilabel.targets.sum(axis=0).tolist()
    lines = [
        "## Tarefas",
        "",
        f"- **Multiclasse:** {len(multiclass.ids)} filmes com exatamente um dos gêneros; o modelo escolhe um gênero.",
        f"- **Multirrótulo:** {len(multilabel.ids)} filmes com ao menos um dos gêneros; um classificador binário por gênero "
        "decide cada gênero com probabilidade ≥ 0,5, e o mais provável é sempre atribuído.",
        "",
        "| Gênero | Multiclasse | Multirrótulo |",
        "|---|---:|---:|",
    ]
    lines += [f"| {name} | {single.count(i)} | {many[i]} |" for i, name in enumerate(multiclass.label_names)]
    return [*lines, ""]


def _multiclass_section(task: Task, results: dict[str, dict], representations: dict[str, dict], best: str) -> list[str]:
    lines = [
        "## Multiclasse: um gênero por filme",
        "",
        "| Representação | Família | Acurácia | F1 macro | F1 macro por dobra | Log loss | Confiança nos acertos | Confiança nos erros |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in [BASELINE, *representations]:
        r = results[name]
        family = representations[name]["family"] if name in representations else "—"
        confidence = r["confianca_media"]
        lines.append(
            f"| {_label(name)} | {family} | {_p(r['acuracia'])} | {_p(r['f1_macro'])} | {_spread(r)} | {_d(r['log_loss'], 3)} "
            f"| {_p(confidence['acertos'])} | {_p(confidence['erros'])} |"
        )
    lines += [
        "",
        "A confiança é a probabilidade média do gênero escolhido. Quando ela é menor nos erros que nos acertos, o modelo sinaliza a própria incerteza.",
        *_gap(results, representations, best),
        "",
        "### F1 por gênero",
        "",
        f"| Representação | {' | '.join(task.label_names)} |",
        f"|---|{'---:|' * len(task.label_names)}",
    ]
    for name in [BASELINE, *representations]:
        values = results[name]["por_genero"]
        lines.append(f"| {_label(name)} | {' | '.join(_p(values[g]['f1']) for g in task.label_names)} |")
    per_genre = results[best]["por_genero"]
    lines += [
        "",
        f"### Melhor F1 macro: `{best}`",
        "",
        "| Gênero | Precisão | Revocação | F1 | Suporte |",
        "|---|---:|---:|---:|---:|",
        *(f"| {g} | {_p(v['precisao'])} | {_p(v['revocacao'])} | {_p(v['f1'])} | {v['suporte']} |" for g, v in per_genre.items()),
        "",
        "Matriz de confusão (linhas = gênero real, colunas = previsto):",
        "",
        f"| Real ↓ / Previsto → | {' | '.join(task.label_names)} |",
        f"|---|{'---:|' * len(task.label_names)}",
        *(
            f"| {g} | {' | '.join(str(v) for v in row)} |"
            for g, row in zip(task.label_names, results[best]["matriz_confusao"], strict=True)
        ),
        "",
    ]
    return lines


def _grouping_section(task: Task, results: dict[str, dict], clusters: dict[str, dict]) -> list[str]:
    if not clusters:
        return []
    lines = [
        "## Descobrir grupos ou reconhecer classes?",
        "",
        f"O K-Means da Etapa 2 (k = {len(task.labels)}, k-means++, sem rótulos) agrupa as mesmas {len(task.ids)} sinopses da tarefa multiclasse em cada representação. "
        "Os gêneros só entram depois, para medir a coincidência entre grupos e classes. "
        "O ARI vale 1 na coincidência perfeita e fica perto de 0 para grupos ao acaso, porque desconta o acaso; o NMI vai de 0 "
        "(grupos independentes dos gêneros) a 1. Nenhum dos dois depende do nome de cada grupo, "
        "por isso medem da mesma forma os grupos do K-Means e as previsões do classificador (fora da dobra). "
        "A acurácia com o melhor mapeamento associa cada grupo a um gênero diferente usando os rótulos: é um teto otimista para usar grupos como classes.",
        "",
        "| Representação | K-Means: ARI | K-Means: NMI | K-Means: acurácia com o melhor mapeamento | Classificador: ARI | Classificador: NMI | Classificador: acurácia |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, grouping in clusters.items():
        r = results[name]
        lines.append(
            f"| `{name}` | {_d(grouping['ari'], 3)} | {_d(grouping['nmi'], 3)} | {_p(grouping['acuracia_melhor_mapeamento'])} "
            f"| {_d(r['ari'], 3)} | {_d(r['nmi'], 3)} | {_p(r['acuracia'])} |"
        )
    wins = sum(results[name]["ari"] > grouping["ari"] for name, grouping in clusters.items())
    closest = max(clusters, key=lambda name: clusters[name]["ari"])
    lines += [
        "",
        f"O classificador tem ARI maior que o agrupamento em {wins} de {len(clusters)} representações. "
        "Os dois partem do mesmo espaço vetorial e só o objetivo muda: o K-Means procura os grupos mais compactos, "
        "e o classificador procura a fronteira que separa os gêneros rotulados.",
        "",
        f"### Grupos de `{closest}`, o agrupamento mais próximo dos gêneros",
        "",
        "Contagem de sinopses de cada gênero real por grupo, termos de maior peso médio no TF-IDF de referência e sinopses mais próximas do centroide.",
        "",
        f"| Grupo | Tamanho | Gênero associado | {' | '.join(task.label_names)} | Termos descritivos | Mais próximos do centroide |",
        f"|---:|---:|---|{'---:|' * len(task.label_names)}---|---|",
    ]
    for group in clusters[closest]["grupos"]:
        counts = " | ".join(str(group["generos"][genre]) for genre in task.label_names)
        lines.append(
            f"| {group['grupo']} | {group['tamanho']} | {group['genero_associado']} | {counts} "
            f"| {', '.join(group['termos'])} | {'; '.join(group['mais_proximos_do_centroide'])} |"
        )
    return [*lines, ""]


def _alternatives_section(results: dict[str, dict], alternatives: dict[str, dict], config: ClassificationConfig) -> list[str]:
    names = config.alternatives
    if not names:
        return []
    lines = [
        "## Outros classificadores (multiclasse)",
        "",
        "F1 macro de cada classificador nas mesmas dobras externas e com a mesma preparação da regressão logística. "
        f"Cada alternativa escolhe o próprio hiperparâmetro pelo F1 macro em {config.inner_folds} dobras internas do treino "
        f"(Naive Bayes: alpha; SVM: C; k vizinhos: k); a floresta aleatória usa {TREES} árvores, sem ajuste. "
        "A regressão logística escolhe C pela log loss, porque suas probabilidades são usadas; o critério das alternativas "
        "é o próprio F1, o que torna a comparação conservadora para a regressão logística. "
        "“—” indica que o classificador não se aplica: o Naive Bayes multinomial exige atributos não negativos, "
        "e os vetores densos padronizados têm valores negativos.",
        "",
        f"| Representação | {LOGISTIC_LABEL} | {' | '.join(ALTERNATIVES[name].label for name in names)} |",
        f"|---|---:|{'---:|' * len(names)}",
    ]
    scores: dict[str, dict[str, float]] = {}
    for representation, by_model in alternatives.items():
        scores[representation] = {LOGISTIC_LABEL: results[representation]["f1_macro"]} | {
            ALTERNATIVES[name].label: by_model[name]["f1_macro"] for name in names if by_model[name] is not None
        }
        cells = [_p(results[representation]["f1_macro"])] + [_p(by_model[name]["f1_macro"]) if by_model[name] else "—" for name in names]
        lines.append(f"| `{representation}` | {' | '.join(cells)} |")
    wins = sum(row[LOGISTIC_LABEL] >= max(row.values()) for row in scores.values())
    logistic = [row[LOGISTIC_LABEL] for row in scores.values()]
    spreads = [max(row.values()) - min(row.values()) for row in scores.values()]
    representation, model = max(((r, m) for r, row in scores.items() for m in row), key=lambda pair: scores[pair[0]][pair[1]])
    lines += [
        "",
        f"A regressão logística tem o maior F1 macro em {wins} de {len(scores)} representações. "
        f"Com ela, trocar a representação muda o F1 macro em até {_d((max(logistic) - min(logistic)) * 100, 1)} pontos; "
        f"na mesma representação, trocar o classificador muda em média {_d(sum(spreads) / len(spreads) * 100, 1)} pontos "
        f"(até {_d(max(spreads) * 100, 1)}). A melhor combinação medida é `{representation}` + {model} ({_p(scores[representation][model])}).",
        "",
    ]
    return lines


def _multilabel_section(task: Task, results: dict[str, dict], representations: dict[str, dict]) -> list[str]:
    base = results[BASELINE]
    cardinality = base["rotulos_por_filme"]["real"]
    lines = [
        "## Multirrótulo: todos os gêneros do filme",
        "",
        "| Representação | F1 micro | F1 macro | F1 macro por dobra | Perda de Hamming | Acerto exato | Gêneros previstos por filme |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in [BASELINE, *representations]:
        r = results[name]
        lines.append(
            f"| {_label(name)} | {_p(r['f1_micro'])} | {_p(r['f1_macro'])} | {_spread(r)} | {_p(r['hamming'])} "
            f"| {_p(r['acuracia_exata'])} | {_d(r['rotulos_por_filme']['previsto'], 2)} |"
        )
    lines += [
        "",
        f"Em média, cada filme tem {_d(cardinality, 2)} dos {len(task.labels)} gêneros. "
        f"Um classificador que nunca atribuísse gênero algum erraria só {_p(cardinality / len(task.labels))} das decisões gênero a gênero (perda de Hamming), "
        f"{'menos' if cardinality / len(task.labels) < base['hamming'] else 'não menos'} que a referência ({_p(base['hamming'])}), com F1 zero: "
        "com rótulos esparsos, acertar “não pertence” é fácil, e por isso o F1 é a métrica principal. "
        "O acerto exato exige todos os gêneros certos ao mesmo tempo e é a métrica mais severa.",
        "",
    ]
    return lines


def _terms_section(terms: dict[str, dict]) -> list[str]:
    if not terms:
        return []
    lines = [
        "## O que os modelos lexicais aprenderam",
        "",
        "Termos com maior coeficiente para cada gênero, num modelo ajustado com todas as sinopses da tarefa multiclasse. "
        "Nas representações densas as dimensões não correspondem a palavras, e esta leitura não é possível.",
        "",
    ]
    for name, by_genre in terms.items():
        lines += [f"### `{name}`", "", "| Gênero | Termos |", "|---|---|"]
        lines += [f"| {genre} | {', '.join(term for term, _ in values)} |" for genre, values in by_genre.items()]
        lines.append("")
    return lines


def _errors_section(errors: list[dict], best: str) -> list[str]:
    if not errors:
        return []
    lines = [
        f"## Erros com mais convicção: `{best}`",
        "",
        "Filmes da tarefa multiclasse em que o modelo deu a maior probabilidade a um gênero errado. As probabilidades de cada filme estão nos arquivos `*.predictions.jsonl`.",
        "",
        "| Filme | Real | Previsto | Probabilidade |",
        "|---|---|---|---:|",
    ]
    lines += [
        f"| {row['title']} ({row['id']}) | {row['real'][0]} | {row['previsto'][0]} | {_p(max(row['probabilidades'].values()))} |"
        for row in errors
    ]
    return [*lines, ""]


def _cost_section(representations: dict[str, dict]) -> list[str]:
    lines = [
        "## Custo e interpretabilidade",
        "",
        "| Representação | Família | Dimensões | Parâmetros pré-treinados | Coeficientes legíveis como termos | Vetores |",
        "|---|---|---:|---:|---|---|",
    ]
    for name, info in representations.items():
        parameters = f"{info['parameters']:,}".replace(",", ".") if info["parameters"] else "—"
        lines.append(
            f"| `{name}` | {info['family']} | {info['dimensions']} | {parameters} | {'sim' if info['interpretable_terms'] else 'não'} | {info['vectors']} |"
        )
    lines += [
        "",
        "Nas lexicais, as dimensões são o vocabulário do corpus inteiro; dentro de cada dobra o vocabulário vem só das sinopses de treino. "
        "Vetores densos lidos da Etapa 2 não são recalculados: a pasta de vetores é verificada e precisa vir do mesmo corpus e da mesma especificação "
        "de modelo. Os tempos de construção e de validação de cada representação estão em `manifest.json` (`seconds`), porque variam entre execuções.",
        "",
    ]
    return lines


def _gap(results: dict[str, dict], representations: dict[str, dict], best: str) -> list[str]:
    """Compara a melhor com a segunda representação; diferença menor que o desvio entre dobras não é conclusiva."""
    ranked = sorted(representations, key=lambda name: -results[name]["f1_macro"])
    if len(ranked) < 2:
        return []
    second = ranked[1]
    gap = results[best]["f1_macro"] - results[second]["f1_macro"]
    spread = max(results[name]["f1_macro_dobras"]["desvio"] for name in (best, second))
    verdict = "menor que" if gap < spread else "maior que"
    conclusion = (
        "a ordem entre as duas não é conclusiva nesta amostra" if gap < spread else "a vantagem se mantém acima da variação entre dobras"
    )
    return [
        "",
        f"`{best}` tem o maior F1 macro, {_d(gap * 100, 1)} pontos acima de `{second}`. "
        f"A diferença é {verdict} o maior desvio entre dobras das duas ({_d(spread * 100, 1)} pontos): {conclusion}.",
    ]


def _label(name: str) -> str:
    return BASELINE_LABEL if name == BASELINE else f"`{name}`"


def _spread(result: dict) -> str:
    folds = result["f1_macro_dobras"]
    return f"{_p(folds['media'])} ± {_p(folds['desvio'])}"


def _p(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%".replace(".", ",")


def _n(value: float) -> str:
    exponent = math.log10(value)
    if value < 0.01 and exponent.is_integer():
        return "10" + str(int(exponent)).translate(SUPERSCRIPT)
    return f"{value:g}".replace(".", ",")


def _d(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", ",")
