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
    # "19h" (sem minutos) é como se escreve hora em aviso de fórum, e era
    # justamente o formato que o robô não lia: caía no padrão sem hora e
    # virava 23:59, dez horas depois da live. O separador aceita travessão
    # porque a agenda de lives vem como "04/08/2026 – 14h".
    hora = (
        r"(?:[,\s)\]–—-]*(?:[àa]s\s*)?"
        r"(\d{1,2})(?:[:h](\d{2})|h)\b)?"
    )
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
                if not hora_certa:
                    mm = 59
                elif encontrado.group(5) is not None:
                    mm = int(encontrado.group(5))
                else:
                    mm = 0  # "19h" é 19:00, não 19:59.
                if hh > 23 or mm > 59:
                    continue
                anos = (
                    [int(encontrado.group(3))]
                    if encontrado.group(3)
                    else [referencia.year, referencia.year + 1, referencia.year - 1]
                )
                # Comparar só o dia. Subtrair datetime de date, ou datetime
                # com fuso de outro sem fuso, levanta TypeError, e o except
                # lá embaixo engolia o achado inteiro: toda data escrita sem
                # o ano ("dia 30/07") sumia calada, porque só aí entram três
                # candidatos e a comparação acontece.
                dia_referencia = (
                    referencia.date()
                    if isinstance(referencia, datetime)
                    else referencia
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
                        (candidato.date() - dia_referencia).days
                    ) < abs((melhor.date() - dia_referencia).days):
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
