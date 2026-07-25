# -*- coding: utf-8 -*-
"""
Monta docs/index.html a partir de docs/data.json + docs/revisao.json.

A ordem da pagina segue a pergunta que o Josemar faz de verdade:
"o que eu tenho que fazer agora, e ate quando?"

  1. Recado da mentora (escrito na revisao semanal)
  2. AGORA: acoes em ordem de urgencia, com verbo, prazo e origem do prazo
  3. Chegou novo: avisos de forum, notificacoes e mensagens do AVA
  4. Mapa das disciplinas
  5. Ja encerrou (recolhido)
"""
import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DATA_PATH = DOCS / "data.json"
RECADO_PATH = DOCS / "revisao.json"

BR_TZ = timezone(timedelta(hours=-3))
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

GRUPOS = [
    ("hoje", "Vence hoje", "pend"),
    ("amanha", "Vence amanhã", "pend"),
    ("semana", "Nos próximos dias", "brick"),
    ("depois", "Mais pra frente", "lock"),
    ("sem_prazo", "Sem prazo definido", "neutral"),
]


def esc(s):
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()


def plural(n, singular, plural_):
    return f"{n} {singular if n == 1 else plural_}"


def fmt_dm(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m")
    except Exception:
        return ""


def fmt_dmhm(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m às %H:%M")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Recado da mentora (markdown minimalista)
# ---------------------------------------------------------------------------
def _inline(s):
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(s))


def _mini_md(texto):
    blocos, saida = re.split(r"\n\s*\n", (texto or "").strip()), []
    for b in blocos:
        linhas = [l.strip() for l in b.splitlines() if l.strip()]
        para, bullets = [], []

        def limpa():
            if para:
                saida.append(f"<p>{_inline(' '.join(para))}</p>")
                para.clear()
            if bullets:
                saida.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in bullets) + "</ul>")
                bullets.clear()

        for l in linhas:
            if l.startswith(("- ", "• ", "* ")):
                if para:
                    saida.append(f"<p>{_inline(' '.join(para))}</p>")
                    para.clear()
                bullets.append(l[2:].strip())
            else:
                if bullets:
                    saida.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in bullets) + "</ul>")
                    bullets.clear()
                para.append(l)
        limpa()
    return "".join(saida)


def render_recado():
    if not RECADO_PATH.exists():
        return ""
    try:
        r = json.loads(RECADO_PATH.read_text(encoding="utf-8"))
    except Exception:
        return ""
    texto = (r.get("text") or "").strip()
    if not texto:
        return ""
    quando = ""
    try:
        quando = datetime.fromisoformat(r["written_at"]).astimezone(BR_TZ).strftime("%d/%m/%Y às %H:%M")
    except Exception:
        pass
    rodape = f'<p class="recado-when">Escrito em {esc(quando)} (Brasília)</p>' if quando else ""
    return ('<div class="recado"><div class="recado-head"><span>📌</span>'
            '<span class="recado-label">Recado da mentora</span></div>'
            f'<div class="recado-body">{_mini_md(texto)}</div>{rodape}</div>')


# ---------------------------------------------------------------------------
# Bloco AGORA
# ---------------------------------------------------------------------------
def render_acao(a):
    chips = []
    cls = {"hoje": "pend", "amanha": "pend", "semana": "brick"}.get(a["urgencia"], "lock")
    if a.get("prazo_txt"):
        chips.append(f'<span class="status {cls}">{esc(a["prazo_txt"])}</span>')
    elif a.get("prioridade_ate"):
        # Não tem prazo próprio: herdou prioridade de uma etapa que tem. O chip
        # diz "faça antes de", nunca "vence", pra não inventar prazo oficial.
        chips.append(f'<span class="status {cls}">faça antes de '
                     f'{esc(fmt_dm(a["prioridade_ate"]))}</span>')
    if a.get("conta_nota"):
        chips.append('<span class="status ok">vale nota</span>')

    alvo = esc(a["o_que"])
    if a.get("url"):
        alvo = f'<a href="{esc(a["url"])}" target="_blank" rel="noopener">{alvo}</a>'

    # "Assista videoaula: S1 - Videoaulas" fica redundante: se o nome do item
    # ja diz o que e, o substantivo sai fora. Compara pela palavra principal
    # (a ultima), pra "do forum" casar com "Forum Tematico".
    coisa = a.get("coisa") or ""
    if coisa:
        principal = _sem_acento(coisa).split()[-1].rstrip("s")
        if len(principal) >= 4 and principal in _sem_acento(a["o_que"]):
            coisa = ""
    frase = f'<b>{esc(a["verbo"])}</b>{" " + esc(coisa) if coisa else ""}: {alvo}'

    if a.get("verificacao") == "indefinida":
        chips.append('<span class="status lock">não verifiquei</span>')

    trava = ""
    if a.get("destrava"):
        quando = fmt_dm(a.get("destrava_em")) if a.get("destrava_em") else ""
        trava = ('<div class="trava">🔑 Este não tem prazo próprio, mas é ele que '
                 f'destrava <b>{esc(a["destrava"])}</b>'
                 + (f', que vence {esc(quando)}' if quando else "")
                 + '. Por isso está aqui em cima.</div>')
    if a.get("bloqueio"):
        trava = (f'<div class="trava">🔒 Ainda não abriu: {esc(a["bloqueio"])}. '
                 'Corra os módulos anteriores pra destravar a tempo.</div>')

    rodape = [f'<b>{esc(a["curso"])}</b> · {esc(a["secao"])}']
    if a.get("prazo_fonte"):
        origem = f'prazo do {esc(a["prazo_fonte"])}'
        if a.get("fonte_url"):
            origem = f'<a href="{esc(a["fonte_url"])}" target="_blank" rel="noopener">{origem}</a>'
        rodape.append(origem)
    elif a.get("prioridade_ate"):
        rodape.append("sem prazo próprio no AVA")
    if a.get("carencia"):
        rodape.append(f'carência até {esc(fmt_dmhm(a["carencia"]))}')

    return (f'<li class="acao">'
            f'<div class="acao-chips">{"".join(chips)}</div>'
            f'<div class="acao-txt">{frase}</div>'
            f'{trava}'
            f'<div class="acao-pe">{" · ".join(rodape)}</div>'
            f'</li>')


def render_lista_acoes(acoes):
    partes = []
    for chave, titulo, _ in GRUPOS:
        do_grupo = [a for a in (acoes or []) if a["urgencia"] == chave]
        if not do_grupo:
            continue
        partes.append(f'<h3 class="grupo">{esc(titulo)} <span class="muted">'
                      f'{len(do_grupo)}</span></h3>')
        partes.append('<ul class="acoes">'
                      + "".join(render_acao(a) for a in do_grupo) + "</ul>")
    return "".join(partes)


def render_agora(data):
    acoes = data.get("acoes")
    if data.get("status") == "coleta_incompleta":
        # Nunca dizer "tudo em dia" quando a leitura falhou: o silêncio aqui
        # é justamente o que faria ele perder prazo achando que estava livre.
        motivos = "".join(f"<li>{esc(p)}</li>" for p in (data.get("problemas") or []))
        return ('<div class="bloco destaque"><h2>Não consegui ler o AVA agora</h2>'
                '<p class="sub" style="margin:0 0 8px;">A lista abaixo é do último '
                'retrato que deu certo, então <b>pode estar desatualizada</b>. '
                'Confira direto no AVA antes de confiar nela.</p>'
                f'<ul class="tasklist">{motivos}</ul></div>'
                + (render_lista_acoes(acoes) if acoes else ""))
    if acoes is None:
        # data.json ainda no formato antigo: o robo nao rodou com o motor novo.
        # Melhor dizer isso do que fingir que esta tudo em dia.
        return ('<div class="bloco destaque"><h2>O que fazer agora</h2>'
                '<p class="sub" style="margin:0;">Ainda não tenho a lista de tarefas desta '
                'versão. Ela aparece na primeira vez que o robô entrar no AVA com a sessão '
                'renovada. Enquanto isso, vale o recado acima e o mapa das disciplinas '
                'abaixo.</p></div>')
    if not acoes:
        return ('<div class="bloco destaque"><h2>O que fazer agora</h2>'
                '<p class="sub" style="margin:0;">Nada pendente. Tudo em dia. 🎉</p></div>')

    partes = [render_lista_acoes(acoes)]
    urgentes = sum(1 for a in acoes if a["urgencia"] in ("hoje", "amanha"))
    resumo = plural(len(acoes), "coisa na fila", "coisas na fila")
    if urgentes:
        resumo += ", " + plural(urgentes, "apertada", "apertadas")
    return ('<div class="bloco destaque">'
            f'<h2>O que fazer agora</h2>'
            f'<p class="sub" style="margin:0 0 10px;">{esc(resumo)}. '
            'Em ordem de urgência, com o prazo real lido do AVA.</p>'
            + "".join(partes) + "</div>")


# ---------------------------------------------------------------------------
# Bloco CHEGOU NOVO
# ---------------------------------------------------------------------------
def render_aviso(curso, a):
    quando = ""
    try:
        quando = datetime.fromisoformat(a["data"]).strftime("%d/%m às %H:%M")
    except Exception:
        pass
    titulo = esc(a.get("titulo") or "Post no fórum")
    if a.get("url"):
        titulo = f'<a href="{esc(a["url"])}" target="_blank" rel="noopener">{titulo}</a>'

    prazos = ""
    if a.get("prazos"):
        itens = "".join(
            f'<li><b>{"abre" if p.get("tipo") == "inicio" else "até"} '
            f'{esc(fmt_dmhm(p["quando"]))}</b> · {esc(p["rotulo"])}</li>'
            for p in a["prazos"][:5])
        prazos = f'<ul class="prazos-lidos">{itens}</ul>'

    links = ""
    quentes = [l for l in (a.get("links") or [])
               if any(k in l for k in ("elos.vc", "youtu", "meet.google", "teams."))]
    if quentes:
        links = ('<div class="acao-pe">🎥 ' + " · ".join(
            f'<a href="{esc(l)}" target="_blank" rel="noopener">gravação / sala</a>'
            for l in quentes[:2]) + "</div>")

    selo = '<span class="status pend">novo</span>' if a.get("novo") else ""
    return (f'<li class="aviso">'
            f'<div class="acao-chips"><span class="status brick">{esc(curso)}</span>{selo}'
            f'<span class="muted">{esc(a.get("forum") or "")} · {esc(quando)}</span></div>'
            f'<div class="acao-txt">{titulo}</div>'
            f'<p class="aviso-txt">{esc((a.get("texto") or "")[:300])}…</p>'
            f'{prazos}{links}</li>')


def render_novidades(data):
    # novos primeiro, depois os recentes que ainda valem (prazo ainda de pé)
    linhas = []
    for c in data.get("courses", []):
        for a in (c.get("avisos") or [])[:4]:
            linhas.append((0 if a.get("novo") else 1, a.get("data") or "",
                           render_aviso(c["code"], a)))
    linhas.sort(key=lambda x: x[1], reverse=True)   # mais recente primeiro
    linhas.sort(key=lambda x: x[0])                 # e os novos no topo (ordenacao estavel)
    avisos_html = "".join(h for _, _, h in linhas[:8])

    extras = []
    nao_lidas = [n for n in data.get("notificacoes", []) if not n.get("lida")]
    for n in nao_lidas[:6]:
        alvo = esc(n.get("assunto") or "")
        if n.get("url"):
            alvo = f'<a href="{esc(n["url"])}" target="_blank" rel="noopener">{alvo}</a>'
        extras.append(f'<li><span class="status lock">notificação</span>'
                      f'<span class="tlabel">{alvo}</span></li>')
    for m in data.get("mensagens", [])[:5]:
        extras.append(
            f'<li><span class="status pend">mensagem</span><span class="tlabel">'
            f'{m["nao_lidas"]} não lida(s) de <b>{esc(m["de"])}</b> · '
            f'<a href="{esc(m["url"])}" target="_blank" rel="noopener">abrir no AVA</a>'
            f'</span></li>')

    if not avisos_html and not extras:
        return ('<div class="bloco"><h2>Chegou novo</h2>'
                '<p class="sub" style="margin:0;">Nenhum post, notificação ou mensagem nova '
                'desde a última checagem.</p></div>')

    extras_html = f'<ul class="tasklist">{"".join(extras)}</ul>' if extras else ""
    return ('<div class="bloco"><h2>Chegou novo</h2>'
            '<p class="sub" style="margin:0 0 10px;">Fóruns, notificações e mensagens que '
            'apareceram desde a última leitura.</p>'
            f'<ul class="acoes">{avisos_html}</ul>{extras_html}</div>')


# ---------------------------------------------------------------------------
# Mapa das disciplinas
# ---------------------------------------------------------------------------
STATUS_CHIP = {
    "Concluído": ("ok", "Feito"),
    "Pendente": ("pend", "Pendente"),
    "Marcar como feito": ("lock", "A marcar"),
}


def render_secao(s):
    if s.get("locked"):
        return ('<details class="sec"><summary><span class="sec-head">'
                '<span class="chev"></span><span class="status lock">Bloqueado</span>'
                f'<span class="sec-title-txt">{esc(s["title"])}</span></span></summary>'
                f'<p class="sec-desc">{esc(s["locked"])}</p></details>')
    if not s["items"]:
        return ""
    tudo_feito = all(i.get("status") == "Concluído" for i in s["items"] if i.get("status"))
    tem_pend = any(i.get("status") == "Pendente" for i in s["items"])
    if tem_pend:
        chip, rot, aberto = "pend", "Pendente", True
    elif tudo_feito:
        chip, rot, aberto = "ok", "Feito", False
    else:
        chip, rot, aberto = "brick", "Em aberto", True

    li = []
    for it in s["items"]:
        cls, rotulo = STATUS_CHIP.get(it.get("status"), ("neutral", "—"))
        nome = esc(it["label"])
        if it.get("url"):
            nome = f'<a href="{esc(it["url"])}" target="_blank" rel="noopener">{nome}</a>'
        marca = ' <span class="muted">· vale nota</span>' if it.get("conta_nota") else ""
        li.append(f'<li><span class="status {cls}">{rotulo}</span>'
                  f'<span class="tlabel">{nome}{marca}</span></li>')

    tema = f'<p class="sec-desc">{esc(s["theme"])}</p>' if s.get("theme") else ""
    return (f'<details class="sec"{" open" if aberto else ""}><summary><span class="sec-head">'
            f'<span class="chev"></span><span class="status {chip}">{rot}</span>'
            f'<span class="sec-title-txt">{esc(s["title"])}</span>'
            f'<span class="muted"> · {len(s["items"])} itens</span>'
            f'</span></summary>{tema}'
            f'<ul class="tasklist">{"".join(li)}</ul></details>')


def render_cards(data):
    cards = []
    for c in data.get("courses", []):
        pct = c.get("progress_pct")
        pill = (f'<div class="progress-pill{" has-progress" if pct else ""}">'
                f'{pct if pct is not None else "?"}% concluído</div>')
        secoes = [s for s in c.get("sections", []) if s.get("fase") != "AIA"]
        corpo = "".join(render_secao(s) for s in secoes) or (
            '<p class="sub">Não consegui ler o conteúdo agora.</p>')
        crit = ""
        if c.get("links", {}).get("plano_ensino"):
            crit = (f'<p class="acao-pe"><a href="{esc(c["links"]["plano_ensino"])}" '
                    'target="_blank" rel="noopener">Plano de ensino</a></p>')
        cards.append(
            f'<div class="card"><div class="card-head"><div>'
            f'<h3>{esc(c["name"])}</h3><div class="code">{esc(c["code"])}</div></div>'
            f'{pill}</div>{crit}<div class="sections">{corpo}</div></div>')
    return "".join(cards)


def render_confirmar(data):
    """Prazos que o robô leu num aviso mas não tem certeza de a quem pertencem
    ou se são início ou fim. Ficam à vista, com a frase original, em vez de
    virarem tarefa com data que pode estar errada."""
    itens = data.get("confirmar") or []
    if not itens:
        return ""
    li = []
    for c in itens[:10]:
        origem = esc(f"aviso de {c['autor']}" if c.get("autor") else "aviso do fórum")
        if c.get("url"):
            origem = (f'<a href="{esc(c["url"])}" target="_blank" '
                      f'rel="noopener">{origem}</a>')
        rotulo = "abre" if c.get("tipo_lido") == "inicio" else "prazo"
        li.append(
            f'<li class="acao"><div class="acao-chips">'
            f'<span class="status lock">{esc(c["curso"])}</span>'
            f'<span class="status pend">{rotulo} {esc(fmt_dmhm(c["quando"]))}?</span>'
            f'</div><p class="aviso-txt">“{esc((c.get("frase") or "")[:200])}”</p>'
            f'<div class="acao-pe">{origem}</div></li>')
    return ('<div class="bloco"><h2>Confirme se isto é prazo mesmo</h2>'
            '<p class="sub" style="margin:0 0 10px;">Li estas datas em avisos, mas '
            'não tenho certeza a que atividade pertencem, ou se são de abertura ou '
            'de entrega. Preferi te mostrar a colocar na lista como se fosse '
            'certo. A frase é a original do aviso.</p>'
            f'<ul class="acoes">{"".join(li)}</ul></div>')


def render_higiene(data):
    """Itens sem prazo e sem peso na nota: 'S1 - Início', 'Em síntese',
    'Referências'. Ficam recolhidos pra não esconder o que vale nota."""
    itens = data.get("higiene") or []
    if not itens:
        return ""
    li = []
    for a in itens:
        nome = esc(a["o_que"])
        if a.get("url"):
            nome = f'<a href="{esc(a["url"])}" target="_blank" rel="noopener">{nome}</a>'
        li.append(f'<li><span class="status neutral">{esc(a["curso"])}</span>'
                  f'<span class="tlabel">{nome}</span></li>')
    return ('<details class="bloco"><summary class="enc-sum">'
            f'Higiene do AVA · {plural(len(itens), "item para marcar", "itens para marcar")}'
            '</summary><p class="sub">Não valem nota e não têm prazo. Servem só pra '
            'fechar a barra de progresso do Moodle.</p>'
            f'<ul class="tasklist">{"".join(li)}</ul></details>')


def render_encerrados(data):
    itens = data.get("encerrados") or []
    if not itens:
        return ""
    li = "".join(
        f'<li><span class="status lock">{esc(e.get("motivo") or "encerrado")}</span>'
        f'<span class="tlabel"><b>{esc(e["curso"])}</b> · {esc(e["o_que"])}</span></li>'
        for e in itens[:25])
    return ('<details class="bloco"><summary class="enc-sum">'
            f'Já encerrou · {plural(len(itens), "item que não dá", "itens que não dão")} '
            'mais pra enviar</summary>'
            f'<ul class="tasklist">{li}</ul>'
            '<p class="sub">Ficam aqui só pra registro. Se algum for importante, '
            'fale com o facilitador pelo fórum de dúvidas.</p></details>')


# ---------------------------------------------------------------------------
# Cabecalho
# ---------------------------------------------------------------------------
def linha_semana(data, hoje):
    crono = None
    for c in data.get("courses", []):
        if c.get("cronograma"):
            crono = c["cronograma"]
            break
    dia = DIAS[hoje.weekday()]
    if not crono:
        return f"Hoje é {dia}, {hoje:%d/%m}"
    for sem in crono["semanas"]:
        inicio = date.fromisoformat(sem["inicio"])
        venc = datetime.fromisoformat(sem["vencimento"]).date()
        if inicio <= hoje <= venc:
            extra = ""
            if sem.get("carencia"):
                extra = f", carência até {fmt_dm(sem['carencia'])}"
            return (f"Hoje é {dia}, {hoje:%d/%m} · Semana {sem['n']} do bimestre "
                    f"(vence {fmt_dm(sem['vencimento'])}{extra})")
    return f"Hoje é {dia}, {hoje:%d/%m}"


def frescor(data):
    """Quão velho é este retrato, dito com franqueza.

    O site é aberto na hora de estudar, não às 8h. Depois que ele avança no
    AVA, a lista envelhece: já chegou a mandar refazer atividade concluída.
    Como a página é estática, ela não tem como saber disso sozinha; o mínimo
    é não usar o presente ("faça agora") sobre um retrato de horas atrás.
    """
    try:
        lido = datetime.fromisoformat(data.get("checked_at", "")).astimezone(BR_TZ)
    except Exception:
        return "", ""
    horas = (datetime.now(BR_TZ) - lido).total_seconds() / 3600
    quando = lido.strftime("%d/%m às %H:%M")
    if horas < 3:
        return f"Li o AVA {quando}", ""
    aviso = (f'<div class="alertbar">Este retrato é de <b>{esc(quando)}</b>, '
             f'cerca de {int(horas)}h atrás. Se você estudou depois disso, '
             'confira no AVA antes de confiar na lista.</div>')
    return f"Li o AVA {quando}", aviso


def render_html(data):
    checado = data.get("checked_at", "")
    try:
        checado = datetime.fromisoformat(checado).astimezone(BR_TZ).strftime("%d/%m/%Y às %H:%M")
    except Exception:
        pass

    _, banner_idade = frescor(data)
    banner = banner_idade
    if data.get("status") == "session_expired":
        banner = ('<div class="alertbar"><b>Sessão do AVA expirou.</b> Este retrato é o '
                  'último válido. Dê 2 cliques em <code>automacao/renovar_sessao.bat</code> '
                  'pra renovar (abre o navegador, você loga, o resto acontece sozinho).</div>')

    hoje = datetime.now(BR_TZ).date()
    html = (TEMPLATE
            .replace("{{SEMANA}}", esc(linha_semana(data, hoje)))
            .replace("{{CHECKED_AT}}", esc(checado))
            .replace("{{BANNER}}", banner)
            .replace("{{RECADO}}", render_recado())
            .replace("{{AGORA}}", render_agora(data))
            .replace("{{CONFIRMAR}}", render_confirmar(data))
            .replace("{{NOVIDADES}}", render_novidades(data))
            .replace("{{CARDS}}", render_cards(data))
            .replace("{{HIGIENE}}", render_higiene(data))
            .replace("{{ENCERRADOS}}", render_encerrados(data)))
    (DOCS / "index.html").write_text(html, encoding="utf-8")


TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guia diário — Univesp</title>
<style>
  :root{
    --bg:#faf9f5; --paper:#ffffff; --ink:#201f1c; --ink-soft:#5c584f; --line:#e7e2d7;
    --brick:#a3222c; --brick-soft:#f3e2df; --ok:#2f6b4f; --ok-bg:#e7f1ea;
    --wait:#8a5a15; --wait-bg:#f6ecd8; --locked:#8b8578; --locked-bg:#eeece4;
    --shadow: 0 1px 2px rgba(32,31,28,.06), 0 6px 20px rgba(32,31,28,.05);
  }
  :root[data-theme="dark"], .dark-vars{}
  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]){
      --bg:#171613; --paper:#201f1b; --ink:#f2efe6; --ink-soft:#b8b2a3; --line:#3a362d;
      --brick:#e2777c; --brick-soft:#3a2222; --ok:#7fcba3; --ok-bg:#1f3129;
      --wait:#e3b463; --wait-bg:#3a2f19; --locked:#87816f; --locked-bg:#2a2820;
      --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.35);
    }
  }
  :root[data-theme="dark"]{
    --bg:#171613; --paper:#201f1b; --ink:#f2efe6; --ink-soft:#b8b2a3; --line:#3a362d;
    --brick:#e2777c; --brick-soft:#3a2222; --ok:#7fcba3; --ok-bg:#1f3129;
    --wait:#e3b463; --wait-bg:#3a2f19; --locked:#87816f; --locked-bg:#2a2820;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.35);
  }
  *{box-sizing:border-box;}
  body{margin:0;background:var(--bg);color:var(--ink);
       font-family:ui-sans-serif,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
       line-height:1.5;padding:18px 14px 60px;}
  h1,h2,h3{font-family:Georgia,"Times New Roman",ui-serif,serif;font-weight:700;
           text-wrap:balance;margin:0;}
  a{color:inherit;}
  .wrap{max-width:580px;margin:0 auto;}
  .eyebrow{font-size:12px;letter-spacing:.09em;text-transform:uppercase;
           color:var(--brick);font-weight:700;margin-bottom:8px;}
  h1{font-size:24px;line-height:1.15;}
  .sub{color:var(--ink-soft);font-size:14px;margin-top:8px;}
  .semana-line{font-size:13px;font-weight:600;margin-top:6px;}
  .alertbar{background:var(--wait-bg);color:var(--wait);border-radius:12px;
            padding:12px 14px;font-size:13.5px;margin:16px 0;}
  .alertbar code{background:rgba(0,0,0,.08);padding:1px 5px;border-radius:5px;}
  .recado{background:var(--brick-soft);border:1px solid var(--brick);border-radius:14px;
          padding:16px;box-shadow:var(--shadow);margin:18px 0 22px;}
  .recado-head{display:flex;align-items:center;gap:8px;margin-bottom:8px;}
  .recado-label{font-size:12px;letter-spacing:.08em;text-transform:uppercase;
                color:var(--brick);font-weight:700;}
  .recado-body p{margin:0 0 8px;font-size:14px;}
  .recado-body ul{margin:6px 0 8px;padding-left:20px;}
  .recado-body li{font-size:14px;margin-bottom:4px;}
  .recado-when{margin:10px 0 0;font-size:11.5px;color:var(--ink-soft);}
  .bloco{background:var(--paper);border:1px solid var(--line);border-radius:14px;
         padding:16px;box-shadow:var(--shadow);margin:18px 0;}
  .bloco.destaque{border-color:var(--brick);}
  .bloco h2{font-size:17px;margin-bottom:6px;}
  .grupo{font-size:12px;letter-spacing:.06em;text-transform:uppercase;
         color:var(--brick);margin:14px 0 6px;}
  .grupo .muted{color:var(--ink-soft);font-weight:400;}
  .acoes{list-style:none;margin:0;padding:0;}
  .acao,.aviso{padding:10px 0;border-top:1px solid var(--line);}
  .acoes li:first-child{border-top:none;}
  .acao-chips{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:5px;}
  .acao-txt{font-size:14.5px;line-height:1.45;}
  .acao-pe{font-size:11.5px;color:var(--ink-soft);margin-top:4px;}
  .aviso-txt{font-size:12.5px;color:var(--ink-soft);margin:5px 0 0;line-height:1.45;}
  .trava{font-size:12px;color:var(--wait);background:var(--wait-bg);border-radius:8px;
         padding:6px 9px;margin-top:6px;line-height:1.4;}
  .prazos-lidos{list-style:none;margin:6px 0 0;padding:6px 10px;border-radius:8px;
                background:var(--wait-bg);}
  .prazos-lidos li{font-size:12px;color:var(--wait);padding:2px 0;}
  .card{background:var(--paper);border:1px solid var(--line);border-radius:14px;
        padding:16px;margin-bottom:14px;box-shadow:var(--shadow);}
  .card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;}
  .card h3{font-size:16px;}
  .code{font-size:12px;color:var(--ink-soft);font-weight:600;}
  .progress-pill{font-size:11px;font-weight:700;padding:3px 8px;border-radius:99px;
                 white-space:nowrap;background:var(--locked-bg);color:var(--locked);}
  .progress-pill.has-progress{background:var(--ok-bg);color:var(--ok);}
  .sections{margin-top:6px;}
  .sec{border-top:1px solid var(--line);}
  .sec:first-child{border-top:none;}
  .sec > summary{list-style:none;cursor:pointer;padding:11px 0;display:block;}
  .sec > summary::-webkit-details-marker{display:none;}
  .sec-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
  .chev{flex:0 0 auto;width:0;height:0;border-left:6px solid var(--ink-soft);
        border-top:5px solid transparent;border-bottom:5px solid transparent;
        transition:transform .18s ease;}
  details[open] > summary .chev{transform:rotate(90deg);}
  .sec-title-txt{font-weight:700;font-size:14px;}
  .muted{color:var(--ink-soft);font-size:12px;font-weight:400;}
  .sec-desc{margin:2px 0 10px 22px;font-size:12.5px;color:var(--ink-soft);}
  .tasklist{list-style:none;margin:0 0 10px;padding:0;}
  .tasklist li{display:flex;align-items:flex-start;gap:9px;padding:6px 0;
               font-size:14px;border-top:1px solid var(--line);}
  .tasklist li:first-child{border-top:none;}
  .tlabel{flex:1;}
  .status{flex:0 0 auto;margin-top:2px;font-size:10.5px;font-weight:700;
          text-transform:uppercase;padding:2px 7px;border-radius:6px;white-space:nowrap;}
  .status.pend{background:var(--wait-bg);color:var(--wait);}
  .status.ok{background:var(--ok-bg);color:var(--ok);}
  .status.lock{background:var(--locked-bg);color:var(--locked);}
  .status.brick{background:var(--brick-soft);color:var(--brick);}
  .status.neutral{background:var(--locked-bg);color:var(--ink-soft);}
  .enc-sum{cursor:pointer;font-weight:700;font-size:14px;
           font-family:Georgia,ui-serif,serif;}
  @media (prefers-reduced-motion: reduce){.chev{transition:none;}}
  footer{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);
         font-size:12px;color:var(--ink-soft);text-align:center;}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">Univesp · BIA · Turma 001</div>
  <h1>Guia diário do AVA</h1>
  <p class="semana-line">{{SEMANA}}</p>
  <p class="sub">Releio o AVA várias vezes ao dia · última leitura: {{CHECKED_AT}} (Brasília)</p>
  {{BANNER}}
  {{RECADO}}
  {{AGORA}}
  {{CONFIRMAR}}
  {{NOVIDADES}}
  <h2 class="grupo" style="margin-top:26px;">Mapa das disciplinas</h2>
  {{CARDS}}
  {{HIGIENE}}
  {{ENCERRADOS}}
  <footer>Um robô lê o AVA todo dia: páginas das disciplinas, calendário, todos os fóruns,
  notificações e mensagens. Prazo só aparece aqui com a origem à mostra.<br>
  Nenhuma data é chutada: se não achei prazo oficial, digo que não tem.</footer>
</div>
</body>
</html>
"""


def main():
    if not DATA_PATH.exists():
        print("Sem data.json para renderizar.")
        return 1
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    render_html(data)
    print("Site gerado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
