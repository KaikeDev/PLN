"""Gera o documento do Trabalho da Unidade 3 (.docx) e as figuras a partir dos resultados do repositório.

Rode em `backend`, depois de `coletar_resultados.py`:

    uv run --frozen --no-sync --with python-docx --with matplotlib python ../docs/entregas/unidade-3/gerar_documento.py

`python-docx` e `matplotlib` entram só no ambiente temporário desta execução; não são dependências do projeto.
Todos os números vêm dos arquivos de `data/` e de `resultados.json`; os trechos de código vêm do código real.
"""

import inspect
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from docx import Document  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = REPO / "data"
FIG = HERE / "figuras"
OUTPUT = HERE / "PLN_2026_2_Trabalho_Unidade_3.docx"
REPRESENTATIONS = [
    "bow_sem_pontuacao", "bow_sem_stopwords", "tfidf_sem_pontuacao", "tfidf_sem_stopwords",
    "word2vec_cbow", "word2vec_skipgram", "bert_base_pt", "sentenca_minilm",
]
LABEL = {
    "bow_sem_pontuacao": "BoW sem pontuação", "bow_sem_stopwords": "BoW sem stopwords",
    "tfidf_sem_pontuacao": "TF-IDF sem pontuação", "tfidf_sem_stopwords": "TF-IDF sem stopwords",
    "word2vec_cbow": "Word2Vec CBOW", "word2vec_skipgram": "Word2Vec skip-gram",
    "bert_base_pt": "BERT (BERTimbau)", "sentenca_minilm": "BERT de sentença (MiniLM)",
    "combinacao": "Combinação do site (0,3 TF-IDF + 0,7 MiniLM)", "maioria": "Referência (classe mais frequente)",
}
GENRE_COLORS = {"Drama": "#4C78A8", "Comédia": "#F2A541", "Terror": "#E45756", "Ficção científica": "#8E6CC8"}
CLUSTER_COLORS = ["#4C78A8", "#F2A541", "#E45756", "#59A14F", "#8E6CC8", "#9C755F"]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def n(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%".replace(".", ",")


# ---------------------------------------------------------------- figuras

def figures(sweep: dict, results: dict, classification: dict, sentiment: dict, ner: dict) -> dict[str, Path]:
    FIG.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    paths = {}

    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    for name in REPRESENTATIONS:
        rows = sweep[name]
        ks = [r["k"] for r in rows]
        style = "-" if name in ("bert_base_pt", "sentenca_minilm", "word2vec_skipgram") else "--"
        axes[0].plot(ks, [r["silhueta_cosseno"] for r in rows], style, marker="o", ms=3, label=LABEL[name])
        axes[1].plot(ks, [r["davies_bouldin"] for r in rows], style, marker="o", ms=3)
        axes[2].plot(ks, [r["ari"] for r in rows], style, marker="o", ms=3)
    for ax, title in zip(axes, ["Silhueta (cosseno) — maior é melhor", "Davies-Bouldin — menor é melhor", "ARI contra os gêneros — maior é melhor"], strict=True):
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("k (número de clusters)")
        ax.set_xticks(range(2, 11))
    axes[1].set_yscale("log")
    fig.legend(loc="lower center", ncol=4, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    paths["varredura"] = FIG / "fig1_varredura_k.png"
    fig.savefig(paths["varredura"], dpi=200)
    plt.close(fig)

    projection = load(DATA / "representacoes" / "tmdb_2026-09-12" / "projection.json")
    clustering = load(DATA / "representacoes" / "tmdb_2026-09-12" / "clustering.json")
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    for row, name in enumerate(["tfidf_sem_stopwords", "bert_base_pt"]):
        points = projection[name]["points"]
        xs, ys = [p["x"] for p in points], [p["y"] for p in points]
        ax = axes[row][0]
        ax.scatter(xs, ys, c=[GENRE_COLORS.get(p["genre"], "#BBBBBB") for p in points], s=10, alpha=0.8)
        ax.set_title(f"{LABEL[name]}: cor = gênero do TMDB", fontsize=9)
        for genre, color in GENRE_COLORS.items():
            ax.scatter([], [], c=color, s=12, label=genre)
        ax.scatter([], [], c="#BBBBBB", s=12, label="vários gêneros")
        ax.legend(fontsize=7, frameon=False)
        ax = axes[row][1]
        assignments = clustering[name]["assignments"]
        ax.scatter(xs, ys, c=[CLUSTER_COLORS[c] for c in assignments], s=10, alpha=0.8)
        ax.set_title(f"{LABEL[name]}: cor = cluster do K-Means (k = 4)", fontsize=9)
        for cluster in range(clustering[name]["k"]):
            ax.scatter([], [], c=CLUSTER_COLORS[cluster], s=12, label=f"Cluster {cluster}")
        ax.legend(fontsize=7, frameon=False)
        for ax in axes[row]:
            ax.set_xticks([])
            ax.set_yticks([])
    fig.tight_layout()
    paths["projecao"] = FIG / "fig2_projecao_tfidf_bert.png"
    fig.savefig(paths["projecao"], dpi=200)
    plt.close(fig)

    precision = results["busca"]["precisao"]
    names = [*REPRESENTATIONS, "combinacao"]
    fig, ax = plt.subplots(figsize=(10, 3.6))
    xs = range(len(names))
    ax.bar([x - 0.2 for x in xs], [precision[k]["p@3"] for k in names], 0.4, label="Precisão @3", color="#4C78A8")
    ax.bar([x + 0.2 for x in xs], [precision[k]["p@5"] for k in names], 0.4, label="Precisão @5", color="#F2A541")
    ax.set_xticks(list(xs), [LABEL[k].replace(" (", "\n(") for k in names], fontsize=7)
    ax.set_ylim(0, 1)
    ax.legend(frameon=False)
    ax.set_title("Busca: fração de filmes relevantes entre os 3 e os 5 primeiros (média de 20 consultas)", fontsize=9)
    fig.tight_layout()
    paths["busca"] = FIG / "fig3_busca_precisao.png"
    fig.savefig(paths["busca"], dpi=200)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    cv = classification["multiclasse"]
    axes[0].barh([LABEL[k] for k in REPRESENTATIONS], [cv[k]["f1_macro"] for k in REPRESENTATIONS], color="#4C78A8")
    axes[0].axvline(cv["maioria"]["f1_macro"], color="#999999", ls="--", label="referência")
    axes[0].set_xlim(0, 1)
    axes[0].set_title("Classificação de gênero: F1 macro (validação cruzada)", fontsize=9)
    axes[0].legend(frameon=False, fontsize=7)
    new = results["dados_novos"]
    groups = ["tfidf_sem_stopwords", "sentenca_minilm"]
    axes[1].bar([0, 1], [cv[k]["f1_macro"] for k in groups], 0.35, label="Validação cruzada na amostra (325)", color="#4C78A8")
    axes[1].bar([0.38, 1.38], [new[k]["f1_macro"] for k in groups], 0.35, label=f"Dados novos do catálogo ({new['sentenca_minilm']['teste']})", color="#E45756")
    axes[1].set_xticks([0.19, 1.19], [LABEL[k] for k in groups])
    axes[1].set_ylim(0, 1)
    axes[1].set_title("Mesmo classificador em sinopses nunca vistas", fontsize=9)
    axes[1].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    paths["classificacao"] = FIG / "fig4_classificacao.png"
    fig.savefig(paths["classificacao"], dpi=200)
    plt.close(fig)

    polarity = sentiment["polaridade"]
    fig, ax = plt.subplots(figsize=(10, 3.4))
    order = sorted(REPRESENTATIONS, key=lambda k: -polarity[k]["f1_macro"])
    xs = range(len(order))
    ax.bar([x - 0.2 for x in xs], [polarity[k]["f1_macro"] for k in order], 0.4, label="Validação cruzada (dobras por filme)", color="#59A14F")
    ax.bar([x + 0.2 for x in xs], [polarity[k]["entre_autores"]["treino_sem_autor_principal"]["f1_macro"] for k in order], 0.4, label="Treino sem o autor principal → teste nele", color="#E45756")
    ax.axhline(polarity["maioria"]["f1_macro"], color="#999999", ls="--", label="referência (sempre positivo)")
    ax.set_xticks(list(xs), [LABEL[k].replace(" (", "\n(") for k in order], fontsize=7)
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    ax.set_title("Análise de sentimentos: F1 macro da polaridade (1.422 críticas)", fontsize=9)
    fig.tight_layout()
    paths["sentimento"] = FIG / "fig5_sentimento.png"
    fig.savefig(paths["sentimento"], dpi=200)
    plt.close(fig)

    categories = ner["categorias_das_mencoes"]
    labels_pt = {"PER": "PER (pessoa)", "LOC": "LOC (lugar)", "MISC": "MISC (outros)", "ORG": "ORG", "nao_reconhecida": "não reconhecida"}
    keys = ["PER", "LOC", "MISC", "ORG", "nao_reconhecida"]
    fig, ax = plt.subplots(figsize=(7, 2.6))
    ax.barh([labels_pt[k] for k in keys][::-1], [categories[k] for k in keys][::-1], color=["#BBBBBB", "#9C755F", "#F2A541", "#59A14F", "#4C78A8"])
    for y, k in enumerate(keys[::-1]):
        ax.text(categories[k] + 5, y, str(categories[k]), va="center", fontsize=8)
    ax.set_title(f"NER: categoria dada aos {ner['mencoes_creditadas']} nomes de personagens/atores dos créditos", fontsize=9)
    fig.tight_layout()
    paths["ner"] = FIG / "fig6_ner_creditos.png"
    fig.savefig(paths["ner"], dpi=200)
    plt.close(fig)
    return paths


# ---------------------------------------------------------------- documento

MARKUP = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")


def add_runs(paragraph, text: str, bold: bool = False, italic: bool = False, size: float | None = None) -> None:
    """Texto com **negrito** e *itálico*."""
    for part in MARKUP.split(text):
        if not part:
            continue
        strong, emphasis = part.startswith("**") and part.endswith("**"), not part.startswith("**") and part.startswith("*") and part.endswith("*") and len(part) > 1
        content = part[2:-2] if strong else part[1:-1] if emphasis else part
        run = paragraph.add_run(content)
        run.bold = bold or strong
        run.italic = italic or emphasis
        if size:
            run.font.size = Pt(size)


def shade(cell, color: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    element = OxmlElement("w:shd")
    element.set(qn("w:val"), "clear")
    element.set(qn("w:color"), "auto")
    element.set(qn("w:fill"), color)
    properties.append(element)


class Writer:
    def __init__(self) -> None:
        self.doc = Document()
        section = self.doc.sections[0]
        section.page_width, section.page_height = Cm(21), Cm(29.7)
        for side in ("left_margin", "right_margin"):
            setattr(section, side, Cm(2.2))
        section.top_margin = section.bottom_margin = Cm(2)
        style = self.doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(10.5)
        style.paragraph_format.space_after = Pt(4)
        self.figure_number = 0
        self.table_number = 0

    def p(self, text: str = "", bold: bool = False, align=None, size: float | None = None, italic: bool = False):
        paragraph = self.doc.add_paragraph()
        add_runs(paragraph, text, bold, italic, size)
        if align is not None:
            paragraph.alignment = align
        return paragraph

    def h(self, text: str, level: int = 1) -> None:
        heading = self.doc.add_heading(text, level=level)
        for run in heading.runs:
            run.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)

    def bullets(self, items: list[str]) -> None:
        for item in items:
            paragraph = self.doc.add_paragraph(style="List Bullet")
            add_runs(paragraph, item)

    def table(self, header: list[str], rows: list[list[str]], widths: list[float], caption: str | None = None, size: float = 8.5) -> None:
        if caption:
            self.table_number += 1
            self.p(f"Tabela {self.table_number} — {caption}", bold=True, size=9)
        table = self.doc.add_table(rows=1, cols=len(header))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for index, text in enumerate(header):
            cell = table.rows[0].cells[index]
            cell.text = ""
            run = cell.paragraphs[0].add_run(text)
            run.bold = True
            run.font.size = Pt(size)
            shade(cell, "DCE6F0")
        for values in rows:
            cells = table.add_row().cells
            for index, text in enumerate(values):
                cells[index].text = ""
                add_runs(cells[index].paragraphs[0], str(text), size=size)
        for row in table.rows:
            for index, width in enumerate(widths):
                row.cells[index].width = Cm(width)
        self.doc.add_paragraph()

    def figure(self, path: Path, caption: str, width: float = 16.5) -> None:
        self.figure_number += 1
        self.doc.add_picture(str(path), width=Cm(width))
        self.doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.p(f"Figura {self.figure_number} — {caption}", italic=True, size=8.5, align=WD_ALIGN_PARAGRAPH.CENTER)

    def code(self, source: str, caption: str) -> None:
        self.p(caption, bold=True, size=9)
        table = self.doc.add_table(rows=1, cols=1)
        cell = table.rows[0].cells[0]
        shade(cell, "F3F3F3")
        cell.text = ""
        paragraph = cell.paragraphs[0]
        lines = source.rstrip("\n").split("\n")
        for index, line in enumerate(lines):
            run = paragraph.add_run(line)
            run.font.name = "Consolas"
            run.font.size = Pt(7.5)
            if index < len(lines) - 1:
                run.add_break()
        cell.width = Cm(16.5)
        self.doc.add_paragraph()


def source_of(obj, start: str | None = None, end: str | None = None) -> str:
    text = inspect.getsource(obj)
    lines = text.split("\n")
    if start:
        lines = lines[next(i for i, line in enumerate(lines) if start in line):]
    if end:
        lines = lines[: next(i for i, line in enumerate(lines) if end in line) + 1]
    indent = min(len(line) - len(line.lstrip()) for line in lines if line.strip())
    return "\n".join(line[indent:] for line in lines)


def main() -> None:
    from app.entities.extraction import relations
    from app.search.hybrid import HybridIndex
    from app.search.query import strip_request
    from app.sentiment.evaluation import grouped_folds

    sweep = load(DATA / "agrupamento" / "tmdb_2026-09-12" / "sweep.json")
    results = load(HERE / "resultados.json")
    classification = load(DATA / "classificacao" / "tmdb_2026-09-12" / "results.json")
    alternatives = load(DATA / "classificacao" / "tmdb_2026-09-12" / "alternatives.json")
    sentiment = load(DATA / "sentimento" / "criticas_2026-10-10" / "results.json")
    sentiment_data = load(DATA / "sentimento" / "criticas_2026-10-10" / "dataset.json")
    entities_stats = load(DATA / "entidades" / "tmdb_2026-09-12" / "statistics.json")
    ner = load(DATA / "entidades" / "tmdb_2026-09-12" / "credits_summary.json")
    review = load(REPO / "config" / "entidades" / "conferencia_relacoes.json")
    paths = figures(sweep, results, classification, sentiment, ner)
    w = Writer()

    for line in ["UNIVERSIDADE REGIONAL DE BLUMENAU", "CENTRO DE CIÊNCIAS EXATAS E NATURAIS", "CURSO DE CIÊNCIA DA COMPUTAÇÃO", "Processamento de Linguagem Natural — 2026/2"]:
        w.p(line, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    w.p("")
    w.p("Trabalho da Unidade 3", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=14)
    w.p("Sinopses e críticas de filmes do TMDB: representações textuais e tarefas de PLN", align=WD_ALIGN_PARAGRAPH.CENTER, italic=True)
    w.p("Equipe: Kaike Ventura Tuerpe, Luana Nitsche, Pedro Henrique Ortunio e Thiago Bodnar", align=WD_ALIGN_PARAGRAPH.CENTER)
    w.p("")
    w.h("Dados e onde está cada coisa no repositório", 1)
    w.bullets([
        "**Amostra avaliada:** 430 filmes do TMDB (4 gêneros × 3 períodos), dos quais **428 têm sinopse em português**. Todas as métricas de agrupamento, busca, recomendação e classificação foram calculadas nessa amostra, como o enunciado permite, porque ler e anotar milhares de sinopses à mão é inviável.",
        "**Catálogo do site:** 5.525 sinopses de 18 gêneros, coletadas pelo mesmo pipeline. Ele é usado pela busca e pela recomendação do site e, neste trabalho, como **dados novos** para testar o classificador (questão 4).",
        "**Críticas:** 1.859 críticas de usuários em português, com a nota que o autor deu ao filme (questão 5).",
        "**Oito representações:** BoW e TF-IDF, cada um sem pontuação e sem stopwords; Word2Vec CBOW e skip-gram (NILC); BERTimbau; e um BERT de sentença (paraphrase-multilingual-MiniLM).",
        "**Código:** backend/src/app/, uma pasta por tarefa. **Resultados:** data/, cada pasta com manifesto e hashes SHA-256. **Este documento e os scripts que o geram:** docs/entregas/unidade-3/. Para rodar o site: docs/tecnico/rodar-o-site.md.",
    ])

    # 1
    w.h("1) Atividades realizadas", 1)
    check = "✔"
    w.table(
        ["", "BoW", "TF-IDF", "Word2Vec", "BERT"],
        [
            ["Clusterização + PCA e visualização", check, check, check, check],
            ["Busca e recomendação", check, check, check, check],
            ["Classificação", check, check, check, check],
        ],
        [4.4, 3, 3, 3, 3],
        size=10,
    )
    w.p("Observações sobre a tabela:")
    w.bullets([
        "**Variantes:** BoW e TF-IDF foram testados sem pontuação e sem stopwords. Word2Vec, em CBOW e skip-gram. BERT, em dois modelos: o BERTimbau (BERT pré-treinado em português) e um BERT de sentença (MiniLM), treinado para comparar frases.",
        "**PCA:** a projeção 2D usa TruncatedSVD, o equivalente ao PCA para matrizes esparsas, que nas lexicais é a LSA. Ela foi aplicada a todas as representações.",
        "**Classificação:** os rótulos vieram prontos, os gêneros que o TMDB atribui a cada filme. Além da regressão logística, testamos Naive Bayes, SVM, floresta aleatória e kNN, e um modelo de linguagem sem treino, o Jev.",
    ])
    w.table(
        ["Tarefa", "Situação"],
        [
            ["Análise de sentimento", "(X) Foi realizada   ( ) Não foi realizada"],
            ["Reconhecimento de Entidades Nomeadas", "(X) Foi realizado   ( ) Não foi realizado"],
            ["Extração de Relações", "(X) Foi realizada   ( ) Não foi realizada"],
        ],
        [7.4, 9],
        size=10,
    )

    # 2
    w.h("2) Clusters: qual representação e quantos clusters", 1)
    w.p(
        "Aplicamos o K-Means (k-means++, 10 inicializações, semente fixa) às linhas com norma L2 de cada uma das oito representações, para k de 2 a 10. "
        "Medimos a forma dos grupos com métricas **intracluster** (distância de cosseno média de cada sinopse ao centroide do próprio grupo) e **intercluster** "
        "(distância de cosseno média entre os centroides), além de três índices que combinam as duas: a silhueta, o Davies-Bouldin e o Calinski-Harabasz. "
        "Também comparamos os grupos com os gêneros do TMDB (ARI, NMI e pureza), usando os 325 filmes de um único gênero. "
        "Código: backend/src/app/clustering/sweep.py; resultados: data/agrupamento/tmdb_2026-09-12/."
    )
    w.figure(paths["varredura"], "Varredura de k: as métricas internas (silhueta e Davies-Bouldin) e a concordância com os gêneros (ARI).")
    rows = []
    for name in REPRESENTATIONS:
        r = next(row for row in sweep[name] if row["k"] == 4)
        rows.append([LABEL[name], n(r["distancia_ao_centroide"]), n(r["distancia_entre_centroides"]), n(r["silhueta_cosseno"]), n(r["davies_bouldin"], 2), n(r["calinski_harabasz"], 1), n(r["ari"]), pct(r["pureza"])])
    w.table(
        ["Representação", "Intra: dist. ao centroide", "Inter: dist. entre centroides", "Silhueta", "Davies-Bouldin", "Calinski-Harabasz", "ARI", "Pureza"],
        rows,
        [3.6, 1.9, 1.9, 1.5, 1.7, 1.9, 1.4, 1.5],
        "Métricas com k = 4 (o número de gêneros da coleta)",
        size=8,
    )
    w.p("**Interpretação das métricas intra e intercluster:**")
    w.bullets([
        "**Não há grupos naturais bem separados.** A silhueta fica abaixo de 0,10 em todas as representações: as sinopses formam uma nuvem contínua, e não ilhas. Nas lexicais (BoW e TF-IDF), a silhueta é praticamente zero (0,001 a 0,033 com k = 4) e o Davies-Bouldin é alto (5,1 a 13,5), contra cerca de 4 nas densas. Com vetores esparsos de milhares de dimensões, quase todas as sinopses ficam a distâncias parecidas umas das outras.",
        "**As distâncias só se comparam dentro de uma mesma representação.** O BERTimbau tem grupos compactos (distância ao centroide de 0,082), mas centroides próximos entre si (0,024): os vetores dele ocupam uma região estreita do espaço. O MiniLM tem distâncias maiores nos dois sentidos (0,450 e 0,276). Por isso não comparamos representações pela distância absoluta, e sim pela silhueta e pelo Davies-Bouldin, que são relativos.",
        "**As métricas internas se contradizem sobre k.** A silhueta e o Calinski-Harabasz preferem k = 2 em quase todas as representações, e o Davies-Bouldin melhora sempre com mais grupos (melhor k = 8 a 10). Isso é típico quando não há estrutura forte: dividir em dois maximiza a separação, e dividir em muitos reduz a dispersão dentro de cada grupo. As métricas internas, sozinhas, não indicam o número de grupos.",
        "**Também não há cotovelo na inércia.** A cada k a mais, a inércia cai só 0,3% no TF-IDF e de 1% a 3% nas densas, de forma suave, sem um ponto em que a queda pare de repente.",
    ])
    w.figure(paths["projecao"], "Projeção 2D (TruncatedSVD) das 428 sinopses, colorida pelo gênero (esquerda) e pelo cluster com k = 4 (direita). Em cima, TF-IDF sem stopwords; embaixo, BERTimbau.", width=15)
    bert4 = next(row for row in sweep["bert_base_pt"] if row["k"] == 4)
    bert5 = next(row for row in sweep["bert_base_pt"] if row["k"] == 5)
    tfidf4 = next(row for row in sweep["tfidf_sem_stopwords"] if row["k"] == 4)
    w.p("**Leitura dos grupos.** Para cada grupo, listamos os termos de maior peso médio no TF-IDF e os três filmes mais próximos do centroide:")
    w.table(
        ["Grupo (BERTimbau, k = 4)", "Tamanho", "Termos mais característicos", "Filmes mais próximos do centroide"],
        [[f"Grupo {i}", str(g["tamanho"]), ", ".join(g["termos"][:6]), "; ".join(g["mais_proximos"])] for i, g in enumerate(bert4["grupos"])],
        [3.2, 1.6, 5.5, 6.2],
        "Grupos do BERTimbau com k = 4",
        size=8,
    )
    w.bullets([
        "**BERTimbau, k = 4:** os grupos têm tema claro. São eles: **ameaça coletiva** (terror e ficção científica, com \"grupo\", \"vírus\", \"missão\"); **super-heróis** (\"Peter\", \"vilão\", *Thor*, *Vingadores*); **família, casa e amigos** (comédia e drama, como *Up*); e **drama de polícia, prisão e guerra** (*Um Sonho de Liberdade*). Um grupo é dominado pelo drama (61 dos 98 filmes), e outro mistura terror (50) e ficção científica (45).",
        f"**BERTimbau, k = 5:** o grupo de ameaça coletiva se divide em **fim do mundo** ({'; '.join(bert5['grupos'][0]['mais_proximos'])}) e **terror de grupo** ({'; '.join(bert5['grupos'][1]['mais_proximos'])}), uma divisão que faz sentido para quem lê as sinopses. Com k = 5, o ARI se mantém em 0,144, e a pureza sobe de 48,9% para 52,6%.",
        f"**TF-IDF sem stopwords, k = 4:** os grupos seguem palavras isoladas: um de \"morte\" e \"família\" ({'; '.join(tfidf4['grupos'][0]['mais_proximos'])}), um de \"amor\" e \"juntos\" (romances) e um de \"casa\" e \"amigos\". Os temas são legíveis, mas cortam os gêneros ao acaso (ARI de 0,024), e a projeção 2D é uma única nuvem, sem regiões de cor.",
    ])
    w.p(
        f"**Conclusão.** O **BERTimbau** gerou os clusters mais representativos, com o maior ARI (0,144), a maior pureza e grupos com temas reconhecíveis na leitura. "
        f"O MiniLM vem em segundo (ARI de {n(next(r for r in sweep['sentenca_minilm'] if r['k'] == 9)['ari'])} com k = 9), e as lexicais quase não se relacionam com os gêneros. "
        "A quantidade que melhor expressou as características originais dos dados foi **k = 4 a 5**: o ARI do BERTimbau tem o pico nesses dois valores, e k = 4 coincide com os quatro gêneros da coleta. "
        "Ainda assim, os grupos refletem mais o **tema da história** (ameaça, heróis, família, polícia) do que o gênero, e a semelhança com os gêneros é fraca. "
        "Para separar gêneros, a classificação supervisionada (questão 4) é muito melhor: com o mesmo BERTimbau, o ARI sobe de 0,13 para 0,37."
    )

    # 3
    w.h("3) Busca: qualidade dos top-3 e top-5", 1)
    w.p(
        "Escrevemos 20 consultas como um usuário digitaria e marcamos os filmes relevantes de cada uma **lendo as 428 sinopses antes de rodar qualquer algoritmo**. "
        "Para cada representação, a busca ordena as sinopses pelo cosseno com a consulta. A combinação usada no site soma 0,3 × o cosseno do TF-IDF e 0,7 × o do MiniLM, "
        "cada um dividido pelo maior cosseno da própria representação."
    )
    w.figure(paths["busca"], "Precisão @3 e @5 média nas 20 consultas anotadas.")
    precision = results["busca"]["precisao"]
    w.table(
        ["Representação", "Precisão @3", "Precisão @5"],
        [[LABEL[k], pct(precision[k]["p@3"]), pct(precision[k]["p@5"])] for k in [*REPRESENTATIONS, "combinacao"]],
        [8, 3.5, 3.5],
        "Precisão nos 3 e nos 5 primeiros (média das 20 consultas)",
    )
    consultas = {q["id"]: q for q in results["busca"]["consultas"]}
    top = results["busca"]["top5"]
    for qid, comment in [
        ("astronautas_perdidos", "Tema concreto, com palavras que aparecem nas sinopses."),
        ("casa_assombrada", "Tema concreto de terror."),
        ("matrix_simulacao", "Tema abstrato: só Matrix é relevante, e nenhuma sinopse fala em \"simulação da realidade\"."),
        ("comedia_romantica", "Tom e gênero, difíceis para o ranking."),
    ]:
        query = consultas[qid]
        relevant = set(query["relevantes"])
        rows = []
        for name in ["tfidf_sem_stopwords", "word2vec_skipgram", "bert_base_pt", "sentenca_minilm", "combinacao"]:
            items = top[name][qid]
            rows.append([LABEL[name], "; ".join(("✔ " if t["id"] in relevant else "✗ ") + t["title"] for t in items)])
        w.table(["Representação", "5 primeiros (✔ = relevante)"], rows, [4.2, 12.3], f"Consulta \"{query['texto']}\" ({len(relevant)} relevantes). {comment}", size=8)
    w.p("**Análise crítica:**")
    w.bullets([
        "**Temas concretos funcionam bem.** Em \"astronautas perdidos no espaço\", o MiniLM acerta 4 dos 5 primeiros, e a combinação também (*O Enigma do Horizonte*, *Interestelar*, *Aliens*, *Alien: Romulus*). Em \"casa assombrada\", o TF-IDF acerta 4 de 5 (*Invocação do Mal* 1 e 2, *Os Outros*, *Sobrenatural*), porque as sinopses usam as mesmas palavras da consulta. O BERTimbau acerta 3, mas erra com *Um Lugar Silencioso*, que é terror sem casa assombrada.",
        "**Temas abstratos e de tom falham.** Em \"filme sobre simulação da realidade\", as lexicais trazem *O Dublê* e *Anaconda*, que só têm a palavra \"filme\" em comum. O MiniLM põe *Matrix* em 2º, depois de *Free Guy*, que se passa num jogo simulado e provavelmente é relevante, embora não tenha sido anotado. Em \"comédia romântica leve\", todos erram quase tudo: o tom \"leve\" não está escrito nas sinopses.",
        "**Cada família de representação erra de um jeito.** O TF-IDF exige a palavra exata, e \"possessão demoníaca e exorcismo\" devolve só 2 filmes, os únicos com essas palavras. O MiniLM entende paráfrases, mas às vezes troca o tema por um vizinho. O BERTimbau e o Word2Vec, que fazem a média de vetores de palavras ou de tokens, ficam com a pior precisão: o vetor médio perde o sentido da frase, e o BERTimbau não foi treinado para comparar frases.",
        "**Utilizável num contexto real?** Para temas concretos, sim: na combinação, **70% dos 3 primeiros são relevantes**, e em 100% das consultas há ao menos um relevante entre os 5 primeiros. Para uma busca de produto, falta uma nota mínima, porque hoje a página sempre é completada com filmes pouco relacionados. Também falta tratar tom e gênero, o que no site é feito pelas regras de filtro, e não pelo ranking.",
        "**Combinação e melhorias feitas.** Primeiro testamos as combinações de 2 a 4 representações, com pesos e por posição (RRF). Escolhemos 0,3 × TF-IDF + 0,7 × MiniLM, que junta a palavra exata com o sentido, e o MAP subiu de 0,560 (MiniLM sozinho) para 0,613. Depois, a consulta passou a perder as palavras de pedido (\"quero\", \"filmes sobre\") e a recuperar acentos (\"saude\" → \"saúde\"), e o MAP foi a 0,627. No site, a busca procura num catálogo de 5.525 filmes, e regras extraem gênero, período e nota da frase como filtros.",
        "**Melhorias possíveis:** uma nota mínima calibrada nas consultas anotadas, um modelo de sentença maior, a busca também por elenco e diretor, e a avaliação com usuários reais, já que as 20 consultas foram escritas e julgadas pela própria equipe.",
    ])
    w.code(source_of(HybridIndex.rank), "Trecho de código — combinação das representações (backend/src/app/search/hybrid.py)")
    w.p(f"Exemplo da limpeza da consulta: \"filmes sobre saude mental\" → \"{strip_request('filmes sobre saude mental')}\" (e o acento é recuperado pelo vocabulário: \"saúde mental\").", size=9)
    w.p(
        "**Recomendação.** Na mesma amostra, a recomendação mostra os 5 filmes de sinopse mais parecida. A precisão @5 por gênero foi de 63,6% (BERTimbau) contra 37,9% ao acaso. "
        "No site, a ficha de cada filme mostra os 5 parecidos no catálogo: *Matrix* → *13º Andar* e as continuações de *Matrix*; *Toy Story* → *Lightyear*, *Toy Story 3*."
    )

    # 4
    w.h("4) Classificação", 1)
    w.p(
        "**Sim, foi possível treinar um classificador.** Os rótulos vieram prontos: os gêneros que o TMDB atribui a cada filme, entre Drama, Comédia, Terror e Ficção científica. "
        "Montamos duas tarefas: **multiclasse**, com as 325 sinopses de um único gênero, e **multirrótulo**, com todas as que têm algum dos quatro gêneros. "
        "Cada representação alimenta uma regressão logística com classes de peso balanceado. O parâmetro C é escolhido dentro do próprio treino, e a avaliação usa validação cruzada em 5 dobras."
    )
    mc, ml = classification["multiclasse"], classification["multirrotulo"]
    alt_rows = []
    for name in REPRESENTATIONS:
        a = alternatives[name]
        alt_rows.append([
            LABEL[name], pct(mc[name]["f1_macro"]), pct(ml[name]["f1_macro"]),
            pct(a["naive_bayes"]["f1_macro"]) if a.get("naive_bayes") else "—",
            pct(a["svm_linear"]["f1_macro"]), pct(a["floresta_aleatoria"]["f1_macro"]), pct(a["knn"]["f1_macro"]),
        ])
    alt_rows.insert(0, [LABEL["maioria"], pct(mc["maioria"]["f1_macro"]), pct(ml["maioria"]["f1_macro"]), "—", "—", "—", "—"])
    w.table(
        ["Representação", "Reg. logística (multiclasse)", "Reg. logística (multirrótulo)", "Naive Bayes", "SVM linear", "Floresta aleatória", "kNN"],
        alt_rows,
        [4.2, 2.2, 2.2, 1.9, 1.9, 2.1, 1.6],
        "F1 macro na validação cruzada (multiclasse: 325 sinopses; multirrótulo: todas com algum dos 4 gêneros)",
        size=8,
    )
    w.figure(paths["classificacao"], "À esquerda, F1 macro de cada representação. À direita, o mesmo classificador aplicado a sinopses que ele nunca viu.")
    new = results["dados_novos"]
    minilm, tfidf = new["sentenca_minilm"], new["tfidf_sem_stopwords"]
    w.p("**Comportamento com dados novos.** Testamos o classificador em **dados novos**, que ele nunca viu no treino:")
    w.bullets([
        f"**Filmes do catálogo fora da amostra.** O classificador foi treinado nas 325 sinopses da amostra e aplicado às **{minilm['teste']} sinopses do catálogo do site que não estão na amostra** e têm um único dos quatro gêneros. "
        f"Com o MiniLM, a acurácia foi de **{pct(minilm['acuracia'])}** e o F1 macro de **{pct(minilm['f1_macro'])}**, contra {pct(mc['sentenca_minilm']['f1_macro'])} na validação cruzada. "
        f"Com o TF-IDF, os valores foram {pct(tfidf['acuracia'])} e {pct(tfidf['f1_macro'])}, contra {pct(mc['tfidf_sem_stopwords']['f1_macro'])}. "
        "A queda é moderada (6 a 7 pontos) e esperada: o catálogo é mais variado, com filmes menos populares e de outros gêneros secundários, e o TF-IDF sofre mais porque muitas palavras novas ficam fora do vocabulário do treino.",
        f"**F1 por gênero nos dados novos (MiniLM):** {', '.join(f'{g} {pct(v)}' for g, v in minilm['f1_por_genero'].items())}. Nos dados novos, terror e comédia são os mais difíceis; na validação cruzada, a comédia era o pior.",
        "**Na tela do site,** a aba \"Classificar sinopse\" classifica qualquer texto digitado.",
    ])
    w.p("**Alguma representação favorece classificações mais precisas?** Sim:")
    w.bullets([
        f"**As densas pré-treinadas vencem as lexicais:** Word2Vec skip-gram ({pct(mc['word2vec_skipgram']['f1_macro'])}) e BERTimbau ({pct(mc['bert_base_pt']['f1_macro'])}) ficam cerca de 11 pontos acima do TF-IDF ({pct(mc['tfidf_sem_stopwords']['f1_macro'])}). Com só 325 exemplos, o vocabulário do treino é pequeno, e os vetores pré-treinados trazem conhecimento de fora: \"fantasma\" e \"espírito\" ficam próximos, mesmo sem aparecer juntos no treino.",
        "**Skip-gram e BERTimbau empatam** dentro da variação entre as dobras. O MiniLM fica um pouco abaixo, mas foi o escolhido para a tela porque o site já o carrega para a busca.",
        "**Remover stopwords ajuda o BoW** (de 46,1% para 56,4%), mas quase não muda o TF-IDF, cujo idf já reduz o peso das palavras comuns.",
    ])
    w.p("**Modelos de linguagem e modelos de decisão.** Usamos os dois:")
    w.bullets([
        "**Modelo de linguagem sem treino (Jev, da TypeSafe AI, Aula 8):** o Jev recebe a sinopse e perguntas tipadas (\"qual é o gênero principal?\" e \"este filme é de terror?\"), sem ver nenhum exemplo rotulado. Nos mesmos 120 filmes, acertou **85,0%** do gênero principal, contra 56,0% do TF-IDF com regressão logística treinado no restante da amostra. Ele é bem melhor, mas cada classificação é uma chamada paga a um serviço externo. Por isso o site usa a regressão logística.",
        "**Modelos de decisão:** além da regressão logística, comparamos Naive Bayes, SVM linear, **floresta aleatória** (um conjunto de árvores de decisão) e kNN nas mesmas dobras (Tabela acima). A floresta aleatória ficou abaixo da regressão logística em sete das oito representações; só no MiniLM ficou ligeiramente acima (66,9% contra 66,1%). Com centenas de exemplos e centenas ou milhares de dimensões, as árvores dividem os dados em regiões pequenas demais e tendem a generalizar pior que um classificador linear. O Naive Bayes, por outro lado, foi o melhor no BoW (61,3% contra 56,4%), porque modela diretamente contagens de palavras.",
        "**Representações de modelos de linguagem:** o BERTimbau e o MiniLM são modelos de linguagem usados como extratores de vetores (congelados), com a regressão logística por cima.",
    ])

    # 5
    w.h("5) Análise de sentimentos, NER e extração de relações", 1)
    w.p("**Sim, as três se aplicam,** mas a dados diferentes:")
    w.bullets([
        "**Análise de sentimentos:** as **sinopses** não têm opinião, então não há sentimento a medir nelas. Por isso coletamos as **críticas de usuários do TMDB**, que vêm com a nota de 0 a 10 que o próprio autor deu ao filme. Isso dá texto e rótulo juntos, sem anotação manual, como havíamos proposto na Unidade 1.",
        "**NER e relações:** as sinopses são ricas em nomes de personagens, lugares e organizações, e descrevem ações (\"Andy Dufresne é condenado por um crime\"). Usamos o spaCy pt_core_news_sm e as regras de dependência do notebook da Aula 9.",
    ])
    w.h("Análise de sentimentos", 2)
    polarity, rating = sentiment["polaridade"], sentiment["nota"]
    w.p(
        f"Foram {sentiment_data['reviews']} críticas em português, de {sentiment_data['movies']} filmes. As críticas com nota ≤ 4 são negativas ({sentiment_data['polarity']['negativo']}), "
        f"as com nota ≥ 7 são positivas ({sentiment_data['polarity']['positivo']}), e as do meio ficam só na previsão da nota. "
        "Testamos as oito representações com regressão logística (polaridade) e Ridge (nota), em 5 dobras, mantendo as críticas de um mesmo filme na mesma dobra. "
        "Os transformers leem a crítica inteira, em partes que cabem no modelo."
    )
    w.figure(paths["sentimento"], "F1 macro da polaridade: validação cruzada e teste entre autores.")
    w.table(
        ["Representação", "F1 macro", "Acurácia", "Erro médio da nota", "Treino sem o autor principal → teste nele"],
        [[LABEL["maioria"], pct(polarity["maioria"]["f1_macro"]), pct(polarity["maioria"]["acuracia"]), n(rating["media_do_treino"]["erro_absoluto_medio"], 2) + " (média)", "—"]]
        + [
            [LABEL[k], pct(polarity[k]["f1_macro"]), pct(polarity[k]["acuracia"]), n(rating[k]["erro_absoluto_medio"], 2), pct(polarity[k]["entre_autores"]["treino_sem_autor_principal"]["f1_macro"])]
            for k in sorted(REPRESENTATIONS, key=lambda k: -polarity[k]["f1_macro"])
        ],
        [4.6, 2.2, 2.2, 3, 4.5],
        "Polaridade e nota prevista das críticas",
        size=8,
    )
    w.bullets([
        f"**O BERTimbau é o melhor** (F1 macro de {pct(polarity['bert_base_pt']['f1_macro'])}; erra a nota em {n(rating['bert_base_pt']['erro_absoluto_medio'], 2)} ponto em média). O TF-IDF fica logo atrás ({pct(polarity['tfidf_sem_stopwords']['f1_macro'])}): em críticas, palavras de opinião como \"excelente\", \"gostei\", \"pior\" e \"desinteressante\" já carregam boa parte do sentimento.",
        f"**Um autor escreveu {pct(sentiment_data['main_author_share'], 0)} das críticas.** Treinando sem ele e testando nele, o TF-IDF cai para {pct(polarity['tfidf_sem_stopwords']['entre_autores']['treino_sem_autor_principal']['f1_macro'])}, e o BERTimbau mantém {pct(polarity['bert_base_pt']['entre_autores']['treino_sem_autor_principal']['f1_macro'])}. O TF-IDF decora o vocabulário de quem mais escreve; os vetores pré-treinados generalizam para outras pessoas.",
        f"**Negação atrapalha todas as representações.** No TF-IDF, a acurácia é de {pct(polarity['tfidf_sem_stopwords']['negacao']['com']['acuracia'])} nas críticas com \"não\", \"nem\", \"nunca\" ou \"sem\", e de {pct(polarity['tfidf_sem_stopwords']['negacao']['sem']['acuracia'])} nas sem. Na tela do site, \"Não é um filme ruim…\" sai negativo, e a ironia \"Ótimo, mais uma continuação que ninguém pediu… Genial.\" sai positiva.",
    ])
    w.h("Reconhecimento de entidades nomeadas", 2)
    labels = entities_stats["entidades_por_categoria"]
    w.p(
        f"Nas 428 sinopses, o spaCy reconheceu {entities_stats['entidades']} menções: {labels['PER']} pessoas (PER), {labels['LOC']} lugares (LOC), {labels['MISC']} outras (MISC) e {labels['ORG']} organizações (ORG). "
        "Para medir sem anotar à mão, usamos os **créditos do TMDB** (os 15 primeiros nomes do elenco, ator e personagem) como referência parcial. Quando um nome dos créditos aparece na sinopse, conferimos que categoria o NER deu a ele."
    )
    w.figure(paths["ner"], "Categoria dada pelo NER aos nomes de personagens e atores que aparecem nas sinopses.", width=12)
    w.bullets([
        f"**O NER quase sempre encontra o nome**: {pct(ner['revocacao_qualquer_categoria'])} das {ner['mencoes_creditadas']} menções foram reconhecidas com alguma categoria.",
        f"**Mas erra a categoria:** só {pct(ner['revocacao_per'])} saem como pessoa. Personagens viram lugar (\"Maximus\" em *Gladiador*, \"Mathilda\" em *O Profissional*) ou MISC (\"Forrest Gump\"). O modelo foi treinado em notícias e conhece pouco os nomes de ficção, como havíamos previsto na Unidade 1.",
        f"**Precisão estimada:** {pct(ner['precisao_estimada_per'])} das entidades PER têm um nome dos créditos. É um piso, porque apelidos como \"Doc\" não aparecem nos créditos.",
    ])
    w.h("Extração de relações", 2)
    rules = entities_stats["triplas_por_regra"]
    w.p(
        f"Aplicamos as regras do notebook da Aula 9: o sujeito (nsubj) de um verbo é ligado a cada complemento (obj e obl), e no obl a preposição entra na relação (\"trabalhar_em\"). "
        f"Foram {entities_stats['triplas']} triplas: {rules['svo']} com objeto direto, {rules['obl']} com complemento preposicionado e {rules['coordenacao']} por uma regra a mais, em que um verbo coordenado herda o sujeito (\"nasceu … e estudou …\"). "
        f"{pct(entities_stats['sentencas_com_tripla'] / entities_stats['sentencas'])} das sentenças têm ao menos uma tripla."
    )
    w.table(
        ["Sinopse (trecho)", "Tripla extraída"],
        [
            ["Matrix: \"Thomas conhece os misteriosos Morpheus e Trinity…\"", "(Thomas, conhecer, Morpheus e Trinity) — correta"],
            ["Akira: \"…fez com que Tóquio fosse destruída em 1988.\"", "(Tóquio, destruir_em, 1988) — correta"],
            ["Drácula: \"O vampiro Conde Drácula vem à Inglaterra…\"", "(vampiro Conde Drácula, vir_a, Inglaterra) — correta"],
            ["Matrix: \"…um sistema chamado Matrix, que manipula a mente das pessoas\"", "(que, manipular, mente das pessoas) — sujeito é pronome"],
            ["A Outra Face: \"…Sean Archer rastreia Troy, que embarcou em um avião…\"", "(…Sean Archer que embarcou em um avião…, rastrear, Troy) — sujeito misturado"],
        ],
        [9, 7.5],
        "Exemplos de triplas",
        size=8,
    )
    judged = [t for t in review["triplas"] if t["correta"] is not None]
    correct = sum(t["correta"] for t in judged)
    w.bullets([
        f"**Correferência é o maior limite:** {entities_stats['sujeitos_pronomes']} triplas ({pct(entities_stats['sujeitos_pronomes'] / entities_stats['triplas'])}) têm \"ele\", \"ela\" ou \"que\" como sujeito, sem ligação ao personagem.",
        f"**Poucas triplas ligam duas entidades** ({pct(entities_stats['triplas_com_duas_entidades'] / entities_stats['triplas'])}). As sinopses descrevem ações de personagens sobre coisas, e não fatos entre entidades.",
        f"**Conferência manual de 40 triplas sorteadas:** {correct} de {len(judged)} corretas ({pct(correct / len(judged))}). Os erros mais comuns foram sujeito ou objeto misturado com outra parte da frase e circunstâncias (\"a partir de…\", \"desde logo\") lidas como complemento. A marcação inicial foi feita pelo assistente de IA (ver \"Uso de IA generativa\") e registrada pela equipe em config/entidades/conferencia_relacoes.json.",
    ])
    w.code(source_of(relations, "for complement in", "return triples"), "Trecho de código — regras de extração de relações (backend/src/app/entities/extraction.py)")
    w.p("**No site:** a aba \"Analisar crítica\" mostra o sentimento, a nota prevista e as palavras que mais pesaram. A ficha de cada filme mostra a sinopse com as entidades marcadas por cor e as relações extraídas.")
    w.code(source_of(grouped_folds), "Trecho de código — dobras que mantêm as críticas de um filme juntas (backend/src/app/sentiment/evaluation.py)")

    # 6
    w.h("6) As técnicas auxiliam o projeto da Unidade 1?", 1)
    w.p(
        "Na Unidade 1, propusemos um **assistente de consulta a filmes em linguagem natural**: o usuário pergunta em português, o sistema descobre o que foi perguntado e sobre qual filme, "
        "consulta a API do TMDB e responde em linguagem natural. **Sim, as técnicas ajudaram**, e a maior parte da proposta virou parte do site:"
    )
    w.table(
        ["Proposta da Unidade 1", "O que foi feito", "Técnica"],
        [
            ["Extração de informação: separar a \"moldura\" da pergunta do nome do filme", "A busca reconhece o título exato e tira as palavras de pedido (\"quero\", \"me indica\", \"filmes sobre\") antes de procurar por tema", "Regras léxicas; preparação da consulta"],
            ["Recuperação: ranquear o filme certo (\"a evolução é vetorizar com TF-IDF e ranquear por cosseno\")", "Foi além: busca por tema nas sinopses com 0,3 × TF-IDF + 0,7 × MiniLM, num catálogo de 5.525 filmes (70% dos 3 primeiros relevantes)", "TF-IDF, BERT de sentença, cosseno"],
            ["Classificação da pergunta", "O modo automático decide entre título, preferências (gênero, período, nota) e tema; a classificação treinada é de gênero das sinopses", "Regras; regressão logística"],
            ["\"Outros\": análise de sentimento em críticas, rotuladas pela nota do autor", "Feita exatamente como proposto: 1.859 críticas, F1 macro de 86,7% e nota com erro médio de 1,33 ponto, na aba \"Analisar crítica\"", "As 8 representações + regressão logística e Ridge"],
            ["Reconhecimento de entidades (\"léxico de títulos\")", "NER e relações nas sinopses, na ficha do filme", "spaCy, dependências"],
            ["Recomendação implícita em \"me recomende algo parecido com Duna\"", "Filmes parecidos na ficha de cada filme", "Cosseno no MiniLM"],
            ["Chatbot de vários turnos (\"e quem dirigiu?\")", "**Não feito:** o site responde a cada busca isoladamente, sem memória de conversa", "—"],
            ["Sumarização de sinopses", "**Não feita**", "—"],
        ],
        [5.2, 7.3, 4],
        "Proposta da Unidade 1 × o que foi realizado",
        size=8,
    )
    w.bullets([
        "**As dificuldades previstas se confirmaram e foram tratadas.** A Unidade 1 previa o desbalanceamento das críticas (\"72% são 7 ou mais\"). Medimos 71% de positivas na polaridade e, como planejado, avaliamos com F1 macro e por classe, e não só com acurácia. Também previa que os nomes próprios de ficção prejudicariam os modelos, e o NER confirmou: um quarto dos personagens recebe outra categoria.",
        "**O que mais ajudou o assistente** foi a busca semântica. Uma pergunta como \"astronautas perdidos no espaço\" não tem título, e só a comparação de sentido entre a pergunta e as sinopses encontra *Interestelar* e *Perdido em Marte*. A classificação e o sentimento acrescentam informação que o TMDB não dá pronta: o gênero de um texto qualquer e o tom das críticas.",
        "**O que falta para o assistente completo** é a camada de diálogo, ou seja, a memória de contexto entre turnos e as respostas redigidas a partir dos dados da API. NER nas perguntas, e não só nas sinopses, ajudaria a delimitar o título dentro de frases longas, o principal obstáculo que apontamos na Unidade 1.",
    ])

    # IA
    w.h("Uso de IA generativa", 1)
    w.p(
        "**Fornecedor e modelo:** Anthropic, **Claude Opus 5.5** (claude-opus-5-5), usado pela extensão **Claude Code** no VS Code, com acesso ao repositório. "
        "O assistente escreveu e testou código, rodou os experimentos, redigiu a documentação e este documento a partir dos resultados, e fez a conferência inicial das 40 triplas de relações. "
        "As decisões de escopo foram da equipe: quais tarefas fazer, quais modelos permitir (só as representações do projeto e o spaCy da aula) e o que mostrar no site. "
        "Separadamente, o **Jev** (TypeSafe AI) foi usado como técnica de classificação, conforme a Aula 8, e não como ferramenta de autoria."
    )
    w.p("**Prompts principais usados nesta etapa** (trechos transcritos como foram digitados; \"…\" marca partes omitidas):")
    w.bullets([
        "\"preciso fazer agora o algoritmo de jev, tem um exemplo … PLN_Aula_8_Teste_Jev.ipynb que pode ser usado, faça o jev\"",
        "\"certo, agora eu preciso decidir oq utilizar para fazer a busca no site … precisa analisar o resultado de cada algoritmo e escoher os melhores para usar na busca\"",
        "\"pode fazer as combinações para decirdir oq fazer para a busca\"",
        "\"ta agora quero fazer a parte da classificação, exidte uma branch chamada luana-classificação … pode fazer o merge e faça o jev\"",
        "\"não acha que esta muito confuso esse repositório? … melhorar a estrutura do projeto\"",
        "\"existe recomendação no projeto? … pode fazer por favor\"",
        "\"pode fazer para 5 mil para busca e recomendação\"",
        "\"nao estou gostando da busca/recomendação Se eu busca algo como: 'filmes sobre saude mental' ele nao retorna nenhum filme parecido\"",
        "\"eu posso usar só oq esta no projeto BoW TF-IDF Word2Vec BERT\"",
        "\"agora preciso verificar se consigo usar algum desses Análise de sentimentos, Extração de Entidades Nomeadas e Extração de Relações … coloquei esse ypyn como base … veja oq da para fazer nesses 3\"",
        "\"comece pela analise de sentimentos, e pode fazer NER + relações com o spaCy da aula tbm depois\"",
        "\"acho que seria melhor deixar melhor explicado oq e onde executar para rodar o projeto no site\"",
        "\"preciso agora preencher esse arquivo para entregar junto … PLN - Trabalho Unidade 3.pdf\" (com o template do Trabalho 1 como base para a questão 6)",
    ])
    w.doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
