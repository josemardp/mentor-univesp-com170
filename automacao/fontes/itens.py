# -*- coding: utf-8 -*-
"""Estado aberto, fechado ou indefinido de uma atividade."""
from dominio.datas import sem_acento

SINAIS_FECHADO = [
    "nao esta aberta",
    "nao esta aberto",
    "nao esta disponivel",
    "nao esta mais disponivel",
    "esta atividade encerrou",
    "o prazo para envio expirou",
    "nao e mais possivel",
    "periodo encerrado",
    "fora do prazo",
    "esta pesquisa nao esta",
    "submissoes fechadas",
    "avaliacoes fechadas",
    "o prazo de envio terminou",
    "prazo encerrado",
    "envio encerrado",
    "atividade encerrada",
]
SINAIS_INDEFINIDO = [
    "precisa fazer login",
    "voce precisa se identificar",
    "acesso negado",
    "nao tem permissao",
    "sem permissao para",
    "erro de permissao",
]


def item_aberto(page, url):
    if not url:
        return None
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(500)
        corpo = sem_acento(page.locator("body").inner_text()[:4000])
    except Exception:
        return None
    if any(sinal in corpo for sinal in SINAIS_INDEFINIDO):
        return None
    if any(sinal in corpo for sinal in SINAIS_FECHADO):
        return False
    return True
