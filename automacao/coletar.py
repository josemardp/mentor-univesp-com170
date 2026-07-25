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
import os  # reexport temporário: testes antigos injetam falha em os.replace
import re
import sys
from datetime import datetime, timedelta, timezone

from playwright.sync_api import sync_playwright

import sessao
import persistencia as _persistencia
from configuracao import (
    AVA,
    BR_TZ,
    CRONOGRAMA_PADRAO,
    DATA_PATH,
    DOCS,
    ESTADO_PATH,
    JANELA_AVISOS_DIAS,
    MAX_DISCUSSOES_POR_RUN,
    MAX_ITENS_CONFERIDOS,
    MAX_POSTS_POR_DISCUSSAO,
    NOVO_ATE_DIAS,
    ROOT,
    TRECHO_AVISO,
)
from dominio.datas import achar_datas, mes as _mes, sem_acento
from dominio.acoes import (
    ORDEM,
    conta_nota,
    montar_acoes,
    urgencia_de,
    verbo_de,
)
from dominio.dependencias import (
    FAMILIA_RE,
    PREDECESSOR_RE,
    predecessor_de,
    propagar_urgencia,
    secao_do_predecessor,
)
from dominio.prazos import (
    ABREV_MES,
    CAIXA_ALTA_RE,
    ESCOPO_RE,
    GATILHOS_FIM,
    GATILHOS_INICIO,
    GATILHOS_PRAZO,
    NEGACAO_RE,
    PALAVRAS_FASE,
    ROTULO_RE,
    _escopo_de,
    _posicoes,
    _tem,
    _tipo_prazo,
    casar_prazos,
    eh_fase,
    encerra_escopo,
    escopo_cobre,
    extrair_prazos,
    fase_de,
    muda_assunto,
    rotulo_fase,
    tem_negacao,
)


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

# Os tres seletores casam o MESMO post (um e descendente do outro), entao a
# uniao dos tres duplicava cada post. Como o corte do cache acontecia antes da
# desduplicacao, o teto de 10 virava 5 posts reais por discussao. Agora usamos
# o primeiro seletor que encontrar algo, em vez da uniao.
JS_POSTS = """
() => {
  const seletores = ['article.forum-post-container', '[data-region="post"]', '.forumpost'];
  let achados = [];
  for (const s of seletores) {
    achados = [...document.querySelectorAll(s)];
    if (achados.length) break;
  }
  return achados.map(p => {
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
  }).filter(p => p.texto);
}
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


def _posicoes(alvo, termos):
    """Todas as posicoes onde algum termo aparece, com limite de palavra.

    O limite existe porque 'inicia' casava dentro de 'LIVE INICIAL' e o aviso
    da live virava "abertura".
    """
    return [m.start() for t in termos
            for m in re.finditer(r"\b" + re.escape(t.strip()) + r"\b", alvo)]


def _tem(alvo, termos):
    """Posicao do primeiro termo achado, ou -1."""
    pos = _posicoes(alvo, termos)
    return min(pos) if pos else -1


GATILHOS_PRAZO = [
    "prazo", "ate", "vencimento", "vence", "entrega", "entregar", "entregue",
    "fechamento", "encerramento", "encerra", "submissao", "submissoes",
    "avaliacao por pares", "avaliacoes por pares", "abertura", "limite",
    "data", "horario", "acontece", "sera realizada",
    # "abre em 27/07 e fecha em 01/08" nao passava no filtro e o prazo sumia
    "abre", "abrem", "fecha", "fecham",
]

# Data de abertura NAO e prazo. O aviso do facilitador lista "Abertura das
# submissoes: 27 jul" e "Fechamento das submissoes: 01 ago"; sem separar as
# duas, o robo anunciava que o Modulo 6 "vencia" no dia em que ele abria.
GATILHOS_INICIO = ["abertura", "abre", "abrem", "inicia", "iniciam", "comeca",
                   "comecam", "disponivel a partir", "libera", "liberacao"]
GATILHOS_FIM = ["fechamento", "ate", "vencimento", "vence", "encerra",
                "encerramento", "limite", "entregue", "entregar", "entrega",
                "prazo", "fecha"]


def _tipo_prazo(fragmento, contexto, pos_data=None):
    """'inicio' quando a data marca abertura, 'fim' quando marca prazo.

    Classifica pela palavra MAIS PRÓXIMA da data, não pela primeira da frase.
    Em "A abertura ocorre em 27/07 e o prazo fecha em 01/08" as duas datas
    saíam como abertura, e o fechamento de 01/08 desaparecia da fila.

    Na dúvida devolve 'fim', que é o caso comum e o que gera alerta.
    """
    # No fragmento sabemos onde a data está, então usamos a palavra que a
    # governa: em português ela vem ANTES ("Abertura das submissões: 27/07").
    # Distância pura escolhia errado, porque "prazo fecha" ficava mais perto de
    # 27/07 do que o "abertura" que abre a frase.
    alvo = sem_acento(fragmento)
    ini, fim = _posicoes(alvo, GATILHOS_INICIO), _posicoes(alvo, GATILHOS_FIM)
    if pos_data is not None and (ini or fim):
        antes_ini = [p for p in ini if p <= pos_data]
        antes_fim = [p for p in fim if p <= pos_data]
        depois_ini = [p for p in ini if p > pos_data]
        depois_fim = [p for p in fim if p > pos_data]

        por_antes = por_depois = None
        if antes_ini or antes_fim:
            por_antes = "inicio" if max(antes_ini or [-1]) > max(antes_fim or [-1]) else "fim"
        if depois_ini or depois_fim:
            por_depois = ("inicio" if min(depois_ini or [10 ** 9])
                          < min(depois_fim or [10 ** 9]) else "fim")

        # A palavra que governa a data costuma vir antes dela. Mas quando a de
        # trás e a da frente discordam ("27/07 (abertura), 01/08 (fechamento)"),
        # não dá pra ter certeza: devolvemos o palpite E o aviso de incerteza,
        # pra o prazo ir parar no bloco de confirmação em vez da fila.
        escolhido = por_antes or por_depois or "fim"
        seguro = (por_antes is None or por_depois is None or por_antes == por_depois)
        return escolhido, seguro

    # Sem posição utilizável, decide pela primeira palavra do trecho e, se ele
    # não disser nada, pelo contexto ao redor.
    for texto in (alvo, sem_acento(contexto)):
        pi, pf = _tem(texto, GATILHOS_INICIO), _tem(texto, GATILHOS_FIM)
        if pi < 0 and pf < 0:
            continue
        if pi >= 0 and (pf < 0 or pi < pf):
            return "inicio", True
        return "fim", True
    return "fim", True


# "Modulo 6 e 7: ..." seguido de uma lista de datas. O escopo vale para as
# datas seguintes ate aparecer outro; sem isso, o "Fechamento das avaliacoes
# por pares" ficava orfao e a fase de avaliacao sumia da fila.
ESCOPO_RE = re.compile(r"\b(m[óo]dulos?|semanas?|quinzenas?)\b([\s\d,ee]{0,20})",
                       re.IGNORECASE)


def _escopo_de(fragmento):
    m = ESCOPO_RE.search(fragmento or "")
    if not m:
        return None
    numeros = [int(x) for x in re.findall(r"\d+", m.group(2))]
    if not numeros:
        return None
    familia = sem_acento(m.group(1)).rstrip("s")
    return {"familia": familia, "numeros": numeros, "txt": fragmento[:120]}


# Rotulos que sao FASE de uma obrigacao ("Abertura das submissoes:") e portanto
# continuam dentro do escopo aberto. Qualquer outro rotulo antes de ":" indica
# assunto novo e encerra o escopo.
PALAVRAS_FASE = ("abertura", "fechamento", "encerramento", "inicio", "fim",
                 "prazo", "entrega", "submissao", "submissoes", "avaliacao",
                 "avaliacoes", "revisao", "data", "horario", "limite",
                 "vencimento", "atencao", "obs")

ROTULO_RE = re.compile(r"^([^:]{2,60}):")


# Frase que NEGA a obrigação. "Não haverá entrega em 30/07" criava um prazo de
# entrega no dia 30/07: o robô lia a negação e inventava a obrigação negada.
NEGACAO_RE = re.compile(
    r"\b(nao\s+(?:hav|have|tera|tem|ha|sera|have?ra)\w*|sem\s+(?:entrega|prazo|"
    r"atividade|submissao)|fica\s+sem|nao\s+e\s+necessario)\b")


def tem_negacao(texto):
    return bool(NEGACAO_RE.search(sem_acento(texto or "")))


def eh_fase(fragmento):
    """O trecho é uma fase da obrigação aberta ("Fechamento das submissões:")?"""
    m = ROTULO_RE.match((fragmento or "").strip())
    if not m:
        return False
    return any(p in sem_acento(m.group(1)) for p in PALAVRAS_FASE)


# Título em caixa alta é como estes avisos marcam assunto novo:
# "LIVE INICIAL: ...", "LIVE MAGNA será realizada em ...".
CAIXA_ALTA_RE = re.compile(r"^[A-ZÀ-Ý][A-ZÀ-Ý]+(\s+[A-ZÀ-Ý0-9]{2,}){1,}")


def muda_assunto(fragmento):
    """O trecho abre um assunto diferente do módulo que estava em pauta?

    Prosa corrida NÃO muda assunto: o aviso real descreve o Módulo 4 em várias
    linhas seguidas, e tratar cada linha como assunto novo rebaixava um prazo
    que é confiável. O que muda assunto é um rótulo antes de dois pontos que
    não seja fase, ou um título em caixa alta.
    """
    f = (fragmento or "").strip()
    if CAIXA_ALTA_RE.match(f):
        return True
    m = ROTULO_RE.match(f)
    return bool(m) and not eh_fase(f)


def encerra_escopo(fragmento):
    """O trecho começa um assunto novo?

    Sem isto o escopo do último "Módulo N" ficava colado em tudo que viesse
    depois. Um aviso com "Módulo 4: entregue até 26/07" seguido de
    "LIVE MAGNA: será realizada em 30/07" fazia a data da live virar prazo do
    Módulo 4 — prazo inventado, que é a pior falha possível aqui.
    """
    m = ROTULO_RE.match((fragmento or "").strip())
    if not m:
        return False
    rotulo = sem_acento(m.group(1))
    if _escopo_de(fragmento):
        return False              # é um novo escopo, tratado à parte
    return not any(p in rotulo for p in PALAVRAS_FASE)


def escopo_cobre(escopo, titulo_secao):
    """O escopo lido do aviso fala desta secao?"""
    if not escopo:
        return False
    m = FAMILIA_RE.match(titulo_secao or "")
    if not m:
        return False
    familia = sem_acento(m.group(1)).strip().rstrip("s")
    return familia == escopo["familia"] and int(m.group(2)) in escopo["numeros"]


ABREV_MES = r"\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\."


def extrair_prazos(texto, referencia):
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
    escopo, escopo_forte = None, False
    for i, f in enumerate(trechos):
        achado = _escopo_de(f)
        if achado:
            escopo, escopo_forte = achado, True   # vale para as datas seguintes
        elif escopo is not None and muda_assunto(f):
            # Assunto novo depois de um módulo: não dá mais pra afirmar que a
            # data pertence àquele módulo. Não jogamos o escopo fora (isso
            # deixaria o prazo órfão e invisível): rebaixamos a confiança, e
            # ele vai pro bloco de conferência em vez da fila de tarefas.
            escopo_forte = False
        if not (4 <= len(f) <= 300):
            continue
        contexto = " ".join(trechos[max(0, i - 2):i + 1])
        if _tem(sem_acento(contexto), GATILHOS_PRAZO) < 0:
            continue
        if tem_negacao(f):
            continue                 # frase que nega não vira obrigação
        for quando, trecho, hora_certa, pos in achar_datas(f, referencia):
            rotulo = f.split(":")[0].strip() if ":" in f[:70] else contexto
            rotulo = rotulo[:87] + "..." if len(rotulo) > 90 else rotulo
            chave = (quando.isoformat(), rotulo[:40])
            if chave in vistos:
                continue
            vistos.add(chave)
            tipo, tipo_seguro = _tipo_prazo(f, contexto, pos)
            prazos.append({
                "rotulo": rotulo, "quando": quando.isoformat(), "trecho": trecho,
                "tipo": tipo, "hora_certa": hora_certa, "escopo": escopo,
                "confianca": "alta" if (escopo_forte and tipo_seguro) else "baixa",
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
        datas = achar_datas(linha, datetime.now(BR_TZ))
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
        "limitnum": 50,   # o Moodle recusa acima de 50
    })
    if dados is None:
        return [], False
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
    return eventos, True


def ler_calendario_dom(page, hoje):
    """Le o calendario pela pagina, quando a API nao coopera."""
    por_id = {}
    leituras_ok = 0
    try:
        page.goto(f"{AVA}/calendar/view.php?view=upcoming&lookahead=365",
                  wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1500)
        for e in page.evaluate(JS_EVENTOS_LISTA):
            if e.get("id"):
                por_id[e["id"]] = e
        leituras_ok += 1
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
            leituras_ok += 1
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
    return eventos, leituras_ok > 0


def ler_calendario(page, hoje, diagnostico=None):
    eventos, api_ok = ler_calendario_api(page)
    if eventos:
        print(f"  calendario pela API: {len(eventos)} evento(s)")
        if diagnostico is not None:
            diagnostico.update({"status": "live", "via": "api", "eventos": len(eventos)})
        return eventos
    eventos, dom_ok = ler_calendario_dom(page, hoje)
    print(f"  calendario pela pagina: {len(eventos)} evento(s)")
    if diagnostico is not None:
        if eventos:
            status = "live"
        elif api_ok or dom_ok:
            status = "vazio_confirmado"
        else:
            status = "falhou"
        diagnostico.update({
            "status": status,
            "via": "dom" if dom_ok else "nenhuma",
            "eventos": len(eventos),
        })
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


def _preparar(post, rotulo_forum, url, titulo_alt, hoje):
    post["forum"] = rotulo_forum
    post["url"] = url
    post["titulo"] = post.get("titulo") or titulo_alt
    # A data do proprio post e a referencia pra resolver ano omitido: um aviso
    # de dezembro que fala em "10 de janeiro" quer dizer o janeiro seguinte.
    try:
        referencia = datetime.fromisoformat(post["data"])
    except (KeyError, TypeError, ValueError):
        referencia = datetime(hoje.year, hoje.month, hoje.day, tzinfo=BR_TZ)
    post["prazos"] = extrair_prazos(post.get("texto", ""), referencia)
    post["texto"] = (post.get("texto") or "")[:TRECHO_AVISO]
    post["links"] = [l for l in (post.get("links") or []) if l][:6]
    post.pop("url_forum", None)
    return post


def varrer_foruns(page, foruns, estado, orcamento, hoje, diagnostico=None):
    """Varre todos os foruns do curso e devolve os avisos da janela recente.

    O estado guarda, por discussao, a data do ultimo post E os avisos ja
    processados. Isso serve a dois propositos: nao reabrir discussao que nao
    mexeu, e continuar entregando o aviso mesmo quando ele deixa de ser
    novidade. Sem o cache, um prazo achado ontem sumia hoje, que foi como o
    alerta do Modulo 4 se perdeu na segunda execucao.
    """
    coletados = []
    listas_live = falhas = pulados_orcamento = cache_em_falha = 0

    def guardar(chave, ultimo, posts):
        # Desduplica ANTES de cortar: cortar primeiro fazia o teto valer metade.
        unicos, vistos_post = [], set()
        for p in posts:
            k = (p.get("data"), (p.get("texto") or "")[:80])
            if k in vistos_post:
                continue
            vistos_post.add(k)
            unicos.append(p)
        cortou = len(unicos) > MAX_POSTS_POR_DISCUSSAO
        if cortou:
            print(f"    aviso: {len(unicos)} posts relevantes, guardando "
                  f"{MAX_POSTS_POR_DISCUSSAO} (truncado) em {chave[-46:]}")
        estado[chave] = {"ultimo": ultimo or "", "truncado": cortou,
                         "posts": unicos[:MAX_POSTS_POR_DISCUSSAO]}
        return estado[chave]["posts"]

    for f in foruns:
        cache_forum = estado.get(f["url"], {})
        if orcamento <= 0:
            coletados.extend(cache_forum.get("posts", []))
            pulados_orcamento += 1
            continue
        try:
            page.goto(f["url"], wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(700)
            if deslogado(page):
                raise RuntimeError("sessão expirou ao abrir fórum")
            orcamento -= 1
            listas_live += 1
        except Exception:
            coletados.extend(cache_forum.get("posts", []))
            falhas += 1
            cache_em_falha += int(bool(cache_forum.get("posts")))
            continue

        try:
            aqui = page.evaluate(JS_POSTS)
        except Exception:
            aqui = []
            falhas += 1
        try:
            discussoes = page.evaluate(JS_DISCUSSOES)
        except Exception:
            discussoes = []
            falhas += 1

        # forum de discussao unica: os posts estao na propria pagina
        if aqui and not discussoes:
            mais_novo = max((p.get("data") or "") for p in aqui)
            if mais_novo > (cache_forum.get("ultimo") or "") or "posts" not in cache_forum:
                bons = [_preparar(p, f["label"], f["url"], f["label"], hoje)
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
                if deslogado(page):
                    raise RuntimeError("sessão expirou ao abrir discussão")
                orcamento -= 1
                posts = page.evaluate(JS_POSTS)
            except Exception:
                coletados.extend(cache.get("posts", []))
                falhas += 1
                cache_em_falha += int(bool(cache.get("posts")))
                continue
            bons = [_preparar(p, f["label"], d["url"], d.get("titulo"), hoje)
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
    if diagnostico is not None:
        if not foruns:
            status = "nao_aplicavel"
        elif falhas and not listas_live:
            status = "falhou"
        elif falhas:
            status = "degradado"
        elif pulados_orcamento:
            status = "parcial"
        else:
            status = "live"
        diagnostico.update({
            "status": status,
            "foruns": len(foruns),
            "listas_live": listas_live,
            "falhas": falhas,
            "pulados_orcamento": pulados_orcamento,
            "cache_usado_em_falha": cache_em_falha,
        })
    return saida, orcamento


# ---------------------------------------------------------------------------
# Item aberto ou fechado
# ---------------------------------------------------------------------------
SINAIS_FECHADO = [
    "nao esta aberta", "nao esta aberto", "nao esta disponivel",
    "nao esta mais disponivel", "esta atividade encerrou",
    "o prazo para envio expirou", "nao e mais possivel",
    "periodo encerrado", "fora do prazo", "esta pesquisa nao esta",
    # texto real do workshop e das tarefas do AVA, que nao estavam cobertos
    "submissoes fechadas", "avaliacoes fechadas", "o prazo de envio terminou",
    "prazo encerrado", "envio encerrado", "atividade encerrada",
]

# Estas frases nao falam da atividade: falam de que NAO conseguimos ve-la.
# Tratar isso como "aberto" era afirmar o que a pagina nao afirmou.
SINAIS_INDEFINIDO = [
    "precisa fazer login", "voce precisa se identificar", "acesso negado",
    "nao tem permissao", "sem permissao para", "erro de permissao",
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
    if any(s in corpo for s in SINAIS_INDEFINIDO):
        return None           # nao sei; quem chama trata como aberto
    if any(s in corpo for s in SINAIS_FECHADO):
        return False
    return True


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


def urgencia_de(prazo_iso, hoje, hora_certa=True):
    """(urgencia, texto). Se a fonte nao informou hora, o texto nao inventa
    uma: dizer 'às 23:59' quando o aviso so disse o dia e precisao falsa."""
    if not prazo_iso:
        return "sem_prazo", ""
    q = datetime.fromisoformat(prazo_iso)
    dias = (q.date() - hoje).days
    hora = f" às {q:%H:%M}" if hora_certa else " (horário não informado)"
    if dias < 0:
        return "vencido", f"venceu em {q:%d/%m}"
    if dias == 0:
        return "hoje", f"vence hoje{hora}"
    if dias == 1:
        return "amanha", f"vence amanhã, {q:%d/%m}{hora}"
    if dias <= 7:
        return "semana", f"vence {q:%d/%m}{hora}"
    return "depois", f"vence {q:%d/%m}"


ORDEM = {"hoje": 0, "amanha": 1, "semana": 2, "depois": 3, "sem_prazo": 4, "vencido": 5}


# ---------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------
def deslogado(page):
    return "/login" in page.url or "univesp_login.php" in page.url


def coletar(estado):
    hoje = datetime.now(BR_TZ).date()
    leitura_iso = datetime.now(timezone.utc).isoformat()
    fontes_status = {}
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
        calendario_diag = {}
        eventos = ler_calendario(page, hoje, calendario_diag)
        if calendario_diag.get("status") in ("live", "vazio_confirmado"):
            calendario_diag["last_live_at"] = leitura_iso
        fontes_status["calendario"] = calendario_diag
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
        cronograma_esperados = cronograma_live = cronograma_falhas = 0
        foruns_global = {
            "foruns": 0, "listas_live": 0, "falhas": 0,
            "pulados_orcamento": 0, "cache_usado_em_falha": 0,
        }
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

            # Cronograma: o link vem do próprio curso. O fallback só vale pra
            # disciplina de modelo semanal; o COM170 é quinzenal e estava
            # recebendo o cronograma regular por padrão, o que fazia a
            # telemetria dizer "cronograma: 4" quando eram 3 de verdade.
            url_crono = links.get("cronograma")
            if not url_crono and modelo == "regular":
                url_crono = CRONOGRAMA_PADRAO
            cronograma = None
            if url_crono:
                cronograma_esperados += 1
                if url_crono not in cronogramas:
                    cronogramas[url_crono] = ler_cronograma(page, url_crono)
                cronograma = cronogramas[url_crono]
                if cronograma:
                    cronograma_live += 1
                else:
                    cronograma_falhas += 1

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
            foruns_diag = {}
            avisos, orcamento = varrer_foruns(
                page, foruns, estado, orcamento, hoje, foruns_diag,
                curso_id=cur["id"])
            for chave in foruns_global:
                foruns_global[chave] += int(foruns_diag.get(chave) or 0)
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
    if cronograma_falhas:
        status_crono = "falhou" if not cronograma_live else "degradado"
    elif cronograma_esperados:
        status_crono = "live"
    else:
        status_crono = "nao_aplicavel"
    fontes_status["cronograma"] = {
        "status": status_crono,
        "esperados": cronograma_esperados,
        "live": cronograma_live,
        "falhas": cronograma_falhas,
    }
    if status_crono == "live":
        fontes_status["cronograma"]["last_live_at"] = leitura_iso

    if not foruns_global["foruns"]:
        status_foruns = "nao_aplicavel"
    elif foruns_global["falhas"] and not foruns_global["listas_live"]:
        status_foruns = "falhou"
    elif foruns_global["falhas"]:
        status_foruns = "degradado"
    elif foruns_global["pulados_orcamento"]:
        status_foruns = "parcial"
    else:
        status_foruns = "live"
    fontes_status["foruns"] = {**foruns_global, "status": status_foruns}
    if status_foruns in ("live", "parcial"):
        fontes_status["foruns"]["last_live_at"] = leitura_iso

    return {"courses": cursos, "notificacoes": notificacoes,
            "mensagens": mensagens, "eventos": eventos,
            "fontes_status": fontes_status}, "ok"


# ---------------------------------------------------------------------------
# Acoes
# ---------------------------------------------------------------------------
def casar_prazos(titulo_secao, prazos_aviso, so_confiaveis=True):
    """Acha, entre os prazos lidos dos avisos, o que fala desta secao.

    So considera data de fechamento: data de abertura nao e prazo e viraria
    alerta falso ("Modulo 6 vence 27/07" quando 27/07 e o dia que ele abre).
    """
    chave = sem_acento(titulo_secao)
    if not chave:
        return []
    saida = []
    for pz in prazos_aviso:
        if pz.get("tipo") == "inicio":
            continue          # data de abertura nao e prazo
        # O casamento é pelo escopo lido do aviso. O reserva olha só o RÓTULO,
        # nunca a frase de contexto: a frase carrega os trechos vizinhos, então
        # "Módulo 4" vazava para a live e para a prova citadas logo abaixo,
        # colando nelas um prazo que não era delas.
        if escopo_cobre(pz.get("escopo"), titulo_secao) or (
                chave in sem_acento(pz.get("rotulo") or "")):
            saida.append(pz)
    saida.sort(key=lambda p: p["quando"])
    if not so_confiaveis:
        return saida
    return [p for p in saida if p.get("confianca", "alta") == "alta"]


def rotulo_fase(pz):
    """Nome curto da fase pro site.

    Quando o aviso escreve "Fechamento das submissões: <data>", o rótulo sai
    pronto e bom. Quando a data está solta no meio de um parágrafo, o rótulo
    vira a frase inteira e fica ilegível ("Módulo 4 · O mesmo vale para o 3 e
    o 4 O Módulo..."), então preferimos o nome da fase.
    """
    r = (pz.get("rotulo") or "").strip()
    if 3 < len(r) <= 55 and not r.endswith("..."):
        return r
    verbo, _ = fase_de(pz)
    return {"Avalie": "avaliação por pares", "Entregue": "entrega"}.get(verbo, "conclusão")


def fase_de(pz):
    """Verbo e nome da fase, lidos do proprio aviso.

    O rotulo manda, e a frase de contexto so decide quando o rotulo nao diz
    nada: a frase do bloco cita entrega E revisao entre pares, entao usa-la
    primeiro fazia "Fechamento das submissoes" virar "Avalie".
    """
    def classificar(alvo):
        if any(k in alvo for k in ("avaliacao por pares", "avaliacoes por pares",
                                   "revisao entre pares", "avaliar")):
            return "Avalie", "o trabalho do outro grupo"
        if any(k in alvo for k in ("submissao", "submissoes", "entrega", "entregue")):
            return "Entregue", "o trabalho"
        return None

    return (classificar(sem_acento(pz.get("rotulo") or ""))
            or classificar(sem_acento(pz.get("frase") or ""))
            or ("Conclua", ""))


def montar_acoes(dados, hoje):
    acoes, encerrados, confirmar, higiene = [], [], [], []
    for c in dados["courses"]:
        prazos_aviso = [{**pz, "aviso": a} for a in c.get("avisos", [])
                        for pz in a.get("prazos", [])]

        # Prazo que o robô leu mas não tem certeza de a quem pertence ou se é
        # início ou fim. Em vez de chutar (e às vezes inventar prazo), vai pra
        # um bloco de conferência, com a frase original e o link do aviso.
        vistos_conf = set()
        for pz in prazos_aviso:
            if pz.get("confianca", "alta") == "alta":
                continue
            urg, txt = urgencia_de(pz["quando"], hoje, pz.get("hora_certa", True))
            if urg == "vencido":
                continue
            k = (pz["quando"], sem_acento(pz.get("rotulo") or ""))
            if k in vistos_conf:
                continue
            vistos_conf.add(k)
            confirmar.append({
                "curso": c["code"], "quando": pz["quando"], "quando_txt": txt,
                "tipo_lido": pz.get("tipo"), "rotulo": pz.get("rotulo"),
                "frase": pz.get("frase"),
                "autor": (pz.get("aviso") or {}).get("autor"),
                "url": (pz.get("aviso") or {}).get("url"),
            })
        for s in c["sections"]:
            # --- obrigacoes da secao, vindas de aviso ---------------------
            # Uma obrigacao pode ter mais de uma fase com prazos diferentes:
            # o trabalho em grupo fecha 01/08 e a avaliacao por pares 04/08.
            # Antes so a primeira virava acao e a segunda, que tambem vale
            # nota, ficava invisivel. Agora cada fase vira uma acao propria.
            vistos_fase = set()
            for pz in casar_prazos(s["title"], prazos_aviso):
                urg, txt = urgencia_de(pz["quando"], hoje, pz.get("hora_certa", True))
                if urg == "vencido":
                    continue
                verbo, coisa = fase_de(pz)
                # O facilitador repete o mesmo prazo em mais de um aviso; sem
                # isto a obrigacao aparecia duas vezes na fila. A chave usa o
                # rotulo inteiro, e nao o verbo: "submissao individual" e
                # "submissao do grupo" caem no mesmo verbo e no mesmo horario,
                # e com chave por verbo uma das duas sumia.
                chave_fase = (pz["quando"], sem_acento(pz.get("rotulo") or ""))
                if chave_fase in vistos_fase:
                    continue
                vistos_fase.add(chave_fase)
                acoes.append({
                    "curso": c["code"], "secao": s["title"], "fase": s.get("fase", "regular"),
                    "verbo": verbo, "coisa": coisa,
                    "o_que": f"{s['title']} · {rotulo_fase(pz)}",
                    "tipo": "obrigacao", "url": None, "conta_nota": True,
                    "prazo": pz["quando"], "prazo_txt": txt,
                    "prazo_fonte": f"aviso de {pz['aviso'].get('autor') or 'facilitador'}",
                    "fonte_url": pz["aviso"].get("url"), "carencia": None,
                    "hora_certa": pz.get("hora_certa", True),
                    "urgencia": urg, "bloqueio": s.get("locked"),
                })
            if s.get("locked"):
                continue     # secao fechada nao tem item pra listar

            # --- itens da secao -------------------------------------------
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

                # Prazo de item so vem de fonte que fala DO ITEM: calendario
                # (por cmid) ou cronograma (por semana). Prazo de aviso fala da
                # secao inteira, entao virava data falsa em material opcional
                # da mesma secao; ele agora aparece como obrigacao, acima.
                prazo, fonte = it.get("prazo"), it.get("prazo_fonte")
                urg, txt = urgencia_de(prazo, hoje)
                if urg == "vencido":
                    encerrados.append({**base, "motivo": txt})
                    continue
                registro = {**base, "prazo": prazo, "prazo_txt": txt,
                            "prazo_fonte": fonte, "fonte_url": None,
                            "carencia": it.get("carencia"), "hora_certa": True,
                            "urgencia": urg}
                # Item que o robô não conseguiu abrir (login, permissão) não
                # pode aparecer igual a um que ele conferiu.
                if it.get("aberto") is None and it.get("status") == "Pendente":
                    registro["verificacao"] = "indefinida"
                # Sem prazo e sem peso na nota: é higiene do Moodle, não tarefa.
                # Sai da fila principal pra não esconder o que vale nota.
                if not prazo and not it.get("conta_nota"):
                    higiene.append(registro)
                    continue
                acoes.append(registro)

    propagar_urgencia(acoes, dados, hoje)
    ordenar = lambda xs: sorted(xs, key=lambda a: (  # noqa: E731
        ORDEM.get(a["urgencia"], 9),
        a.get("prazo") or a.get("prioridade_ate") or "9999",
        0 if a["conta_nota"] else 1, a["curso"]))
    confirmar.sort(key=lambda x: x["quando"])
    return ordenar(acoes), encerrados, ordenar(higiene), confirmar


FAMILIA_RE = re.compile(r"(\D+?)\s*(\d+)\s*$")

# "Disponivel se: A atividade M3 - O custo invisivel da IA esteja marcada como
# concluida" -> queremos o nome da atividade que trava. O Moodle as vezes corta
# a frase ("...esteja" e mais nada), entao nao exigimos o "marcada como
# concluida" no fim, so o verbo.
PREDECESSOR_RE = re.compile(
    r"atividade\s+(.+?)\s+(?:esteja|estiver|for|seja)\b", re.IGNORECASE)


def predecessor_de(bloqueio):
    if not bloqueio:
        return None
    m = PREDECESSOR_RE.search(bloqueio)
    return m.group(1).strip(" .:-") if m else None


def secao_do_predecessor(pred, titulos):
    """Em que secao mora a atividade citada no bloqueio.

    Modulos travados vem sem itens, entao a cadeia nao pode ser andada so
    pelos itens lidos. Aqui casamos "M3 - O custo invisivel" com a secao
    "Modulo 3" pela inicial e pelo numero. Isso serve APENAS pra continuar
    andando na cadeia; quem recebe prioridade e sempre uma atividade real e
    pendente encontrada no fim dela.
    """
    m = re.match(r"\s*([A-Za-zÀ-ÿ]{1,12})\s*0*(\d+)", pred or "")
    if not m:
        return None
    inicial, numero = sem_acento(m.group(1))[:1], int(m.group(2))
    for t in titulos:
        mm = FAMILIA_RE.match(t or "")
        if mm and int(mm.group(2)) == numero and sem_acento(mm.group(1))[:1] == inicial:
            return t
    return None


def propagar_urgencia(acoes, dados, hoje):
    """Marca o que precisa ser feito ANTES de uma etapa com prazo.

    O Modulo 4 vence amanha e so abre depois do M3, que so abre depois do M2,
    que so abre depois do quiz do M1. Logo, o quiz do M1 e pra agora.

    Duas diferencas em relacao a versao anterior, ambas pedidas na auditoria:

      - A cadeia agora vem da condicao real do AVA ("a atividade X esteja
        marcada como concluida"), seguida nome a nome. Antes bastava o numero
        da secao ser menor, o que era palpite disfarcado de dependencia.
      - O item herda PRIORIDADE, nunca prazo. Continua sem `prazo` e sem
        `prazo_fonte`, porque nenhuma fonte oficial deu prazo a ele. O site
        mostra "faca antes de X" e explica por que, em vez de fingir que o
        AVA marcou uma data que nao marcou.
    """
    por_curso = {}
    for a in acoes:
        por_curso.setdefault(a["curso"], []).append(a)

    for c in dados["courses"]:
        lista = por_curso.get(c["code"], [])
        if not lista:
            continue
        # quem trava quem, pelo texto de bloqueio de cada secao
        trava_de = {}
        for s in c["sections"]:
            pred = predecessor_de(s.get("locked"))
            if pred:
                trava_de[s["title"]] = pred
        if not trava_de:
            continue
        por_label = {sem_acento(a["o_que"]): a for a in lista}

        titulos = [s["title"] for s in c["sections"]]
        for alvo in sorted([a for a in lista if a.get("prazo")],
                           key=lambda a: a["prazo"]):
            secao, visitados = alvo.get("secao"), set()
            prazo = alvo["prazo"]
            # anda pra tras na cadeia: M4 <- M3 <- M2 <- M1, ate encontrar uma
            # atividade que exista de verdade e ainda esteja pendente
            while secao and secao in trava_de and secao not in visitados:
                visitados.add(secao)
                pred = trava_de[secao]
                anterior = por_label.get(sem_acento(pred))
                if anterior:
                    if not anterior.get("prazo") and not anterior.get("prioridade_ate"):
                        urg, _ = urgencia_de(prazo, hoje)
                        anterior["prioridade_ate"] = prazo
                        anterior["urgencia"] = urg
                        anterior["prazo_txt"] = ""      # nao ha prazo proprio
                        anterior["destrava"] = alvo.get("secao")
                        anterior["destrava_em"] = prazo
                    break
                secao = secao_do_predecessor(pred, titulos)
    return acoes


# Reexports temporários: preservam a API histórica enquanto as fontes ainda
# vivem neste arquivo. A implementação usada em runtime já é a modular.
from dominio import acoes as _acoes_mod  # noqa: E402
from dominio import datas as _datas_mod  # noqa: E402
from dominio import dependencias as _dependencias_mod  # noqa: E402
from dominio import prazos as _prazos_mod  # noqa: E402
from fontes import foruns as _foruns_mod  # noqa: E402

achar_datas = _datas_mod.achar_datas
sem_acento = _datas_mod.sem_acento
_mes = _datas_mod.mes
_posicoes = _prazos_mod._posicoes
_tem = _prazos_mod._tem
_tipo_prazo = _prazos_mod._tipo_prazo
_escopo_de = _prazos_mod._escopo_de
tem_negacao = _prazos_mod.tem_negacao
eh_fase = _prazos_mod.eh_fase
muda_assunto = _prazos_mod.muda_assunto
encerra_escopo = _prazos_mod.encerra_escopo
escopo_cobre = _prazos_mod.escopo_cobre
extrair_prazos = _prazos_mod.extrair_prazos
casar_prazos = _prazos_mod.casar_prazos
rotulo_fase = _prazos_mod.rotulo_fase
fase_de = _prazos_mod.fase_de
conta_nota = _acoes_mod.conta_nota
verbo_de = _acoes_mod.verbo_de
urgencia_de = _acoes_mod.urgencia_de
montar_acoes = _acoes_mod.montar_acoes
predecessor_de = _dependencias_mod.predecessor_de
secao_do_predecessor = _dependencias_mod.secao_do_predecessor
propagar_urgencia = _dependencias_mod.propagar_urgencia
JS_DISCUSSOES = _foruns_mod.JS_DISCUSSOES
JS_POSTS = _foruns_mod.JS_POSTS
post_interessa = _foruns_mod.post_interessa
_preparar = _foruns_mod.preparar
varrer_foruns = _foruns_mod.varrer_foruns


def validar_cobertura(dados, anterior):
    """A coleta parece confiável? Devolve (ok, problemas).

    Existe porque a falha mais perigosa deste robô não é errar: é ficar mudo.
    Se o Moodle mudar o HTML e a leitura voltar vazia, sem esta checagem o
    arquivo era gravado como 'ok', a Action passava verde e o site anunciava
    "Nada pendente. Tudo em dia" — omitindo tudo, com cara de sucesso.

    Não fixa "sempre 4 disciplinas": compara com a última coleta boa e exige
    invariantes mínimas, pra continuar valendo no próximo bimestre.
    """
    problemas = []
    cursos = dados.get("courses") or []
    if not cursos:
        problemas.append("não encontrei nenhuma disciplina em Meus cursos")

    # Contar disciplina não basta: o limiar antigo (< metade) deixava perder 2
    # de 4 em silêncio. Comparar por ID também tinha dois furos: se o ID não
    # viesse no JSON a checagem se desligava calada, e qualquer disciplina nova
    # perdoava a perda de outra. Agora a chave cai pro código quando não há ID,
    # e só a troca COMPLETA (todas saem, outras entram) é aceita como virada de
    # bimestre.
    def chave(c):
        return str(c.get("id") or c.get("code") or "")

    virada = False
    antes = {chave(c): c.get("code") for c in (anterior or {}).get("courses", [])
             if chave(c)}
    agora = {chave(c) for c in cursos if chave(c)}
    if antes:
        sumiram = set(antes) - agora
        novas = agora - set(antes)
        virada = sumiram == set(antes) and bool(novas)
        if sumiram and not virada:
            perdidas = [antes[k] for k in sumiram if antes.get(k)]
            problemas.append("disciplina que existia ontem sumiu hoje: "
                             + ", ".join(perdidas or sorted(sumiram)))

    sem_secao = [c["code"] for c in cursos if not c.get("sections")]
    if sem_secao:
        problemas.append("disciplina sem nenhuma seção: " + ", ".join(sem_secao))

    sem_item = [c["code"] for c in cursos
                if not any(s.get("items") for s in c.get("sections", []))]
    if sem_item:
        problemas.append("disciplina sem nenhuma atividade: " + ", ".join(sem_item))

    # Ler o Moodle não basta: os prazos moram em avisos, calendário e
    # cronograma, e todas as três podiam falhar juntas com a saúde verde. O
    # robô ficava sem nenhum prazo e dizia que estava tudo certo, que é a
    # omissão silenciosa que ele existe pra evitar.
    agora_f = resumo_fontes(dados)
    # `anterior["fontes"]` é sempre a última leitura VÁLIDA. Tentativas
    # incompletas ficam em `fontes_tentativa` e não podem ensinar ao ciclo
    # seguinte que zero virou normal.
    antes_f = (anterior or {}).get("fontes") or {}
    for chave, nome in (("itens_com_prazo", "nenhum item ficou com prazo"),
                        ("avisos", "não li nenhum aviso de fórum"),
                        ("eventos_calendario", "o calendário voltou vazio"),
                        ("cronograma", "não li o cronograma de nenhuma disciplina")):
        antes_n = int(antes_f.get(chave, 0) or 0)
        agora_n = int(agora_f.get(chave, 0) or 0)
        if virada or antes_n <= 0:
            continue
        if agora_n == 0:
            problemas.append(f"{nome} (na última leitura válida eram {antes_n})")
        elif agora_n < antes_n * 0.5:
            problemas.append(
                f"{chave} caiu de {antes_n} para {agora_n} "
                "(menos da metade da última leitura válida)")

    for fonte, info in (dados.get("fontes_status") or {}).items():
        status = (info or {}).get("status")
        if status in ("falhou", "degradado"):
            falhas = (info or {}).get("falhas")
            detalhe = f", {falhas} falha(s)" if falhas else ""
            problemas.append(f"fonte {fonte} não foi conferida por inteiro ({status}{detalhe})")

    return (not problemas), problemas


def resumo_fontes(dados):
    """Quanto cada fonte trouxe. Vai pro site pra a coleta ser auditável."""
    cursos = dados.get("courses") or []
    return {
        "disciplinas": len(cursos),
        "secoes": sum(len(c.get("sections") or []) for c in cursos),
        "itens": sum(len(s.get("items") or [])
                     for c in cursos for s in c.get("sections") or []),
        "avisos": sum(len(c.get("avisos") or []) for c in cursos),
        "eventos_calendario": len(dados.get("eventos") or []),
        "notificacoes": len(dados.get("notificacoes") or []),
        "cronograma": sum(1 for c in cursos if c.get("cronograma")),
        # O sinal mais direto de "as fontes de prazo funcionaram".
        "itens_com_prazo": sum(1 for c in cursos for s in c.get("sections") or []
                               for it in s.get("items") or [] if it.get("prazo")),
    }


def _preparar_json(caminho, conteudo):
    """Reexport temporário durante a migração."""
    return _persistencia.preparar_json(caminho, conteudo)


def gravar_json(caminho, conteudo):
    return _persistencia.gravar_json(caminho, conteudo)


def gravar_snapshot(data, estado):
    return _persistencia.gravar_snapshot(data, estado, DATA_PATH, ESTADO_PATH)


def carregar(caminho, padrao, critico=False):
    return _persistencia.carregar(caminho, padrao, critico)


def identidade_item(curso, secao, item):
    """Identidade estável: ID Moodle, URL e só então seção+rótulo."""
    cmid = item.get("cmid")
    if cmid is not None and str(cmid).strip():
        return curso.get("code"), "cmid", str(cmid).strip()
    url = (item.get("url") or "").strip()
    if url:
        return curso.get("code"), "url", url
    secao_id = secao.get("id") or secao.get("title") or ""
    return (curso.get("code"), "fallback", str(secao_id),
            sem_acento(item.get("label") or ""))


def novidades(anterior, dados):
    mudou = []
    antes = {}
    for c in (anterior or {}).get("courses", []):
        for s in c.get("sections", []):
            for it in s.get("items", []):
                antes[identidade_item(c, s, it)] = it.get("status")
    for c in dados["courses"]:
        for s in c["sections"]:
            for it in s["items"]:
                k = identidade_item(c, s, it)
                if k not in antes and it.get("status") is not None:
                    mudou.append({
                        "curso": c["code"], "label": it["label"], "kind": "novo",
                        "cmid": str(it["cmid"]) if it.get("cmid") is not None else None,
                    })
                elif antes.get(k) != it.get("status") and it.get("status") == "Concluído":
                    mudou.append({
                        "curso": c["code"], "label": it["label"], "kind": "concluido",
                        "cmid": str(it["cmid"]) if it.get("cmid") is not None else None,
                    })
        for a in c.get("avisos", []):
            if a.get("novo"):   # os antigos ficam no site, mas nao contam como mudanca
                mudou.append({"curso": c["code"], "label": a.get("titulo") or "novo post",
                              "kind": "aviso"})
    return mudou


def main():
    anterior = carregar(DATA_PATH, None, critico=True)
    estado = carregar(ESTADO_PATH, {})
    agora = datetime.now(timezone.utc).isoformat()
    dados, status = coletar(estado)

    if status == "session_expired":
        saida = dict(anterior or {"courses": []})
        saida["status"] = "session_expired"
        saida["snapshot_at"] = saida.get("snapshot_at") or saida.get("checked_at")
        saida["attempted_at"] = agora
        saida["publication_id"] = agora
        saida["problemas"] = ["não consegui autenticar no AVA nesta tentativa"]
        gravar_json(DATA_PATH, saida)
        print("SESSAO EXPIRADA - mantive o ultimo retrato e avisei no site.")
        return 0

    hoje = datetime.now(BR_TZ).date()
    fontes = resumo_fontes(dados)
    confiavel, problemas = validar_cobertura(dados, anterior)

    if not confiavel:
        # Falhar fechado: melhor um site dizendo "não consegui ler" do que um
        # site dizendo "tudo em dia" porque a leitura voltou vazia.
        saida = dict(anterior or {"courses": []})
        saida["status"] = "coleta_incompleta"
        saida["snapshot_at"] = saida.get("snapshot_at") or saida.get("checked_at")
        saida["attempted_at"] = agora
        saida["publication_id"] = agora
        saida["problemas"] = problemas
        saida["fontes_tentativa"] = fontes
        saida["fontes_status_tentativa"] = dados.get("fontes_status") or {}
        gravar_json(DATA_PATH, saida)
        print("COLETA INCOMPLETA, mantive o ultimo retrato valido:")
        for p in problemas:
            print(f"  - {p}")
        return 2

    acoes, encerrados, higiene, confirmar = montar_acoes(dados, hoje)
    saida = {
        "status": "ok", "checked_at": agora, "snapshot_at": agora,
        "attempted_at": agora, "publication_id": agora,
        "fontes": fontes, "problemas": [],
        "fontes_status": dados.get("fontes_status") or {},
        "courses": dados["courses"],
        "notificacoes": dados.get("notificacoes", []),
        "mensagens": dados.get("mensagens", []),
        "acoes": acoes, "encerrados": encerrados,
        "higiene": higiene, "confirmar": confirmar,
        "novidades": novidades(anterior, dados),
    }
    gravar_snapshot(saida, estado)
    print(f"OK. {len(acoes)} acao(oes), {len(higiene)} de higiene, "
          f"{len(confirmar)} a confirmar, {len(encerrados)} encerrada(s). Fontes: {fontes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
