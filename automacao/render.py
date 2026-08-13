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
import os
import re
import tempfile
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
    # Neutro de propósito: o grupo mistura entrega que vence com live que
    # acontece. Cada linha já diz o seu ("vence hoje" / "acontece hoje às 14h").
    ("hoje", "Para hoje", "pend"),
    ("amanha", "Para amanhã", "pend"),
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


def _cmids_pendentes(data):
    return {
        str(it.get("cmid"))
        for c in data.get("courses", [])
        for s in c.get("sections", [])
        for it in s.get("items", [])
        if it.get("cmid") is not None and it.get("status") != "Concluído"
    }


# Quantos dias o aviso de "aquele recado venceu" continua valendo a pena.
DIAS_DE_RECADO_ARQUIVADO = 3


def _recado_vencido_ha_muito(recado, agora=None):
    """O recado é velho demais até para anunciar que venceu?

    Conta a partir da validade quando ela existe; sem validade, da escrita.
    Sem nenhuma das duas datas, responde ``False``: sem saber a idade, o
    caminho seguro é continuar mostrando.
    """
    agora = agora or datetime.now(BR_TZ)
    for campo in ("valid_until", "written_at"):
        bruto = recado.get(campo)
        if not bruto:
            continue
        try:
            quando = datetime.fromisoformat(bruto).astimezone(BR_TZ)
        except Exception:
            continue
        return (agora - quando).days > DIAS_DE_RECADO_ARQUIVADO
    return False


def render_recado(data):
    if not RECADO_PATH.exists():
        return ""
    try:
        r = json.loads(RECADO_PATH.read_text(encoding="utf-8"))
    except Exception:
        return ""
    texto = (r.get("text") or "").strip()
    if not texto:
        return ""
    motivos = []
    exigidos = {str(x) for x in (r.get("requires_pending_cmids") or [])}
    if exigidos and not exigidos.issubset(_cmids_pendentes(data)):
        motivos.append("a atividade citada já mudou de estado")
    if r.get("valid_until"):
        try:
            if datetime.now(BR_TZ) > datetime.fromisoformat(r["valid_until"]).astimezone(BR_TZ):
                motivos.append("a validade do recado terminou")
        except Exception:
            motivos.append("a validade do recado não pôde ser verificada")
    if motivos:
        # Dizer "o recado de ontem não vale mais" é útil por alguns dias;
        # depois disso é uma aba que não informa nada. A de 25/07 ficou no ar
        # 18 dias anunciando o próprio vencimento. Passada a carência, o
        # recado some junto com a aba, e a fila fala por si.
        if _recado_vencido_ha_muito(r):
            return ""
        return (
            '<div class="bloco recado-antigo">'
            '<p class="recado-antigo-tag">Recado anterior arquivado automaticamente</p>'
            f'<p class="sub" style="margin:0;">{esc("; ".join(motivos).capitalize())}. '
            'A aba "O que fazer agora" já usa a leitura mais recente do AVA.</p></div>'
        )
    quando = ""
    try:
        quando = datetime.fromisoformat(r["written_at"]).astimezone(BR_TZ).strftime("%d/%m/%Y às %H:%M")
    except Exception:
        pass
    rodape = f'<p class="recado-when">Escrito em {esc(quando)} (Brasília)</p>' if quando else ""
    return ('<div class="recado"><div class="recado-head"><span>📌</span>'
            '<span class="recado-label">Recado da mentora</span></div>'
            f'<div class="recado-body">{_mini_md(texto)}</div>{rodape}</div>')


def render_fontes_status(data):
    estados = (
        data.get("fontes_status_tentativa")
        if data.get("status") in ("coleta_incompleta", "session_expired")
        else data.get("fontes_status")
    ) or {}
    if not estados:
        return ""
    nomes = {
        "disciplinas": "disciplinas",
        "calendario": "calendário",
        "cronograma": "cronogramas",
        "foruns": "fóruns",
        "itens": "itens",
        "notificacoes": "notificações",
        "boletim": "boletins",
        "participacao": "progresso de participação",
    }
    # Esta linha existe pra responder "posso confiar no que estou lendo?".
    # A primeira versão saía em idioma de programador ("foruns: live (60,
    # truncado, último ao vivo 20:46)") e o dono do projeto, que não é dev,
    # precisou perguntar o que significava. Agora: uma frase no caso normal,
    # e nome aos bois quando alguma fonte falha.
    # Boletim e participação ficavam de fora desta linha, então podiam falhar
    # dias seguidos enquanto a frase continuava dizendo "li tudo agora, sem
    # reaproveitar dados antigos". Oito fontes lidas, oito fontes declaradas.
    ordem = ("disciplinas", "calendario", "cronograma", "foruns", "itens",
             "notificacoes", "boletim", "participacao")
    quantidades = {
        "disciplinas": "{n} disciplinas",
        "calendario": "{n} prazos no calendário",
        "cronograma": "{n} cronogramas",
        "itens": "{n} atividades conferidas",
        "notificacoes": "{n} notificações",
        "boletim": "{n} notas no boletim",
        "participacao": "{n} quinzenas de participação",
    }

    horas, numeros, falhas, parciais, truncadas = set(), [], [], [], []
    for chave in ordem:
        info = estados.get(chave) or {}
        if not info.get("status"):
            continue
        if info.get("status") == "nao_aplicavel":
            # Disciplina nenhuma tem essa fonte nesta leitura. Contar "0" aqui
            # pareceria perda de dado onde não há dado a perder.
            continue
        quando = ""
        if info.get("last_live_at"):
            try:
                quando = datetime.fromisoformat(info["last_live_at"]).astimezone(
                    BR_TZ).strftime("%H:%M")
                horas.add(quando)
            except Exception:
                pass
        if info.get("quantidade_atual") is not None:
            quantidade = info["quantidade_atual"]
            if chave == "foruns":
                total_foruns = info.get("foruns")
                complemento = ""
                if total_foruns is not None:
                    rotulo = "fórum" if total_foruns == 1 else "fóruns"
                    complemento = f" em {total_foruns} {rotulo}"
                numeros.append(
                    f"{quantidade} publicações selecionadas{complemento}"
                )
            else:
                numeros.append(quantidades[chave].format(n=quantidade))
        status = info.get("status")
        if info.get("from_cache") or status in ("falhou", "degradado"):
            falhas.append((nomes[chave], quando, bool(info.get("from_cache"))))
        elif status == "parcial":
            parciais.append(nomes[chave])
        if info.get("truncado"):
            # Cada corte tem um motivo diferente e uma consequência diferente:
            # post que ficou de fora é ruído perdido, atividade que ficou sem
            # conferência é obrigação dele que o guia não olhou.
            if chave == "itens":
                quantos = info.get("nao_conferidos")
                truncadas.append(
                    f"{quantos} atividade(s) ficaram sem conferência de "
                    "abertura nesta leitura, por limite de tempo da rodada; "
                    "elas continuam na lista, só não tive como confirmar se "
                    "ainda estão abertas"
                    if quantos
                    else "algumas atividades ficaram sem conferência"
                )
            else:
                truncadas.append(
                    f"nos {nomes[chave]} havia mais posts do que eu guardo, "
                    "então fiquei com os mais importantes"
                )

    if not numeros and not falhas and not parciais:
        return ""

    detalhes = ""
    if numeros:
        extra = "".join(
            f" {esc(frase[0].upper() + frase[1:])}." for frase in truncadas
        )
        detalhes = (f'<details class="fontes-det"><summary>o que eu li</summary>'
                    f'<p>{esc(", ".join(numeros))}.{extra}</p></details>')

    if falhas:
        quais = ", ".join(nome for nome, _, _ in falhas)
        caches = [
            f"{nome} (última leitura boa às {hora})" if hora else nome
            for nome, hora, usou_cache in falhas if usou_cache
        ]
        cache_txt = (
            f' Mantive o dado anterior de {esc(", ".join(caches))}.'
            if caches else ""
        )
        parcial_txt = (
            f' A leitura de {esc(", ".join(parciais))} também ficou incompleta.'
            if parciais else ""
        )
        return ('<div class="sourcebar degraded">'
                f'<b>Atenção:</b> houve falha ao atualizar: {esc(quais)}.'
                f'{cache_txt}{parcial_txt} Confira essa parte no AVA.'
                f'{detalhes}</div>')

    if parciais:
        return ('<div class="sourcebar degraded">'
                f'<b>Leitura parcial:</b> li agora, mas não consegui cobrir '
                f'completamente: {esc(", ".join(parciais))}. Confira essa parte '
                f'no AVA.{detalhes}</div>')

    hora = f" às {sorted(horas)[-1]}" if horas else ""
    return ('<div class="sourcebar">'
            f'Li as fontes do AVA agora{esc(hora)}, sem reaproveitar dados antigos.'
            f'{detalhes}</div>')


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
    if a.get("autoridade") == "institucional":
        chips.append('<span class="status ok">aviso oficial</span>')

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
    if a.get("entrega_nao_confirmada"):
        chips.append('<span class="status pend">sem entrega registrada</span>')
    if a.get("resgatado"):
        # Veio pela rede de segurança: o calendário tinha o prazo, a leitura da
        # disciplina não trouxe a atividade. Melhor mostrar demais que de menos.
        chips.append('<span class="status lock">achei no calendário</span>')

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
    if a.get("explicacao"):
        # Aviso que não nasce de um item do AVA e por isso precisa dizer, no
        # próprio cartão, por que está ali.
        trava += f'<div class="trava">👥 {esc(a["explicacao"])}</div>'
    if a.get("entrega_nao_confirmada"):
        # O selo verde do AVA aqui é de "visualizou", não de "entregou". Se o
        # guia repetisse o selo, você só descobriria pela nota que faltou.
        trava += ('<div class="trava">⚠️ O AVA marca esta atividade como '
                  '<b>concluída</b>, mas não encontrei nota lançada nem '
                  'tentativa registrada. Nessas atividades a conclusão fecha '
                  'só por abrir a página. Abra e confirme que você respondeu '
                  'e enviou.</div>')

    # Um mesmo encontro anunciado em vários horários: o aviso pede pra
    # escolher um, então o cartão mostra as opções em vez de virar seis
    # compromissos separados na fila.
    opcoes = a.get("opcoes") or []
    if len(opcoes) > 1:
        linhas = "".join(
            f'<li>{esc(o.get("prazo_txt") or "")}'
            + (f' — {esc(o["o_que"])}' if o.get("o_que") else "")
            + "</li>"
            for o in opcoes
        )
        trava += ('<div class="trava">🗓️ Mesmo encontro, vários horários. '
                  'Participe do que couber na sua agenda:'
                  f'<ul class="tasklist">{linhas}</ul></div>')
    if a.get("repete", 1) > 1:
        restantes = a["repete"] - 1
        trava += ('<div class="trava">🔁 Se repete: mais '
                  + (f'{restantes} encontros iguais' if restantes > 1
                     else 'um encontro igual')
                  + ' adiante no calendário.</div>')

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
        return ('<div class="bloco destaque">'
                '<p class="sub" style="margin:0 0 8px;"><b>Não consegui ler o AVA agora.</b> '
                'A lista abaixo é do último retrato que deu certo, então '
                '<b>pode estar desatualizada</b>. Confira direto no AVA antes de confiar nela.</p>'
                f'<ul class="tasklist">{motivos}</ul></div>'
                + (render_lista_acoes(acoes) if acoes else ""))
    if acoes is None:
        # data.json ainda no formato antigo: o robo nao rodou com o motor novo.
        # Melhor dizer isso do que fingir que esta tudo em dia.
        return ('<div class="bloco destaque">'
                '<p class="sub" style="margin:0;">Ainda não tenho a lista de tarefas desta '
                'versão. Ela aparece na primeira vez que o robô entrar no AVA com a sessão '
                'renovada. Enquanto isso, vale abrir as abas "Recado" e "Mapa das '
                'disciplinas".</p></div>')
    if not acoes:
        return ('<div class="bloco destaque">'
                '<p class="sub" style="margin:0;">Nada pendente. Tudo em dia. 🎉</p></div>')

    partes = [render_lista_acoes(acoes)]
    urgentes = sum(1 for a in acoes if a["urgencia"] in ("hoje", "amanha"))
    resumo = plural(len(acoes), "coisa na fila", "coisas na fila")
    if urgentes:
        resumo += ", " + plural(urgentes, "apertada", "apertadas")
    return ('<div class="bloco destaque">'
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
    institucional = a.get("autoridade") == "institucional"
    autoridade = (
        '<span class="status ok">aviso oficial</span>'
        if institucional
        else '<span class="status neutral">post de colega</span>'
    )
    classe = "aviso oficial" if institucional else "aviso colega"
    return (f'<li class="{classe}">'
            f'<div class="acao-chips"><span class="status brick">{esc(curso)}</span>{selo}'
            f'{autoridade}'
            f'<span class="muted">{esc(a.get("forum") or "")} · {esc(quando)}</span></div>'
            f'<div class="acao-txt">{titulo}</div>'
            f'<p class="aviso-txt">{esc((a.get("texto") or "")[:300])}…</p>'
            f'{prazos}{links}</li>')


def _dias_para_evento(aviso):
    """Extrai a data mais proxima mencionada no texto do aviso.
    Retorna o numero de dias ate o evento (0 = hoje, 1 = amanha, etc).
    Retorna 999 se nao houver data explicita no texto.
    """
    texto = aviso.get("texto") or ""
    titulo = aviso.get("titulo") or ""
    combinado = f"{titulo} {texto}"
    hoje = date.today()
    dias = 999
    # Padrao DD/MM
    for m in re.finditer(r"(\d{1,2})/(\d{1,2})(?:/\d{4})?", combinado):
        try:
            d, mes = int(m.group(1)), int(m.group(2))
            candidato = date(hoje.year, mes, d)
            if candidato < hoje:
                candidato = date(hoje.year + 1, mes, d)
            delta = (candidato - hoje).days
            if 0 <= delta < dias:
                dias = delta
        except ValueError:
            continue
    # Padrao DD de Mes
    meses_br = {
        "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5,
        "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
        "novembro": 11, "dezembro": 12, "jan": 1, "fev": 2, "mar": 3,
        "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9,
        "out": 10, "nov": 11, "dez": 12,
    }
    for m in re.finditer(r"(\d{1,2})(?:\u00ba|\u00aa)?\s+(?:de\s+)?(\w+)", combinado, re.IGNORECASE):
        try:
            d, mes_nome = int(m.group(1)), m.group(2).lower().strip(".")
            mes_num = meses_br.get(mes_nome)
            if mes_num is None:
                continue
            candidato = date(hoje.year, mes_num, d)
            if candidato < hoje:
                candidato = date(hoje.year + 1, mes_num, d)
            delta = (candidato - hoje).days
            if 0 <= delta < dias:
                dias = delta
        except (ValueError, KeyError):
            continue
    return dias


_MAX_DIAS_URGENTE = 4  # hoje + 3 dias para frente


def render_nota_nova(n):
    """Uma linha de nota que saiu ou mudou desde a leitura anterior."""
    nome = esc(n.get("label") or "")
    if n.get("url"):
        nome = (f'<a href="{esc(n["url"])}" target="_blank" rel="noopener">'
                f'{nome}</a>')
    if n.get("de"):
        motivo = (f'a nota mudou de {esc(n["de"])} para '
                  f'{esc(n.get("nota") or "")}')
    else:
        motivo = "saiu a nota desta atividade"
    devolutiva = ""
    if n.get("feedback"):
        devolutiva = f'<div class="trava">💬 {esc(n["feedback"][:600])}</div>'
    return (f'<li class="acao"><div class="acao-chips">'
            f'<span class="status ok">{esc(n.get("nota") or "")}</span>'
            f'<span class="status lock">{esc(n.get("curso") or "")}</span>'
            f'</div><div class="acao-txt">{nome}</div>'
            f'<div class="acao-pe">{motivo}</div>{devolutiva}</li>')


def render_prazo_novo(p):
    """Uma linha de prazo que o AVA passou a mostrar."""
    nome = esc(p.get("label") or "")
    if p.get("url"):
        nome = (f'<a href="{esc(p["url"])}" target="_blank" rel="noopener">'
                f'{nome}</a>')
    try:
        quando = datetime.fromisoformat(p["prazo"]).astimezone(BR_TZ)
        momento = f"{quando:%d/%m às %H:%M}"
    except (KeyError, TypeError, ValueError):
        momento = esc(str(p.get("prazo") or ""))
    if p.get("de"):
        try:
            antes = datetime.fromisoformat(p["de"]).astimezone(BR_TZ)
            motivo = f"antes era {antes:%d/%m às %H:%M}"
        except (TypeError, ValueError):
            motivo = "a data mudou"
    elif p.get("atividade_nova"):
        motivo = "atividade nova, já com prazo"
    else:
        motivo = "o AVA passou a mostrar prazo nesta atividade"
    if p.get("fonte"):
        motivo += f' · fonte: {esc(p["fonte"])}'
    chips = f'<span class="status pend">{esc(momento)}</span>'
    if p.get("conta_nota"):
        chips += '<span class="status lock">vale nota</span>'
    return (f'<li class="acao"><div class="acao-chips">{chips}</div>'
            f'<div class="acao-txt">{esc(p.get("curso") or "")} · {nome}</div>'
            f'<div class="acao-pe">{motivo}</div></li>')


def secao_novidade(titulo, linhas_html):
    """Um bloco da aba "Chegou novo", com o respiro que o separa do de cima."""
    return (f'<p class="sub secao-novidade">{titulo}</p>'
            f'<ul class="acoes">{linhas_html}</ul>')


def render_prazos_novos(data):
    prazos = data.get("prazos_novos") or []
    if not prazos:
        return ""
    rotulo = "Prazo novo" if len(prazos) == 1 else "Prazos novos"
    return secao_novidade(
        f"{rotulo} desde a leitura anterior.",
        "".join(render_prazo_novo(p) for p in prazos[:10]),
    )


def agrupar_itens_novos(data):
    """Atividades novas juntadas por disciplina e seção.

    Uma semana que abre traz vinte itens de uma vez. Vinte linhas soltas viram
    parede e escondem o que interessa, que é "a Semana 4 do COM100 abriu".
    """
    grupos = {}
    for novo in data.get("novidades") or []:
        # O formato antigo trazia item concluído e post de fórum misturados,
        # marcados por "kind". Sem esta linha, no primeiro dia da mudança o
        # data.json ainda velho faria a aba anunciar título de post como se
        # fosse atividade nova.
        if novo.get("kind") is not None and novo.get("kind") != "novo":
            continue
        grupos.setdefault(
            (novo.get("curso") or "", novo.get("secao") or ""), []
        ).append(novo)
    return grupos


def render_itens_novos(data):
    grupos = agrupar_itens_novos(data)
    if not grupos:
        return ""
    linhas = []
    for (codigo, secao), itens in list(grupos.items())[:8]:
        quantas = len(itens)
        titulo = f"{esc(codigo)}"
        if secao:
            titulo += f' · {esc(secao)}'
        exemplos = ", ".join(esc(i.get("label") or "") for i in itens[:3])
        if quantas > 3:
            exemplos += f" e mais {quantas - 3}"
        linhas.append(
            f'<li class="acao"><div class="acao-chips">'
            f'<span class="status pend">{quantas}</span></div>'
            f'<div class="acao-txt">{titulo}</div>'
            f'<div class="acao-pe">{exemplos}</div></li>'
        )
    rotulo = ("Atividade nova no AVA" if len(grupos) == 1
              else "Atividades novas no AVA")
    return secao_novidade(f"{rotulo} desde a leitura anterior.",
                          "".join(linhas))


def contar_novidades(data):
    """O número no rótulo da aba. Tem que contar tudo o que a aba mostra."""
    novos = sum(
        1 for c in data.get("courses", []) or []
        for a in (c.get("avisos") or [])
        if a.get("novo")
    )
    nao_lidas = len(
        [n for n in data.get("notificacoes") or [] if not n.get("lida")]
    )
    mensagens = sum(m.get("nao_lidas", 0) for m in data.get("mensagens") or [])
    # Atividade nova conta por grupo, não por item: uma semana que abre com
    # vinte itens é uma novidade para ele, não vinte.
    return (novos + nao_lidas + mensagens
            + len(data.get("notas_novas") or [])
            + len(data.get("prazos_novos") or [])
            + len(agrupar_itens_novos(data)))


def render_novidades(data):
    hoje = date.today()
    # Nota é a novidade que muda o resultado dele, e até 10/08/2026 o guia
    # mostrava a nota na aba "Como estou" sem nunca dizer que ela tinha
    # acabado de sair.
    notas = data.get("notas_novas") or []
    notas_html = ""
    if notas:
        quantas = len(notas)
        notas_html = secao_novidade(
            f'{"Saiu nota nova" if quantas == 1 else "Saíram notas novas"} '
            "desde a leitura anterior.",
            "".join(render_nota_nova(n) for n in notas[:12]),
        )
    # --- Fase 1: coletar candidatos (sem corte por disciplina para urgentes) ---
    linhas = []
    for c in data.get("courses", []):
        for a in (c.get("avisos") or [])[:12]:  # aumentado de 4 para 12 para capturar mais
            dias_evento = _dias_para_evento(a)
            urgente = dias_evento <= _MAX_DIAS_URGENTE
            autoridade = 0 if a.get("autoridade") == "institucional" else 1
            # Prioridade: urgente=0, depois autoridade, depois novo, depois data
            prioridade = (
                0 if urgente else 1,
                autoridade,
                0 if a.get("novo") else 1,
            )
            linhas.append((prioridade, urgente, dias_evento,
                           a.get("data") or "",
                           render_aviso(c["code"], a)))
    # --- Fase 2: separar urgentes dos nao-urgentes ---
    urgentes = [linha for linha in linhas if linha[1]]     # linha[1] = urgente bool
    nao_urgentes = [linha for linha in linhas if not linha[1]]
    # --- Fase 3: ordenar dentro de cada grupo ---
    nao_urgentes.sort(key=lambda x: x[3], reverse=True)       # data desc
    nao_urgentes.sort(key=lambda x: (x[0][2], x[0][1], x[0][0]))  # prioridade
    urgentes.sort(key=lambda x: x[2])                         # dias ate evento (asc)
    urgentes.sort(key=lambda x: x[3], reverse=True)           # data desc (tie)
    # --- Fase 4: urgentes SEMPRE aparecem (sem limite). Nao-urgentes limitados a 12 ---
    total = [h for _, _, _, _, h in urgentes] + [
        h for _, _, _, _, h in nao_urgentes[:12]
    ]
    avisos_html = "".join(total)

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

    # Prazo vem antes de tudo: é o único aqui que pode vencer hoje.
    prazos_html = render_prazos_novos(data)
    itens_html = render_itens_novos(data)
    topo = f"{prazos_html}{notas_html}{itens_html}"

    if not avisos_html and not extras:
        if topo:
            return f'<div class="bloco">{topo}</div>'
        return ('<div class="bloco">'
                '<p class="sub" style="margin:0;">Nenhum prazo, nota, atividade, '
                'post, notificação ou mensagem nova desde a última checagem.'
                '</p></div>')

    extras_html = f'<ul class="tasklist">{"".join(extras)}</ul>' if extras else ""
    # Prazo, nota, atividade e fórum são assuntos diferentes: colados, o olho
    # lê a lista de posts como se fosse continuação do bloco de cima. O respiro
    # sai do CSS, que também tira a margem do primeiro bloco da aba.
    return ('<div class="bloco">'
            f'{topo}'
            '<p class="sub secao-novidade">Fóruns, notificações e mensagens que '
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
        institucional = c.get("autoridade") == "institucional"
        tipo_autor = "aviso oficial" if institucional else "post de colega"
        origem = esc(
            f"{tipo_autor} de {c['autor']}"
            if c.get("autor")
            else tipo_autor
        )
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
    return ('<div class="bloco">'
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
    return ('<p class="sub" style="margin:0 0 10px;">Não valem nota e não têm prazo. '
            'Servem só pra fechar a barra de progresso do Moodle.</p>'
            f'<ul class="tasklist">{"".join(li)}</ul>')


def render_composicao(data):
    """O que o guia acompanha da nota, e o que ele não acompanha.

    Sem esta linha, "está tudo em dia" soa como "está tudo em dia na
    disciplina", quando o robô só enxerga a menor metade: os 60% da prova
    presencial ficam fora, num sistema com login próprio.
    """
    from dominio.avaliacao import lacuna_da_prova

    linhas = []
    for c in data.get("courses", []):
        lacuna = lacuna_da_prova(c)
        if not lacuna:
            continue
        origem = f'aviso de {esc(lacuna.get("autor") or "facilitador")}'
        if lacuna.get("url"):
            origem = (f'<a href="{esc(lacuna["url"])}" target="_blank" '
                      f'rel="noopener">{origem}</a>')
        # A data não vem do Sistema de Provas (login à parte), mas costuma
        # circular em aviso de facilitador antes disso. Quando circula, o guia
        # mostra — com a frase original e o link, como faz com todo prazo.
        achada = lacuna.get("data_achada")
        if achada:
            corpo = (
                '<div class="trava">📌 Um aviso oficial já falou em data de '
                f'prova: <b>{esc(fmt_dm(achada["quando"]))}</b>. Confirme no '
                f'<a href="{esc(lacuna["onde"])}" target="_blank" '
                'rel="noopener">Sistema de Provas</a>, que é a fonte que vale.'
                f'<br><span class="muted">"{esc(achada["frase"])}"</span>'
                '</div>'
            )
        else:
            corpo = (
                '<div class="acao-pe">Este guia acompanha só a parte do AVA. '
                'A prova presencial não é lida por ele: a data e o local saem '
                f'no <a href="{esc(lacuna["onde"])}" target="_blank" '
                'rel="noopener">Sistema de Provas</a>, que tem login '
                'separado. O guia fica de olho nos avisos: se um facilitador '
                'disser a data, ela aparece aqui.</div>'
            )
        linhas.append(
            f'<li class="acao"><div class="acao-chips">'
            f'<span class="status lock">{esc(c.get("code") or "")}</span>'
            f'<span class="status ok">{lacuna["ava"]}% AVA</span>'
            f'<span class="status pend">{lacuna["prova"]}% prova presencial'
            '</span></div>'
            f'{corpo}<div class="acao-pe">{origem}</div></li>'
        )
    if not linhas:
        return ""
    return ('<h3 class="grupo">Como a nota é composta</h3>'
            f'<ul class="acoes">{"".join(linhas)}</ul>')


def render_pontos_da_quinzena(data):
    """Os dez pontos contáveis da quinzena, e quais deles já contaram.

    O painel oficial só mostra cinco. Ver "progresso avançado, 4 de 5" e não
    ver que as duas entregas e os dois feedbacks também são ponto dá a
    impressão de que falta pouco quando falta quase metade.
    """
    from dominio.acoes import quinzenas_encerradas
    from dominio.avaliacao import pontos_da_quinzena

    blocos = []
    for c in data.get("courses", []):
        placar = pontos_da_quinzena(c, quinzenas_encerradas(c))
        if not placar:
            continue
        itens = "".join(
            f'<li><span class="status {_classe_criterio(p)}">'
            + ("já contou" if p["atendido"] is True
               else "falta" if p["atendido"] is False else "não sei")
            + f'</span><span class="tlabel">{esc(p.get("nome") or "")}'
            + (f' <span class="muted">({esc(p["detalhe"])})</span>'
               if p.get("detalhe") else "")
            + "</span></li>"
            for p in placar["pontos"]
        )
        resumo = (f'{placar["atendidos"]} de {placar["total"]} já contaram')
        if placar["desconhecidos"]:
            resumo += (f', {placar["desconhecidos"]} o guia não consegue '
                       'conferir')
        blocos.append(
            f'<h3 class="grupo">Pontos da quinzena · '
            f'{esc(c.get("code") or "")}</h3>'
            f'<ul class="acoes"><li class="acao">'
            f'<div class="acao-txt"><b>{esc(resumo)}</b></div>'
            f'<ul class="tasklist">{itens}</ul>'
            '<div class="acao-pe">Todos valem o mesmo peso, pelo aviso '
            'CRITÉRIOS DE AVALIAÇÃO da disciplina. O painel oficial de '
            'participação só mostra os módulos e a qualidade; os outros o '
            'guia monta do que lê no AVA.</div></li></ul>'
        )
    return "".join(blocos)


def _classe_criterio(criterio):
    """Verde só quando a ferramenta afirma que o critério contou.

    Antes isto era `situacao.startswith("atendido")`, o que passou a errar
    quando a ferramenta trocou "atendido" por "Critério atendido": tudo caía
    em pendente. Quem responde agora é o campo booleano que a leitura já
    resolveu, e "parcialmente atendido" (nem um nem outro) fica neutro.
    """
    atendido = criterio.get("atendido")
    if atendido is True:
        return "ok"
    if atendido is False:
        return "pend"
    return "neutral"


def render_participacao(data):
    """Placar oficial de participação da COM170, lido fora do Moodle.

    Metade da nota da disciplina sai daqui, e a régua não é só "entregou":
    conta a distribuição das interações ao longo da quinzena. Sem isto à
    vista, dá pra entregar tudo no último dia e perder ponto sem saber.
    """
    blocos = []
    for c in data.get("courses", []):
        p = c.get("participacao") or {}
        atual = p.get("quinzena_atual") or {}
        if not (atual or p.get("criterios") or p.get("quinzenas")):
            continue
        linhas = []
        if atual:
            linhas.append(
                f'<div class="acao-txt"><b>{esc(atual.get("rotulo") or "")}</b>'
                f' · {esc(atual.get("progresso") or "")}</div>'
            )
            if atual.get("detalhe"):
                linhas.append(
                    f'<div class="acao-pe">{esc(atual["detalhe"])}</div>'
                )
        if p.get("perfil_temporal"):
            linhas.append(
                '<div class="acao-pe">Perfil temporal: '
                f'<b>{esc(p["perfil_temporal"])}</b>. A ferramenta considera '
                'como as interações se distribuem na quinzena, não só se você '
                'entregou.</div>'
            )
        criterios = "".join(
            f'<li><span class="status {_classe_criterio(cr)}">'
            f'{esc(cr.get("situacao") or "")}</span>'
            f'<span class="tlabel">{esc(cr.get("nome") or "")}</span></li>'
            for cr in (p.get("criterios") or [])
        )
        if criterios:
            linhas.append(f'<ul class="tasklist">{criterios}</ul>')
        # Critério que ainda não contou é a única parte acionável deste bloco:
        # é ponto de participação em aberto, e a quinzena tem data para fechar.
        pendentes = p.get("criterios_pendentes") or []
        if pendentes:
            linhas.append(
                '<div class="acao-pe">Ainda não contaram: '
                f'<b>{esc(", ".join(pendentes))}</b>. Vale conferir se todos '
                'os itens desse ponto ficaram mesmo concluídos, porque '
                'atividade fechada antes da tela final não registra.</div>'
            )
        panorama = " · ".join(
            f'{esc(q.get("quinzena") or "")}: {esc(q.get("estado") or "")}'
            for q in (p.get("quinzenas") or [])[:7]
        )
        if panorama:
            linhas.append(f'<div class="acao-pe">{panorama}</div>')
        if p.get("atualizado_em"):
            linhas.append(
                '<div class="acao-pe">A própria ferramenta atualiza de tempos '
                f'em tempos. Última atualização dela: {esc(p["atualizado_em"])}.'
                '</div>'
            )
        blocos.append(
            f'<h3 class="grupo">Participação · {esc(c.get("code") or "")}</h3>'
            f'<ul class="acoes"><li class="acao">{"".join(linhas)}</li></ul>'
        )
    return "".join(blocos)


def _boletim_vazio(curso, boletim):
    """Diz por que não há nota, sem deixar o silêncio parecer resposta.

    "Sem nota" e "não consegui ler" levam a decisões opostas: o primeiro é
    estado do AVA e não pede nada dele; o segundo é falha do guia e pede que
    ele confira na mão. Uma frase só para os dois casos escondia essa
    diferença.
    """
    estado = boletim.get("status")
    if estado == "vazio_confirmado":
        texto = ("Li o boletim desta disciplina e ele está vazio: o AVA ainda "
                 "não publicou nenhuma nota aqui. Isso é estado do boletim, "
                 "não sinal de que você deixou de entregar.")
        # A prova de entrega não vem só da nota. Onde o robô abriu a atividade
        # e viu a tentativa registrada, ele sabe mais que o boletim.
        entregues = [
            item
            for secao in curso.get("sections") or []
            for item in secao.get("items") or []
            if item.get("entrega_confirmada") is True
        ]
        if entregues:
            quantas = len(entregues)
            texto += (f' Mesmo assim, conferi {quantas} '
                      f'{"atividade" if quantas == 1 else "atividades"} '
                      "abrindo a página no AVA e a entrega está registrada.")
    elif estado == "falhou":
        texto = ("Não consegui ler o boletim desta disciplina nesta leitura, "
                 "então não sei se há nota. Confira no AVA.")
    else:
        texto = "Esta disciplina não mostra nenhuma atividade no boletim."
    return f'<li class="acao"><div class="acao-txt">{texto}</div></li>'


def _entregou_e_zerou(item):
    """Entrega confirmada pela própria atividade e nota lançada zero.

    Só vale com prova de envio lida na página (``enviado``), nunca com o selo
    de conclusão. E só onde zero é anormal: no COM170 as atividades SCORM
    valem 0,00 por desenho — lá o que conta é o módulo concluído, não a nota,
    e alertar em todas elas seria ruído em cima de estado normal.
    """
    return (
        item.get("enviado") is True
        and item.get("tem_nota")
        and item.get("nota") == 0
    )


def render_notas(data):
    """Aba "Como estou": nota por atividade e devolutiva do facilitador.

    Antes disso, saber a nota exigia abrir quatro boletins no AVA, e o guia
    não tinha como avisar que uma atividade marcada como concluída estava sem
    nota nenhuma. É a mesma leitura que sustenta a prova de entrega.
    """
    blocos = []
    for c in data.get("courses", []):
        boletim = c.get("boletim") or {}
        avaliadas = [
            (secao, item)
            for secao in c.get("sections") or []
            for item in secao.get("items") or []
            if item.get("nota_txt") or item.get("feedback")
        ]
        # Sumir com a disciplina era o pior desfecho: em 10/08/2026 o SOC100
        # não aparecia nesta aba, e não dava para saber se ele estava sem nota
        # ou se o guia é que não tinha olhado. Boletim lido, mesmo vazio, é
        # informação e fica à vista; some só o que nunca foi lido.
        if not avaliadas and not boletim.get("media") and not boletim.get(
            "status"
        ):
            continue
        linhas = []
        for _, item in avaliadas:
            nota = item.get("nota_txt") or "-"
            classe = "ok" if item.get("tem_nota") else "pend"
            nome = esc(item.get("label") or "")
            if item.get("url"):
                nome = (f'<a href="{esc(item["url"])}" target="_blank" '
                        f'rel="noopener">{nome}</a>')
            devolutiva = ""
            if item.get("feedback"):
                devolutiva = ('<div class="trava">💬 '
                              f'{esc(item["feedback"][:600])}</div>')
            faltou = ""
            if item.get("entrega_confirmada") is False:
                faltou = ('<div class="acao-pe">o AVA não registrou nenhuma '
                          'entrega sua nesta atividade</div>')
            elif not item.get("tem_nota") and item.get("conta_nota"):
                faltou = ('<div class="acao-pe">sem nota lançada até agora'
                          '</div>')
            elif _entregou_e_zerou(item):
                # Achado em 13/08/2026, conferido no AVA: o M6 da Quinzena 1
                # foi entregue em 29/07, o colega marcou o nível máximo em
                # todos os critérios ("Nota: 1 de 1") e mesmo assim o boletim
                # registra 0,00 no envio. Zero em atividade entregue não é o
                # mesmo que zero em atividade não feita, e o guia mostrava os
                # dois com a mesma cara.
                classe = "pend"
                faltou = ('<div class="trava">⚠️ O AVA registra a sua entrega '
                          'nesta atividade e mesmo assim lançou <b>zero</b>. '
                          'Em Laboratório de Avaliação a nota do envio só '
                          'fecha depois que o facilitador roda a fase de '
                          'encerramento. Abra o seu envio, veja a avaliação '
                          'que os colegas deixaram e, se ela não bate com o '
                          'zero, pergunte ao facilitador.</div>')
            linhas.append(
                f'<li class="acao"><div class="acao-chips">'
                f'<span class="status {classe}">{esc(nota)}</span></div>'
                f'<div class="acao-txt">{nome}</div>{devolutiva}{faltou}</li>'
            )
        media = boletim.get("media") or {}
        cabecalho = f'<b>{esc(c.get("code") or "")}</b>'
        if media.get("nota"):
            valor = media["nota"]
            # "Erro" é o próprio AVA falhando no cálculo, não o guia.
            if _sem_acento(str(valor)).startswith("erro"):
                cabecalho += (' · <span class="status lock">o AVA não '
                              'consegue calcular esta média</span>')
            else:
                cabecalho += (f' · {esc(media.get("rotulo") or "média")}: '
                              f'<span class="status ok">{esc(valor)}</span>')
        # Total de quinzena entra como detalhe, nunca como o número principal:
        # é ele que explica de onde veio a média, não a média em si.
        parciais = " · ".join(
            f'{esc(total.get("rotulo") or "")}: {esc(total.get("nota") or "")}'
            for total in (boletim.get("totais") or [])[:6]
        )
        if parciais:
            cabecalho += (f' <span class="sub" style="font-size:.78em;'
                          f'font-weight:400;">({parciais})</span>')
        if not linhas:
            linhas.append(_boletim_vazio(c, boletim))
        blocos.append(f'<h3 class="grupo">{cabecalho}</h3>'
                      f'<ul class="acoes">{"".join(linhas)}</ul>')
    participacao_html = render_participacao(data)
    composicao_html = render_composicao(data)
    pontos_html = render_pontos_da_quinzena(data)
    if not (blocos or participacao_html or composicao_html or pontos_html):
        return ""
    return ('<p class="sub" style="margin:0 0 10px;">Lido do boletim de cada '
            'disciplina. Nota em branco numa atividade que vale nota quer '
            'dizer que o AVA ainda não registrou entrega ou correção.</p>'
            + composicao_html
            # Antes da participação: o placar dos dez dá a escala em que os
            # cinco critérios do painel oficial devem ser lidos.
            + pontos_html
            + participacao_html
            + "".join(blocos))


def render_encerrados(data):
    itens = data.get("encerrados") or []
    if not itens:
        return ""
    li = "".join(
        f'<li><span class="status lock">{esc(e.get("motivo") or "encerrado")}</span>'
        f'<span class="tlabel"><b>{esc(e["curso"])}</b> · {esc(e["o_que"])}</span></li>'
        for e in itens[:25])
    return (f'<ul class="tasklist">{li}</ul>'
            '<p class="sub">Ficam aqui só pra registro. Se algum for importante, '
            'fale com o facilitador pelo fórum de dúvidas.</p>')


# ---------------------------------------------------------------------------
# Abas
# ---------------------------------------------------------------------------
def render_tabs(data):
    """Cada bloco que antes era mais uma seção pra rolar vira uma aba.

    A página inteira era uma coluna só; pra ver "Higiene" o Josemar tinha que
    passar por tudo antes. Aqui cada seção só existe como aba se tiver algo
    pra mostrar (Recado, Confirme, Higiene e Já encerrou somem sozinhas
    quando vazias, exatamente como sumiam da coluna antes).
    """
    abas = []

    recado_html = render_recado(data)
    if recado_html:
        rotulo = (
            "Recado anterior" if "recado-antigo" in recado_html
            else "Recado da mentora"
        )
        abas.append(("recado", rotulo, None, recado_html))

    acoes = data.get("acoes")
    badge_agora = len(acoes) if isinstance(acoes, list) else None
    abas.append(("agora", "O que fazer agora", badge_agora, render_agora(data)))

    confirmar_itens = data.get("confirmar") or []
    confirmar_html = render_confirmar(data)
    if confirmar_html:
        abas.append(
            ("confirmar", "Confirme se é prazo", len(confirmar_itens), confirmar_html)
        )

    badge_novidades = contar_novidades(data) or None
    abas.append(("novidades", "Chegou novo", badge_novidades, render_novidades(data)))

    notas_html = render_notas(data)
    if notas_html:
        com_nota = sum(
            1
            for c in data.get("courses", [])
            for secao in c.get("sections") or []
            for item in secao.get("items") or []
            if item.get("tem_nota")
        )
        abas.append(("notas", "Como estou", com_nota or None, notas_html))

    abas.append(("mapa", "Mapa das disciplinas", None, render_cards(data)))

    higiene_itens = data.get("higiene") or []
    higiene_html = render_higiene(data)
    if higiene_html:
        abas.append(("higiene", "Higiene do AVA", len(higiene_itens), higiene_html))

    encerrados_itens = data.get("encerrados") or []
    encerrados_html = render_encerrados(data)
    if encerrados_html:
        abas.append(
            ("encerrados", "Já encerrou", len(encerrados_itens), encerrados_html)
        )

    botoes, paineis = [], []
    for chave, rotulo, contagem, conteudo in abas:
        selo = (
            f'<span class="tab-badge">{contagem}</span>'
            if contagem is not None else ""
        )
        botoes.append(
            f'<button type="button" class="tab-btn" data-tab="{chave}" '
            f'role="tab" aria-selected="false" id="tabbtn-{chave}">'
            f'{esc(rotulo)}{selo}</button>'
        )
        paineis.append(
            f'<section class="tab-panel" id="panel-{chave}" role="tabpanel" '
            f'aria-labelledby="tabbtn-{chave}" hidden>{conteudo}</section>'
        )
    return (
        f'<div class="tabbar" role="tablist">{"".join(botoes)}</div>'
        f'<div class="tab-panels">{"".join(paineis)}</div>'
    )


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
        lido = datetime.fromisoformat(
            data.get("snapshot_at") or data.get("checked_at", "")).astimezone(BR_TZ)
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


def gravar_texto_atomico(caminho, texto):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, nome = tempfile.mkstemp(
        prefix=f".{caminho.name}.", suffix=".tmp", dir=str(caminho.parent))
    temp = Path(nome)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as arq:
            arq.write(texto)
            arq.flush()
            os.fsync(arq.fileno())
        os.replace(temp, caminho)
    finally:
        temp.unlink(missing_ok=True)


def render_html(data):
    snapshot_at = data.get("snapshot_at") or data.get("checked_at", "")
    checado = snapshot_at
    tentativa = data.get("attempted_at")
    tentativa_txt = ""
    try:
        checado = datetime.fromisoformat(checado).astimezone(BR_TZ).strftime("%d/%m/%Y às %H:%M")
    except Exception:
        pass
    try:
        tentativa_txt = datetime.fromisoformat(tentativa).astimezone(
            BR_TZ).strftime("%d/%m às %H:%M")
    except Exception:
        pass

    banners = []
    if data.get("status") == "session_expired":
        banners.append(
            '<div class="alertbar"><b>Sessão do AVA expirou.</b> Este é o último '
            'retrato válido; a tentativa mais recente'
            f'{f" ({esc(tentativa_txt)})" if tentativa_txt else ""} não conseguiu entrar.</div>')
    elif data.get("status") == "coleta_incompleta":
        problemas = "; ".join(data.get("problemas") or [])
        banners.append(
            '<div class="alertbar"><b>Leitura incompleta.</b> Mantive o último '
            f'retrato válido. Tentativa: {esc(tentativa_txt or "horário desconhecido")}. '
            f'{esc(problemas)}</div>')
    elif data.get("status") == "coleta_degradada":
        problemas = "; ".join(data.get("problemas") or [])
        banners.append(
            '<div class="alertbar"><b>Leitura parcial.</b> Atualizei o que '
            'respondeu e mantive o último dado válido da fonte indisponível. '
            f'{esc(problemas)}</div>'
        )
    # Este elemento sempre existe. O JavaScript recalcula a idade enquanto a
    # página está aberta; HTML estático não envelhece sozinho.
    banners.append(
        f'<div id="freshness-alert" class="alertbar" '
        f'data-snapshot-at="{esc(snapshot_at)}" hidden></div>')
    banner = "".join(banners)

    hoje = datetime.now(BR_TZ).date()
    html = (TEMPLATE
            .replace("{{SEMANA}}", esc(linha_semana(data, hoje)))
            .replace("{{CHECKED_AT}}", esc(checado))
            .replace("{{SNAPSHOT_AT}}", esc(snapshot_at))
            .replace("{{BANNER}}", banner)
            .replace("{{FONTES_STATUS}}", render_fontes_status(data))
            .replace("{{TABS}}", render_tabs(data)))
    gravar_texto_atomico(DOCS / "index.html", html)


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
       line-height:1.5;padding:18px 14px 60px;
       /* Link de gravação de live vem como uma palavra de 90 caracteres e
          empurrava a página inteira para o lado no celular: no aparelho dele
          a aba "Chegou novo" abria com rolagem horizontal. A propriedade é
          herdada, então uma linha aqui cobre todo o conteúdo do AVA. */
       overflow-wrap:break-word;}
  h1,h2,h3{font-family:Georgia,"Times New Roman",ui-serif,serif;font-weight:700;
           text-wrap:balance;margin:0;}
  a{color:inherit;}
  .wrap{max-width:580px;margin:0 auto;}
  .eyebrow{font-size:12px;letter-spacing:.09em;text-transform:uppercase;
           color:var(--brick);font-weight:700;margin-bottom:8px;}
  h1{font-size:24px;line-height:1.15;}
  .sub{color:var(--ink-soft);font-size:14px;margin-top:8px;}
  /* Cada assunto da aba "Chegou novo" ganha respiro, menos o primeiro. */
  .secao-novidade{margin:22px 0 10px;}
  .secao-novidade:first-child{margin-top:0;}
  .semana-line{font-size:13px;font-weight:600;margin-top:6px;}
  .alertbar{background:var(--wait-bg);color:var(--wait);border-radius:12px;
            padding:12px 14px;font-size:13.5px;margin:16px 0;}
  .alertbar code{background:rgba(0,0,0,.08);padding:1px 5px;border-radius:5px;}
  .sourcebar{font-size:11.5px;color:var(--ink-soft);margin:8px 0 14px;line-height:1.4;}
  .sourcebar.degraded{color:var(--wait);font-weight:600;}
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
  .aviso.oficial{border-left:3px solid var(--ok);padding-left:9px;}
  .aviso.colega{opacity:.78;}
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
  .recado-antigo-tag{font-size:12px;letter-spacing:.06em;text-transform:uppercase;
                     color:var(--ink-soft);font-weight:700;margin:0 0 6px;}
  .tabbar{display:flex;flex-wrap:wrap;gap:6px;margin:18px 0 4px;}
  .tab-btn{flex:0 0 auto;display:flex;align-items:center;gap:6px;
           font-family:ui-sans-serif,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
           font-size:13px;font-weight:600;color:var(--ink-soft);
           background:var(--paper);border:1px solid var(--line);border-radius:99px;
           padding:8px 14px;cursor:pointer;white-space:nowrap;transition:.15s ease;}
  .tab-btn:hover{color:var(--ink);}
  .tab-btn.active{background:var(--brick-soft);border-color:var(--brick);color:var(--brick);}
  .tab-badge{font-size:11px;font-weight:700;background:rgba(128,128,128,.22);
             color:inherit;border-radius:99px;padding:1px 7px;}
  .tab-panels{margin-top:10px;}
  .tab-panel[hidden]{display:none;}
  @media (prefers-reduced-motion: reduce){.chev{transition:none;}}
  footer{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);
         font-size:12px;color:var(--ink-soft);text-align:center;}
</style>
</head>
<body data-snapshot-at="{{SNAPSHOT_AT}}">
<div class="wrap">
  <div class="eyebrow">Univesp · BIA · Turma 001</div>
  <h1>Guia diário do AVA</h1>
  <p class="semana-line">{{SEMANA}}</p>
  <p class="sub">Releio o AVA várias vezes ao dia · última leitura: {{CHECKED_AT}} (Brasília)</p>
  {{BANNER}}
  {{FONTES_STATUS}}
  {{TABS}}
  <footer>Um robô lê o AVA todo dia: páginas das disciplinas, calendário, todos os fóruns,
  notificações e mensagens. Prazo só aparece aqui com a origem à mostra.<br>
  Nenhuma data é chutada: se não achei prazo oficial, digo que não tem.</footer>
</div>
<script>
(() => {
  const aviso = document.getElementById('freshness-alert');
  if (!aviso) return;
  const atualizar = () => {
    const valor = aviso.dataset.snapshotAt || document.body.dataset.snapshotAt;
    const instante = Date.parse(valor || '');
    if (!Number.isFinite(instante)) {
      aviso.textContent = 'Não consegui verificar a idade deste retrato. Confirme no AVA.';
      aviso.hidden = false;
      return;
    }
    const horas = Math.max(0, (Date.now() - instante) / 3600000);
    if (horas < 3) {
      aviso.hidden = true;
      return;
    }
    const quando = new Date(instante).toLocaleString('pt-BR', {
      timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit',
      hour: '2-digit', minute: '2-digit'
    });
    aviso.textContent = `Este retrato é de ${quando}, cerca de ${Math.floor(horas)}h atrás. ` +
      'Se você estudou depois disso, confira no AVA antes de confiar na lista.';
    aviso.hidden = false;
  };
  atualizar();
  setInterval(atualizar, 60000);
  document.addEventListener('visibilitychange', atualizar);
})();
</script>
<script>
(() => {
  const botoes = [...document.querySelectorAll('.tab-btn')];
  const paineis = [...document.querySelectorAll('.tab-panel')];
  if (!botoes.length) return;
  const ativar = (chave, focar) => {
    botoes.forEach(b => {
      const on = b.dataset.tab === chave;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    paineis.forEach(p => { p.hidden = p.id !== `panel-${chave}`; });
    if (focar) history.replaceState(null, '', `#${chave}`);
  };
  botoes.forEach(b => b.addEventListener('click', () => ativar(b.dataset.tab, true)));
  const doHash = (location.hash || '').slice(1);
  const existe = botoes.some(b => b.dataset.tab === doHash);
  const padrao = botoes.some(b => b.dataset.tab === 'agora') ? 'agora' : botoes[0].dataset.tab;
  ativar(existe ? doHash : padrao, false);
})();
</script>
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
