import re
from dataclasses import dataclass
from datetime import date

_RE_DECADA = re.compile(r"\bdos anos (\d{2})\b")
_RE_ANO_EXPLICITO = re.compile(r"\b(depois de|apos|a partir de|antes de)\s+(\d{4})\b")

_TERMOS_RECENTE = (
    "nao seja muito antigo",
    "nao muito antigo",
    "nao seja muito antiga",
    "nao muito antiga",
    "recente",
    "recentes",
    "novo",
    "nova",
    "atual",
    "atuais",
)

_TERMOS_ANTIGO = ("antigo", "antiga", "classico", "classica", "cult")

_JANELA_RECENTE_ANOS = 10
_JANELA_ANTIGO_ANOS = 25


@dataclass
class PeriodoExtraido:
    lancado_apos: str | None = None
    lancado_antes: str | None = None


def extrair_periodo(texto_normalizado: str, ano_atual: int | None = None) -> PeriodoExtraido:
    """Aplica, em ordem de especificidade: decada > ano explicito (depois/antes) > termos relativos.

    Os termos relativos de "recente" sao checados (como frases inteiras, ex.
    "nao seja muito antigo") antes de "antigo" isolado, para que a negacao
    explicita no proprio texto vença o termo generico.
    """
    ano_atual = ano_atual if ano_atual is not None else date.today().year

    m_decada = _RE_DECADA.search(texto_normalizado)
    if m_decada:
        decada = int(m_decada.group(1))
        seculo = 2000 if decada <= 29 else 1900
        ano_inicio = seculo + decada
        return PeriodoExtraido(
            lancado_apos=f"{ano_inicio}-01-01",
            lancado_antes=f"{ano_inicio + 9}-12-31",
        )

    matches = list(_RE_ANO_EXPLICITO.finditer(texto_normalizado))
    if matches:
        lower, upper = [], []
        for match in matches:
            direcao, ano = match.group(1), int(match.group(2))
            if not 1874 <= ano <= 9998:
                continue
            if direcao == "antes de":
                upper.append(f"{ano - 1}-12-31")
            else:
                lower.append(f"{ano}-01-01")
        return PeriodoExtraido(max(lower) if lower else None, min(upper) if upper else None)

    if any(re.search(r"\b" + re.escape(termo) + r"\b", texto_normalizado) for termo in _TERMOS_RECENTE):
        return PeriodoExtraido(lancado_apos=f"{ano_atual - _JANELA_RECENTE_ANOS}-01-01")

    if any(re.search(r"\b" + re.escape(termo) + r"\b", texto_normalizado) for termo in _TERMOS_ANTIGO):
        return PeriodoExtraido(lancado_antes=f"{ano_atual - _JANELA_ANTIGO_ANOS}-01-01")

    return PeriodoExtraido()

