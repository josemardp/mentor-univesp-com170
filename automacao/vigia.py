# -*- coding: utf-8 -*-
"""Confere se o guia publicado ainda é recente, e avisa quando congela.

O robô sabe reclamar de uma rodada que roda e falha. O que ele nunca cobriu é
a rodada que **não acontece**: cron que o GitHub não dispara, workflow
desativado por inatividade, Action que morre antes do primeiro passo. Em todos
esses casos o site continua no ar, bonito, com o retrato de ontem — e site
congelado é indistinguível de dia sem novidade. Era o residual anotado no
STATUS desde 10/08/2026.

Este módulo não lê o AVA e não depende de nada do robô. Ele pergunta ao
retrato que o painel está servindo qual é o ``snapshot_at``, e compara com o
relógio. Se a própria leitura falhar, isso também é motivo de aviso: painel
que não responde é pior que painel velho.

Desde 15/09/2026 o retrato é **local**: o Pages foi desligado em 11/09 e o
painel passou a ser servido de ``docs/data.json`` na própria máquina. O vigia
lê o arquivo por padrão. Perguntar por HTTP continua possível (``VIGIA_URL``),
porque a mecânica anti-cache foi caro de descobrir e não se joga fora.

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
from pathlib import Path

from configuracao import BR_TZ

# O painel é local desde 11/09/2026 (Pages desligado). Este é o arquivo que o
# abrir-painel.ps1 serve em 127.0.0.1, e é dele que sai o carimbo do retrato.
RETRATO_LOCAL = Path(__file__).resolve().parent.parent / "docs" / "data.json"
PAINEL_LOCAL = "http://127.0.0.1:8790/"
TAREFA_AGENDADA = "Univesp - guia diario"
SCRIPT_DIARIO = Path(__file__).resolve().parent / "rodar_diario.ps1"
LIMITE_HORAS_PADRAO = 16
TEMPO_LIMITE_REDE = 30


def _limite():
    try:
        return float(os.environ.get("LIMITE_HORAS") or LIMITE_HORAS_PADRAO)
    except ValueError:
        return LIMITE_HORAS_PADRAO


def _por_http(url, agora):
    """``(dados, erro)`` do data.json servido por HTTP.

    O parâmetro anti-cache é obrigatório: sem ele o CDN devolve a cópia antiga
    e o vigia aprova um painel que congelou faz dias. Custou uma rodada
    inteira de investigação em 2026 e fica aqui mesmo com o Pages desligado.
    """
    alvo = url + f"?vigia={int(agora.timestamp())}"
    pedido = urllib.request.Request(
        alvo, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"}
    )
    try:
        with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE_REDE) as resposta:
            return json.loads(resposta.read().decode("utf-8")), None
    except (urllib.error.URLError, TimeoutError, OSError) as erro:
        return None, f"o site não respondeu ({type(erro).__name__})"
    except (ValueError, json.JSONDecodeError):
        return None, "o site respondeu, mas não com o data.json"


def _por_arquivo(caminho):
    """``(dados, erro)`` do data.json na máquina.

    Arquivo que não existe é motivo de aviso, não de silêncio: é exatamente o
    que acontece se a tarefa agendada nunca rodou uma primeira vez.
    """
    if not caminho.exists():
        return None, f"o painel local não existe ainda ({caminho.name})"
    try:
        return json.loads(caminho.read_text(encoding="utf-8")), None
    except (ValueError, json.JSONDecodeError):
        return None, f"o {caminho.name} local está corrompido"
    except OSError as erro:
        return None, f"não consegui abrir o {caminho.name} ({type(erro).__name__})"


def ler_retrato(url=None, agora=None):
    """Devolve ``(horas, quando, erro)`` do retrato que o painel está servindo.

    ``horas`` é ``None`` quando não deu para saber. Lê o arquivo local, que é
    onde o painel vive desde 11/09/2026; ``url`` (ou ``VIGIA_URL``) força a
    leitura por HTTP, para quem voltar a servir o guia de fora da máquina.
    """
    agora = agora or datetime.now(timezone.utc)
    alvo = url or os.environ.get("VIGIA_URL")
    if alvo:
        dados, erro = _por_http(alvo, agora)
        onde = "publicado"
    else:
        dados, erro = _por_arquivo(RETRATO_LOCAL)
        onde = "local"
    if erro:
        return None, None, erro

    bruto = dados.get("snapshot_at") or dados.get("checked_at")
    if not bruto:
        return None, None, f"o data.json {onde} não diz quando foi lido"
    try:
        quando = datetime.fromisoformat(bruto)
    except ValueError:
        return None, None, f"data ilegível no data.json {onde} ({bruto!r})"
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    return (agora - quando).total_seconds() / 3600, quando, None


def diagnostico(agora=None):
    """``(congelou, texto)``. Falha de leitura conta como congelado."""
    agora = agora or datetime.now(timezone.utc)
    limite = _limite()
    horas, quando, erro = ler_retrato(agora=agora)
    if erro:
        return True, f"Não consegui conferir o guia: {erro}."
    quando_br = quando.astimezone(BR_TZ)
    carimbo = f"{quando_br:%d/%m às %H:%M}"
    if horas > limite:
        return True, (
            f"O guia é de {carimbo}, cerca de {int(horas)}h atrás. "
            f"O robô devia reler todo dia, então mais de "
            f"{int(limite)}h sem retrato novo quer dizer que as rodadas "
            "pararam de acontecer."
        )
    return False, f"O guia é de {carimbo}, {int(horas)}h atrás."


def _corpo(texto):
    return (
        f"{texto}\n\n"
        "Isto aqui é o vigia, não o robô. Ele não lê o AVA: só confere se o "
        "guia continua sendo atualizado.\n\n"
        "O que costuma ser:\n"
        "- o computador ficou desligado na hora marcada: a tarefa só dispara "
        "com a máquina ligada;\n"
        "- a tarefa agendada do Windows foi desativada ou apagada;\n"
        "- as credenciais do AVA venceram e toda rodada morre no login.\n\n"
        "Onde olhar: Agendador de Tarefas do Windows, tarefa "
        f"{TAREFA_AGENDADA!r}, aba Histórico.\n"
        "Rodar na mão: powershell -ExecutionPolicy Bypass -File "
        f"{SCRIPT_DIARIO}\n"
        f"O guia: {PAINEL_LOCAL}\n"
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
