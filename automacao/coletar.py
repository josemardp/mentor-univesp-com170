# -*- coding: utf-8 -*-
"""
Coleta o estado real do AVA da Univesp: o que existe, o que falta e ate quando.

A versao antiga so lia a lista de atividades da pagina de 4 disciplinas fixas.
Esta aqui se vira sozinha e nao depende do bimestre atual:

  1. Descobre as disciplinas em "Meus cursos". Se entrar disciplina nova no
     proximo bimestre, ela aparece sem ninguem mexer no codigo.
  2. Le a pagina de cada curso pelo DOM do Moodle (nome, tipo, link e status
     reais), inclusive itens sem caixinha de conclusao, que antes sumiam.
  3. Cronograma oficial da Univesp: inicio, vencimento e carencia por semana.
  4. Calendario, notificacoes e mensagens pela API interna do Moodle, com
     data e hora exatas. Nada de adivinhar prazo.
  5. Varre TODOS os foruns de cada curso (geral, duvidas, tematico, do grupo)
     de forma incremental: guarda a data do ultimo post lido e so reabre
     discussao que mexeu desde ontem.
  6. Abre a pagina de cada item pendente pra ver se ainda da pra fazer.

No fim monta a lista de acoes ("o que fazer, em que ordem, ate quando") e
grava docs/data.json.

Privacidade: o site e publico. Por isso mensagem privada entra so como
"tem mensagem nova de fulano" (sem conteudo), e de post de forum guardamos
um trecho curto com link pro original.
"""
import json
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

import sessao

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DATA_PATH = DOCS / "data.json"
ESTADO_PATH = DOCS / "estado.json"

BR_TZ = timezone(timedelta(hours=-3))
AVA = "https://ava.univesp.br"
CRONOGRAMA_PADRAO = "https://assets.univesp.br/cronograma/2026/cronograma_regular_3.html"

# Limites pra nao estourar o tempo da GitHub Action.
MAX_DISCUSSOES_POR_RUN = 60
MAX_ITENS_CONFERIDOS = 45
TRECHO_AVISO = 400

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11,
    "dezembro": 12, "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def sem_acento(s):
    return "".join(
        c for c in unicodedata.normalize("NFD", s or "")
        if unicodedata.category(c) != "Mn"
    ).lower()


def limpar_bloqueio(texto):
    """Tira do aviso de bloqueio o texto de botao do Moodle ('Mostrar mais'),
    que senao aparece no meio da frase no site."""
    if not texto:
        return None
    limpo = re.sub(r"\b(Mostrar mais|Mostrar menos|Show more|Show less)\b", " ", texto)
    limpo = re.sub(r"\s+", " ", limpo).strip(" .…")
    return limpo or None


# ---------------------------------------------------------------------------
# API interna do Moodle (a mesma que a interface usa, via sessao ja logada)
# ---------------------------------------------------------------------------
JS_API = """
async ([nome, args]) => {
  const sk = (window.M && M.cfg && M.cfg.sesskey) || null;
  if (!sk) return { error: true, motivo: 'sem sesskey' };
  const r = await fetch('/lib/ajax/service.php?sesskey=' + sk + '&info=' + nome, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify([{ index: 0, methodname: nome, args: args }]),
  });
  const j = await r.json();
  return j[0];
}
"""


def api(page, metodo, args):
    """Chama a API interna do Moodle. Devolve None quando nao der, sempre
    dizendo o porque: erro engolido aqui deixa a coleta cega."""
    try:
        r = page.evaluate(JS_API, [metodo, args])
    except Exception as e:
        print(f"  aviso: API {metodo} nao executou ({type(e).__name__})")
        return None
    if not r:
        print(f"  aviso: API {metodo} nao respondeu")
        return None
    if r.get("error"):
        excecao = r.get("exception") or {}
        motivo = (excecao.get("message") or r.get("motivo") or "sem detalhe")
        print(f"  aviso: API {metodo} recusou: {str(motivo)[:160]}")
        return None
    return r.get("data")


def user_id(page):
    try:
        return page.evaluate("() => (window.M && M.cfg && M.cfg.userId) || null")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# JS de leitura de paginas
# ---------------------------------------------------------------------------
JS_MEUS_CURSOS = """
() => {
  const vistos = {};
  document.querySelectorAll('a[href*="/course/view.php?id="]').forEach(a => {
    const m = a.href.match(/id=(\\d+)/);
    if (!m) return;
    const nome = (a.innerText || '').trim();
    if (!nome || nome.length < 4) return;
    const card = a.closest('[data-region="course-content"], .card, li, .course-listitem') || a.parentElement;
    const prog = card ? card.querySelector('[role="progressbar"], .progress-bar') : null;
    const pct = prog ? (prog.getAttribute('aria-valuenow') || '').trim() : null;
    if (!vistos[m[1]] || (pct && !vistos[m[1]].pct)) {
      vistos[m[1]] = { id: m[1], nome: nome, pct: pct ? parseInt(pct, 10) : null };
    }
  });
  return Object.values(vistos);
}
"""

JS_CURSO = """
() => {
  const limpa = (t) => (t || '').replace(/^(Contrair|Expandir)\\s*/, '').split('\\n')[0].trim();
  const secoes = [...document.querySelectorAll('li.section, li.course-section')].map(s => {
    const own = [...s.querySelectorAll('li.activity')]
      .filter(a => a.closest('li.section, li.course-section') === s);
    const nameEl = s.querySelector('h3 .sectionname, .sectionname');
    const avail = s.querySelector('.availabilityinfo, .section_availability');
    const resumo = s.querySelector('.section_summary, .summarytext, .course-description-item');
    return {
      id: s.id,
      title: limpa(nameEl ? nameEl.innerText : ''),
      parent: (s.parentElement.closest('li.section, li.course-section') || {}).id || null,
      locked: avail ? avail.innerText.trim() : null,
      theme: resumo ? resumo.innerText.replace(/^Tema:\\s*/, '').trim().slice(0, 200) : null,
      items: own.map(a => {
        const m = a.className.match(/modtype_(\\w+)/);
        const link = a.querySelector('a.aalink, a.stretched-link, .activity-instance a');
        const compl = a.querySelector('.activity-completion');
        const nameNode = a.querySelector('[data-activityname]');
        const badge = a.querySelector('.badge, .unread');
        return {
          cmid: a.getAttribute('data-id'),
          label: nameNode ? nameNode.getAttribute('data-activityname') : null,
          type: m ? m[1] : null,
          url: link ? link.href : null,
          status: compl ? compl.innerText.trim() : null,
          nao_lidas: badge ? (badge.innerText.match(/\\d+/) || [null])[0] : null,
        };
      }).filter(x => x.label && x.type !== 'subsection'),
    };
  }).filter(s => s.title);
  const links = {};
  document.querySelectorAll('a[href*="planos-de-ensino"]').forEach(a => links.plano_ensino = a.href);
  document.querySelectorAll('a[href*="cronograma"]').forEach(a => links.cronograma = a.href);
  return { secoes, links };
}
"""

JS_DISCUSSOES = """
() => {
  const linhas = [...document.querySelectorAll('tr')].filter(r => r.querySelector('a[href*="discuss.php"]'));
  return linhas.map(r => {
    const a = r.querySelector('a[href*="discuss.php"]');
    const times = [...r.querySelectorAll('time')].map(t => t.getAttribute('datetime')).filter(Boolean);
    return {
      url: a.href.split('#')[0],
      titulo: (a.innerText || '').trim(),
      ultimo: times.length ? times[times.length - 1] : null,
    };
  }).filter(d => d.titulo);
}
"""

JS_POSTS = """
() => [...document.querySelectorAll('article.forum-post-container, [data-region="post"], .forumpost')]
  .map(p => {
    const autor = p.querySelector('a[href*="user/view"]');
    const t = p.querySelector('time');
    const h = p.querySelector('h3, h4, .subject');
    const body = p.querySelector('[data-region="post-content"], .post-content-container, .posting');
    return {
      autor: autor ? autor.innerText.trim() : null,
      data: t ? t.getAttribute('datetime') : null,
      titulo: h ? h.innerText.trim() : null,
      texto: body ? body.innerText.trim() : '',
      links: [...p.querySelectorAll('a[href]')].map(a => a.href)
               .filter(h => h && !h.includes('user/view') && !h.includes('#p')),
    };
  }).filter(p => p.texto)
"""

JS_CRONOGRAMA = """
() => [...document.querySelectorAll('tr')]
  .map(tr => tr.innerText.replace(/\\s+/g, ' ').trim())
  .filter(t => /Semana\\s+\\d/i.test(t))
"""

# Plano B do calendario: ler a propria pagina. A visao "proximos eventos" traz
# curso, titulo e link da atividade; a visao de mes traz a data exata em
# data-day-timestamp. Casando os dois pelo id do evento sai a mesma informacao
# que a API daria.
JS_EVENTOS_LISTA = """
() => [...document.querySelectorAll('.event[data-event-id]')].map(e => {
  const link = e.querySelector('a[href*="/mod/"]');
  const hora = ((e.innerText || '').match(/\\d{1,2}:\\d{2}/) || [null])[0];
  return {
    id: e.getAttribute('data-event-id'),
    curso_id: e.getAttribute('data-course-id'),
    titulo: e.getAttribute('data-event-title'),
    tipo: e.getAttribute('data-event-eventtype'),
    url: link ? link.href : null,
    hora: hora,
  };
})
"""

JS_EVENTOS_MES = """
() => {
  const saida = [];
  document.querySelectorAll('td[data-day-timestamp]').forEach(td => {
    const ts = parseInt(td.getAttribute('data-day-timestamp'), 10);
    if (!ts) return;
    td.querySelectorAll('[data-event-id]').forEach(e => {
      saida.push({ id: e.getAttribute('data-event-id'), dia_ts: ts });
    });
  });
  return saida;
}
"""


# ---------------------------------------------------------------------------
# Datas em texto livre
# ---------------------------------------------------------------------------
def _mes(nome):
    return MESES.get(sem_acento(nome).strip(". "))


def achar_datas(texto, ano_padrao):
    """[(datetime, trecho)] para '26/07', '26 de julho', '01 ago. 2026', com
    hora opcional ('23:59' ou '23h59')."""
    achados = []
    hora = r"(?:[,\s]*(?:às\s*)?(\d{1,2})[:h](\d{2}))?"
    padroes = [
        (r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?", True),
        (r"(\d{1,2})\s+(?:de\s+)?([A-Za-zçÇãÃéÉ]{3,10})\.?(?:\s+(?:de\s+)?(\d{4}))?", False),
    ]
    for padrao, numerico in padroes:
        for m in re.finditer(padrao + hora, texto, re.IGNORECASE):
            try:
                dia = int(m.group(1))
                mes = int(m.group(2)) if numerico else _mes(m.group(2))
                if not mes or not (1 <= mes <= 12) or not (1 <= dia <= 31):
                    continue
                ano = int(m.group(3)) if m.group(3) else ano_padrao
                hh = int(m.group(4)) if m.group(4) else 23
                mm = int(m.group(5)) if m.group(5) else 59
                if hh > 23 or mm > 59:
                    continue
                achados.append((datetime(ano, mes, dia, hh, mm, tzinfo=BR_TZ), m.group(0).strip()))
            except (ValueError, TypeError):
                continue
    return achados


GATILHOS_PRAZO = [
    "prazo", "ate ", "vencimento", "vence", "entrega", "entregar", "entregue",
    "fechamento", "encerramento", "encerra", "submissao", "submissoes",
    "avaliacao por pares", "avaliacoes por pares", "abertura", "limite",
    "data:", "horario:", "acontece", "sera realizada", "live",
]

# Data de abertura NAO e prazo. O aviso do facilitador diz "Abertura das
# submissoes: 27 jul, 00:00" e "Fechamento das submissoes: 01 ago, 23:59";
# sem separar os dois, o robo anunciava que o Modulo 6 "vencia" no dia em
# que ele na verdade abria.
GATILHOS_INICIO = ["abertura", "abre em", "abre ", "abrem", "inicio de", "inicia",
                   "comeca", "disponivel a partir", "libera em", "liberacao"]
GATILHOS_FIM = ["fechamento", "ate ", "vencimento", "vence", "encerra",
                "encerramento", "limite", "entregue", "entregar", "entrega", "prazo"]


def _tipo_prazo(fragmento, contexto):
    """'inicio' quando a data marca abertura, 'fim' quando marca prazo.
    Na duvida devolve 'fim', que e o caso comum e o que gera alerta."""
    for alvo in (sem_acento(fragmento), sem_acento(contexto)):
        pos_ini = min((alvo.find(g) for g in GATILHOS_INICIO if g in alvo), default=-1)
        pos_fim = min((alvo.find(g) for g in GATILHOS_FIM if g in alvo), default=-1)
        if pos_ini < 0 and pos_fim < 0:
            continue           # nada decisivo aqui, tenta o contexto
        if pos_ini >= 0 and (pos_fim < 0 or pos_ini < pos_fim):
            return "inicio"
        return "fim"
    return "fim"


ABREV_MES = r"\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\."


def extrair_prazos(texto, ano_padrao):
    """So aceita data que aparece perto de uma palavra de prazo.

    Duas manhas necessarias no texto real dos avisos:
      - 'sabado, 01 ago. 2026' nao pode ser cortado no ponto da abreviacao,
        entao protegemos 'ago.' antes de quebrar em frases;
      - o facilitador escreve 'precisa ser entregue ate o primeiro\\ndomingo
        da quinzena, dia 26/07', ou seja, a palavra de prazo cai numa linha e
        a data na seguinte. Por isso olhamos uma janela de 2 trechos atras.

    Guarda o contexto junto, que serve pro site mostrar a origem e pra casar
    o prazo com a secao certa ('Modulo 4').
    """
    protegido = re.sub(ABREV_MES, r"\1§", texto or "", flags=re.IGNORECASE)
    trechos = [t.strip().replace("§", ".")
               for t in re.split(r"[\n;]|\.\s+", protegido) if t.strip()]

    prazos, vistos = [], set()
    for i, f in enumerate(trechos):
        if not (4 <= len(f) <= 300):
            continue
        contexto = " ".join(trechos[max(0, i - 2):i + 1])
        if not any(g in sem_acento(contexto) for g in GATILHOS_PRAZO):
            continue
        for quando, trecho in achar_datas(f, ano_padrao):
            rotulo = f.split(":")[0].strip() if ":" in f[:70] else contexto
            rotulo = rotulo[:87] + "..." if len(rotulo) > 90 else rotulo
            chave = (quando.isoformat(), rotulo[:40])
            if chave in vistos:
                continue
            vistos.add(chave)
            prazos.append({
                "rotulo": rotulo, "quando": quando.isoformat(), "trecho": trecho,
                "tipo": _tipo_prazo(f, contexto),
                "frase": contexto if len(contexto) <= 220 else contexto[:217] + "...",
            })
    return prazos


def ler_cronograma(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(800)
        linhas = page.evaluate(JS_CRONOGRAMA)
    except Exception as e:
        print(f"  aviso: cronograma {url} falhou ({e})")
        return None
    semanas = []
    for linha in linhas:
        m = re.search(r"Semana\s+(\d+)", linha, re.IGNORECASE)
        if not m:
            continue
        datas = achar_datas(linha, date.today().year)
        if len(datas) < 2:
            continue
        semanas.append({
            "n": int(m.group(1)),
            "inicio": datas[0][0].date().isoformat(),
            "vencimento": datas[1][0].isoformat(),
            "carencia": datas[2][0].isoformat() if len(datas) > 2 else None,
        })
    if not semanas:
        return None
    return {"fonte": url, "semanas": sorted(semanas, key=lambda s: s["n"])}


# ---------------------------------------------------------------------------
# Fontes estruturadas: calendario, notificacoes, mensagens
# ---------------------------------------------------------------------------
def _cmid_de(url):
    m = re.search(r"id=(\d+)", url or "")
    return m.group(1) if m else ""


def ler_calendario_api(page):
    agora = int(datetime.now(timezone.utc).timestamp())
    dados = api(page, "core_calendar_get_action_events_by_timesort", {
        "timesortfrom": agora - 86400 * 60,
        "timesortto": agora + 86400 * 240,
        "limitnum": 200,
    })
    eventos = []
    for e in (dados or {}).get("events", []) or []:
        if not e.get("timesort"):
            continue
        curso = e.get("course") or {}
        eventos.append({
            "nome": e.get("name"),
            "quando": datetime.fromtimestamp(e["timesort"], BR_TZ).isoformat(),
            "curso_id": str(curso.get("id") or ""),
            "curso": curso.get("shortname"),
            "atividade": e.get("activityname"),
            "url": e.get("url"),
            "acao": (e.get("action") or {}).get("name"),
            "cmid": _cmid_de(e.get("url")),
        })
    return eventos


def ler_calendario_dom(page, hoje):
    """Le o calendario pela pagina, quando a API nao coopera."""
    por_id = {}
    try:
        page.goto(f"{AVA}/calendar/view.php?view=upcoming&lookahead=365",
                  wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1500)
        for e in page.evaluate(JS_EVENTOS_LISTA):
            if e.get("id"):
                por_id[e["id"]] = e
    except Exception as e:
        print(f"  aviso: lista de eventos falhou ({type(e).__name__})")

    base = datetime(hoje.year, hoje.month, 15, 12, 0, tzinfo=BR_TZ)
    for salto in range(-1, 5):
        alvo = base + timedelta(days=31 * salto)
        try:
            page.goto(f"{AVA}/calendar/view.php?view=month&time={int(alvo.timestamp())}",
                      wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(900)
            for ev in page.evaluate(JS_EVENTOS_MES):
                alvo_ev = por_id.setdefault(ev["id"], {"id": ev["id"]})
                alvo_ev["dia"] = datetime.fromtimestamp(ev["dia_ts"], BR_TZ).date()
        except Exception:
            continue

    eventos = []
    for e in por_id.values():
        if not e.get("dia"):
            continue
        hh, mm = 23, 59
        if e.get("hora"):
            try:
                hh, mm = [int(x) for x in e["hora"].split(":")]
            except ValueError:
                pass
        d = e["dia"]
        eventos.append({
            "nome": e.get("titulo"),
            "quando": datetime(d.year, d.month, d.day, hh, mm, tzinfo=BR_TZ).isoformat(),
            "curso_id": str(e.get("curso_id") or ""),
            "curso": None,
            "atividade": e.get("titulo"),
            "url": e.get("url"),
            "acao": None,
            "cmid": _cmid_de(e.get("url")),
        })
    return eventos


def ler_calendario(page, hoje):
    eventos = ler_calendario_api(page)
    if eventos:
        print(f"  calendario pela API: {len(eventos)} evento(s)")
        return eventos
    eventos = ler_calendario_dom(page, hoje)
    print(f"  calendario pela pagina: {len(eventos)} evento(s)")
    return eventos


def ler_notificacoes(page, uid):
    dados = api(page, "message_popup_get_popup_notifications",
                {"useridto": uid, "limit": 40, "offset": 0})
    saida = []
    for n in (dados or {}).get("notifications", []) or []:
        quando = n.get("timecreated")
        saida.append({
            "assunto": n.get("subject"),
            "quando": datetime.fromtimestamp(quando, BR_TZ).isoformat() if quando else None,
            "lida": bool(n.get("read")),
            "url": n.get("contexturl"),
        })
    return saida


def ler_mensagens(page, uid):
    """So metadado. O site e publico, entao conteudo de conversa nao sai daqui."""
    dados = api(page, "core_message_get_conversations",
                {"userid": uid, "limitnum": 20})
    saida = []
    for c in (dados or {}).get("conversations", []) or []:
        nao_lidas = c.get("unreadcount") or 0
        if not nao_lidas:
            continue
        nomes = [m.get("fullname") for m in (c.get("members") or []) if m.get("fullname")]
        saida.append({
            "de": ", ".join(nomes[:3]) or "alguém no AVA",
            "nao_lidas": nao_lidas,
            "url": f"{AVA}/message/index.php?id={c.get('id')}",
        })
    return saida


# ---------------------------------------------------------------------------
# Foruns, com leitura incremental
# ---------------------------------------------------------------------------
LINKS_QUENTES = ("elos.vc", "youtube", "youtu.be", "meet.google", "teams.microsoft", "zoom.")
CHAVES_AVISO = ("criterio", "avaliacao", "organizacao", "aviso", "comunicado", "live",
                "gravacao", "representante", "peso", "prazo", "entrega", "grupo")


def post_interessa(post):
    alvo = sem_acento(post.get("texto", ""))[:800]
    titulo = sem_acento(post.get("titulo", ""))
    if any(g in alvo for g in GATILHOS_PRAZO):
        return True
    if any(k in (l or "") for l in post.get("links", []) for k in LINKS_QUENTES):
        return True
    return any(c in titulo or c in alvo for c in CHAVES_AVISO)


JANELA_AVISOS_DIAS = 45
NOVO_ATE_DIAS = 3
MAX_POSTS_POR_DISCUSSAO = 10


def _preparar(post, rotulo_forum, url, titulo_alt, ano):
    post["forum"] = rotulo_forum
    post["url"] = url
    post["titulo"] = post.get("titulo") or titulo_alt
    post["prazos"] = extrair_prazos(post.get("texto", ""), ano)
    post["texto"] = (post.get("texto") or "")[:TRECHO_AVISO]
    post["links"] = [l for l in (post.get("links") or []) if l][:6]
    post.pop("url_forum", None)
    return post


def varrer_foruns(page, foruns, estado, ano, orcamento, hoje):
    """Varre todos os foruns do curso e devolve os avisos da janela recente.

    O estado guarda, por discussao, a data do ultimo post E os avisos ja
    processados. Isso serve a dois propositos: nao reabrir discussao que nao
    mexeu, e continuar entregando o aviso mesmo quando ele deixa de ser
    novidade. Sem o cache, um prazo achado ontem sumia hoje, que foi como o
    alerta do Modulo 4 se perdeu na segunda execucao.
    """
    coletados = []

    def guardar(chave, ultimo, posts):
        estado[chave] = {"ultimo": ultimo or "", "posts": posts[:MAX_POSTS_POR_DISCUSSAO]}
        return estado[chave]["posts"]

    for f in foruns:
        cache_forum = estado.get(f["url"], {})
        if orcamento <= 0:
            coletados.extend(cache_forum.get("posts", []))
            continue
        try:
            page.goto(f["url"], wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(700)
            orcamento -= 1
        except Exception:
            coletados.extend(cache_forum.get("posts", []))
            continue

        try:
            aqui = page.evaluate(JS_POSTS)
        except Exception:
            aqui = []
        try:
            discussoes = page.evaluate(JS_DISCUSSOES)
        except Exception:
            discussoes = []

        # forum de discussao unica: os posts estao na propria pagina
        if aqui and not discussoes:
            mais_novo = max((p.get("data") or "") for p in aqui)
            if mais_novo > (cache_forum.get("ultimo") or "") or "posts" not in cache_forum:
                bons = [_preparar(p, f["label"], f["url"], f["label"], ano)
                        for p in aqui if post_interessa(p)]
                bons.sort(key=lambda p: p.get("data") or "", reverse=True)
                coletados.extend(guardar(f["url"], mais_novo, bons))
            else:
                coletados.extend(cache_forum.get("posts", []))
            continue

        for d in discussoes:
            cache = estado.get(d["url"], {})
            parada = (cache.get("ultimo") and d.get("ultimo")
                      and d["ultimo"] <= cache["ultimo"] and "posts" in cache)
            if parada or orcamento <= 0:
                coletados.extend(cache.get("posts", []))
                continue
            try:
                page.goto(d["url"], wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(600)
                orcamento -= 1
                posts = page.evaluate(JS_POSTS)
            except Exception:
                coletados.extend(cache.get("posts", []))
                continue
            bons = [_preparar(p, f["label"], d["url"], d.get("titulo"), ano)
                    for p in posts if post_interessa(p)]
            bons.sort(key=lambda p: p.get("data") or "", reverse=True)
            coletados.extend(guardar(d["url"], d.get("ultimo"), bons))

    corte = (hoje - timedelta(days=JANELA_AVISOS_DIAS)).isoformat()
    recente = (hoje - timedelta(days=NOVO_ATE_DIAS)).isoformat()
    saida, vistos = [], set()
    for p in coletados:
        data = (p.get("data") or "")[:10]
        if data < corte:
            continue
        chave = (p.get("url"), p.get("data"), (p.get("titulo") or "")[:40])
        if chave in vistos:
            continue
        vistos.add(chave)
        p["novo"] = data >= recente
        saida.append(p)
    saida.sort(key=lambda a: a.get("data") or "", reverse=True)
    return saida, orcamento


# ---------------------------------------------------------------------------
# Item aberto ou fechado
# ---------------------------------------------------------------------------
SINAIS_FECHADO = [
    "nao esta aberta", "nao esta aberto", "nao esta disponivel",
    "nao esta mais disponivel", "esta atividade encerrou",
    "o prazo para envio expirou", "nao e mais possivel",
    "periodo encerrado", "fora do prazo", "esta pesquisa nao esta",
]


def item_aberto(page, url):
    """True da pra fazer, False a pagina diz que fechou, None nao deu pra saber."""
    if not url:
        return None
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(500)
        corpo = sem_acento(page.locator("body").inner_text()[:4000])
    except Exception:
        return None
    return not any(s in corpo for s in SINAIS_FECHADO)


# ---------------------------------------------------------------------------
# Nota, verbo, urgencia
# ---------------------------------------------------------------------------
def conta_nota(modelo, item, secao):
    lab = sem_acento(item.get("label", ""))
    tipo = item.get("type")
    if tipo in ("quiz", "scorm", "assign", "workshop"):
        return True
    if modelo == "regular":
        return any(k in lab for k in
                   ("videoaula", "video-base", "video base", "texto-base",
                    "material-base", "material base"))
    if sem_acento(secao).startswith("modulo") or "live" in lab:
        return True
    return tipo == "feedback"


def verbo_de(item):
    lab = sem_acento(item.get("label", ""))
    tipo = item.get("type")
    if tipo == "quiz":
        return "Responda", "questionário"
    if tipo == "scorm":
        return "Faça", "quiz interativo"
    if tipo == "feedback":
        return "Responda", "formulário"
    if tipo == "assign":
        return "Entregue", "tarefa"
    if tipo == "workshop":
        return "Entregue e avalie", "revisão por pares"
    if tipo == "lti":
        return ("Assista", "live") if "live" in lab else ("Acesse", "ferramenta")
    if tipo == "forum":
        return "Participe", "do fórum"
    if any(k in lab for k in ("videoaula", "video-base", "video base")):
        return "Assista", "videoaula"
    if any(k in lab for k in ("texto-base", "material-base", "material", "leia")):
        return "Leia", "material-base"
    if tipo == "url":
        return "Acesse", "link"
    return "Abra e conclua", "página"


def urgencia_de(prazo_iso, hoje):
    if not prazo_iso:
        return "sem_prazo", ""
    q = datetime.fromisoformat(prazo_iso)
    dias = (q.date() - hoje).days
    if dias < 0:
        return "vencido", f"venceu em {q:%d/%m}"
    if dias == 0:
        return "hoje", f"vence hoje às {q:%H:%M}"
    if dias == 1:
        return "amanha", f"vence amanhã, {q:%d/%m} às {q:%H:%M}"
    if dias <= 7:
        return "semana", f"vence {q:%d/%m} às {q:%H:%M}"
    return "depois", f"vence {q:%d/%m}"


ORDEM = {"hoje": 0, "amanha": 1, "semana": 2, "depois": 3, "sem_prazo": 4, "vencido": 5}


# ---------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------
def deslogado(page):
    return "/login" in page.url or "univesp_login.php" in page.url


def coletar(estado):
    hoje = datetime.now(BR_TZ).date()
    with sync_playwright() as p:
        nav = p.chromium.launch(headless=True)
        ctx = sessao.novo_contexto(nav)
        page = ctx.new_page()

        # Se a sessao salva ainda vale, entra direto. Se venceu, loga sozinho
        # com as credenciais do cofre. So desiste se nao houver credenciais.
        ok, como = sessao.garantir(page)
        if not ok:
            print(f"  {como}")
            nav.close()
            return None, "session_expired"
        if como == "login":
            sessao.salvar_sessao(ctx)
            print("  sessao renovada sozinha.")

        uid = user_id(page)
        print("Lendo calendario, notificacoes e mensagens...")
        eventos = ler_calendario(page, hoje)
        notificacoes = ler_notificacoes(page, uid) if uid else []
        mensagens = ler_mensagens(page, uid) if uid else []
        print(f"  {len(eventos)} evento(s), {len(notificacoes)} notificacao(oes), "
              f"{len(mensagens)} conversa(s) nao lida(s).")

        page.goto(f"{AVA}/my/courses.php", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        descobertos = page.evaluate(JS_MEUS_CURSOS)
        print(f"Disciplinas encontradas: {len(descobertos)}")

        eventos_por_curso = {}
        for e in eventos:
            eventos_por_curso.setdefault(e["curso_id"], []).append(e)

        cronogramas = {}
        orcamento = MAX_DISCUSSOES_POR_RUN
        cursos = []

        for cur in descobertos:
            nome = cur["nome"]
            m = re.search(r"\b([A-Z]{3}\d{3})\b", nome)
            codigo = m.group(1) if m else nome[:12]
            print(f"Lendo {codigo}...")

            page.goto(f"{AVA}/course/view.php?id={cur['id']}",
                      wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            if deslogado(page):
                # caiu no meio da leitura: tenta voltar sozinho antes de desistir
                ok, _ = sessao.garantir(page)
                if not ok:
                    nav.close()
                    return None, "session_expired"
                page.goto(f"{AVA}/course/view.php?id={cur['id']}",
                          wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1500)

            bruto = page.evaluate(JS_CURSO)
            secoes, links = bruto["secoes"], bruto.get("links") or {}
            for s in secoes:
                s["locked"] = limpar_bloqueio(s.get("locked"))
            modelo = "quinzenal" if any(
                sem_acento(s["title"]).startswith("quinzena") for s in secoes) else "regular"

            # cronograma: o link vem do proprio curso, com fallback
            url_crono = links.get("cronograma") or CRONOGRAMA_PADRAO
            if url_crono not in cronogramas:
                cronogramas[url_crono] = ler_cronograma(page, url_crono)
            cronograma = cronogramas[url_crono]

            # prazo real por cmid
            prazo_por_cmid = {}
            for e in eventos_por_curso.get(str(cur["id"]), []):
                if e.get("cmid"):
                    prazo_por_cmid[e["cmid"]] = e

            # fase AIA (ambientacao ja encerrada) por heranca de secao
            por_id = {s["id"]: s for s in secoes}

            def em_aia(sec):
                atual, n = sec, 0
                while atual and n < 6:
                    if sem_acento(atual["title"]).startswith("aia"):
                        return True
                    atual = por_id.get(atual.get("parent"))
                    n += 1
                return False

            for s in secoes:
                s["fase"] = "AIA" if em_aia(s) else "regular"
                num = None
                mm = re.match(r"Semana (\d+)$", s["title"])
                if mm and modelo == "regular":
                    num = int(mm.group(1))
                for it in s["items"]:
                    it["conta_nota"] = conta_nota(modelo, it, s["title"])
                    it["prazo"] = it["prazo_fonte"] = it["carencia"] = None
                    ev = prazo_por_cmid.get(str(it.get("cmid")))
                    if ev:
                        it["prazo"] = ev["quando"]
                        it["prazo_fonte"] = "calendário do AVA"
                    elif num and cronograma and it["conta_nota"]:
                        sem = next((x for x in cronograma["semanas"] if x["n"] == num), None)
                        if sem:
                            it["prazo"] = sem["vencimento"]
                            it["carencia"] = sem["carencia"]
                            it["prazo_fonte"] = "cronograma oficial da Univesp"

            # todos os foruns do curso, incremental
            foruns = [{"label": it["label"], "url": it["url"]}
                      for s in secoes for it in s["items"]
                      if it["type"] == "forum" and it.get("url")]
            print(f"  {len(foruns)} forum(ns) a varrer (orcamento {orcamento})")
            avisos, orcamento = varrer_foruns(page, foruns, estado, hoje.year,
                                              orcamento, hoje)
            novos = sum(1 for a in avisos if a.get("novo"))
            print(f"  {len(avisos)} aviso(s) na janela, {novos} novo(s)")

            # confere se pendente ainda esta aberto
            pendentes = [(s, it) for s in secoes if not s.get("locked")
                         for it in s["items"]
                         if it.get("status") != "Concluído"
                         and (it.get("status") == "Pendente" or it.get("conta_nota"))]
            for s, it in pendentes[:MAX_ITENS_CONFERIDOS]:
                if s.get("fase") == "AIA":
                    it["aberto"] = False
                    it["motivo_fechado"] = "a ambientação (AIA) encerrou"
                    continue
                it["aberto"] = item_aberto(page, it.get("url"))
                if it["aberto"] is False:
                    it["motivo_fechado"] = "o AVA diz que não está aberta"

            cursos.append({
                "code": codigo, "name": nome, "id": cur["id"], "modelo": modelo,
                "progress_pct": cur.get("pct"), "links": links,
                "cronograma": cronograma, "avisos": avisos[:15], "sections": secoes,
            })

        nav.close()
    return {"courses": cursos, "notificacoes": notificacoes,
            "mensagens": mensagens, "eventos": eventos}, "ok"


# ---------------------------------------------------------------------------
# Acoes
# ---------------------------------------------------------------------------
def casar_prazo(titulo_secao, prazos_aviso):
    """Acha, entre os prazos lidos dos avisos, o que fala desta secao.

    So considera data de fechamento: data de abertura nao e prazo e viraria
    alerta falso ("Modulo 6 vence 27/07" quando 27/07 e o dia que ele abre).
    """
    chave = sem_acento(titulo_secao)
    if not chave:
        return None
    for pz in prazos_aviso:
        if pz.get("tipo") == "inicio":
            continue
        if chave in sem_acento(pz["rotulo"] + " " + pz["frase"]):
            return pz
    return None


def montar_acoes(dados, hoje):
    acoes, encerrados = [], []
    for c in dados["courses"]:
        prazos_aviso = [{**pz, "aviso": a} for a in c.get("avisos", [])
                        for pz in a.get("prazos", [])]
        for s in c["sections"]:
            if s.get("locked"):
                # Secao fechada nao gera tarefa... a nao ser que um aviso diga
                # que ela tem prazo. E o caso classico do "Modulo 4 vence
                # domingo" enquanto o modulo so abre depois de concluir o 1.
                # Sem isso, o item mais urgente do bimestre ficaria invisivel.
                pz = casar_prazo(s["title"], prazos_aviso)
                if not pz:
                    continue
                urg, txt = urgencia_de(pz["quando"], hoje)
                if urg == "vencido":
                    continue
                acoes.append({
                    "curso": c["code"], "secao": s["title"], "fase": s.get("fase", "regular"),
                    "verbo": "Destrave e entregue", "coisa": "", "o_que": s["title"],
                    "tipo": "bloqueado", "url": None, "conta_nota": True,
                    "prazo": pz["quando"], "prazo_txt": txt,
                    "prazo_fonte": f"aviso de {pz['aviso'].get('autor') or 'facilitador'}",
                    "fonte_url": pz["aviso"].get("url"), "carencia": None,
                    "urgencia": urg, "bloqueio": s["locked"],
                })
                continue
            for it in s["items"]:
                if it.get("status") == "Concluído":
                    continue
                if it.get("status") is None and not it.get("conta_nota"):
                    continue  # material de apoio, sem cobranca
                verbo, coisa = verbo_de(it)
                base = {
                    "curso": c["code"], "secao": s["title"], "fase": s.get("fase", "regular"),
                    "verbo": verbo, "coisa": coisa, "o_que": it["label"],
                    "tipo": it["type"], "url": it.get("url"),
                    "conta_nota": it.get("conta_nota", False),
                }
                if it.get("aberto") is False:
                    encerrados.append({**base, "motivo": it.get("motivo_fechado", "encerrado")})
                    continue

                prazo, fonte, fonte_url = it.get("prazo"), it.get("prazo_fonte"), None
                if not prazo:
                    pz = casar_prazo(s["title"], prazos_aviso)
                    if pz:
                        prazo = pz["quando"]
                        fonte = f"aviso de {pz['aviso'].get('autor') or 'facilitador'}"
                        fonte_url = pz["aviso"].get("url")

                urg, txt = urgencia_de(prazo, hoje)
                if urg == "vencido":
                    encerrados.append({**base, "motivo": txt})
                    continue
                acoes.append({**base, "prazo": prazo, "prazo_txt": txt, "prazo_fonte": fonte,
                              "fonte_url": fonte_url, "carencia": it.get("carencia"),
                              "urgencia": urg})

    propagar_urgencia(acoes, hoje)
    acoes.sort(key=lambda a: (ORDEM.get(a["urgencia"], 9), a["prazo"] or "9999",
                              0 if a["conta_nota"] else 1, a["curso"]))
    return acoes, encerrados


FAMILIA_RE = re.compile(r"(\D+?)\s*(\d+)\s*$")


def propagar_urgencia(acoes, hoje):
    """Se o Modulo 4 vence amanha, mas so abre depois de concluir o 1, 2 e 3,
    entao o que falta no Modulo 1 tambem e pra agora.

    Sem isso o item que destrava tudo (o quiz do Modulo 1) aparecia la no fim
    da lista, sem prazo, enquanto o prazo real corria. So propaga quando o
    bloqueio e por conclusao de etapa; bloqueio por data ('disponivel a partir
    de 27/07') nao encadeia nada.
    """
    por_curso = {}
    for a in acoes:
        por_curso.setdefault(a["curso"], []).append(a)

    for lista in por_curso.values():
        travas = []
        for a in lista:
            m = FAMILIA_RE.match(a.get("secao") or "")
            if not m or not a.get("prazo"):
                continue
            if a.get("bloqueio") and "conclu" not in sem_acento(a["bloqueio"]):
                continue  # bloqueio por data nao forma cadeia
            travas.append((sem_acento(m.group(1)).strip(), int(m.group(2)), a["prazo"],
                           a.get("prazo_fonte"), a.get("fonte_url")))
        if not travas:
            continue
        for a in lista:
            if a.get("prazo"):
                continue
            m = FAMILIA_RE.match(a.get("secao") or "")
            if not m:
                continue
            familia, numero = sem_acento(m.group(1)).strip(), int(m.group(2))
            adiante = [t for t in travas if t[0] == familia and t[1] > numero]
            if not adiante:
                continue
            _, _, prazo, fonte, fonte_url = min(adiante, key=lambda t: t[2])
            urg, txt = urgencia_de(prazo, hoje)
            a["prazo"] = prazo
            a["urgencia"] = urg
            a["prazo_txt"] = txt
            a["destrava"] = True
            # o prazo e o mesmo da etapa travada, entao a origem tambem e
            a["prazo_fonte"] = a.get("prazo_fonte") or fonte
            a["fonte_url"] = a.get("fonte_url") or fonte_url
    return acoes


def carregar(caminho, padrao):
    if caminho.exists():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except Exception:
            return padrao
    return padrao


def novidades(anterior, dados):
    mudou = []
    antes = {}
    for c in (anterior or {}).get("courses", []):
        for s in c.get("sections", []):
            for it in s.get("items", []):
                antes[(c.get("code"), it.get("label"))] = it.get("status")
    for c in dados["courses"]:
        for s in c["sections"]:
            for it in s["items"]:
                k = (c["code"], it.get("label"))
                if k not in antes and it.get("status") is not None:
                    mudou.append({"curso": c["code"], "label": it["label"], "kind": "novo"})
                elif antes.get(k) != it.get("status") and it.get("status") == "Concluído":
                    mudou.append({"curso": c["code"], "label": it["label"], "kind": "concluido"})
        for a in c.get("avisos", []):
            if a.get("novo"):   # os antigos ficam no site, mas nao contam como mudanca
                mudou.append({"curso": c["code"], "label": a.get("titulo") or "novo post",
                              "kind": "aviso"})
    return mudou


def main():
    anterior = carregar(DATA_PATH, None)
    estado = carregar(ESTADO_PATH, {})
    agora = datetime.now(timezone.utc).isoformat()
    dados, status = coletar(estado)

    if status == "session_expired":
        saida = anterior or {"courses": []}
        saida["status"] = "session_expired"
        saida["checked_at"] = agora
        DATA_PATH.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
        print("SESSAO EXPIRADA - mantive o ultimo retrato e avisei no site.")
        return 0

    hoje = datetime.now(BR_TZ).date()
    acoes, encerrados = montar_acoes(dados, hoje)
    saida = {
        "status": "ok", "checked_at": agora,
        "courses": dados["courses"],
        "notificacoes": dados.get("notificacoes", []),
        "mensagens": dados.get("mensagens", []),
        "acoes": acoes, "encerrados": encerrados,
        "novidades": novidades(anterior, dados),
    }
    DATA_PATH.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    ESTADO_PATH.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK. {len(acoes)} acao(oes), {len(encerrados)} encerrada(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
