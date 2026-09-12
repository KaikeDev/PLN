GENEROS_POSITIVOS: dict[str, tuple[str, ...]] = {
    "descontraido": ("Comedia", "Familia"),
    "descontraida": ("Comedia", "Familia"),
    "leve": ("Comedia", "Familia"),
    "divertido": ("Comedia",),
    "divertida": ("Comedia",),
    "engracado": ("Comedia",),
    "engracada": ("Comedia",),
    "comedia": ("Comedia",),
    "familia": ("Familia",),
    "infantil": ("Familia", "Animacao"),
    "animacao": ("Animacao",),
    "tenso": ("Terror", "Thriller"),
    "tensa": ("Terror", "Thriller"),
    "assustador": ("Terror",),
    "assustadora": ("Terror",),
    "medo": ("Terror",),
    "terror": ("Terror",),
    "suspense": ("Thriller", "Misterio"),
    "misterio": ("Misterio",),
    "emocionante": ("Drama", "Romance"),
    "dramatico": ("Drama",),
    "dramatica": ("Drama",),
    "romantico": ("Romance",),
    "romantica": ("Romance",),
    "romance": ("Romance",),
    "acao": ("Acao",),
    "aventura": ("Aventura",),
    "fantasia": ("Fantasia",),
    "ficcao": ("Ficcao cientifica",),
    "guerra": ("Guerra",),
    "policial": ("Crime",),
    "crime": ("Crime",),
    "investigacao": ("Crime","Misterio",),
    "documentario": ("Documentario",),
    "musical": ("Musica",),
    "historico": ("Historia",),
    "historica": ("Historia",),
}

PALAVRAS_QUALIDADE_ALTA = (
    "bem avaliado",
    "bem avaliada",
    "bem avaliados",
    "boa avaliacao",
    "boas avaliacoes",
    "aclamado",
    "aclamada",
    "premiado",
    "premiada",
)

PALAVRAS_QUALIDADE_MUITO_ALTA = (
    "muito bem avaliado",
    "muito bem avaliada",
    "excelente",
    "nota alta",
    "aclamadissimo",
    "aclamadissima",
    "obra-prima",
    "obra prima",
)


def buscar_generos_no_texto(tokens: list[str]) -> dict[str, list[str]]:
    """Varre os tokens contra GENEROS_POSITIVOS.

    Retorna {token_original: [nomes_de_genero...]} - preserva o token que
    disparou o match, para negacao.py poder localizar a posicao dele.
    """
    encontrados: dict[str, list[str]] = {}
    for token in tokens:
        generos = GENEROS_POSITIVOS.get(token)
        if generos:
            encontrados[token] = list(generos)
    return encontrados


def buscar_qualidade_no_texto(texto_normalizado: str) -> tuple[float | None, int | None]:
    """Casa expressoes de qualidade (substring, pois sao multi-palavra).

    Retorna (nota_minima, votos_minimos). votos_minimos evita que a nota
    minima seja cumprida por um filme com poucos votos.
    """
    if any(expressao in texto_normalizado for expressao in PALAVRAS_QUALIDADE_MUITO_ALTA):
        return 8.0, 200

    if any(expressao in texto_normalizado for expressao in PALAVRAS_QUALIDADE_ALTA):
        return 7.0, 100

    return None, None
