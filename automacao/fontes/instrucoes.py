# -*- coding: utf-8 -*-
"""Datas anunciadas na página de instruções da quinzena/semana.

A Univesp publica o calendário da quinzena numa página do próprio curso
("Q2 - Instruções da Quinzena 2"), e não no calendário do Moodle nem em
aviso de fórum. Em 04/08/2026 essa página dizia "9 de agosto para concluir
o Módulo 4" e "15 de agosto para enviar os trabalhos", enquanto o guia
mostrava as atividades da quinzena como "sem prazo definido".

Texto corrido é a camada onde este projeto mais errou (quatro rodadas de
auditoria). Por isso nada daqui entra na fila de tarefas: tudo nasce com
confiança baixa e cai no bloco "Confirme se isto é prazo mesmo", com a
frase original e o link da página. O robô mostra o que leu; quem decide é
o Josemar.
"""
import re

from playwright.sync_api import Error as PlaywrightError

from dominio.datas import sem_acento
from dominio.prazos import extrair_prazos

ROTULO_RE = re.compile(r"instrucoes da (quinzena|semana)", re.IGNORECASE)
MAX_PAGINAS = 4


def paginas_de_instrucao(secoes):
    achadas = []
    for secao in secoes:
        for item in secao.get("items") or []:
            if item.get("type") != "page" or not item.get("url"):
                continue
            if ROTULO_RE.search(sem_acento(item.get("label") or "")):
                achadas.append(item)
    return achadas[:MAX_PAGINAS]


def _texto_da_pagina(page, url):
    """O conteúdo fica dentro de um iframe, então lê a página e os quadros."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(800)
        partes = []
        for quadro in page.frames:
            try:
                partes.append(quadro.locator("body").inner_text()[:12000])
            except PlaywrightError:
                continue
        return "\n".join(partes)
    except PlaywrightError:
        return None


def ler(page, secoes, referencia):
    saida = []
    for item in paginas_de_instrucao(secoes):
        texto = _texto_da_pagina(page, item["url"])
        if not texto:
            continue
        prazos = []
        vistos = set()
        for prazo in extrair_prazos(texto, referencia):
            if prazo["quando"][:10] < referencia.isoformat():
                continue
            chave = (prazo["quando"][:10], prazo.get("tipo"))
            if chave in vistos:
                continue
            vistos.add(chave)
            prazos.append({**prazo, "confianca": "baixa"})
        if prazos:
            saida.append(
                {
                    "autor": item["label"],
                    "titulo": item["label"],
                    "url": item["url"],
                    "autoridade": "institucional",
                    "prazos": prazos,
                }
            )
    return saida
