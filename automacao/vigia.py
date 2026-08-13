# -*- coding: utf-8 -*-
"""Confere se o guia publicado ainda é recente, e avisa quando congela.

O robô sabe reclamar de uma rodada que roda e falha. O que ele nunca cobriu é
a rodada que **não acontece**: cron que o GitHub não dispara, workflow
desativado por inatividade, Action que morre antes do primeiro passo. Em todos
esses casos o site continua no ar, bonito, com o retrato de ontem — e site
congelado é indistinguível de dia sem novidade. Era o residual anotado no
STATUS desde 10/08/2026.

Este módulo não lê o AVA e não depende de nada do robô. Ele pergunta ao site
público (o mesmo endereço que o Josemar abre) qual é o ``snapshot_at`` que
está sendo servido, e compara com o relógio. Se a leitura do próprio site
falhar, isso também é motivo de aviso: um site que não responde é pior que um
site velho.

  python automacao/vigia.py             confere e falha (exit 1) se congelou
  python automacao/vigia.py --avisar    manda o e-mail contando o que achou
"""
import json
import os
import ssl
import smtplib
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage

from configuracao import BR_TZ

SITE = "https://esdraaline.github.io/mentor-univesp-com170"
LIMITE_HORAS_PADRAO = 16
TEMPO_LIMITE_REDE = 30


def _limite():
    try:
        return float(os.environ.get("LIMITE_HORAS") or LIMITE_HORAS_PADRAO)
    except ValueError:
        return LIMITE_HORAS_PADRAO


def ler_publicado(url=None, agora=None):
    """Devolve ``(horas, quando, erro)`` do retrato que o site está servindo.

    ``horas`` é ``None`` quando não deu para saber. O parâmetro anti-cache é
    obrigatório: sem ele o CDN do Pages devolve a cópia antiga e o vigia
    aprova um site que congelou faz dias.
    """
    agora = agora or datetime.now(timezone.utc)
    alvo = (url or f"{SITE}/data.json") + f"?vigia={int(agora.timestamp())}"
    pedido = urllib.request.Request(
        alvo, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"}
    )
    try:
        with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE_REDE) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as erro:
        return None, None, f"o site não respondeu ({type(erro).__name__})"
    except (ValueError, json.JSONDecodeError):
        return None, None, "o site respondeu, mas não com o data.json"

    bruto = dados.get("snapshot_at") or dados.get("checked_at")
    if not bruto:
        return None, None, "o data.json publicado não diz quando foi lido"
    try:
        quando = datetime.fromisoformat(bruto)
    except ValueError:
        return None, None, f"data ilegível no data.json publicado ({bruto!r})"
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    return (agora - quando).total_seconds() / 3600, quando, None


def diagnostico(agora=None):
    """``(congelou, texto)``. Falha de leitura conta como congelado."""
    agora = agora or datetime.now(timezone.utc)
    limite = _limite()
    horas, quando, erro = ler_publicado(agora=agora)
    if erro:
        return True, f"Não consegui conferir o guia publicado: {erro}."
    quando_br = quando.astimezone(BR_TZ)
    carimbo = f"{quando_br:%d/%m às %H:%M}"
    if horas > limite:
        return True, (
            f"O guia publicado é de {carimbo}, cerca de {int(horas)}h atrás. "
            f"O robô devia reler a cada poucas horas, então mais de "
            f"{int(limite)}h sem retrato novo quer dizer que as rodadas "
            "pararam de acontecer."
        )
    return False, f"O guia publicado é de {carimbo}, {int(horas)}h atrás."


def _corpo(texto):
    return (
        f"{texto}\n\n"
        "Isto aqui é o vigia, não o robô. Ele não lê o AVA: só confere de fora "
        "se o site continua sendo atualizado.\n\n"
        "O que costuma ser:\n"
        "- o agendamento do GitHub Actions parou de disparar (acontece, e "
        "silenciosamente);\n"
        "- o workflow foi desativado por inatividade do repositório;\n"
        "- as credenciais do AVA venceram e toda rodada morre no login.\n\n"
        f"Onde olhar: https://github.com/esdraaline/mentor-univesp-com170/actions\n"
        f"O guia: {SITE}/\n"
    )


def avisar(texto):
    host = os.environ.get("SMTP_HOST")
    porta = os.environ.get("SMTP_PORT", "587")
    user = os.environ.get("SMTP_USER")
    senha = os.environ.get("SMTP_PASS")
    para = os.environ.get("EMAIL_PARA")
    if not all([host, user, senha, para]):
        print("::error::vigia sem SMTP configurado; não consegui avisar.")
        return 2
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = para
    msg["Subject"] = (
        f"[Univesp {datetime.now(BR_TZ):%d/%m}] o guia parou de atualizar"
    )
    msg.set_content(_corpo(texto))
    with smtplib.SMTP(host, int(porta), timeout=45) as servidor:
        servidor.starttls(context=ssl.create_default_context())
        servidor.login(user, senha)
        servidor.send_message(msg)
    print("Aviso de guia congelado enviado.")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    congelou, texto = diagnostico()
    print(texto)
    if "--avisar" in argv:
        return avisar(texto)
    # Exit 1 é o que acende o passo de e-mail no workflow. Guia em dia sai 0 e
    # o vigia não fala nada — vigia que fala todo dia deixa de ser lido.
    return 1 if congelou else 0


if __name__ == "__main__":
    raise SystemExit(main())
