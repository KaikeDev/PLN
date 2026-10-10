"""Relatório Markdown gerado somente a partir dos resultados calculados de NER e relações.

Os grafos dos filmes de exemplo são escritos em Mermaid, que o GitHub desenha, no lugar do NetworkX do notebook:
o resultado é o mesmo grafo dirigido de argumentos, sem uma dependência a mais.
"""

from app.entities.extraction import is_pronoun

MAX_EXAMPLES = 10
MAX_DEPENDENCY_ROWS = 25


def make_report(statistics: dict, credits: dict, checks: list[dict], examples: list[dict], config: object) -> str:
    """Entidades, conferência com os créditos, relações, filmes de exemplo com grafo e limitações."""
    labels = statistics["entidades_por_categoria"]
    rules = statistics["triplas_por_regra"]
    total = statistics["triplas"]
    lines = [
        "# Entidades nomeadas e relações nas sinopses",
        "",
        f"As {statistics['sinopses']} sinopses passam pelo spaCy `pt_core_news_sm`, o modelo do notebook da Aula 9: "
        "texto → dependências e NER → relações → normalização dos argumentos → grafo. "
        f"O spaCy processou tudo em {_n(statistics['segundos_spacy'], 1)} s.",
        "",
        "## Entidades",
        "",
        f"{statistics['entidades']} menções reconhecidas. O modelo só conhece quatro categorias: PER (pessoa), LOC (lugar), ORG (organização) e MISC (outras).",
        "",
        "| Categoria | Menções | Mais frequentes |",
        "|---|---:|---|",
        *(
            f"| {label} | {count} | {', '.join(f'{name} ({times})' for name, times in statistics['entidades_mais_frequentes'][label][:8])} |"
            for label, count in labels.items()
        ),
        "",
        "## Conferência com os créditos do TMDB",
        "",
        "Uma menção de pessoa creditada é uma sequência de palavras da sinopse que fazem parte do nome de um personagem ou ator do filme "
        f"(os 15 primeiros do elenco). Foram {credits['mencoes_creditadas']} menções, em {credits['filmes_com_mencao']} sinopses.",
        "",
        "| Medida | Valor |",
        "|---|---:|",
        f"| Revocação de pessoas: menções creditadas marcadas como PER | {_pct(credits['revocacao_per'])} |",
        f"| Menções creditadas reconhecidas com qualquer categoria | {_pct(credits['revocacao_qualquer_categoria'])} |",
        f"| Precisão estimada (piso): entidades PER com nome dos créditos | {_pct(credits['precisao_estimada_per'])} de {credits['pessoas_previstas']} |",
        "",
        "Categoria dada às menções creditadas: "
        + ", ".join(f"{label} {count}" for label, count in credits["categorias_das_mencoes"].items())
        + ".",
        "",
        "Pessoas creditadas que o NER não marcou como PER (exemplos):",
        "",
        *_missed(checks),
        "",
        "Entidades PER sem nenhum nome dos créditos (exemplos; parte são pessoas reais fora do elenco principal):",
        "",
        *_unconfirmed(checks),
        "",
        "## Relações",
        "",
        "Triplas sujeito — relação → objeto pelas regras de dependência do notebook: sujeito (`nsubj`, `nsubj:pass`) de um verbo com cada "
        "complemento (`obj`, `iobj`, `obl`); no `obl`, a preposição entra na relação (`trabalhar_em`). Os argumentos são a entidade que contém o "
        "núcleo ou o sintagma sem artigo e preposição iniciais.",
        "",
        "| Medida | Valor |",
        "|---|---:|",
        f"| Triplas | {total} |",
        f"| Pelas regras do notebook (objeto direto e complemento com preposição) | {statistics['triplas_regras_do_notebook']} ({rules.get('svo', 0)} `svo`, {rules.get('obl', 0)} `obl`) |",
        f"| A mais pela regra de coordenação (verbo coordenado herda o sujeito) | {rules.get('coordenacao', 0)} |",
        f"| Sentenças com ao menos uma tripla | {statistics['sentencas_com_tripla']} de {statistics['sentencas']} ({_pct(statistics['sentencas_com_tripla'] / statistics['sentencas'])}) |",
        f"| Triplas com entidades nos dois lados | {statistics['triplas_com_duas_entidades']} ({_pct(statistics['triplas_com_duas_entidades'] / total if total else None)}) |",
        f'| Triplas cujo sujeito é só um pronome pessoal ou relativo ("Ela", "que") | {statistics["sujeitos_pronomes"]} |',
        "",
        "Relações mais frequentes: "
        + ", ".join(f"`{relation}` ({count})" for relation, count in statistics["relacoes_mais_frequentes"])
        + ".",
        "",
    ]
    for example in examples:
        lines += _example(example)
    lines += [
        "## Conferência manual",
        "",
        f"`review_sample.json` traz {getattr(config, 'review_sample', 0)} triplas sorteadas, com a sentença de origem e o campo `correta` vazio, "
        "para a equipe julgar como no notebook. Sem esse julgamento, este relatório não afirma a precisão das relações.",
        "",
        "## Limitações (as da seção 8 do notebook, medidas nas sinopses)",
        "",
        f'- **Correferência:** {statistics["sujeitos_pronomes"]} triplas têm um pronome ("Ela", "que") como sujeito, que não é ligado ao personagem.',
        '- **Voz passiva com agente:** em "Thomas Anderson é atormentado por estranhos pesadelos", o agente é `obl:agent`, fora das regras do notebook, e não há tripla.',
        '- **Taxonomia do modelo:** não há categorias para datas, valores ou obras; "Universidade de Paris" vira LOC, e títulos de filmes viram MISC ou PER.',
        "- **Nomes estrangeiros e de personagens** são a maior parte das pessoas das sinopses; o modelo, treinado em notícias, erra mais com eles.",
        "- **Papéis semânticos, negação e tempo** não são representados; a voz passiva não vira agente–ação–paciente.",
        "- **Propagação de erros:** falhas do parser e do NER passam para as triplas; a tabela guarda a sentença de origem para conferência.",
        "",
    ]
    return "\n".join(lines)


def _example(example: dict) -> list[str]:
    triples = example["triplas"]
    lines = [
        f"## Exemplo: {example['title']}",
        "",
        f"> {example['texto']}",
        "",
        "Entidades: " + (", ".join(f"{e['entidade']} ({e['categoria']})" for e in example["entidades"]) or "nenhuma") + ".",
        "",
        f"Dependências da primeira sentença (até {MAX_DEPENDENCY_ROWS} tokens; a tabela completa está em `examples.json`):",
        "",
        "| Token | Lema | Classe | Dependência | Núcleo |",
        "|---|---|---|---|---|",
        *(
            f"| {d['token']} | {d['lema']} | {d['classe']} | {d['dependencia']} | {d['nucleo']} |"
            for d in example["dependencias_primeira_sentenca"][:MAX_DEPENDENCY_ROWS]
        ),
        "",
    ]
    if not triples:
        return [*lines, "Nenhuma tripla extraída.", ""]
    lines += [
        "| Sentença | Sujeito | Relação | Objeto | Regra |",
        "|---:|---|---|---|---|",
        *(f"| {t['sentence']} | {t['subject']} | `{t['relation']}` | {t['object']} | {t['rule']} |" for t in triples),
        "",
        "```mermaid",
        "graph LR",
    ]
    nodes: dict[str, str] = {}
    for t in triples:
        for name in (t["subject"], t["object"]):
            nodes.setdefault(name, f"n{len(nodes)}")
    lines += [f'    {node}["{_mermaid(name)}"]' for name, node in nodes.items()]
    lines += [f'    {nodes[t["subject"]]} -->|"{_mermaid(t["relation"])}"| {nodes[t["object"]]}' for t in triples]
    return [*lines, "```", ""]


def _missed(checks: list[dict]) -> list[str]:
    rows = [(check["title"], m) for check in checks for m in check["mencoes_creditadas"] if m["categoria"] != "PER"][:MAX_EXAMPLES]
    return [f'- *{title}*: "{m["mencao"]}" → {m["categoria"] or "não reconhecida"}' for title, m in rows] or ["- nenhuma"]


def _unconfirmed(checks: list[dict]) -> list[str]:
    rows = [
        (check["title"], p) for check in checks for p in check["pessoas_previstas"] if not p["confirmada"] and not is_pronoun(p["entidade"])
    ]
    return [f'- *{title}*: "{p["entidade"]}"' for title, p in rows[:MAX_EXAMPLES]] or ["- nenhuma"]


def _mermaid(text: str) -> str:
    return text.replace('"', "'").replace("|", "/")


def _n(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}".replace(".", ",")
