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
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError

from configuracao import BR_TZ
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


CAPTION_RE = re.compile(
    r"calend[áa]rio da (quinzena|semana)\s*(\d+).{0,80}?de\s+(\w+)\s+de\s+(\d{4})",
    re.IGNORECASE,
)
CELULA_RE = re.compile(r"^(\d{1,2})\s+(.+)$")
ESCOPO_MODULO_RE = re.compile(r"m[óo]dulo\s+(\d+)", re.IGNORECASE)


def calendario_da_quinzena(page, url):
    """Prazos lidos da tabela-calendário, não do texto corrido.

    A página de instruções traz uma tabela com legenda ("Calendário da
    Quinzena 2, de 3 a 18 de agosto de 2026") e células marcadas por classe:
    ``prazo`` nas datas de fechamento, ``estudo``/``entrega``/``leitura`` nas
    etapas. Isso é dado estruturado: o dia vem do número da célula, o mês e o
    ano vêm da legenda, e o rótulo vem escrito ("PRAZO MÓDULO 4").

    Por ser estrutura e não prosa, estes prazos nascem com confiança alta,
    diferente do resto desta fonte. Foi a leitura de texto livre que causou
    quatro rodadas de auditoria; tabela com legenda não tem essa ambiguidade.
    """
    from dominio.datas import mes as numero_do_mes

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(1500)
    except PlaywrightError:
        return []
    for quadro in page.frames:
        try:
            tabela = quadro.evaluate(JS_CALENDARIO)
        except PlaywrightError:
            continue
        if not tabela:
            continue
        achado = CAPTION_RE.search(tabela.get("caption") or "")
        if not achado:
            continue
        numero_mes = numero_do_mes(achado.group(3))
        if not numero_mes:
            continue
        ano = int(achado.group(4))
        familia = sem_acento(achado.group(1))
        prazos = []
        for celula in tabela.get("celulas") or []:
            if "prazo" not in (celula.get("classe") or ""):
                continue
            partes = CELULA_RE.match(celula.get("texto") or "")
            if not partes:
                continue
            dia = int(partes.group(1))
            rotulo = partes.group(2).strip()
            try:
                quando = datetime(
                    ano, numero_mes, dia, 23, 59, tzinfo=BR_TZ
                )
            except ValueError:
                continue
            modulo = ESCOPO_MODULO_RE.search(rotulo)
            numero_quinzena = int(achado.group(2))
            escopo = (
                {
                    "familia": "modulo",
                    "numeros": [int(modulo.group(1))],
                    # Sem isto, "Módulo 4" da Quinzena 2 casaria também com o
                    # Módulo 4 da Quinzena 1, que já encerrou.
                    "quinzena": numero_quinzena,
                    "txt": rotulo,
                }
                if modulo
                else {
                    "familia": familia,
                    "numeros": [numero_quinzena],
                    "txt": rotulo,
                }
            )
            prazos.append(
                {
                    "rotulo": rotulo.capitalize(),
                    "quando": quando.isoformat(),
                    "trecho": celula.get("texto"),
                    "tipo": "fim",
                    "hora_certa": False,
                    "escopo": escopo,
                    "confianca": "alta",
                    "frase": (
                        f"{tabela.get('caption')}. Célula: "
                        f"{celula.get('texto')}"
                    ),
                }
            )
        if prazos:
            return prazos
    return []


JS_CALENDARIO = """
() => {
  const t = [...document.querySelectorAll('table')]
    .find(x => /calend[áa]rio da (quinzena|semana)/i.test(
      (x.querySelector('caption') || {}).innerText || ''));
  if (!t) return null;
  return {
    caption: (t.querySelector('caption').innerText || '').replace(/\\s+/g, ' ').trim(),
    celulas: [...t.querySelectorAll('td')].map(td => ({
      texto: (td.innerText || '').replace(/\\s+/g, ' ').trim(),
      classe: td.className || '',
    })).filter(c => c.texto),
  };
}
"""


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
        # Tabela primeiro: é estrutura, e o que ela afirma dispensa o
        # tratamento defensivo que o texto corrido exige.
        prazos = [
            prazo
            for prazo in calendario_da_quinzena(page, item["url"])
            if prazo["quando"][:10] >= referencia.isoformat()
        ]
        texto = _texto_da_pagina(page, item["url"])
        if not texto:
            if prazos:
                saida.append(_como_aviso(item, prazos))
            continue
        vistos = {prazo["quando"][:10] for prazo in prazos}
        for prazo in extrair_prazos(texto, referencia):
            if prazo["quando"][:10] < referencia.isoformat():
                continue
            # Uma linha por data: a mesma página repete "15 de agosto" em
            # vários parágrafos, e o bloco de conferência não precisa de eco.
            chave = prazo["quando"][:10]
            if chave in vistos:
                continue
            vistos.add(chave)
            prazos.append({**prazo, "confianca": "baixa"})
        if prazos:
            saida.append(_como_aviso(item, prazos))
    return saida


def _como_aviso(item, prazos):
    return {
        "autor": item["label"],
        "titulo": item["label"],
        "url": item["url"],
        "autoridade": "institucional",
        "prazos": prazos,
    }
