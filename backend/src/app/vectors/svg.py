"""Gráfico de dispersão em SVG sem dependências. Todo texto vindo dos dados é escapado.

A paleta é Okabe–Ito, legível por pessoas com daltonismo. Os rótulos recebem contorno branco para
continuar legíveis sobre os pontos, e os pontos neutros são desenhados primeiro para que os de gênero
único fiquem por cima.
"""

from html import escape

PALETTE = ("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9")
NEUTRAL = "#9A9A9A"
NEUTRAL_LABEL = "Mais de um gênero de coleta"
WIDTH, HEIGHT, MARGIN, LEGEND, HEADER, PADDING, LABEL_GAP = 760, 540, 48, 210, 28, 10, 18
HALO = 'stroke="#ffffff" stroke-width="3" paint-order="stroke"'


def render_projection(heading: str, points: list[dict], variance: list[float], highlight_ids: set[int]) -> str:
    """SVG com os pontos coloridos por gênero de coleta, legenda e rótulos dos filmes destacados."""
    genres = sorted({point["genre"] for point in points if point["genre"]})
    colors = {genre: PALETTE[index % len(PALETTE)] for index, genre in enumerate(genres)}
    left, top = MARGIN, MARGIN + HEADER
    width, height = WIDTH - 2 * MARGIN - LEGEND, HEIGHT - top - MARGIN
    xs, ys = [point["x"] for point in points], [point["y"] for point in points]

    def position(point: dict) -> tuple[float, float]:
        inner_width, inner_height = width - 2 * PADDING, height - 2 * PADDING
        return (
            left + PADDING + _scale(point["x"], min(xs), max(xs)) * inner_width,
            top + PADDING + (1 - _scale(point["y"], min(ys), max(ys))) * inner_height,
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" '
        'font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="12" role="img">',
        f"<title>{escape(heading)}</title>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="{MARGIN}" font-size="15" font-weight="600" fill="#1f1f1f">{escape(heading)}</text>',
        f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="none" stroke="#d9d9d9"/>',
        f'<text x="{left + width / 2:.1f}" y="{HEIGHT - 14}" text-anchor="middle" fill="#555555">Componente 1 ({variance[0]:.1%} da variância)</text>',
        f'<text x="16" y="{top + height / 2:.1f}" text-anchor="middle" fill="#555555" transform="rotate(-90 16 {top + height / 2:.1f})">'
        f"Componente 2 ({variance[1]:.1%} da variância)</text>",
    ]
    for point in sorted(points, key=lambda item: item["genre"] is not None):
        x, y = position(point)
        label = point["genre"] or NEUTRAL_LABEL
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{colors.get(point["genre"], NEUTRAL)}" fill-opacity="0.8">'
            f"<title>{escape(point['title'])} ({point['id']}) — {escape(label)}</title></circle>"
        )
    highlighted = sorted(((point, *position(point)) for point in points if point["id"] in highlight_ids), key=lambda item: item[2])
    for (point, x, y), label_y in zip(highlighted, _spread([y for _, _, y in highlighted], top + LABEL_GAP, top + height - 6), strict=True):
        anchor, label_x = ("end", x - 24) if x > left + width / 2 else ("start", x + 24)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="none" stroke="#1f1f1f" stroke-width="1.5"/>')
        parts.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{label_x:.1f}" y2="{label_y - 4:.1f}" stroke="#1f1f1f" stroke-width="1"/>')
        parts.append(
            f'<text x="{label_x + (-3 if anchor == "end" else 3):.1f}" y="{label_y:.1f}" text-anchor="{anchor}" font-weight="600" '
            f'fill="#1f1f1f" {HALO}>{escape(point["title"])}</text>'
        )
    legend_x = left + width + 24
    for index, (label, color) in enumerate([*colors.items(), (NEUTRAL_LABEL, NEUTRAL)]):
        y = top + 12 + index * 22
        parts.append(f'<circle cx="{legend_x}" cy="{y}" r="5" fill="{color}"/>')
        parts.append(f'<text x="{legend_x + 12}" y="{y + 4}" fill="#1f1f1f">{escape(label)}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _spread(positions: list[float], low: float, high: float) -> list[float]:
    """Afasta verticalmente rótulos próximos (entrada ordenada) para que não se sobreponham."""
    placed: list[float] = []
    for position in positions:
        placed.append(max(position, placed[-1] + LABEL_GAP) if placed else max(position, low))
    shift = max(0.0, placed[-1] - high) if placed else 0.0
    return [max(low, value - shift) for value in placed]


def _scale(value: float, low: float, high: float) -> float:
    return 0.5 if high == low else (value - low) / (high - low)
