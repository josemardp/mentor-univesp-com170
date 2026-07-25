# -*- coding: utf-8 -*-
"""Notificações e metadados de mensagens privadas."""
from datetime import datetime

from configuracao import AVA, BR_TZ
from fontes.moodle import api_opcional


def ler_notificacoes(page, uid):
    dados = api_opcional(
        page,
        "message_popup_get_popup_notifications",
        {"useridto": uid, "limit": 40, "offset": 0},
    )
    saida = []
    for notificacao in (dados or {}).get("notifications", []) or []:
        quando = notificacao.get("timecreated")
        saida.append(
            {
                "assunto": notificacao.get("subject"),
                "quando": (
                    datetime.fromtimestamp(quando, BR_TZ).isoformat()
                    if quando
                    else None
                ),
                "lida": bool(notificacao.get("read")),
                "url": notificacao.get("contexturl"),
            }
        )
    return saida


def ler_mensagens(page, uid):
    """Somente metadado; conteúdo privado nunca vai ao artefato público."""
    dados = api_opcional(
        page,
        "core_message_get_conversations",
        {"userid": uid, "limitnum": 20},
    )
    saida = []
    for conversa in (dados or {}).get("conversations", []) or []:
        nao_lidas = conversa.get("unreadcount") or 0
        if not nao_lidas:
            continue
        nomes = [
            membro.get("fullname")
            for membro in (conversa.get("members") or [])
            if membro.get("fullname")
        ]
        saida.append(
            {
                "de": ", ".join(nomes[:3]) or "alguém no AVA",
                "nao_lidas": nao_lidas,
                "url": f"{AVA}/message/index.php?id={conversa.get('id')}",
            }
        )
    return saida
