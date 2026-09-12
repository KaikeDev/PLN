_MARCADORES_NEGACAO = {"nao", "sem", "nunca"}
_JANELA = 3


def separar_generos_negados(
    tokens: list[str], generos_no_texto: dict[str, list[str]]
) -> tuple[list[str], list[str]]:
    """Para cada token gatilho de genero, verifica se ha marcador de negacao na janela anterior.

    Retorna (generos_incluir, generos_excluir) - nomes de genero, sem duplicatas,
    na ordem de primeira ocorrencia no texto.
    """
    incluir: list[str] = []
    excluir: list[str] = []
    vistos_incluir: set[str] = set()
    vistos_excluir: set[str] = set()

    for indice, token in enumerate(tokens):
        generos = generos_no_texto.get(token)
        if not generos:
            continue

        janela_anterior = tokens[max(0, indice - _JANELA):indice]
        negado = any(marcador in janela_anterior for marcador in _MARCADORES_NEGACAO)

        destino, vistos = (excluir, vistos_excluir) if negado else (incluir, vistos_incluir)
        for genero in generos:
            if genero not in vistos:
                destino.append(genero)
                vistos.add(genero)

    return incluir, excluir
