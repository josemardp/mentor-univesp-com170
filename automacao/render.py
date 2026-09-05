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


def cmid_da_url(url):
    encontrado = re.search(r"[?&]id=(\d+)", url or "")
    return encontrado.group(1) if encontrado else None


def _cursos_por_cmid(data):
    """De qual disciplina é cada atividade, pelo cmid que já está na URL."""
    mapa = {}
    for curso in data.get("courses") or []:
        for secao in curso.get("sections") or []:
            for item in secao.get("items") or []:
                cmid = item.get("cmid") or cmid_da_url(item.get("url"))
                if cmid:
                    mapa.setdefault(str(cmid), curso.get("code"))
    return mapa


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
        "meus_posts": "suas mensagens de fórum",
        "portal": "portal do aluno",
    }
    # Esta linha existe pra responder "posso confiar no que estou lendo?".
    # A primeira versão saía em idioma de programador ("foruns: live (60,
    # truncado, último ao vivo 20:46)") e o dono do projeto, que não é dev,
    # precisou perguntar o que significava. Agora: uma frase no caso normal,
    # e nome aos bois quando alguma fonte falha.
    # Boletim e participação ficavam de fora desta linha, então podiam falhar
    # dias seguidos enquanto a frase continuava dizendo "li tudo agora, sem
    # reaproveitar dados antigos". O mesmo defeito voltou com as duas fontes
    # novas: em 15/08 o portal estava parcial, com "o Sistema de Provas pediu
    # verificação de robô" registrado, e a linha saía verde. Toda fonte lida é
    # fonte declarada, sem exceção — é isso que impede a linha de mentir.
    ordem = ("disciplinas", "calendario", "cronograma", "foruns", "itens",
             "notificacoes", "boletim", "participacao", "meus_posts", "portal")
    quantidades = {
        "disciplinas": "{n} disciplinas",
        "calendario": "{n} prazos no calendário",
        "cronograma": "{n} cronogramas",
        "itens": "{n} atividades conferidas",
        "notificacoes": "{n} notificações",
        "boletim": "{n} notas no boletim",
        "participacao": "{n} quinzenas de participação",
        "meus_posts": "{n} fóruns em que você escreveu",
        "portal": "{n} provas no portal",
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
    elif a.get("cobrado_por"):
        # Não é portão de nada: é item que o prazo da unidade nomeia. Em
        # 19/08/2026 os dois quizzes do Q3 Módulo 1 ficavam em "sem prazo
        # definido" com "Prazo módulos 1 a 4, vence 23/08" logo acima.
        quando = fmt_dm(a.get("destrava_em")) if a.get("destrava_em") else ""
        trava = ('<div class="trava">🔑 Este não tem prazo próprio, mas entra '
                 f'no prazo de <b>{esc(a["cobrado_por"])}</b>'
                 + (f', que vence {esc(quando)}' if quando else "")
                 + '. Por isso está aqui em cima.</div>')
    if a.get("bloqueio"):
        trava = (f'<div class="trava">🔒 Ainda não abriu: {esc(a["bloqueio"])}. '
                 'Corra os módulos anteriores pra destravar a tempo.</div>')
    if a.get("abre_em"):
        # Fase que o AVA ainda vai abrir. Aparece antes da hora de propósito:
        # a revisão entre pares costuma abrir e fechar dentro da mesma semana,
        # e quem só descobre no dia da abertura perde o tempo de se organizar.
        trava += ('<div class="trava">🗓️ Ainda não abriu. A fase começa '
                  f'<b>{esc(fmt_dmhm(a["abre_em"]))}</b> e você tem até o prazo '
                  'acima. Nada a fazer até lá, é só para você já contar com '
                  'ela.</div>')
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
    if a.get("sem_rastreio"):
        trava += ('<div class="trava">👁️ O AVA não acompanha a conclusão deste '
                  'item: ele não tem a marca "Concluído" que os vizinhos têm, '
                  'e por isso não vai sair da fila sozinho. Se você já fez, '
                  'ignore — não adianta clicar de novo à procura da marca.</div>')
    if a.get("lives_anunciadas"):
        # A página da Quinzena 3 escrevia "A quinzena oferece 7 lives" e
        # listava seis. Mostrar as seis sem dizer isso transforma leitura
        # parcial em oferta completa, e a presença ao vivo vale ponto.
        trava += ('<div class="trava">⚠️ A página anuncia '
                  f'<b>{a["lives_anunciadas"]} lives</b> e eu só encontrei '
                  f'{a.get("lives_lidas")}. Confira na página se falta '
                  'alguma antes de escolher a sua.</div>')
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
    # A notificação não diz de qual disciplina é, e as três disciplinas
    # publicam a mesma atividade na mesma semana: em 19/08/2026 a aba mostrou
    # "Abre em segunda-feira, 17 ago. 2026, 00:00: S5 - Atividade Avaliativa"
    # três vezes, idênticas, parecendo repetição de um aviso só. O curso está
    # no cmid da URL, que o guia já lê para tudo o mais.
    curso_do_cmid = _cursos_por_cmid(data)
    nao_lidas = [n for n in data.get("notificacoes", []) if not n.get("lida")]
    for n in nao_lidas[:6]:
        alvo = esc(n.get("assunto") or "")
        if n.get("url"):
            alvo = f'<a href="{esc(n["url"])}" target="_blank" rel="noopener">{alvo}</a>'
        curso = curso_do_cmid.get(cmid_da_url(n.get("url")))
        marca = f'<span class="status brick">{esc(curso)}</span>' if curso else ""
        extras.append(f'<li><span class="status lock">notificação</span>{marca}'
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

    # Notificação e mensagem não são filtradas por novidade: a lista é o que
    # está **não lido** no AVA, e ele não abre o sininho. Em 19/08/2026 a aba
    # anunciava "apareceram desde a última leitura" e mostrava aviso de
    # atividade que abriu em 10/08. Post de fórum ali em cima é novidade de
    # verdade (vem com a marca `novo`); estes dois têm frase própria.
    extras_html = (
        '<p class="sub secao-novidade">Notificações e mensagens do AVA ainda '
        'não lidas. Podem ser antigas: elas ficam aqui até você abrir.</p>'
        f'<ul class="tasklist">{"".join(extras)}</ul>'
    ) if extras else ""
    # Prazo, nota, atividade e fórum são assuntos diferentes: colados, o olho
    # lê a lista de posts como se fosse continuação do bloco de cima. O respiro
    # sai do CSS, que também tira a margem do primeiro bloco da aba.
    posts_html = (
        '<p class="sub secao-novidade">Publicações de fórum que '
        'apareceram desde a última leitura.</p>'
        f'<ul class="acoes">{avisos_html}</ul>'
    ) if avisos_html else ""
    return f'<div class="bloco">{topo}{posts_html}{extras_html}</div>'


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
        # "?% concluído" ocupava o canto do card sem dizer nada. Barra de
        # progresso que o Moodle não publicou simplesmente não aparece.
        pill = (
            f'<div class="progress-pill has-progress">{pct}% concluído</div>'
            if pct else ""
        )
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
    return f'<div class="cards">{"".join(cards)}</div>'


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

    # A data da prova deixou de ser lacuna em 15/08: ela vem do Sistema de
    # Provas, no portal do aluno. Enquanto houver prova conhecida para a
    # disciplina, este bloco não pode continuar dizendo que ninguém sabe a
    # data, senão o site se contradiz na mesma página — a fila publica dia e
    # hora e a aba "Como estou" diz que não é lida.
    provas_por_curso = {
        (prova.get("codigo") or "").upper()
        for prova in ((data.get("portal") or {}).get("provas") or [])
    }
    linhas = []
    for c in data.get("courses", []):
        lacuna = lacuna_da_prova(c)
        if not lacuna:
            continue
        if (c.get("code") or "").upper() in provas_por_curso:
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
                '<div class="acao-pe">Este guia acompanha a parte do AVA. '
                'A prova presencial mora no '
                f'<a href="{esc(lacuna["onde"])}" target="_blank" '
                'rel="noopener">Sistema de Provas</a>, no portal do aluno, e '
                'para esta disciplina ainda não há prova marcada lá. Quando '
                'houver, ela aparece na aba Secretaria e na fila, com dia e '
                'hora.</div>'
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
        # O painel oficial segue pontuando a quinzena anterior depois que a
        # nova abre. Em 18/08/2026 este placar era da Quinzena 2, com a 3
        # correndo desde o dia 16: o número estava certo e parecia ser o de
        # agora, que é o jeito de um dado certo enganar.
        avaliada, em_curso = placar.get("quinzena"), placar.get(
            "quinzena_em_curso"
        )
        de_qual = ""
        if avaliada:
            de_qual = f'<div class="acao-pe">Este placar é da <b>Quinzena '
            de_qual += f'{avaliada}</b>, que é a que o painel oficial está '
            de_qual += 'pontuando'
            if em_curso and em_curso != avaliada:
                de_qual += (
                    f'. A quinzena em curso é a <b>{em_curso}</b>, e ela '
                    'ainda não tem placar: o painel só passa a pontuá-la '
                    'quando fecha a anterior'
                )
            de_qual += '.</div>'
        blocos.append(
            f'<h3 class="grupo">Pontos da quinzena · '
            f'{esc(c.get("code") or "")}</h3>'
            f'<ul class="acoes"><li class="acao">'
            f'<div class="acao-txt"><b>{esc(resumo)}</b></div>'
            f'<ul class="tasklist">{itens}</ul>'
            + de_qual +
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
# Quadro das materias
# ---------------------------------------------------------------------------
CHIP_DA_CELULA = {
    "ok": "ok",
    "falta": "pend",
    "perdeu": "brick",
    "atencao": "brick",
    "nao_sei": "neutral",
}


def _celula_html(celula):
    if celula.get("estado") == "vazio":
        return '<td class="q-cel"><span class="q-vazio">—</span></td>'
    texto = esc(celula.get("texto") or "")
    if celula.get("url"):
        texto = (f'<a href="{esc(celula["url"])}" target="_blank" '
                 f'rel="noopener">{texto}</a>')
    detalhe = (f'<div class="q-detalhe">{esc(celula["detalhe"])}</div>'
               if celula.get("detalhe") else "")
    chip = CHIP_DA_CELULA.get(celula.get("estado"), "neutral")
    return (f'<td class="q-cel"><span class="status {chip} q-chip">{texto}'
            f'</span>{detalhe}</td>')


def _prazo_html(prazo, fechada=False):
    quando = prazo.get("quando")
    if not quando:
        return '<td class="q-prazo"><span class="q-vazio">—</span></td>'
    corpo = f'<b>{esc(fmt_dm(quando))}</b>'
    # Numa semana já encerrada a data-alvo não decide nada e repetia em todas
    # as linhas, dobrando a altura do quadro no celular por informação morta.
    if not fechada and prazo.get("alvo") and prazo["alvo"] != quando:
        # O cronograma oficial tem uma data-alvo e uma carência, e é na
        # carência que o AVA fecha de verdade. Mostrar só o alvo dava quatro
        # dias a menos do que ele tem; mostrar só a carência escondia a data
        # que a Univesp publica. Ficam as duas, com a que fecha em destaque.
        corpo += (f'<div class="q-detalhe">alvo '
                  f'{esc(fmt_dm(prazo["alvo"]))}</div>')
    return f'<td class="q-prazo">{corpo}</td>'


def _cabecalho_do_quadro(quadro):
    partes = []
    media = quadro.get("media") or {}
    if media.get("nota"):
        valor = str(media["nota"])
        if _sem_acento(valor).startswith("erro"):
            partes.append('<span class="status lock">o AVA não calcula esta '
                          'média</span>')
        else:
            partes.append(f'{esc(media.get("rotulo") or "média")}: '
                          f'<span class="status ok">{esc(valor)}</span>')
    elif quadro.get("boletim_status") == "vazio_confirmado":
        # SOC100: o relatório do usuário abre sem nenhuma linha. Dizer "sem
        # nota" seria mentira, as notas estão nas próprias atividades.
        partes.append('<span class="status lock">o boletim desta disciplina '
                      'vem vazio do AVA</span>')
    if quadro.get("notas_do_questionario"):
        partes.append('as notas abaixo o guia leu na página de cada '
                      'questionário')
    if quadro.get("atual"):
        unidade = "Quinzena" if quadro["modelo"] == "quinzenal" else "Semana"
        partes.append(f'você está na <b>{unidade} {quadro["atual"]}</b>')
    linha = " · ".join(partes)
    zeros = quadro.get("zeros_interativos") or 0
    if zeros and quadro.get("media"):
        linha += (f'<div class="q-detalhe" style="max-width:none;">Esta média '
                  f'inclui {zeros} atividades interativas lançadas com 0,00 '
                  'no boletim, mesmo concluídas, então ela não mede como você '
                  'está. Quem mede é o painel de participação.</div>')
    return linha


def render_quadros(data):
    """Aba "Quadro das matérias": uma linha por semana ou por quinzena.

    Pedido dele em 25/08/2026. As outras abas respondem "o que fazer agora" e
    "quanto tirei nesta atividade"; nenhuma respondia "onde eu estou nesta
    matéria", que era a pergunta que ele levava para o AVA toda semana e que
    exigia abrir quatro páginas para responder.
    """
    from dominio.quadro import montar

    blocos = []
    for quadro in montar(data):
        cabecalho = _cabecalho_do_quadro(quadro)
        colunas = "".join(f"<th>{esc(coluna)}</th>"
                          for coluna in quadro["colunas"])
        linhas = []
        for linha in quadro["linhas"]:
            classes = ["q-linha"]
            if linha.get("atual"):
                classes.append("q-atual")
            if linha["situacao"] == "nao_aberta":
                vazias = len(quadro["colunas"]) - 1
                linhas.append(
                    f'<tr class="q-linha q-fora"><th scope="row">'
                    f'{esc(linha["rotulo"])}</th>'
                    f'<td class="q-cel" colspan="{vazias}">'
                    '<span class="q-vazio">ainda não aberta</span></td></tr>'
                )
                continue
            fechada = linha["situacao"] == "fechada"
            if fechada:
                classes.append("q-fechada")
            celulas = "".join(
                _prazo_html(p, fechada) for p in linha["prazos"]
            )
            celulas += "".join(_celula_html(c) for c in linha["celulas"])
            rotulo = esc(linha["rotulo"])
            if linha.get("atual"):
                rotulo += '<span class="q-agora">agora</span>'
            linhas.append(
                f'<tr class="{" ".join(classes)}"><th scope="row">{rotulo}'
                f'</th>{celulas}</tr>'
            )
        blocos.append(
            '<section class="quadro-bloco">'
            f'<h3 class="grupo">{esc(quadro["codigo"] or "")}</h3>'
            + (f'<p class="q-cab">{cabecalho}</p>' if cabecalho
               else '<p class="q-cab q-cab-vazio">&nbsp;</p>')
            + '<div class="q-rolagem"><table class="quadro">'
            f'<thead><tr>{colunas}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>'
            '</section>'
        )
    if not blocos:
        return ""
    return ('<p class="sub" style="margin:0 0 10px;">Uma linha por semana, ou '
            'por quinzena na COM170. <b>Fecha</b> é a data em que o AVA fecha '
            'de verdade, não a do cronograma. <b>Avaliativa</b> é o '
            'questionário da semana e <b>Fórum</b> é o temático. Na COM170, '
            '<b>Entrega</b> e <b>Avaliar</b> são os dois prazos do '
            'Laboratório, e os dois valem nota. Onde está escrito “não sei”, '
            'é o guia dizendo que não conseguiu ler, nunca que você não fez. '
            'Arraste o quadro para o lado se ele não couber na tela.</p>'
            f'<div class="quadros">{"".join(blocos)}</div>')


def render_portal(data):
    """Aba "Secretaria": o que só existe no portal do aluno.

    O guia nasceu olhando só o AVA, e o AVA não sabe da prova presencial, não
    sabe em quantas disciplinas ele está matriculado e não recebe recado da
    secretaria. Estas três coisas moram no SEI, com login separado, e é por
    isso que elas ficaram invisíveis até 15/08/2026.

    A aba some quando o portal não foi lido. Portal que falhou nunca vira
    "não tem prova marcada", que seria a pior frase possível aqui.
    """
    portal = data.get("portal") or {}
    if not portal:
        return ""
    blocos = []

    provas = portal.get("provas") or []
    if provas:
        linhas = []
        for prova in provas:
            quando = fmt_dmhm(prova.get("inicio")) if prova.get("inicio") else ""
            ate = ""
            if prova.get("fim"):
                ate = f' até {esc(fmt_dmhm(prova["fim"]).split(" ")[-1])}'
            modalidade = esc(prova.get("modalidade") or "")
            linhas.append(
                f'<li class="acao"><div class="acao-chips">'
                f'<span class="status brick">{esc(quando)}{ate}</span>'
                f'<span class="status ok">{modalidade}</span></div>'
                f'<div class="acao-frase">{esc(prova.get("titulo") or "")}</div></li>'
            )
        # A origem vai junto, como em todo prazo deste guia. Na fila ela já
        # aparecia; aqui não, e era justamente aqui que alguém viria conferir
        # a prova. Data sem origem é data sem validade.
        origem = "lido no Sistema de Provas nesta rodada"
        if portal.get("provas_origem") == "conferido à mão":
            quando_conf = portal.get("provas_conferido_em")
            origem = "conferido à mão no Sistema de Provas"
            if quando_conf:
                origem += f", em {esc(fmt_dm(quando_conf + 'T00:00:00'))}"
            origem += (
                ". O sistema de provas exige verificação de robô, então esta "
                "data não é relida sozinha: vale reconferir a cada bimestre"
            )
        blocos.append(
            '<p class="sub secao-novidade">Provas deste bimestre, no seu dia. '
            'O calendário geral lista vários dias por disciplina; estes são os '
            'seus.</p>'
            f'<ul class="acoes">{"".join(linhas)}</ul>'
            f'<p class="sub">{origem}.</p>'
        )

    fora = portal.get("_so_no_portal") or []
    if fora:
        itens = "".join(
            f'<li class="acao"><div class="acao-frase"><b>{esc(d["codigo"])}</b> '
            f'{esc(d.get("nome") or "")}</div></li>'
            for d in fora
        )
        blocos.append(
            '<p class="sub secao-novidade">Matrícula que a secretaria registra e '
            'o AVA ainda não mostra. Não há o que fazer enquanto a turma não '
            'abrir, mas conta carga horária e pode ter prova.</p>'
            f'<ul class="acoes">{itens}</ul>'
        )

    nao_lidos = portal.get("recados_nao_lidos")
    if nao_lidos:
        blocos.append(
            '<p class="sub secao-novidade">'
            f'{plural(nao_lidos, "recado não lido", "recados não lidos")} '
            'na secretaria. O robô não abre a caixa de propósito: abrir marca '
            'como lido e apagaria o aviso antes de você ver. '
            '<a href="https://acesso.univesp.br/" '
            'target="_blank" rel="noopener">Abrir o portal</a>.</p>'
        )

    notas = [n for n in portal.get("notas") or [] if any(n.get("parcelas", {}).values())]
    if notas:
        linhas = "".join(
            f'<li class="acao"><div class="acao-frase"><b>{esc(n["codigo"])}</b> '
            + ", ".join(
                f'{esc(rotulo.lower())} {esc(valor)}'
                for rotulo, valor in n["parcelas"].items() if valor
            )
            + "</div></li>"
            for n in notas
        )
        blocos.append(
            '<p class="sub secao-novidade">Boletim da secretaria, que é outro '
            'boletim: aqui a nota da prova presencial e a média do bimestre '
            'aparecem, e no AVA não.</p>'
            f'<ul class="acoes">{linhas}</ul>'
        )

    if not blocos:
        return ""
    return ('<div class="bloco"><h2>Secretaria (portal do aluno)</h2>'
            + "".join(blocos) + "</div>")


def _comeca_nao_lida(texto):
    return _sem_acento(texto).strip().startswith("nao lid")


def render_outlook(data):
    """Aba "E-mail (Outlook)": o retrato da caixa institucional nesta rodada.

    Sem histórico de propósito (ver ``fontes/outlook_univesp.py`` sobre o
    porquê desta fonte nunca guardar e-mail em cache entre rodadas): o que
    aparece aqui é sempre a leitura desta rodada, substituindo a anterior por
    inteiro, nunca uma lista que cresce.
    """
    status_outlook = (data.get("fontes_status") or {}).get("outlook") or {}
    status = status_outlook.get("status")
    outlook = data.get("outlook") or {}

    if status == "nao_aplicavel" and not outlook:
        return (
            '<div class="bloco"><h2>E-mail (Outlook)</h2>'
            '<p class="sub">Sem sessão salva do Outlook institucional. Rode '
            '<code>automacao/capturar_sessao_outlook.py</code> uma vez para '
            'habilitar esta leitura.</p></div>'
        )
    if status == "falhou" and not outlook:
        motivo = "; ".join(status_outlook.get("problemas") or [])
        return (
            '<div class="bloco"><h2>E-mail (Outlook)</h2>'
            '<p class="sub secao-novidade">Não consegui ler o Outlook nesta '
            f'rodada{": " + esc(motivo) if motivo else ""}.</p></div>'
        )
    if not outlook:
        return ""

    inbox = outlook.get("inbox") or {}
    lixo = outlook.get("lixo_eletronico") or {}
    blocos = []

    ultima = inbox.get("ultima")
    if ultima:
        blocos.append(
            '<p class="sub secao-novidade">Última mensagem da caixa de '
            'entrada.</p>'
            '<ul class="acoes"><li class="acao"><div class="acao-frase">'
            f'{esc(ultima.get("texto") or "")}</div></li></ul>'
        )

    nao_lidas_inbox = [
        m for m in inbox.get("mensagens") or []
        if _comeca_nao_lida(m.get("texto") or "")
    ]
    if nao_lidas_inbox:
        itens = "".join(
            f'<li class="acao"><div class="acao-frase">'
            f'{esc(m.get("texto") or "")}</div></li>'
            for m in nao_lidas_inbox
        )
        blocos.append(
            '<p class="sub secao-novidade">'
            f'{plural(len(nao_lidas_inbox), "mensagem não lida", "mensagens não lidas")} '
            'na caixa de entrada.</p>'
            f'<ul class="acoes">{itens}</ul>'
        )
    elif "mensagens" in inbox:
        blocos.append(
            '<p class="sub">Nenhuma mensagem não lida na caixa de entrada.</p>'
        )

    mensagens_lixo = lixo.get("mensagens") or []
    if mensagens_lixo:
        itens = "".join(
            f'<li class="acao"><div class="acao-frase">'
            f'{esc(m.get("texto") or "")}</div></li>'
            for m in mensagens_lixo
        )
        blocos.append(
            '<p class="sub secao-novidade">'
            f'{plural(len(mensagens_lixo), "mensagem", "mensagens")} no Lixo '
            'Eletrônico. Confira se nenhuma caiu ali por engano.</p>'
            f'<ul class="acoes">{itens}</ul>'
        )
    elif "mensagens" in lixo:
        blocos.append(
            '<p class="sub">Lixo Eletrônico sem mensagens nesta leitura.</p>'
        )

    if status_outlook.get("problemas"):
        blocos.append(
            '<p class="sub secao-novidade">'
            f'{esc("; ".join(status_outlook["problemas"]))}.</p>'
        )

    if not blocos:
        return ""
    return '<div class="bloco"><h2>E-mail (Outlook)</h2>' + "".join(blocos) + '</div>'


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

    # Logo depois da fila: a fila diz o que fazer hoje, o quadro diz de onde
    # essa tarefa veio e o que mais está em aberto na mesma matéria.
    quadros_html = render_quadros(data)
    if quadros_html:
        abas.append(("quadro", "Quadro das matérias", None, quadros_html))

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

    portal_html = render_portal(data)
    if portal_html:
        provas = len((data.get("portal") or {}).get("provas") or [])
        abas.append(("portal", "Secretaria", provas or None, portal_html))

    outlook_html = render_outlook(data)
    if outlook_html:
        outlook_dados = data.get("outlook") or {}
        badge_outlook = (
            (outlook_dados.get("inbox") or {}).get("nao_lidas")
            or None
        )
        abas.append(("outlook", "E-mail (Outlook)", badge_outlook, outlook_html))

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
    # As duas partes ficam dentro de um contêiner só porque no desktop elas
    # deixam de ser uma acima da outra: viram grid de duas colunas, com as
    # abas em pé na lateral. No celular o contêiner não muda nada.
    return (
        '<div class="tabs">'
        f'<div class="tabbar" role="tablist">{"".join(botoes)}</div>'
        f'<div class="tab-panels">{"".join(paineis)}</div>'
        '</div>'
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
    --bg:#f4f5f1; --paper:#ffffff; --paper-subtle:#f8f9f7;
    --ink:#121a16; --ink-soft:#45524b; --line:#d7ded6;
    --accent:#1c4454; --accent-soft:#eaf1f4;
    --brick:#941a23; --brick-soft:#fbeae8;
    --ok:#185c37; --ok-bg:#eaf4ee;
    --wait:#7a4b04; --wait-bg:#f8f1df;
    --locked:#585346; --locked-bg:#eae7de;
    --tab-active-bg:var(--accent); --tab-active-ink:#ffffff;
    --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Georgia Pro",Georgia,"Century Schoolbook",serif;
    --sans:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
    --mono:ui-monospace,"Cascadia Code","SFMono-Regular",Consolas,Menlo,monospace;
    --shadow:0 1px 2px rgba(18,26,22,.03), 0 3px 10px rgba(18,26,22,.04);
  }
  :root[data-theme="dark"], .dark-vars{}
  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]){
      --bg:#0e1411; --paper:#161e1b; --paper-subtle:#1b2521;
      --ink:#f0f4f0; --ink-soft:#a0aca4; --line:#25332c;
      --accent:#8fc3d8; --accent-soft:#162730;
      --brick:#e57378; --brick-soft:#35181a;
      --ok:#6ecc96; --ok-bg:#152e20;
      --wait:#e5b760; --wait-bg:#332610;
      --locked:#9c9685; --locked-bg:#24221a;
      --tab-active-bg:var(--accent); --tab-active-ink:#0e1411;
      --shadow:0 1px 3px rgba(0,0,0,.35), 0 4px 14px rgba(0,0,0,.3);
    }
  }
  :root[data-theme="dark"]{
    --bg:#0e1411; --paper:#161e1b; --paper-subtle:#1b2521;
    --ink:#f0f4f0; --ink-soft:#a0aca4; --line:#25332c;
    --accent:#8fc3d8; --accent-soft:#162730;
    --brick:#e57378; --brick-soft:#35181a;
    --ok:#6ecc96; --ok-bg:#152e20;
    --wait:#e5b760; --wait-bg:#332610;
    --locked:#9c9685; --locked-bg:#24221a;
    --tab-active-bg:var(--accent); --tab-active-ink:#0e1411;
    --shadow:0 1px 3px rgba(0,0,0,.35), 0 4px 14px rgba(0,0,0,.3);
  }
  *{box-sizing:border-box;}
  body{margin:0;background:var(--bg);color:var(--ink);
       font-family:var(--sans);
       line-height:1.55;padding:20px 14px 64px;
       -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
       /* Link de gravação de live vem como uma palavra de 90 caracteres e
          empurrava a página inteira para o lado no celular: no aparelho dele
          a aba "Chegou novo" abria com rolagem horizontal. A propriedade é
          herdada, então uma linha aqui cobre todo o conteúdo do AVA. */
       overflow-wrap:break-word;}
  h1,h2,h3{font-family:var(--serif);font-weight:700;letter-spacing:-.015em;
           text-wrap:balance;margin:0;}
  a{color:inherit;text-decoration:underline;text-decoration-color:color-mix(in srgb, var(--accent) 40%, transparent);text-underline-offset:2px;transition:color .15s ease,text-decoration-color .15s ease;}
  a:hover{color:var(--accent);text-decoration-color:var(--accent);}
  :focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px;}
  .wrap{max-width:580px;margin:0 auto;}
  .eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;
           color:var(--accent);font-weight:700;margin-bottom:6px;}
  header.topo{border-bottom:2px solid var(--accent);padding-bottom:14px;margin-bottom:8px;}
  h1{font-size:26px;line-height:1.15;}
  .sub{color:var(--ink-soft);font-size:13.5px;margin-top:8px;line-height:1.45;}
  /* Cada assunto da aba "Chegou novo" ganha respiro, menos o primeiro. */
  .secao-novidade{margin:22px 0 10px;}
  .secao-novidade:first-child{margin-top:0;}
  .semana-line{font-size:13.5px;font-weight:600;margin-top:6px;color:var(--ink);}
  .alertbar{background:var(--wait-bg);color:var(--wait);border:1px solid color-mix(in srgb, var(--wait) 25%, transparent);border-radius:8px;
            padding:12px 14px;font-size:13.5px;margin:16px 0;line-height:1.45;}
  .alertbar code{background:rgba(0,0,0,.08);padding:1px 5px;border-radius:4px;font-family:var(--mono);font-size:12px;}
  .sourcebar{font-size:12px;color:var(--ink-soft);margin:10px 0 14px;line-height:1.45;}
  .sourcebar.degraded{color:var(--wait);font-weight:600;}
  .fontes-det{margin-top:5px;font-size:12px;color:var(--ink-soft);}
  .fontes-det summary{cursor:pointer;font-weight:600;text-decoration:underline;text-underline-offset:2px;}
  .fontes-det summary:hover{color:var(--ink);}
  .fontes-det p{margin:4px 0 0;line-height:1.45;}
  .recado{background:var(--accent-soft);border:1px solid color-mix(in srgb, var(--accent) 35%, var(--line));border-left:3.5px solid var(--accent);border-radius:8px;
          padding:16px 18px;box-shadow:var(--shadow);margin:18px 0 22px;}
  .recado-head{display:flex;align-items:center;gap:8px;margin-bottom:8px;}
  .recado-label{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;
                color:var(--accent);font-weight:700;}
  .recado-body p{margin:0 0 8px;font-size:14px;line-height:1.5;}
  .recado-body ul{margin:6px 0 8px;padding-left:20px;}
  .recado-body li{font-size:14px;margin-bottom:4px;}
  .recado-when{margin:10px 0 0;font-size:11.5px;color:var(--ink-soft);}
  .bloco{background:var(--paper);border:1px solid var(--line);border-radius:8px;
         padding:18px 16px;box-shadow:var(--shadow);margin:16px 0;}
  .bloco.destaque{border-color:var(--line);border-top:3px solid var(--accent);}
  .bloco h2{font-size:18px;margin-bottom:8px;}
  .grupo{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;
         color:var(--accent);margin:16px 0 8px;font-weight:700;}
  .grupo .muted{color:var(--ink-soft);font-weight:400;}
  .acoes{list-style:none;margin:0;padding:0;}
  .acao,.aviso{padding:11px 0;border-top:1px solid var(--line);}
  .aviso.oficial{border-left:3px solid var(--ok);padding-left:10px;margin-left:-2px;}
  .aviso.colega{opacity:.82;}
  .acoes li:first-child{border-top:none;}
  .acao-chips{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:6px;}
  .acao-txt{font-size:14.5px;line-height:1.45;}
  .acao-frase{font-size:14px;line-height:1.45;}
  .acao-pe{font-size:11.5px;color:var(--ink-soft);margin-top:5px;line-height:1.4;}
  .aviso-txt{font-size:13px;color:var(--ink-soft);margin:6px 0 0;line-height:1.45;}
  .trava{font-size:12px;color:var(--wait);background:var(--wait-bg);border:1px solid color-mix(in srgb, var(--wait) 25%, transparent);border-radius:6px;
         padding:7px 10px;margin-top:6px;line-height:1.45;}
  .prazos-lidos{list-style:none;margin:6px 0 0;padding:6px 10px;border-radius:6px;
                background:var(--wait-bg);border:1px solid color-mix(in srgb, var(--wait) 20%, transparent);}
  .prazos-lidos li{font-size:12px;color:var(--wait);padding:2px 0;}
  .card{background:var(--paper);border:1px solid var(--line);border-radius:8px;
        padding:18px 16px;margin-bottom:14px;box-shadow:var(--shadow);}
  .card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;}
  .card h3{font-size:16.5px;line-height:1.25;}
  .code{font-family:var(--mono);font-size:11.5px;color:var(--accent);font-weight:700;letter-spacing:.04em;}
  .progress-pill{font-family:var(--mono);font-size:10.5px;font-weight:700;padding:3px 8px;border-radius:4px;
                 border:1px solid color-mix(in srgb, var(--locked) 35%, transparent);white-space:nowrap;background:var(--locked-bg);color:var(--locked);}
  .progress-pill.has-progress{background:var(--ok-bg);color:var(--ok);border-color:color-mix(in srgb, var(--ok) 35%, transparent);}
  .sections{margin-top:8px;}
  .sec{border-top:1px solid var(--line);}
  .sec:first-child{border-top:none;}
  .sec > summary{list-style:none;cursor:pointer;padding:10px 0;display:block;user-select:none;}
  .sec > summary::-webkit-details-marker{display:none;}
  .sec-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
  .chev{flex:0 0 auto;width:0;height:0;border-left:5.5px solid var(--ink-soft);
        border-top:4.5px solid transparent;border-bottom:4.5px solid transparent;
        transition:transform .18s cubic-bezier(0.16, 1, 0.3, 1);}
  details[open] > summary .chev{transform:rotate(90deg);}
  .sec-title-txt{font-weight:600;font-size:13.5px;}
  .muted{color:var(--ink-soft);font-size:12px;font-weight:400;}
  .sec-desc{margin:2px 0 10px 20px;font-size:12.5px;color:var(--ink-soft);line-height:1.4;}
  .tasklist{list-style:none;margin:0 0 10px;padding:0;}
  .tasklist li{display:flex;align-items:flex-start;gap:9px;padding:6px 0;
               font-size:13.5px;border-top:1px solid var(--line);line-height:1.4;}
  .tasklist li:first-child{border-top:none;}
  .tlabel{flex:1;}
  .status{flex:0 0 auto;margin-top:2px;font-family:var(--mono);font-size:10.5px;font-weight:700;
          letter-spacing:.03em;text-transform:uppercase;padding:2px 7px;border-radius:4px;
          border:1px solid transparent;white-space:nowrap;line-height:1.35;}
  .status.pend{background:var(--wait-bg);color:var(--wait);border-color:color-mix(in srgb, var(--wait) 35%, transparent);}
  .status.ok{background:var(--ok-bg);color:var(--ok);border-color:color-mix(in srgb, var(--ok) 35%, transparent);}
  .status.lock{background:var(--locked-bg);color:var(--locked);border-color:color-mix(in srgb, var(--locked) 35%, transparent);}
  .status.brick{background:var(--brick-soft);color:var(--brick);border-color:color-mix(in srgb, var(--brick) 35%, transparent);}
  .status.neutral{background:var(--locked-bg);color:var(--ink-soft);border-color:var(--line);}
  /* Quadro das matérias. São 4 ou 5 colunas dentro de 580px, e ele abre isto
     no celular: a tabela rola dentro da própria caixa em vez de empurrar a
     página inteira para o lado. */
  .q-cab{color:var(--ink-soft);font-size:13px;margin:2px 0 8px;line-height:1.4;}
  /* Cabeçalho vazio só existe para o subgrid do desktop ter sempre três
     linhas. Fora dele seria uma linha em branco sem motivo. */
  .q-cab-vazio{display:none;}
  .q-rolagem{overflow-x:auto;-webkit-overflow-scrolling:touch;
             border:1px solid var(--line);border-radius:8px;
             background:var(--paper);margin-bottom:18px;box-shadow:var(--shadow);}
  table.quadro{border-collapse:collapse;width:100%;font-size:12.5px;}
  table.quadro th,table.quadro td{padding:8px 10px;text-align:left;
                                  vertical-align:top;white-space:nowrap;}
  table.quadro thead th{font-family:var(--sans);font-size:11px;font-weight:700;
                        letter-spacing:.06em;text-transform:uppercase;
                        color:var(--ink-soft);border-bottom:1px solid var(--line);background:var(--paper-subtle);}
  table.quadro tbody th{font-weight:600;}
  .q-linha td,.q-linha th{border-top:1px solid var(--line);}
  .q-linha:first-child td,.q-linha:first-child th{border-top:none;}
  .q-atual{background:var(--accent-soft);}
  .q-atual th{color:var(--accent);font-weight:700;}
  .q-fechada{color:var(--ink-soft);}
  .q-fora th,.q-fora td{color:var(--locked);}
  .q-agora{display:inline-block;margin-left:6px;font-family:var(--mono);font-size:9px;font-weight:700;
           letter-spacing:.06em;text-transform:uppercase;color:var(--accent);padding:1px 4px;border-radius:3px;background:color-mix(in srgb, var(--accent) 15%, transparent);vertical-align:middle;}
  .q-chip{display:inline-block;margin-top:0;}
  .q-chip a{text-decoration:none;}
  /* O detalhe é a única coisa que pode quebrar linha: sem isto, "nenhuma das
     3 tentativas usada" faria a tabela ter o dobro da largura da tela. */
  .q-detalhe{margin-top:3px;font-size:11px;color:var(--ink-soft);
             white-space:normal;max-width:120px;line-height:1.35;}
  .q-vazio{color:var(--locked);}
  .recado-antigo-tag{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;
                     color:var(--ink-soft);font-weight:700;margin:0 0 6px;}
  .tabbar{display:flex;flex-wrap:wrap;gap:6px;margin:18px 0 6px;}
  .tab-btn{flex:0 0 auto;display:flex;align-items:center;gap:6px;
           font-family:var(--sans);
           font-size:13px;font-weight:600;color:var(--ink-soft);
           background:var(--paper);border:1px solid var(--line);border-radius:6px;
           padding:8px 13px;cursor:pointer;white-space:nowrap;transition:background .15s ease,border-color .15s ease,color .15s ease;box-shadow:0 1px 1px rgba(0,0,0,.02);}
  .tab-btn:hover{color:var(--ink);border-color:var(--accent);}
  .tab-btn.active{background:var(--tab-active-bg);border-color:var(--tab-active-bg);color:var(--tab-active-ink);font-weight:700;}
  .tab-badge{font-family:var(--mono);font-size:10.5px;font-weight:700;background:color-mix(in srgb, var(--ink) 10%, transparent);
             color:inherit;border-radius:4px;padding:1px 6px;}
  .tab-btn.active .tab-badge{background:rgba(255,255,255,.22);color:inherit;}
  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]) .tab-btn.active .tab-badge{background:rgba(0,0,0,.18);color:inherit;}
  }
  :root[data-theme="dark"] .tab-btn.active .tab-badge{background:rgba(0,0,0,.18);color:inherit;}
  .tab-panels{margin-top:10px;}
  .tab-panel[hidden]{display:none;}
  @media (prefers-reduced-motion: reduce){.chev,.tab-btn,a{transition:none !important;}}

  /* ---------------------------------------------------------------------
     Desktop. Tudo daqui para baixo é aditivo: o site nasceu para o celular,
     e no celular ele está do jeito que ele aprovou. O que faltava era o
     outro extremo — num monitor de 1920px o guia era uma coluna de 580px
     com 1300px de vazio dos lados, as nove abas quebravam em três fileiras
     de pílulas e as tabelas ficavam espremidas sobrando tela.
     --------------------------------------------------------------------- */

  /* Primeiro degrau: só ar. A coluna cresce e o cabeçalho vira faixa, com a
     identidade à esquerda e a hora da leitura à direita, em vez de empilhar
     quatro linhas antes de qualquer conteúdo. */
  @media (min-width: 760px){
    body{padding:28px 24px 72px;}
    .wrap{max-width:720px;}
    .topo{display:flex;align-items:flex-end;justify-content:space-between;
          gap:24px;flex-wrap:wrap;}
    .topo-meta{margin-top:0;text-align:right;flex:1 1 220px;}
    h1{font-size:28px;}
    .semana-line{font-size:14px;}
  }

  /* Segundo degrau: as abas ficam em pé. Nove pílulas empilhadas em três
     fileiras não têm hierarquia nenhuma e empurram o conteúdo para baixo da
     dobra; a mesma lista na vertical lê-se de uma olhada, e fica grudada na
     tela enquanto ele rola o painel. */
  @media (min-width: 1000px){
    .wrap{max-width:1080px;}
    .tabs{display:grid;grid-template-columns:224px minmax(0,1fr);
          gap:0 30px;align-items:start;margin-top:22px;}
    .tabbar{flex-direction:column;flex-wrap:nowrap;gap:2px;margin:0;
            position:sticky;top:26px;padding-right:22px;
            border-right:1px solid var(--line);}
    .tab-btn{width:100%;justify-content:space-between;text-align:left;
             background:transparent;border-color:transparent;border-radius:6px;
             padding:9px 12px;font-size:13.5px;box-shadow:none;}
    .tab-btn:hover{background:var(--locked-bg);border-color:transparent;color:var(--ink);}
    .tab-btn.active{background:var(--accent-soft);border-color:transparent;color:var(--accent);}
    .tab-btn.active .tab-badge{background:color-mix(in srgb, var(--accent) 18%, transparent);color:var(--accent);}
    .tab-badge{background:color-mix(in srgb, var(--ink) 8%, transparent);}
    .tab-panels{margin:0;min-width:0;}
    /* Medida de leitura. A fila é texto corrido, e linha de mil pixels
       cansa: o olho perde onde recomeça. O painel para em 860px e alinha à
       esquerda, junto da lateral. Os dois painéis que são grade, e que
       ganham de verdade com espaço, são liberados logo abaixo. */
    .tab-panel{max-width:860px;}
    #panel-quadro,#panel-mapa{max-width:none;}
    .tab-panel > .sub,.tab-panel > p{max-width:70ch;}
  }

  /* Terceiro degrau: as quatro disciplinas lado a lado. É o ganho que ele
     pediu desde o começo, ver o semestre inteiro de uma vez sem rolar. */
  @media (min-width: 1240px){
    .wrap{max-width:1240px;}
    .quadros{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
             column-gap:30px;row-gap:8px;}
    /* Sem o subgrid, o cabeçalho de duas linhas do SOC100 empurrava só a
       tabela dele para baixo e as duas colunas ficavam desencontradas. Com
       ele, título alinha com título e tabela com tabela. Navegador sem
       subgrid cai no comportamento anterior, que continua legível. */
    .quadro-bloco{min-width:0;display:grid;grid-template-rows:subgrid;
                  grid-row:span 3;align-content:start;}
    .quadro-bloco .grupo{margin-top:14px;align-self:end;}
    .quadro-bloco .q-cab{align-self:start;}
    .q-cab-vazio{display:block;visibility:hidden;}
    .cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
           gap:0 24px;align-items:start;}
    .cards .card{min-width:0;}
  }
  footer{margin-top:32px;padding-top:18px;border-top:1px solid var(--line);
         font-size:12px;color:var(--ink-soft);text-align:center;line-height:1.55;}
</style>
</head>
<body data-snapshot-at="{{SNAPSHOT_AT}}">
<div class="wrap">
  <header class="topo">
    <div class="topo-id">
      <div class="eyebrow">Univesp · BIA · Turma 001</div>
      <h1>Guia diário do AVA</h1>
      <p class="semana-line">{{SEMANA}}</p>
    </div>
    <p class="sub topo-meta">Releio o AVA várias vezes ao dia · última leitura: {{CHECKED_AT}} (Brasília)</p>
  </header>
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
