# -*- coding: utf-8 -*-
"""
Avisa por e-mail quando sair nota nova no Portal do Aluno da Univesp.

O que faz, em ordem:
  1. garante o Chrome do AVA de pe (ava_vivo.py, idempotente);
  2. le o boletim da secretaria pelo mesmo leitor do robo diario
     (fontes/portal.py, que enxerga PROVA, MEDIA PARCIAL e EXAME);
  3. compara com o que ja foi avisado, guardado em privado/estudo/notas_vistas.json;
  4. se apareceu nota nova ou mudou a situacao, manda UM e-mail com o quadro
     das disciplinas para josemardp@gmail.com.

Notas ficam so no e-mail e em privado/ (o repositorio e publico). Este script
nao imprime nota no console nem no log, so a contagem, exceto com --simular.

Uso:
    python automacao/avisar_notas.py             le, compara e envia se houver novidade
    python automacao/avisar_notas.py --simular   mostra o e-mail na tela, nao envia, nao grava
    python automacao/avisar_notas.py --marcar-visto   grava o boletim atual como ja avisado, sem enviar

Configuracao do envio (variaveis de ambiente do usuario, nunca no codigo):
    SMTP_HOST   smtp.gmail.com
    SMTP_PORT   587
    SMTP_USER   o Gmail que envia (pode ser o proprio josemardp@gmail.com)
    NOTAS_SMTP_PASS   SENHA DE APP do Google (myaccount.google.com/apppasswords).
                Nome proprio, e nao SMTP_PASS, para nao ligar junto o e-mail
                do guia diario e do vigia.
    EMAIL_PARA  opcional; se faltar, vai para josemardp@gmail.com
Credenciais do portal: AVA_USUARIO e AVA_SENHA (ja definidas nesta maquina).

Sem SMTP configurado o script termina com erro e NAO grava o estado, entao a
proxima rodada tenta de novo e a nota nao fica sem aviso.

Agendamento: roda no fim de cada rodada do guia diario (rodar_diario.ps1,
07:30, 13:00 e no logon/desbloqueio), ate 31/12/2026.
"""
import json
import os
import smtplib
import ssl
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
ESTADO = ROOT / "privado" / "estudo" / "notas_vistas.json"
CDP = "http://127.0.0.1:9222"
BR_TZ = timezone(timedelta(hours=-3))
PARA_PADRAO = "josemardp@gmail.com"
# Parcelas que contam como "nota que saiu". ATIVIDADE AVA muda o tempo todo e
# nao deve disparar aviso sozinha.
PARCELAS_DE_AVISO = ("PROVA", "MÉDIA PARCIAL", "EXAME")
SITUACOES_FINAIS = ("aprovado", "reprovado", "recupera")


def garantir_chrome():
    import urllib.request

    try:
        with urllib.request.urlopen(f"{CDP}/json/version", timeout=2):
            return True
    except Exception:
        pass
    r = subprocess.run(
        [sys.executable, str(ROOT / "automacao" / "ava_vivo.py")],
        capture_output=True, text=True, timeout=180,
    )
    return r.returncode == 0


def ler_boletim():
    """Lista de disciplinas do boletim, ou (None, motivo)."""
    from playwright.sync_api import sync_playwright
    from fontes import portal

    with sync_playwright() as p:
        navegador = p.chromium.connect_over_cdp(CDP)
        ctx = navegador.contexts[0] if navegador.contexts else navegador.new_context()
        res = portal.resultado(ctx, datetime.now(timezone.utc).isoformat())
    notas = (res.dados or {}).get("notas")
    if res.status not in ("live", "parcial") or not notas:
        return None, "; ".join(res.problemas) or f"portal devolveu status {res.status}"
    return notas, ""


def retrato(notas):
    return {
        n["codigo"]: {
            "nome": n["nome"],
            "parcelas": n.get("parcelas", {}),
            "situacao": n.get("situacao", ""),
            "frequencia": n.get("frequencia", ""),
        }
        for n in notas
    }


def novidades(atual, visto):
    achados = []
    for cod, d in atual.items():
        antigo = visto.get(cod, {})
        for parcela in PARCELAS_DE_AVISO:
            novo = d["parcelas"].get(parcela, "")
            # O portal mostra EXAME 0,0 para quem passou direto: nao e nota.
            if parcela == "EXAME" and novo == "0,0":
                continue
            if novo and novo != antigo.get("parcelas", {}).get(parcela, ""):
                achados.append(f"{cod} {parcela}: {novo}")
        sit = d["situacao"]
        if sit and sit != antigo.get("situacao", "") and any(
            s in sit.lower() for s in SITUACOES_FINAIS
        ):
            achados.append(f"{cod} situação: {sit}")
    return achados


def montar_email(atual, achados):
    linhas = ["Saiu novidade no Portal do Aluno da Univesp.", ""]
    linhas += ["O que mudou:"] + [f"- {a}" for a in achados] + ["", "Quadro completo:", ""]
    for cod, d in sorted(atual.items()):
        p = d["parcelas"]
        linhas.append(f"{cod} {d['nome']}")
        linhas.append(
            "  Atividade AVA: {} | Prova: {} | Média parcial: {} | Exame: {}".format(
                p.get("ATIVIDADE AVA") or "--", p.get("PROVA") or "--",
                p.get("MÉDIA PARCIAL") or "--", p.get("EXAME") or "--",
            )
        )
        linhas.append(f"  Situação: {d['situacao'] or '--'}  Frequência: {d['frequencia'] or '--'}")
        linhas.append("")
    linhas += [
        "Exame do 4º bimestre: 14 a 17/12/2026, só para quem não atingiu a média.",
        "Conferir também no Portal do Aluno: https://sa.univesp.br/visaoAluno/minhasNotasAlunos.xhtml",
    ]
    msg = EmailMessage()
    msg["Subject"] = f"[Univesp {datetime.now(BR_TZ):%d/%m}] Saíram notas: " + ", ".join(
        sorted({a.split()[0] for a in achados})
    )
    msg.set_content("\n".join(linhas))
    return msg


def enviar(msg):
    host, user = os.environ.get("SMTP_HOST"), os.environ.get("SMTP_USER")
    # Nome proprio de proposito: SMTP_PASS ligaria tambem o e-mail do guia
    # diario e do vigia (enviar_email.py, vigia.py), que nao foi pedido.
    senha, porta = os.environ.get("NOTAS_SMTP_PASS"), os.environ.get("SMTP_PORT", "587")
    if not all([host, user, senha]):
        print("ERRO: faltam SMTP_HOST, SMTP_USER ou NOTAS_SMTP_PASS. Nada enviado, estado não gravado.")
        return False
    msg["From"] = user
    msg["To"] = os.environ.get("EMAIL_PARA") or PARA_PADRAO
    with smtplib.SMTP(host, int(porta), timeout=45) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(user, senha)
        s.send_message(msg)
    return True


def main():
    simular = "--simular" in sys.argv
    if not garantir_chrome():
        print("ERRO: não consegui subir o Chrome do AVA (ava_vivo.py).")
        return 2
    notas, motivo = ler_boletim()
    if notas is None:
        print(f"ERRO: não consegui ler o boletim: {motivo}")
        return 2
    atual = retrato(notas)
    try:
        visto = json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        visto = {}
    if "--marcar-visto" in sys.argv:
        # Grava o boletim de agora como ja avisado, sem enviar nada. Serve para
        # nao reavisar notas antigas na primeira rodada de verdade.
        ESTADO.parent.mkdir(parents=True, exist_ok=True)
        ESTADO.write_text(json.dumps(atual, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Boletim atual marcado como visto ({len(atual)} disciplinas). Nada enviado.")
        return 0
    achados = novidades(atual, visto)
    if not achados:
        print(f"Sem nota nova ({len(atual)} disciplinas lidas).")
        return 0
    msg = montar_email(atual, achados)
    if simular:
        print(msg["Subject"], "\n", msg.get_content())
        return 0
    if not enviar(msg):
        return 2
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(atual, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"E-mail enviado ({len(achados)} novidade(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
