# -*- coding: utf-8 -*-
"""Normalização textual e datas sem dependência de rede."""
import re
import unicodedata
from datetime import datetime

from configuracao import BR_TZ

MESES = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
    "jan": 1,
    "fev": 2,
    "mar": 3,
    "abr": 4,
    "mai": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "set": 9,
    "out": 10,
    "nov": 11,
    "dez": 12,
}


def sem_acento(texto):
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(caractere) != "Mn"
    ).lower()


def mes(nome):
    return MESES.get(sem_acento(nome).strip(". "))


def achar_datas(texto, referencia):
    """Extrai datas e preserva se a hora veio explicitamente da fonte."""
    achados = []
    hora = r"(?:[,\s]*(?:às\s*)?(\d{1,2})[:h](\d{2}))?"
    padroes = [
        (r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?", True),
        (
            r"(\d{1,2})(?:º|ª)?\s+(?:de\s+)?([A-Za-zçÇãÃéÉ]{3,10})\.?"
            r"(?:\s+(?:de\s+)?(\d{4}))?",
            False,
        ),
    ]
    for padrao, numerico in padroes:
        for encontrado in re.finditer(padrao + hora, texto, re.IGNORECASE):
            try:
                dia = int(encontrado.group(1))
                numero_mes = (
                    int(encontrado.group(2))
                    if numerico
                    else mes(encontrado.group(2))
                )
                if (
                    not numero_mes
                    or not 1 <= numero_mes <= 12
                    or not 1 <= dia <= 31
                ):
                    continue
                hora_certa = encontrado.group(4) is not None
                hh = int(encontrado.group(4)) if hora_certa else 23
                mm = int(encontrado.group(5)) if hora_certa else 59
                if hh > 23 or mm > 59:
                    continue
                anos = (
                    [int(encontrado.group(3))]
                    if encontrado.group(3)
                    else [referencia.year, referencia.year + 1, referencia.year - 1]
                )
                melhor = None
                for ano in anos:
                    try:
                        candidato = datetime(
                            ano, numero_mes, dia, hh, mm, tzinfo=BR_TZ
                        )
                    except ValueError:
                        continue
                    if melhor is None or abs(
                        (candidato - referencia).days
                    ) < abs((melhor - referencia).days):
                        melhor = candidato
                if melhor:
                    achados.append(
                        (
                            melhor,
                            encontrado.group(0).strip(),
                            hora_certa,
                            encontrado.start(),
                        )
                    )
            except (ValueError, TypeError):
                continue
    return achados
