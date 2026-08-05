# -*- coding: utf-8 -*-
"""Leitura do cronograma oficial da Univesp."""
import re
from datetime import date, datetime, timedelta

from playwright.sync_api import Error as PlaywrightError

from configuracao import BR_TZ
from dominio.datas import achar_datas
from modelos import SourceResult

JS_CRONOGRAMA = """
() => [...document.querySelectorAll('tr')]
  .map(tr => tr.innerText.replace(/\\s+/g, ' ').trim())
  .filter(t => /Semana\\s+\\d/i.test(t))
"""


def ler(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(800)
        linhas = page.evaluate(JS_CRONOGRAMA)
    except PlaywrightError as erro:
        print(f"  aviso: cronograma {url} falhou ({erro})")
        return None
    semanas = []
    for linha in linhas:
        encontrada = re.search(r"Semana\s+(\d+)", linha, re.IGNORECASE)
        if not encontrada:
            continue
        datas = achar_datas(linha, datetime.now(BR_TZ))
        if len(datas) < 2:
            continue
        semanas.append(
            {
                "n": int(encontrada.group(1)),
                "inicio": datas[0][0].date().isoformat(),
                "vencimento": datas[1][0].isoformat(),
                "carencia": (
                    datas[2][0].isoformat() if len(datas) > 2 else None
                ),
            }
        )
    if not semanas:
        return None
    semanas.sort(key=lambda semana: semana["n"])
    if not _cobre_hoje(semanas):
        # Cronograma de outro bimestre. Acontece quando a disciplina não
        # publica o link e a URL de reserva é montada a partir da data, e
        # aconteceria em silêncio na virada do bimestre: um calendário
        # inteiro de datas vencidas, apresentado como se fosse o atual.
        print(f"  aviso: cronograma {url} não cobre a data de hoje; descartado")
        return None
    return {"fonte": url, "semanas": semanas}


MARGEM_CRONOGRAMA = timedelta(days=30)


def _cobre_hoje(semanas, hoje=None):
    """As semanas deste cronograma cercam a data de hoje?"""
    hoje = hoje or datetime.now(BR_TZ).date()
    try:
        inicio = date.fromisoformat(semanas[0]["inicio"])
        fim = datetime.fromisoformat(
            semanas[-1]["carencia"] or semanas[-1]["vencimento"]
        ).date()
    except (KeyError, TypeError, ValueError):
        return True  # sem como conferir, não invento motivo para descartar
    return inicio - MARGEM_CRONOGRAMA <= hoje <= fim + MARGEM_CRONOGRAMA


def resultado(page, url, checked_at, cache=None):
    if not url:
        return SourceResult(
            status="nao_aplicavel",
            dados=None,
            checked_at=checked_at,
            quantidade_atual=0,
        )
    cronograma = ler(page, url)
    if cronograma is None:
        return SourceResult(
            status="falhou",
            dados=cache,
            problemas=[f"cronograma indisponível: {url}"],
            checked_at=checked_at,
            from_cache=cache is not None,
            quantidade_atual=1 if cache else 0,
        )
    return SourceResult(
        status="live",
        dados=cronograma,
        checked_at=checked_at,
        last_live_at=checked_at,
        quantidade_atual=1,
    )
