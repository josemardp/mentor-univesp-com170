# -*- coding: utf-8 -*-
"""Estado aberto, fechado ou indefinido de uma atividade."""
from playwright.sync_api import Error as PlaywrightError

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
SINAIS_NAO_ENVIADO = [
    "voce nao enviou seu trabalho ainda",
    "voce ainda nao enviou",
    "nenhum envio",
]
SINAIS_ENVIADO = [
    "editar envio",
    "excluir envio",
]


def item_aberto(page, url):
    if not url:
        return None
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(500)
        corpo = sem_acento(page.locator("body").inner_text()[:4000])
    except PlaywrightError:
        return None
    if any(sinal in corpo for sinal in SINAIS_INDEFINIDO):
        return None
    if any(sinal in corpo for sinal in SINAIS_FECHADO):
        return False
    return True


def envio_workshop(page, url):
    """Estado do envio do aluno num Laboratório de Avaliação (workshop).

    Aberto/fechado (``item_aberto``) só enxerga a janela de datas. Um
    workshop com prazo em aberto continua "pendente" pra ele mesmo depois
    do aluno enviar, porque o selo de conclusão do Moodle só fecha quando
    as 5 fases terminam (inclusive a avaliação por pares de terceiros).
    Aqui a fonte da verdade é a própria página "Meu envio".
    """
    if not url:
        return None
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(500)
        corpo = sem_acento(page.locator("body").inner_text()[:4000])
    except PlaywrightError:
        return None
    if any(sinal in corpo for sinal in SINAIS_INDEFINIDO):
        return None
    if any(sinal in corpo for sinal in SINAIS_NAO_ENVIADO):
        return False
    if any(sinal in corpo for sinal in SINAIS_ENVIADO):
        return True
    return None
