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

Em CI, faltar qualquer uma é erro: Secret removido não pode parar o e-mail com
a Action verde. Para uma execução local deliberadamente sem e-mail, use
EMAIL_OPCIONAL=1.
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
ULTIMO_ENVIO_PATH = ROOT / "automacao" / ".ultimo_email_enviado"
ULTIMA_FALHA_PATH = ROOT / "automacao" / ".ultimo_aviso_falha"
SITE = "https://esdraaline.github.io/mentor-univesp-com170/"
BR_TZ = timezone(timedelta(hours=-3))

TITULOS = {
    "hoje": "Para hoje",
    "amanha": "Para amanhã",
    "semana": "Nos próximos dias",
    "depois": "Mais pra frente",
    "sem_prazo": "Sem prazo definido",
}


# Prazo novo só interrompe o dia dele se for perto. Mais longe que isso cabe
# no e-mail da manhã seguinte, e virar notificação de tudo é como o aviso
# deixa de ser lido.
HORIZONTE_ALERTA_HORAS = 48


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


def _quando(iso):
    try:
        return datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None


def linha_prazo_novo(p):
    quando = _quando(p.get("prazo"))
    momento = f"{quando:%d/%m às %H:%M}" if quando else str(p.get("prazo"))
    extra = []
    if p.get("conta_nota"):
        extra.append("vale nota")
    antes = _quando(p.get("de"))
    if antes:
        extra.append(f"antes era {antes:%d/%m às %H:%M}")
    elif p.get("atividade_nova"):
        extra.append("atividade nova no AVA")
    if p.get("fonte"):
        extra.append(str(p["fonte"]))
    sufixo = f"  ({' · '.join(extra)})" if extra else ""
    return f"- {momento}: {p.get('curso')} - {curto(p.get('label'), 46)}{sufixo}"


def prazos_para_alertar(data, agora=None):
    """Prazo novo e perto: o que justifica um e-mail fora da hora combinada.

    Não é "o que está urgente hoje", que repetiria todo dia o mesmo aviso. É
    o que o AVA passou a dizer desde a leitura anterior e vence dentro do
    horizonte. Prazo que já venceu fica de fora: aí não há o que interromper.
    """
    agora = agora or datetime.now(BR_TZ)
    limite = agora + timedelta(hours=HORIZONTE_ALERTA_HORAS)
    perto = []
    for p in data.get("prazos_novos") or []:
        quando = _quando(p.get("prazo"))
        if quando is None:
            continue
        if agora <= quando <= limite:
            perto.append((quando, p))
    perto.sort(key=lambda par: par[0])
    return [p for _, p in perto]


def montar_alerta(data, prazos):
    hoje = datetime.now(BR_TZ)
    linhas = [
        f"Guia Univesp - aviso fora de hora - {hoje:%d/%m às %H:%M}",
        "",
        "O AVA passou a mostrar prazo que não estava no e-mail da manhã:",
        "",
    ]
    linhas += [linha_prazo_novo(p) for p in prazos[:8]]
    if len(prazos) > 8:
        linhas.append(f"  ... e mais {len(prazos) - 8}, no site.")
    linhas += [
        "",
        "O resto do dia continua valendo o e-mail da manhã. Lista completa:",
        SITE,
    ]
    return "\n".join(linhas)


def assunto_alerta(prazos):
    hoje = datetime.now(BR_TZ)
    primeiro = prazos[0]
    quando = _quando(primeiro.get("prazo"))
    momento = f"{quando:%d/%m %H:%M}" if quando else "sem hora"
    if len(prazos) > 1:
        return (f"[Univesp {hoje:%d/%m}] prazo novo em {len(prazos)} "
                f"atividades, a primeira {momento}")
    return (f"[Univesp {hoje:%d/%m}] prazo novo: {primeiro.get('curso')} "
            f"{curto(primeiro.get('label'), 28)} até {momento}")


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

    # Live tem hora e não tem carência: se listar junto de entrega, some no
    # meio e vira exatamente o que já aconteceu, ele perder por não ver.
    lives = [a for a in acoes if a.get("tipo") == "compromisso"][:6]
    if lives:
        linhas.append("COM HORA MARCADA")
        for a in lives:
            quando = datetime.fromisoformat(a["prazo"])
            linhas.append(
                f"- {quando:%d/%m} às {quando:%H:%M}: {a['curso']} "
                f"live ({curto(a['o_que'], 40)})"
            )
        linhas.append("")

    duros = [
        a
        for a in acoes
        if a.get("prazo") and a.get("tipo") != "compromisso"
    ][:6]
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
    elif data.get("status") == "coleta_degradada":
        linhas += [
            "ATENCAO: uma fonte falhou. Atualizei as demais e mantive o último",
            "resultado válido da fonte indisponível. Confira a saúde no site.",
        ]
        linhas += [f"  - {p}" for p in (data.get("problemas") or [])]
        linhas.append("")

    acoes = data.get("acoes") or []
    if not acoes:
        linhas.append("Nada pendente. Tudo em dia.")
        linhas.append("")

    # Topo: a decisão. Embaixo: a lista inteira, pra não precisar abrir o site.
    linhas += topo_decisorio(data, acoes)

    # Prazo que o AVA passou a dizer desde a leitura anterior. Fica no topo
    # porque é o único item do e-mail que ele ainda não tinha visto ontem.
    novos_prazos = data.get("prazos_novos") or []
    if novos_prazos:
        linhas.append(f"PRAZO NOVO DESDE A ÚLTIMA LEITURA ({len(novos_prazos)})")
        linhas += [linha_prazo_novo(p) for p in novos_prazos[:6]]
        if len(novos_prazos) > 6:
            linhas.append(f"  ... e mais {len(novos_prazos) - 6}, no site.")
        linhas.append("")

    # Nota que saiu não é tarefa, mas é a notícia que ele mais espera, e nao
    # aparecia em lugar nenhum do e-mail ate 10/08/2026.
    notas = data.get("notas_novas") or []
    if notas:
        linhas.append(f"SAIU NOTA ({len(notas)})")
        for n in notas[:8]:
            if n.get("de"):
                virada = f"{n['de']} -> {n.get('nota')}"
            else:
                virada = f"{n.get('nota')}"
            linhas.append(f"- {n.get('curso')}: {curto(n.get('label'), 46)} = {virada}")
            if n.get("feedback"):
                linhas.append(f"    devolutiva: {curto(n['feedback'], 70)}")
        if len(notas) > 8:
            linhas.append(f"  ... e mais {len(notas) - 8}, no site.")
        linhas.append("")

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
    avisos.sort(
        key=lambda item: (
            0 if item[2].get("autoridade") == "institucional" else 1
        )
    )
    if avisos:
        linhas.append("Chegou novo nos foruns:")
        for _, code, a in avisos[:6]:
            titulo = a.get("titulo") or "post"
            origem = (
                "OFICIAL"
                if a.get("autoridade") == "institucional"
                else "colega"
            )
            linhas.append(
                f"- [{code}] [{origem}] {titulo} ({a.get('forum') or ''})"
            )
            for p in (a.get("prazos") or [])[:2]:
                try:
                    quando = datetime.fromisoformat(p["quando"]).strftime("%d/%m às %H:%M")
                except Exception:
                    quando = p["quando"]
                rotulo = (
                    "prazo oficial"
                    if a.get("autoridade") == "institucional"
                    else "data para conferir"
                )
                linhas.append(
                    f"    {rotulo}: {quando} - {p['rotulo']}"
                )
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
    if data.get("status") == "coleta_degradada":
        return f"[Univesp {hoje:%d/%m}] leitura parcial, confira as fontes"
    # O assunto é o que ele vê primeiro: diz a decisão, não a contagem.
    # "2 coisas vencendo" era impreciso quando uma delas não tinha prazo.
    primeira = next((a for a in acoes if a["urgencia"] in ("hoje", "amanha")), None)
    if primeira:
        alvo = curto(primeira["o_que"], 34)
        if primeira.get("tipo") == "compromisso":
            quando_live = datetime.fromisoformat(primeira["prazo"])
            alvo = f"live {quando_live:%H:%M} ({alvo})"
        duro = next((a for a in acoes if a.get("prazo")
                     and a["urgencia"] in ("hoje", "amanha")), None)
        if duro is not None and duro is not primeira:
            q = datetime.fromisoformat(duro["prazo"])
            return (f"[Univesp {hoje:%d/%m}] Hoje: {primeira['curso']} {alvo}"
                    f"; entrega {q:%d/%m} {q:%H:%M}")
        return f"[Univesp {hoje:%d/%m}] Hoje: {primeira['curso']} {alvo}"
    # Sem nada urgente, "tudo em dia" no assunto escondia a única novidade do
    # dia quando o que mudou foi a nota. Nota entra no assunto só aqui, para
    # não empurrar prazo para baixo.
    notas = data.get("notas_novas") or []
    if notas:
        primeira_nota = notas[0]
        aviso = f"saiu nota em {primeira_nota['curso']} ({primeira_nota.get('nota')})"
        if len(notas) > 1:
            aviso = f"saiu nota em {len(notas)} atividades"
        if acoes:
            return f"[Univesp {hoje:%d/%m}] {aviso}; {len(acoes)} na fila"
        return f"[Univesp {hoje:%d/%m}] {aviso}"
    if acoes:
        return f"[Univesp {hoje:%d/%m}] {len(acoes)} na fila, nada urgente"
    return f"[Univesp {hoje:%d/%m}] tudo em dia"


def montar_falha(passo, run_url, idade_txt):
    """O e-mail que existe para o silêncio não parecer dia calmo.

    Se a rodada morre antes do passo de e-mail (dependência que não instala,
    Pages que não confirma, teste vermelho), nada chegava nele. E "nenhum
    e-mail" é exatamente igual a "nada pendente" na caixa de entrada. A Action
    ficava vermelha, mas isso só avisa quem lê notificação do GitHub.
    """
    hoje = datetime.now(BR_TZ)
    linhas = [
        f"Guia Univesp - o robô não conseguiu terminar - {hoje:%d/%m às %H:%M}",
        "",
        "Não confie na lista de hoje sem conferir no AVA.",
        "",
        f"Onde parou: {passo or 'não identificado'}.",
    ]
    if idade_txt:
        linhas.append(f"O site continua no ar, mas com o retrato de {idade_txt}.")
    linhas += [
        "",
        "O que fazer:",
        "1. Abrir o log da rodada e ver o passo vermelho:",
        f"   {run_url or 'https://github.com/esdraaline/mentor-univesp-com170/actions'}",
        "2. Se disser que a sessão do AVA expirou, rodar "
        "automacao/salvar_credenciais.bat.",
        "3. Se o site estiver velho demais, conferir prazo direto no AVA.",
        "",
        SITE,
    ]
    return "\n".join(linhas)


def idade_do_retrato():
    """Há quanto tempo é o retrato que está publicado, em palavras."""
    if not DATA_PATH.exists():
        return ""
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        quando = _quando(data.get("snapshot_at") or data.get("checked_at"))
        if quando is None:
            return ""
        horas = (datetime.now(timezone.utc) - quando).total_seconds() / 3600
    except Exception:
        return ""
    quando_br = quando.astimezone(BR_TZ)
    return f"{quando_br:%d/%m às %H:%M}, cerca de {int(horas)}h atrás"


def enviar(msg, host, porta, user, senha, para):
    with smtplib.SMTP(host, int(porta), timeout=45) as servidor:
        servidor.starttls(context=ssl.create_default_context())
        servidor.login(user, senha)
        servidor.send_message(msg)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Rodada intermediária: só fala se o AVA passou a mostrar prazo perto.
    modo_alerta = "--alerta" in argv
    modo_falha = "--falha" in argv
    host = os.environ.get("SMTP_HOST")
    porta = os.environ.get("SMTP_PORT", "587")
    user = os.environ.get("SMTP_USER")
    senha = os.environ.get("SMTP_PASS")
    para = os.environ.get("EMAIL_PARA")
    opcional = os.environ.get("EMAIL_OPCIONAL", "").lower() in ("1", "true", "sim")

    if not all([host, user, senha, para]):
        mensagem = "E-mail nao configurado (faltam SMTP_HOST/USER/PASS ou EMAIL_PARA)."
        if opcional:
            print(mensagem + " EMAIL_OPCIONAL ativo; sigo sem enviar.")
            return 0
        print(f"::error::{mensagem}")
        return 2
    hoje_str = datetime.now(BR_TZ).strftime("%Y-%m-%d")
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = para

    if modo_falha:
        # Este é o único modo que não depende do data.json: quando ele falta é
        # exatamente quando o aviso mais importa. Uma vez por dia basta; cinco
        # avisos iguais num dia ruim é o jeito de ele parar de ler o aviso.
        if (ULTIMA_FALHA_PATH.exists()
                and ULTIMA_FALHA_PATH.read_text(encoding="utf-8").strip() == hoje_str):
            print(f"Já avisei da falha hoje ({hoje_str}). Não repito.")
            return 0
        msg["Subject"] = (f"[Univesp {datetime.now(BR_TZ):%d/%m}] o robô não "
                          "conseguiu terminar")
        msg.set_content(montar_falha(
            os.environ.get("PASSO_FALHOU"),
            os.environ.get("RUN_URL"),
            idade_do_retrato(),
        ))
        try:
            enviar(msg, host, porta, user, senha, para)
            ULTIMA_FALHA_PATH.write_text(hoje_str, encoding="utf-8")
            print(f"Aviso de falha enviado para {para}.")
        except Exception as erro:
            print(f"::error::Nao consegui enviar o aviso de falha: {erro}")
            return 1
        return 0

    if not DATA_PATH.exists():
        mensagem = "Sem data.json, nao ha o que enviar."
        if opcional:
            print(mensagem + " EMAIL_OPCIONAL ativo; sigo sem enviar.")
            return 0
        print(f"::error::{mensagem}")
        return 2

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    if modo_alerta:
        # A trava diária não vale aqui: este e-mail existe justamente para o
        # que apareceu depois dela. Quem impede repetição é o registro de
        # prazo já avisado, no estado do coletor, não a data do envio.
        prazos = prazos_para_alertar(data)
        if not prazos:
            print("Nenhum prazo novo nas próximas "
                  f"{HORIZONTE_ALERTA_HORAS}h. Sigo sem enviar.")
            return 0
        if data.get("status") in ("session_expired", "coleta_incompleta"):
            print("Leitura não confiável nesta rodada; não alerto por e-mail "
                  "com dado velho.")
            return 0
        msg["Subject"] = assunto_alerta(prazos)
        msg.set_content(montar_alerta(data, prazos))
    else:
        # O publication_id e um timestamp, muda a cada execucao: nao serve pra
        # saber se ja mandei hoje. Reenvio (rerun manual, retry de job que falhou
        # depois deste passo) sem essa trava foi o que gerou 8 alertas iguais no
        # mesmo dia em 04/08/2026. A trava e por data de Brasilia, nao por conteudo:
        # a intencao e sempre um e-mail por dia, mesmo que o guia mude ao longo dele.
        if (ULTIMO_ENVIO_PATH.exists()
                and ULTIMO_ENVIO_PATH.read_text(encoding="utf-8").strip() == hoje_str):
            print(f"E-mail de hoje ({hoje_str}) ja foi enviado antes. Pulando para nao duplicar.")
            return 0
        msg["Subject"] = assunto(data)
        msg.set_content(montar_texto(data))

    try:
        enviar(msg, host, porta, user, senha, para)
        if not modo_alerta:
            # Só o resumo diário carimba a data. Se o alerta carimbasse, um
            # prazo publicado às 11h engoliria o e-mail da manhã seguinte.
            ULTIMO_ENVIO_PATH.write_text(hoje_str, encoding="utf-8")
        print(f"{'Alerta' if modo_alerta else 'E-mail'} enviado para {para}.")
    except Exception as e:
        # Antes devolvia 0 aqui "pra nao derrubar a Action". O efeito era pior:
        # o e-mail parava de chegar e nada avisava. Agora o passo fica vermelho.
        # O site nao se perde por isso, porque a publicacao acontece antes.
        print(f"::error::Nao consegui enviar o e-mail: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
