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
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
STATE_PATH = ROOT / "automacao" / "storage_state.json"
DATA_PATH = DOCS / "data.json"

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


def esc(s):
    if s is None:
        return ""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


BR_TZ = timezone(timedelta(hours=-3))


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
            'Rode <code>python automacao/capturar_sessao.py</code> e depois '
            '<code>python automacao/publicar_sessao_no_github.py</code> para renovar.'
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
        items_html = []
        past_the_horizon = False
        for s in c["sections"]:
            label_bit = f'{esc(s["title"])}{" — " + esc(s["theme"]) if s.get("theme") else ""}'

            if s.get("locked"):
                items_html.append(
                    f'<div class="unlock"><b>{esc(s["title"])}:</b> {esc(s["locked"])}</div>'
                )
                past_the_horizon = True
                continue

            if not s["items"]:
                continue

            if past_the_horizon:
                items_html.append(
                    f'<div class="sec-done"><span class="status lock">Ainda não</span>{label_bit} '
                    f'<span class="muted">({len(s["items"])} itens à frente)</span></div>'
                )
                continue

            all_done = all(it["status"] == "Concluído" for it in s["items"])
            if all_done:
                items_html.append(
                    f'<div class="sec-done"><span class="status ok">Feito</span>{label_bit} '
                    f'<span class="muted">({len(s["items"])} itens)</span></div>'
                )
                continue
            items_html.append(f'<div class="sec-label">{label_bit}</div>')
            li = []
            for it in s["items"]:
                cls, label = STATUS_META.get(it["status"], ("lock", it["status"]))
                li.append(f'<li><span class="status {cls}">{label}</span><span class="tlabel">{esc(it["label"])}</span></li>')
            items_html.append(f'<ul class="tasklist">{"".join(li)}</ul>')
        cards_html.append(f"""
  <div class="card">
    <div class="card-head">
      <div><h3>{esc(c["name"])}</h3><div class="code">{esc(c["code"])}</div></div>
      {pct_html}
    </div>
    {"".join(items_html) if items_html else '<p class="sub">Não consegui ler o conteúdo agora. <a href="https://ava.univesp.br/course/view.php?id=' + str(c["id"]) + '">Abrir no AVA</a>.</p>'}
  </div>""")

    html = TEMPLATE.replace("{{BANNER}}", banner) \
                    .replace("{{CHECKED_AT}}", esc(checked_at_fmt)) \
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
  .sec-label{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--ink-soft);font-weight:700;margin:14px 0 4px;}
  .sec-done{display:flex;align-items:center;gap:8px;font-size:13px;padding:7px 0;border-top:1px solid var(--line);}
  .sec-done:first-child{border-top:none;}
  .sec-done .muted{color:var(--ink-soft);font-size:12px;}
  .tasklist{list-style:none;margin:0;padding:0;}
  .tasklist li{display:flex;align-items:flex-start;gap:9px;padding:6px 0;font-size:14px;border-top:1px solid var(--line);}
  .tasklist li:first-child{border-top:none;}
  .status{flex:0 0 auto;margin-top:2px;font-size:10.5px;font-weight:700;text-transform:uppercase;padding:2px 7px;border-radius:6px;}
  .status.pend{background:var(--wait-bg);color:var(--wait);}
  .status.ok{background:var(--ok-bg);color:var(--ok);}
  .status.lock{background:var(--locked-bg);color:var(--locked);}
  .unlock{margin-top:10px;padding:8px 10px;border-radius:10px;background:var(--brick-soft);font-size:12.5px;}
  .unlock b{color:var(--brick);}
  footer{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;color:var(--ink-soft);text-align:center;}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">Univesp · BIA · Turma 001</div>
  <h1>Guia diário do AVA</h1>
  <p class="sub">Atualizado automaticamente todo dia às 8h · última entrada no AVA: {{CHECKED_AT}} (Brasília)</p>
  {{BANNER}}
  {{CHANGES}}
  {{CARDS}}
  <footer>Gerado por um robô que lê o AVA de verdade todo dia. Sem clique manual — o status aqui é o status real de lá.</footer>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main() or 0)
