# -*- coding: utf-8 -*-
"""Leitura do cronograma oficial da Univesp."""
import re
from datetime import datetime

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
    return {
        "fonte": url,
        "semanas": sorted(semanas, key=lambda semana: semana["n"]),
    }


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
