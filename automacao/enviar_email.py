# -*- coding: utf-8 -*-
"""
Manda o resumo do dia por e-mail, logo depois que o robo le o AVA.

Le docs/data.json e monta um resumo curto: o que vence, o que chegou de novo
e o link do site. Nao repete o mapa inteiro das disciplinas: quem quiser o
detalhe abre o site.

Configuracao (Secrets do GitHub, nunca no codigo):
  SMTP_HOST   ex.: smtp.gmail.com
  SMTP_PORT   ex.: 587
  SMTP_USER   o e-mail que envia
  SMTP_PASS   senha de app (Gmail: Conta Google > Seguranca > Senhas de app)
  EMAIL_PARA  para quem vai (pode ser o mesmo endereco)

Se faltar qualquer uma, o script sai quieto e sem erro: o site ja foi gerado,
o e-mail e um extra.
"""
import json
import os
import smtplib
import ssl
import sys
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "docs" / "data.json"
SITE = "https://esdraaline.github.io/mentor-univesp-com170/"
BR_TZ = timezone(timedelta(hours=-3))

TITULOS = {
    "hoje": "Vence hoje",
    "amanha": "Vence amanhã",
    "semana": "Nos próximos dias",
    "depois": "Mais pra frente",
    "sem_prazo": "Sem prazo definido",
}


def plural(n, singular, plural_):
    return f"{n} {singular if n == 1 else plural_}"


def linha_acao(a):
    partes = [f"{a['verbo']} {a.get('coisa') or ''}".strip(), f": {a['o_que']}"]
    txt = "".join(partes)
    extra = [a["curso"]]
    if a.get("prazo_txt"):
        extra.append(a["prazo_txt"])
    elif a.get("prioridade_ate"):
        extra.append("sem prazo próprio")
    if a.get("conta_nota"):
        extra.append("vale nota")
    if a.get("verificacao") == "indefinida":
        extra.append("não consegui verificar se está aberta")
    return f"- {txt}  ({' · '.join(extra)})"


def curto(texto, limite=64):
    """Título de atividade vem com a referência bibliográfica inteira. No
    e-mail isso vira parede de texto e atrapalha achar o que importa."""
    t = (texto or "").split(" | ")[0].strip()
    return t if len(t) <= limite else t[:limite - 1].rstrip() + "…"


def topo_decisorio(data, acoes):
    """As primeiras linhas, que é o que ele lê no celular às 8h."""
    linhas = []
    primeira = next((a for a in acoes if a["urgencia"] in ("hoje", "amanha")), None)
    if primeira:
        linhas.append("FAÇA AGORA")
        alvo = f"{primeira['curso']}: {curto(primeira['o_que'])}"
        linhas.append(f"- {alvo}")
        if primeira.get("destrava"):
            linhas.append(f"  Não tem prazo próprio. Está no topo porque destrava "
                          f"{primeira['destrava']}.")
        elif primeira.get("prazo_txt"):
            linhas.append(f"  {primeira['prazo_txt']}.")
        linhas.append("")

    duros = [a for a in acoes if a.get("prazo")][:6]
    if duros:
        linhas.append("PRAZOS FIRMES")
        por_data = {}
        for a in duros:
            por_data.setdefault(a["prazo"][:10], []).append(a)
        for dia in sorted(por_data):
            quando = datetime.fromisoformat(por_data[dia][0]["prazo"])
            itens = por_data[dia]
            nomes = ", ".join(f"{a['curso']} ({curto(a['o_que'], 40)})" for a in itens[:3])
            if len(itens) > 3:
                nomes += f" e mais {len(itens) - 3}"
            linhas.append(f"- {quando:%d/%m} às {quando:%H:%M}: {nomes}")
        linhas.append("")

    pendentes_confirmar = data.get("confirmar") or []
    if pendentes_confirmar:
        linhas.append(f"CONFIRA ({len(pendentes_confirmar)})")
        linhas.append("- Li datas em avisos e não tenho certeza se são prazo. "
                      "Estão no site, com a frase original.")
        linhas.append("")
    return linhas


def montar_texto(data):
    hoje = datetime.now(BR_TZ)
    linhas = [f"Guia Univesp - {hoje:%d/%m/%Y}", ""]

    if data.get("status") == "session_expired":
        linhas += [
            "ATENCAO: a sessao do AVA expirou, os dados abaixo sao do ultimo retrato valido.",
            "Renove com 2 cliques em automacao/salvar_credenciais.bat.", "",
        ]
    elif data.get("status") == "coleta_incompleta":
        linhas += ["ATENCAO: entrei no AVA mas a leitura veio incompleta, entao o que",
                   "vem abaixo e do ultimo retrato que deu certo e PODE ESTAR VELHO.",
                   "Confira direto no AVA. Motivos:"]
        linhas += [f"  - {p}" for p in (data.get("problemas") or [])]
        linhas.append("")

    acoes = data.get("acoes") or []
    if not acoes:
        linhas.append("Nada pendente. Tudo em dia.")
        linhas.append("")

    # Topo: a decisão. Embaixo: a lista inteira, pra não precisar abrir o site.
    linhas += topo_decisorio(data, acoes)

    if acoes:
        linhas.append("-" * 58)
        linhas.append("LISTA COMPLETA")
        linhas.append("")
    for chave, titulo in TITULOS.items():
        grupo = [a for a in acoes if a["urgencia"] == chave]
        if not grupo:
            continue
        linhas.append(f"{titulo}:")
        linhas += [linha_acao(a) for a in grupo[:12]]
        linhas.append("")

    hig = data.get("higiene") or []
    if hig:
        linhas.append(f"Higiene do AVA ({len(hig)} itens a marcar, não valem nota):")
        linhas += [f"- {a['curso']}: {curto(a['o_que'], 50)}" for a in hig[:12]]
        if len(hig) > 12:
            linhas.append(f"  ... e mais {len(hig) - 12}, no site.")
        linhas.append("")

    avisos = [(a.get("data") or "", c["code"], a)
              for c in data.get("courses", []) for a in (c.get("avisos") or [])]
    avisos.sort(reverse=True)
    if avisos:
        linhas.append("Chegou novo nos foruns:")
        for _, code, a in avisos[:6]:
            titulo = a.get("titulo") or "post"
            linhas.append(f"- [{code}] {titulo} ({a.get('forum') or ''})")
            for p in (a.get("prazos") or [])[:2]:
                try:
                    quando = datetime.fromisoformat(p["quando"]).strftime("%d/%m às %H:%M")
                except Exception:
                    quando = p["quando"]
                linhas.append(f"    prazo lido: {quando} - {p['rotulo']}")
        linhas.append("")

    msgs = data.get("mensagens") or []
    if msgs:
        linhas.append("Mensagens nao lidas no AVA:")
        linhas += [f"- {m['nao_lidas']} de {m['de']}" for m in msgs[:5]]
        linhas.append("")

    nots = [n for n in data.get("notificacoes", []) if not n.get("lida")]
    if nots:
        linhas.append("Notificacoes nao lidas:")
        linhas += [f"- {n.get('assunto')}" for n in nots[:6]]
        linhas.append("")

    linhas += ["Detalhe completo no site:", SITE]
    return "\n".join(linhas)


def assunto(data):
    hoje = datetime.now(BR_TZ)
    acoes = data.get("acoes") or []
    urgentes = [a for a in acoes if a["urgencia"] in ("hoje", "amanha")]
    if data.get("status") == "session_expired":
        return f"[Univesp {hoje:%d/%m}] sessao do AVA expirou"
    if data.get("status") == "coleta_incompleta":
        return f"[Univesp {hoje:%d/%m}] leitura incompleta, confira no AVA"
    # O assunto é o que ele vê primeiro: diz a decisão, não a contagem.
    # "2 coisas vencendo" era impreciso quando uma delas não tinha prazo.
    primeira = next((a for a in acoes if a["urgencia"] in ("hoje", "amanha")), None)
    if primeira:
        alvo = curto(primeira["o_que"], 34)
        duro = next((a for a in acoes if a.get("prazo")
                     and a["urgencia"] in ("hoje", "amanha")), None)
        if duro is not None and duro is not primeira:
            q = datetime.fromisoformat(duro["prazo"])
            return (f"[Univesp {hoje:%d/%m}] Hoje: {primeira['curso']} {alvo}"
                    f"; entrega {q:%d/%m} {q:%H:%M}")
        return f"[Univesp {hoje:%d/%m}] Hoje: {primeira['curso']} {alvo}"
    if acoes:
        return f"[Univesp {hoje:%d/%m}] {len(acoes)} na fila, nada urgente"
    return f"[Univesp {hoje:%d/%m}] tudo em dia"


def main():
    host = os.environ.get("SMTP_HOST")
    porta = os.environ.get("SMTP_PORT", "587")
    user = os.environ.get("SMTP_USER")
    senha = os.environ.get("SMTP_PASS")
    para = os.environ.get("EMAIL_PARA")

    if not all([host, user, senha, para]):
        print("E-mail nao configurado (faltam Secrets). Sigo sem enviar.")
        return 0
    if not DATA_PATH.exists():
        print("Sem data.json, nao ha o que enviar.")
        return 0

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    msg = EmailMessage()
    msg["Subject"] = assunto(data)
    msg["From"] = user
    msg["To"] = para
    msg.set_content(montar_texto(data))

    try:
        with smtplib.SMTP(host, int(porta), timeout=45) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(user, senha)
            s.send_message(msg)
        print(f"E-mail enviado para {para}.")
    except Exception as e:
        # Antes devolvia 0 aqui "pra nao derrubar a Action". O efeito era pior:
        # o e-mail parava de chegar e nada avisava. Agora o passo fica vermelho.
        # O site nao se perde por isso, porque a publicacao acontece antes.
        print(f"::error::Nao consegui enviar o e-mail: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
