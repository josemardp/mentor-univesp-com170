# -*- coding: utf-8 -*-
"""
Robo diario do guia Univesp.

Le a sessao salva (storage_state), entra no AVA, le o status real de cada
disciplina (Concluido / Pendente / Marcar como feito), compara com o que
tinha no dia anterior (docs/data.json) para saber o que mudou, e escreve
docs/index.html + docs/data.json de novo.

Se a sessao expirou (Moodle pediu login), nao derruba o robo: escreve um
aviso bem visivel no site e sai sem erro, pra alguem rodar
automacao/capturar_sessao.py de novo.
"""
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
STATE_PATH = ROOT / "automacao" / "storage_state.json"
DATA_PATH = DOCS / "data.json"
RECADO_PATH = DOCS / "revisao.json"

COURSES = [
    {"code": "COM170", "name": "Inteligência Artificial na Prática Acadêmica e Profissional", "id": 18922},
    {"code": "LET110", "name": "Leitura e Produção de Textos", "id": 18893},
    {"code": "SOC100", "name": "Ética, Cidadania e Sociedade", "id": 18880},
    {"code": "COM100", "name": "Pensamento Computacional", "id": 18870},
]

TYPE_TOKENS = {"Página", "Questionário", "URL", "Ferramenta externa", "Fórum", "Pasta", "Rótulo", "Arquivo", "Pacote SCORM"}
STATUS_TOKENS = {"Concluído", "Pendente", "Marcar como feito"}
SECTION_RE = re.compile(r"^(Semana \d+|Quinzena \d+|Módulo \d+|Revisão.*|Geral|Arquivos da Disciplina)$")
LOCKED_RE = re.compile(r"^Disponível a partir de (.+)$")
LOCKED_COND_RE = re.compile(r"^Disponível se: (.+)$")


def parse_course_text(text):
    """Turn the raw inner_text of the course index into sections/items."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    sections = []
    cur_section = None
    i = 0
    while i < len(lines):
        line = lines[i]

        m = SECTION_RE.match(line)
        if m:
            cur_section = {"title": line, "theme": None, "locked": None, "items": []}
            sections.append(cur_section)
            # peek ahead for "Tema:" / theme / locked notice
            j = i + 1
            if j < len(lines) and lines[j] == "Tema:":
                if j + 1 < len(lines):
                    cur_section["theme"] = lines[j + 1]
                    i = j + 1
            i += 1
            continue

        lm = LOCKED_RE.match(line)
        if lm and cur_section is not None:
            cur_section["locked"] = f"disponível a partir de {lm.group(1)}"
            i += 1
            continue

        lcm = LOCKED_COND_RE.match(line)
        if lcm and cur_section is not None:
            cur_section["locked"] = f"libera quando {lcm.group(1).rstrip('. ')}"
            i += 1
            continue

        if line in STATUS_TOKENS and cur_section is not None:
            # walk back to find the item title, skipping pure type tokens
            k = len(cur_section["items"])
            title = None
            back = i - 1
            seen_type = None
            while back >= 0:
                cand = lines[back]
                if cand in TYPE_TOKENS:
                    seen_type = cand
                    back -= 1
                    continue
                if SECTION_RE.match(cand) or cand in STATUS_TOKENS or cand == "Tema:":
                    break
                title = cand
                break
            if title and not any(it["label"] == title for it in cur_section["items"]):
                cur_section["items"].append({"label": title, "status": line, "type": seen_type})
            i += 1
            continue

        i += 1
    return sections


def get_progress_map(page):
    page.goto("https://ava.univesp.br/my/courses.php", wait_until="networkidle")
    text = page.locator("body").inner_text()
    progress = {}
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for idx, line in enumerate(lines):
        if "% concluído" in line or "% completo" in line:
            pct_match = re.match(r"(\d+)%", line)
            if pct_match and idx > 0:
                progress[lines[idx - 1]] = int(pct_match.group(1))
    return progress


def is_logged_out(page):
    return "/login" in page.url or "univesp_login.php" in page.url


def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(STATE_PATH))
        page = context.new_page()

        page.goto("https://ava.univesp.br/my/", wait_until="networkidle", timeout=60000)
        if is_logged_out(page):
            browser.close()
            return None, "session_expired"

        progress_map = get_progress_map(page)

        courses_out = []
        for c in COURSES:
            page.goto(f"https://ava.univesp.br/course/view.php?id={c['id']}", wait_until="networkidle", timeout=60000)
            if is_logged_out(page):
                browser.close()
                return None, "session_expired"
            try:
                page.get_by_role("link", name="Expandir tudo").first.click(timeout=5000)
                page.wait_for_timeout(600)
            except Exception:
                pass
            # some courses nest sub-accordions (e.g. Módulo N inside Quinzena N)
            # that "Expandir tudo" does not reach - click every remaining
            # collapsed toggle inside the content area, a few passes deep.
            for _ in range(6):
                toggles = page.locator("#region-main a[aria-expanded='false'], #region-main [data-toggle='collapse'][aria-expanded='false']")
                count = toggles.count()
                if count == 0:
                    break
                clicked_any = False
                for idx in range(count):
                    try:
                        toggles.nth(idx).click(timeout=2000)
                        clicked_any = True
                    except Exception:
                        continue
                page.wait_for_timeout(400)
                if not clicked_any:
                    break
            main = page.locator("#region-main")
            text = main.inner_text() if main.count() else page.locator("body").inner_text()
            sections = parse_course_text(text)
            pct = None
            for title, value in progress_map.items():
                if c["code"] in title or c["name"].split(" - ")[0][:15] in title:
                    pct = value
                    break
            courses_out.append({
                "code": c["code"], "name": c["name"], "id": c["id"],
                "progress_pct": pct, "sections": sections,
            })

        browser.close()
        return courses_out, "ok"


def load_previous():
    if DATA_PATH.exists():
        try:
            return json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def diff_new_items(prev, cur_courses):
    """Return list of (course_code, section_title, item_label) newly seen or newly Pendente."""
    prev_index = {}
    if prev and prev.get("status") == "ok":
        for c in prev.get("courses", []):
            for s in c.get("sections", []):
                for it in s.get("items", []):
                    prev_index[(c["code"], s["title"], it["label"])] = it["status"]

    changes = []
    for c in cur_courses:
        for s in c["sections"]:
            for it in s["items"]:
                key = (c["code"], s["title"], it["label"])
                old_status = prev_index.get(key)
                if old_status is None:
                    changes.append({"course": c["code"], "section": s["title"], "label": it["label"], "kind": "novo"})
                elif old_status != it["status"] and it["status"] == "Concluído":
                    changes.append({"course": c["code"], "section": s["title"], "label": it["label"], "kind": "concluido"})
    return changes


def main():
    prev = load_previous()
    courses, status = scrape()
    now = datetime.now(timezone.utc).isoformat()

    if status == "session_expired":
        data = prev or {"courses": []}
        data["status"] = "session_expired"
        data["checked_at"] = now
        DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        render_html(data, changes=[])
        print("SESSAO EXPIRADA - avisei no site, nao mexi no resto.")
        return

    changes = diff_new_items(prev, courses)
    data = {"status": "ok", "checked_at": now, "courses": courses}
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    render_html(data, changes)
    print(f"Atualizado. {len(changes)} mudanca(s) detectada(s).")


STATUS_META = {
    "Concluído": ("ok", "Feito"),
    "Pendente": ("pend", "Pendente"),
    "Marcar como feito": ("lock", "A marcar"),
}

# ---------------------------------------------------------------------------
# Calendário do bimestre — âncoras reais lidas do próprio AVA:
# - AIA (COM170, Semanas 1-4): início 22/06/2026; aberturas confirmadas
#   06/07 (Semana 3) e 13/07 (Semana 4). Terminou em 19/07/2026.
# - Disciplinas regulares (LET110/SOC100/COM100 e a fase Quinzena/Módulo do
#   COM170): Semana 1 começa em 20/07/2026 (segunda). As liberações que o AVA
#   mostra confirmam o grid semanal: 27/07 (S2), 03/08 (S3), 10/08 (S4).
# ---------------------------------------------------------------------------
AIA_START = date(2026, 6, 22)
REGULAR_START = date(2026, 7, 20)

MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}

DIAS_PT = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def parse_lock_date(locked):
    """Extrai a data real de um texto tipo 'disponível a partir de 27 de julho de 2026'."""
    if not locked:
        return None
    m = re.search(r"(\d{1,2}) de (\w+) de (\d{4})", locked)
    if not m:
        return None
    mes = MESES_PT.get(m.group(2).lower())
    if not mes:
        return None
    try:
        return date(int(m.group(3)), mes, int(m.group(1)))
    except ValueError:
        return None


def fmt_dm(d):
    return f"{d.day:02d}/{d.month:02d}"


def fmt_range(d1, d2):
    if d1.month == d2.month:
        return f"{d1.day:02d} a {fmt_dm(d2)}"
    return f"{fmt_dm(d1)} a {fmt_dm(d2)}"


def section_dates(code, title):
    """(início, fim) reais de uma seção, derivados do calendário do bimestre.
    Devolve None para seções sem data (Módulos liberados por conclusão, Geral etc.)."""
    m = re.match(r"Semana (\d+)$", title)
    if m:
        n = int(m.group(1))
        start = AIA_START if code == "COM170" else REGULAR_START
        d1 = start + timedelta(days=7 * (n - 1))
        return d1, d1 + timedelta(days=6)
    m = re.match(r"Quinzena (\d+)$", title)
    if m:
        n = int(m.group(1))
        d1 = REGULAR_START + timedelta(days=14 * (n - 1))
        return d1, d1 + timedelta(days=13)
    return None


def when_badge(code, s, today=None):
    """Badge de data da seção: período real, ou data de liberação vinda do AVA."""
    lock_dt = parse_lock_date(s.get("locked"))
    if lock_dt:
        return f"abre {fmt_dm(lock_dt)}"
    if s.get("locked"):
        return ""  # liberação por conclusão, sem data
    dates = section_dates(code, s["title"])
    if not dates:
        return ""
    return fmt_range(*dates)

# Resumos curtos por seção, baseados no conteúdo real que o robô lê no AVA.
# Onde não houver entrada aqui, cai no "tema" da seção (também vindo do AVA).
DESCRICOES = {
    ("COM170", "Semana 1"): "Ambientação (AIA): guia de IAs gratuitas e primeiro contato com o Gemini.",
    ("COM170", "Semana 2"): "Ambientação (AIA): NotebookLM e a missão da semana no fórum do grupo.",
    ("COM170", "Semana 3"): "Ambientação (AIA): seu curso em 6 pistas e leitura do PPC.",
    ("COM170", "Semana 4"): "Ambientação (AIA): revisão entre pares na ferramenta Laboratório.",
    ("COM170", "Quinzena 1"): "Abertura da disciplina regular: página de introdução e os fóruns geral e de dúvidas.",
    ("COM170", "Módulo 1"): "O que é (e o que não é) IA: os paradigmas por trás dela e seu primeiro contato prático.",
    ("LET110", "Semana 1"): "As funções sociais da leitura e da escrita: por que lemos e escrevemos e o papel disso na vida em sociedade.",
    ("SOC100", "Semana 1"): "Introdução à Ética: conceitos fundamentais e a diferença entre ética e moral.",
    ("COM100", "Semana 1"): "O século XXI e a computação na BNCC: por que o pensamento computacional importa hoje.",
}


def esc(s):
    if s is None:
        return ""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def section_desc(code, s):
    d = DESCRICOES.get((code, s["title"]))
    if d:
        return d
    return s.get("theme") or ""


def _join_pt(xs):
    xs = [x for x in xs if x]
    if not xs:
        return ""
    if len(xs) == 1:
        return xs[0]
    return ", ".join(xs[:-1]) + " e " + xs[-1]


def _find(items, *needles):
    out = []
    for it in items:
        lab = it["label"].lower()
        if any(n in lab for n in needles):
            out.append(it)
    return out


def _status_word(items):
    sts = [it["status"] for it in items]
    if "Pendente" in sts:
        return "pendente"
    if sts and all(x == "Concluído" for x in sts):
        return "feita"
    return "a fazer"


def _forum_topic(label):
    l = re.sub(r"\s*\d+\s+mensage.*$", "", label).strip()
    m = re.search(r"[Ff]órum[^-:]*[-:]\s*(.+)$", l)
    if not m:
        return ""
    t = m.group(1).strip().rstrip("?").strip()
    if len(t) > 64:
        t = t[:61] + "…"
    return f"o fórum “{t}”" if t else ""


def build_rich(code, s):
    """Resumo rico e automático da seção atual: tema + o que há dentro."""
    base = DESCRICOES.get((code, s["title"])) or s.get("theme") or ""
    items = s["items"]

    leituras = _find(items, "texto-base", "material-base")
    videos = _find(items, "videoaula", "vídeo-base", "video-base", "vídeo base")
    aval = _find(items, "atividade avaliativa")
    quiz = [it for it in _find(items, "quiz") if it not in aval]
    forum = _find(items, "fórum", "forum")
    live = _find(items, "live com facilitador")

    bits = []
    if leituras:
        n = len(leituras)
        bits.append(f"{n} leitura{'s' if n > 1 else ''}")
    if videos:
        bits.append("videoaulas")
    if aval:
        bits.append(f"atividade avaliativa ({_status_word(aval)})")
    elif quiz:
        n = len(quiz)
        bits.append(f"{'quizzes' if n > 1 else 'quiz'} ({_status_word(quiz)})")
    if forum:
        topic = _forum_topic(forum[0]["label"])
        bits.append(topic or "fórum temático")
    if live:
        bits.append("live com facilitador")

    parts = []
    if base:
        parts.append(base if base.rstrip().endswith(".") else base.rstrip() + ".")
    has_graded = bool(aval or quiz)
    if bits and (has_graded or len(bits) >= 2):
        parts.append("Nesta seção: " + _join_pt(bits) + ".")
    return " ".join(parts)


def render_locked_row(code, s):
    badge = when_badge(code, s)
    when_html = f'<span class="when">{esc(badge)}</span>' if badge else ""
    theme = s.get("theme")
    desc = f"{theme} · {s['locked']}" if theme else s["locked"]
    return (
        '<details class="sec">'
        '<summary><span class="sec-head">'
        '<span class="chev"></span>'
        '<span class="status lock">Bloqueado</span>'
        f'<span class="sec-title-txt">{esc(s["title"])}</span>'
        f'{when_html}'
        '</span></summary>'
        f'<p class="sec-desc">{esc(desc)}</p>'
        '</details>'
    )


def render_accordion(code, s, state):
    if state == "done":
        chip_cls, chip_label, is_open = "ok", "Feito", False
    elif state == "future":
        chip_cls, chip_label, is_open = "lock", "Depois", False
    elif state == "geral":
        chip_cls, chip_label, is_open = "neutral", "Referências", False
    else:  # current
        if any(it["status"] == "Pendente" for it in s["items"]):
            chip_cls, chip_label = "pend", "Pendente"
        else:
            chip_cls, chip_label = "brick", "Atual"
        is_open = True

    desc = build_rich(code, s) if state == "current" else section_desc(code, s)
    desc_html = f'<p class="sec-desc">{esc(desc)}</p>' if desc else ""
    count_html = (
        f'<span class="muted"> · {len(s["items"])} itens</span>'
        if state in ("done", "future") else ""
    )
    badge = when_badge(code, s)
    when_html = f'<span class="when">{esc(badge)}</span>' if badge else ""

    li = []
    for it in s["items"]:
        cls, label = STATUS_META.get(it["status"], ("lock", it["status"]))
        li.append(
            f'<li><span class="status {cls}">{esc(label)}</span>'
            f'<span class="tlabel">{esc(it["label"])}</span></li>'
        )
    items_html = f'<ul class="tasklist">{"".join(li)}</ul>'

    return (
        f'<details class="sec"{" open" if is_open else ""}>'
        '<summary><span class="sec-head">'
        '<span class="chev"></span>'
        f'<span class="status {chip_cls}">{chip_label}</span>'
        f'<span class="sec-title-txt">{esc(s["title"])}</span>{count_html}'
        f'{when_html}'
        '</span></summary>'
        f'{desc_html}{items_html}'
        '</details>'
    )


def _section_state(s, horizon):
    done = all(it["status"] == "Concluído" for it in s["items"])
    if done:
        return "done"
    if horizon:
        return "future"
    if s["title"] == "Geral":
        return "geral"
    return "current"


def _render_section_list(code, sections):
    out = []
    horizon = False
    for s in sections:
        if not s.get("locked") and not s["items"]:
            continue  # pastas/rótulos sem status
        if s.get("locked"):
            out.append(render_locked_row(code, s))
            horizon = True
            continue
        out.append(render_accordion(code, s, _section_state(s, horizon)))
    return "".join(out)


def render_sections(c):
    code = c["code"]
    sections = c["sections"]

    if code != "COM170":
        return _render_section_list(code, sections)

    # COM170 tem duas fases com nomes de seção que se confundem com as outras
    # disciplinas: as "Semanas 1-4" dele são a Ambientação (AIA), que já
    # terminou em 19/07. Agrupamos a AIA num bloco próprio, fechado, e
    # deixamos a fase regular (Quinzena/Módulos) como o corpo do card.
    aia = [s for s in sections if re.match(r"Semana \d+$", s["title"])]
    regular = [s for s in sections if s not in aia]

    aia_pend = sum(
        1 for s in aia for it in s["items"] if it["status"] == "Pendente"
    )
    if aia_pend:
        aia_chip = '<span class="status pend">Pendente</span>'
        aia_note = (
            f"Fase de ambientação, encerrada em 19/07. Ainda consta {aia_pend} "
            f"pendência aqui dentro (vale conferir no AVA se ainda dá pra fazer)."
            if aia_pend == 1 else
            f"Fase de ambientação, encerrada em 19/07. Ainda constam {aia_pend} "
            f"pendências aqui dentro (vale conferir no AVA se ainda dá pra fazer)."
        )
    else:
        aia_chip = '<span class="status ok">Feito</span>'
        aia_note = "Fase de ambientação, encerrada em 19/07. Tudo concluído."

    aia_inner = []
    for s in aia:
        state = "done" if all(it["status"] == "Concluído" for it in s["items"]) else "current"
        # dentro do grupo AIA nada fica aberto por padrão: é passado
        html = render_accordion(code, s, state)
        aia_inner.append(html.replace('<details class="sec" open>', '<details class="sec">'))

    aia_block = (
        '<details class="sec phase-group">'
        '<summary><span class="sec-head">'
        '<span class="chev"></span>'
        f'{aia_chip}'
        '<span class="sec-title-txt">Ambientação (AIA) · Semanas 1 a 4</span>'
        f'<span class="when">{fmt_range(AIA_START, date(2026, 7, 19))}</span>'
        '</span></summary>'
        f'<p class="sec-desc">{esc(aia_note)}</p>'
        f'<div class="nested">{"".join(aia_inner)}</div>'
        '</details>'
    )

    regular_html = _render_section_list(code, regular)
    return (
        f'{aia_block}'
        f'<div class="phase-label">Disciplina regular · começou em {fmt_dm(REGULAR_START)}</div>'
        f'{regular_html}'
    )


BR_TZ = timezone(timedelta(hours=-3))


def _inline_md(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return s


def _is_bullet(l):
    return l.startswith(("- ", "• ", "* "))


def _mini_md(text):
    """Markdown minimalista: parágrafos (linhas juntas por espaço) e
    listas. Um bloco pode misturar linhas normais e bullets."""
    blocks = re.split(r"\n\s*\n", text.strip())
    out = []
    for b in blocks:
        lines = [l.strip() for l in b.splitlines() if l.strip()]
        para = []
        bullets = []

        def flush():
            if para:
                out.append(f"<p>{_inline_md(' '.join(para))}</p>")
                para.clear()
            if bullets:
                lis = "".join(f"<li>{_inline_md(x)}</li>" for x in bullets)
                out.append(f"<ul>{lis}</ul>")
                bullets.clear()

        for l in lines:
            if _is_bullet(l):
                if para:
                    out.append(f"<p>{_inline_md(' '.join(para))}</p>")
                    para.clear()
                bullets.append(l[2:].strip())
            else:
                if bullets:
                    lis = "".join(f"<li>{_inline_md(x)}</li>" for x in bullets)
                    out.append(f"<ul>{lis}</ul>")
                    bullets.clear()
                para.append(l)
        flush()
    return "".join(out)


def render_recado():
    if not RECADO_PATH.exists():
        return ""
    try:
        r = json.loads(RECADO_PATH.read_text(encoding="utf-8"))
    except Exception:
        return ""
    text = (r.get("text") or "").strip()
    if not text:
        return ""
    when = ""
    try:
        dt = datetime.fromisoformat(r.get("written_at", "")).astimezone(BR_TZ)
        when = dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        pass
    when_html = f'<p class="recado-when">Escrito em {esc(when)} (Brasília)</p>' if when else ""
    return (
        '<div class="recado">'
        '<div class="recado-head"><span class="recado-ico">📌</span>'
        '<span class="recado-label">Recado da mentora</span></div>'
        f'<div class="recado-body">{_mini_md(text)}</div>'
        f'{when_html}'
        '</div>'
    )


def _como_fazer(it):
    t = it.get("type")
    lab = it["label"].lower()
    if t == "Questionário":
        return "questionário no AVA"
    if t == "Pacote SCORM":
        return "quiz interativo no AVA"
    if "fórum" in lab or "forum" in lab:
        return "participar do fórum"
    if "pesquisa" in lab:
        return "responder à pesquisa"
    if t == "Página":
        return "abrir a página e concluir a atividade"
    if t == "URL":
        return "acessar o link"
    return "fazer no AVA"


def _quando(code, s, today):
    """(chip curto, complemento, urgência) do prazo de uma seção."""
    dates = section_dates(code, s["title"])
    if dates:
        d1, d2 = dates
        if d2 < today:
            return "atrasado", f"era de {fmt_range(d1, d2)}", "late"
        if d1 <= today <= d2:
            return f"até {fmt_dm(d2)}", "", "now"
        return f"a partir de {fmt_dm(d1)}", "", "soon"
    if s["title"].startswith("Módulo"):
        return "livre", "concluir destrava o próximo módulo", "now"
    return "", "", "now"


def render_pendencias(data, today):
    """Mapa único do que está pendente de verdade: o quê, como e quando."""
    rows = []
    for c in data.get("courses", []):
        for s in c.get("sections", []):
            for it in s.get("items", []):
                if it["status"] != "Pendente":
                    continue
                quando, extra, urg = _quando(c["code"], s, today)
                sec_label = s["title"]
                if c["code"] == "COM170" and re.match(r"Semana \d+$", sec_label):
                    sec_label = f"AIA · {sec_label}"
                rows.append({
                    "code": c["code"], "section": sec_label,
                    "label": it["label"], "como": _como_fazer(it),
                    "quando": quando, "extra": extra, "urg": urg,
                })
    if not rows:
        return (
            '<div class="pend-block"><h2>O que falta agora</h2>'
            '<p class="sub" style="margin:0;">Nada pendente. Tudo em dia. 🎉</p></div>'
        )
    order = {"late": 0, "now": 1, "soon": 2}
    rows.sort(key=lambda r: (order.get(r["urg"], 1), r["code"]))
    lis = []
    for r in rows:
        urg_cls = {"late": "pend", "now": "brick", "soon": "lock"}[r["urg"]]
        quando_html = (
            f'<span class="status {urg_cls}">{esc(r["quando"])}</span>'
            if r["quando"] else ""
        )
        detalhes = " · ".join(x for x in (r["como"], r["extra"]) if x)
        lis.append(
            f'<li>{quando_html}<span class="tlabel"><b>{esc(r["code"])}</b> '
            f'({esc(r["section"])}) — {esc(r["label"])} '
            f'<span class="muted">· {esc(detalhes)}</span></span></li>'
        )
    n = len(rows)
    return (
        '<div class="pend-block">'
        f'<h2>O que falta agora · {n} {"item" if n == 1 else "itens"}</h2>'
        '<p class="sub" style="margin:0 0 8px;">Só o que conta como pendência real no AVA. '
        'O resto do site mostra o mapa completo, com datas.</p>'
        f'<ul class="tasklist pendlist">{"".join(lis)}</ul>'
        '</div>'
    )


def semana_atual_line(today):
    delta = (today - REGULAR_START).days
    dia = DIAS_PT[today.weekday()]
    if delta < 0:
        return f"Hoje é {dia}, {fmt_dm(today)} · o bimestre regular começa em {fmt_dm(REGULAR_START)}"
    n = delta // 7 + 1
    d1 = REGULAR_START + timedelta(days=7 * (n - 1))
    d2 = d1 + timedelta(days=6)
    return f"Hoje é {dia}, {fmt_dm(today)} · Semana {n} do bimestre ({fmt_range(d1, d2)})"


def render_html(data, changes):
    checked_at = data.get("checked_at", "")
    try:
        dt = datetime.fromisoformat(checked_at).astimezone(BR_TZ)
        checked_at_fmt = dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        checked_at_fmt = checked_at

    banner = ""
    if data.get("status") == "session_expired":
        banner = (
            '<div class="alertbar">'
            '<b>Sessão do AVA expirou.</b> Este retrato é o último válido. '
            'Dê 2 cliques em <code>automacao/renovar_sessao.bat</code> pra renovar '
            '(abre o navegador, você loga, e o resto acontece sozinho).'
            '</div>'
        )

    changes_html = ""
    if changes:
        rows = "".join(
            f'<li><b>{esc(c["course"])}</b> — {esc(c["label"])} '
            f'<span class="tag">{"concluído" if c["kind"]=="concluido" else "novidade"}</span></li>'
            for c in changes
        )
        n = len(changes)
        resumo = f"{n} novidade{'s' if n != 1 else ''} encontrada{'s' if n != 1 else ''}:"
        changes_html = f"""
    <div class="today">
      <h2>Entrei no AVA em {esc(checked_at_fmt)} (horário de Brasília)</h2>
      <p class="sub" style="margin:0 0 8px;">{esc(resumo)}</p>
      <ul class="changelist">{rows}</ul>
    </div>"""
    else:
        changes_html = f"""
    <div class="today">
      <h2>Entrei no AVA em {esc(checked_at_fmt)} (horário de Brasília)</h2>
      <p class="sub" style="margin:0;">Nenhuma novidade desde a última checagem. Volto amanhã às 8h.</p>
    </div>"""

    cards_html = []
    for c in data.get("courses", []):
        pct = c.get("progress_pct")
        pct_html = f'<div class="progress-pill{" has-progress" if pct else ""}">{pct if pct is not None else "?"}% concluído</div>'
        sections_html = render_sections(c)
        body = sections_html or (
            '<p class="sub">Não consegui ler o conteúdo agora. '
            f'<a href="https://ava.univesp.br/course/view.php?id={c["id"]}">Abrir no AVA</a>.</p>'
        )
        cards_html.append(f"""
  <div class="card">
    <div class="card-head">
      <div><h3>{esc(c["name"])}</h3><div class="code">{esc(c["code"])}</div></div>
      {pct_html}
    </div>
    <div class="sections">{body}</div>
  </div>""")

    today = datetime.now(BR_TZ).date()
    html = TEMPLATE.replace("{{BANNER}}", banner) \
                    .replace("{{RECADO}}", render_recado()) \
                    .replace("{{CHECKED_AT}}", esc(checked_at_fmt)) \
                    .replace("{{SEMANA}}", esc(semana_atual_line(today))) \
                    .replace("{{PENDENCIAS}}", render_pendencias(data, today)) \
                    .replace("{{CHANGES}}", changes_html) \
                    .replace("{{CARDS}}", "".join(cards_html))
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
  :root[data-theme="dark"]{
    --bg:#171613; --paper:#201f1b; --ink:#f2efe6; --ink-soft:#b8b2a3; --line:#3a362d;
    --brick:#e2777c; --brick-soft:#3a2222; --ok:#7fcba3; --ok-bg:#1f3129;
    --wait:#e3b463; --wait-bg:#3a2f19; --locked:#87816f; --locked-bg:#2a2820;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.35);
  }
  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]){
      --bg:#171613; --paper:#201f1b; --ink:#f2efe6; --ink-soft:#b8b2a3; --line:#3a362d;
      --brick:#e2777c; --brick-soft:#3a2222; --ok:#7fcba3; --ok-bg:#1f3129;
      --wait:#e3b463; --wait-bg:#3a2f19; --locked:#87816f; --locked-bg:#2a2820;
      --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.35);
    }
  }
  *{box-sizing:border-box;}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:ui-sans-serif,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.5;padding:18px 14px 60px;}
  h1,h2,h3{font-family:Georgia,"Times New Roman",ui-serif,serif;font-weight:700;text-wrap:balance;margin:0;}
  .wrap{max-width:560px;margin:0 auto;}
  .eyebrow{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:var(--brick);font-weight:700;margin-bottom:8px;}
  h1{font-size:24px;line-height:1.15;}
  .sub{color:var(--ink-soft);font-size:14px;margin-top:8px;}
  .alertbar{background:var(--wait-bg);color:var(--wait);border-radius:12px;padding:12px 14px;font-size:13.5px;margin:16px 0;}
  .alertbar code{background:rgba(0,0,0,.08);padding:1px 5px;border-radius:5px;}
  .recado{background:var(--brick-soft);border:1px solid var(--brick);border-radius:14px;padding:16px;box-shadow:var(--shadow);margin:18px 0 22px;}
  .recado-head{display:flex;align-items:center;gap:8px;margin-bottom:8px;}
  .recado-ico{font-size:15px;}
  .recado-label{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--brick);font-weight:700;}
  .recado-body p{margin:0 0 8px;font-size:14px;line-height:1.5;}
  .recado-body p:last-child{margin-bottom:0;}
  .recado-body ul{margin:6px 0 8px;padding-left:20px;}
  .recado-body li{font-size:14px;margin-bottom:4px;line-height:1.45;}
  .recado-body strong{font-weight:700;}
  .recado-when{margin:10px 0 0;font-size:11.5px;color:var(--ink-soft);}
  .today{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:16px;box-shadow:var(--shadow);margin:18px 0 26px;}
  .today h2{font-size:16px;margin-bottom:10px;}
  .changelist{list-style:none;margin:0;padding:0;}
  .changelist li{font-size:14px;padding:6px 0;border-top:1px solid var(--line);}
  .changelist li:first-child{border-top:none;}
  .changelist .tag{font-size:11px;color:var(--ink-soft);}
  .card{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px;box-shadow:var(--shadow);}
  .card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;}
  .card h3{font-size:16px;}
  .code{font-size:12px;color:var(--ink-soft);font-weight:600;}
  .progress-pill{font-size:11px;font-weight:700;padding:3px 8px;border-radius:99px;white-space:nowrap;background:var(--locked-bg);color:var(--locked);}
  .progress-pill.has-progress{background:var(--ok-bg);color:var(--ok);}
  .sections{margin-top:6px;}
  .sec{border-top:1px solid var(--line);}
  .sec:first-child{border-top:none;}
  .sec > summary{list-style:none;cursor:pointer;padding:11px 0;display:block;border-radius:8px;}
  .sec > summary::-webkit-details-marker{display:none;}
  .sec > summary:focus-visible{outline:2px solid var(--brick);outline-offset:2px;}
  .sec-head{display:flex;align-items:center;gap:8px;}
  .chev{flex:0 0 auto;width:0;height:0;border-left:6px solid var(--ink-soft);border-top:5px solid transparent;border-bottom:5px solid transparent;transition:transform .18s ease;}
  details[open] > summary .chev{transform:rotate(90deg);}
  .sec-title-txt{font-weight:700;font-size:14px;}
  .sec-head .muted{color:var(--ink-soft);font-size:12px;font-weight:400;}
  .sec-desc{margin:2px 0 10px 22px;font-size:12.5px;color:var(--ink-soft);line-height:1.45;}
  .tasklist{list-style:none;margin:0 0 10px 22px;padding:0;}
  .tasklist li{display:flex;align-items:flex-start;gap:9px;padding:6px 0;font-size:14px;border-top:1px solid var(--line);}
  .tasklist li:first-child{border-top:none;}
  .status{flex:0 0 auto;margin-top:2px;font-size:10.5px;font-weight:700;text-transform:uppercase;padding:2px 7px;border-radius:6px;white-space:nowrap;}
  .status.pend{background:var(--wait-bg);color:var(--wait);}
  .status.ok{background:var(--ok-bg);color:var(--ok);}
  .status.lock{background:var(--locked-bg);color:var(--locked);}
  .status.brick{background:var(--brick-soft);color:var(--brick);}
  .status.neutral{background:var(--locked-bg);color:var(--ink-soft);}
  .when{margin-left:auto;flex:0 0 auto;font-size:11px;font-weight:600;color:var(--ink-soft);white-space:nowrap;padding-left:8px;}
  .phase-label{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--brick);font-weight:700;margin:14px 0 2px;padding-top:10px;border-top:1px solid var(--line);}
  .phase-group .nested{margin-left:18px;border-left:2px solid var(--line);padding-left:10px;margin-bottom:10px;}
  .pend-block{background:var(--paper);border:1px solid var(--wait);border-radius:14px;padding:16px;box-shadow:var(--shadow);margin:18px 0 22px;}
  .pend-block h2{font-size:16px;margin-bottom:8px;}
  .pendlist{margin-left:0 !important;}
  .semana-line{font-size:13px;color:var(--ink);font-weight:600;margin-top:6px;}
  @media (prefers-reduced-motion: reduce){.chev{transition:none;}}
  footer{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;color:var(--ink-soft);text-align:center;}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">Univesp · BIA · Turma 001</div>
  <h1>Guia diário do AVA</h1>
  <p class="semana-line">{{SEMANA}}</p>
  <p class="sub">Atualizado automaticamente todo dia às 8h · última entrada no AVA: {{CHECKED_AT}} (Brasília)</p>
  {{BANNER}}
  {{RECADO}}
  {{PENDENCIAS}}
  {{CHANGES}}
  {{CARDS}}
  <footer>Gerado por um robô que lê o AVA de verdade todo dia. Sem clique manual — o status aqui é o status real de lá.<br>
  Datas das semanas seguem o calendário do bimestre (Semana 1 regular: 20 a 26/07); liberações com data específica vêm do próprio AVA.</footer>
</div>
</body>
</html>
"""

def render_only():
    """Regenera o index.html a partir do data.json + revisao.json,
    sem entrar no AVA. Usado pela revisão semanal (que não tem sessão)."""
    data = load_previous()
    if not data:
        print("Sem data.json para renderizar.")
        return
    render_html(data, changes=[])
    print("Render-only OK.")


if __name__ == "__main__":
    if "--render-only" in sys.argv:
        render_only()
    else:
        sys.exit(main() or 0)
