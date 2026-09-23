# -*- coding: utf-8 -*-
"""Apostila de prova do bimestre, montada a partir das fichas semanais.

Por que existe: a REVISAO.md de cada semana é completa e longa (300 linhas).
Ele pediu em 23/09/2026 uma apostila bonita, colorida, funcional, "na medida
exata para estudar para as provas", que vá engordando toda semana e sirva
tanto no celular quanto impressa.

Como: a revisão semanal pede ao Claude uma ficha curta por semana
(`apostila.json`, formato fixo e com limites, prompt em
`apostila_prompt.md`). Este módulo valida as fichas e monta, sempre com o
mesmo desenho, sem IA:

  privado/estudo/<bimestre>/APOSTILA.html          tela: tudo, com questões clicáveis
  privado/estudo/<bimestre>/APOSTILA_<COD>.pdf     resumo A4, meta de 1 página por semana
  privado/estudo/<bimestre>/TREINO_<COD>.pdf       questões de treino, gabarito no fim

O HTML é um arquivo só, sem nada da internet: abre sem rede. O PDF é o que
serve no celular (o app do Google Drive mostra PDF, não HTML).

  python automacao/apostila.py                      bimestre mais recente
  python automacao/apostila.py --bimestre 2026-3bim
  python automacao/apostila.py --sem-pdf
"""
import argparse
import html
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESTUDO = RAIZ / "privado" / "estudo"
DATA = RAIZ / "docs" / "data.json"

# Meta: uma página A4 por semana no resumo. A primeira versão (8 conceitos,
# 8 autores, treino dentro) deu 19 páginas para 3 semanas de SOC100, umas 45
# no bimestre, e ele recusou: "muito demais para um resumo" (23/09/2026).
LIMITES = {"conceitos": 6, "autores": 5, "comparacoes": 1, "exemplos": 3,
           "cobrado": 5, "pegadinhas": 3, "treino": 4}
LETRAS = "ABCDE"
CORES = {"com100": "#3b5bdb", "let110": "#e8590c", "soc100": "#0c8599",
         "com170": "#9c36b5", "mmb002": "#2b8a3e", "int100": "#c2255c"}
RESERVA = ["#5f3dc4", "#d6336c", "#1971c2", "#5c940d", "#e67700"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


# --------------------------------------------------------------- fichas

class FichaInvalida(ValueError):
    pass


def _texto(v):
    return " ".join(str(v).split()) if isinstance(v, (str, int, float)) else ""


def validar(bruto):
    """Confere e normaliza a ficha. Corta excesso em vez de recusar; recusa só
    o que quebraria a apostila (sem tema, treino malformado)."""
    if not isinstance(bruto, dict):
        raise FichaInvalida("a ficha não é um objeto JSON")
    f = {"tema": _texto(bruto.get("tema")), "ideia_central": _texto(bruto.get("ideia_central"))}
    if not f["tema"]:
        raise FichaInvalida("ficha sem tema")

    def lista(chave, campos):
        saida = []
        for x in (bruto.get(chave) or [])[: LIMITES[chave]]:
            if isinstance(x, dict) and all(_texto(x.get(c)) for c in campos[:1]):
                saida.append({c: _texto(x.get(c)) for c in campos})
        return saida

    f["conceitos"] = lista("conceitos", ["termo", "definicao"])
    f["autores"] = lista("autores", ["nome", "referencia", "ideia"])
    f["exemplos"] = lista("exemplos", ["exemplo", "explicacao"])
    f["pegadinhas"] = lista("pegadinhas", ["confusao", "certo"])
    f["cobrado"] = [_texto(x) for x in (bruto.get("cobrado") or [])[: LIMITES["cobrado"]] if _texto(x)]
    f["ler_por_conta"] = [_texto(x) for x in (bruto.get("ler_por_conta") or []) if _texto(x)]

    f["comparacoes"] = []
    for c in (bruto.get("comparacoes") or [])[: LIMITES["comparacoes"]]:
        if not isinstance(c, dict):
            continue
        colunas = [_texto(x) for x in c.get("colunas") or []]
        linhas = [[_texto(x) for x in l] for l in c.get("linhas") or [] if isinstance(l, list)][:5]
        linhas = [l[: len(colunas)] + [""] * (len(colunas) - len(l)) for l in linhas]
        if len(colunas) >= 2 and linhas:
            f["comparacoes"].append({"titulo": _texto(c.get("titulo")), "colunas": colunas, "linhas": linhas})

    f["treino"] = []
    for q in (bruto.get("treino") or [])[: LIMITES["treino"]]:
        if not isinstance(q, dict):
            continue
        alts = [_texto(a) for a in q.get("alternativas") or []]
        correta = _texto(q.get("correta")).upper()[:1]
        if _texto(q.get("enunciado")) and len(alts) == 5 and all(alts) and correta in LETRAS:
            f["treino"].append({"enunciado": str(q["enunciado"]).strip(), "alternativas": alts,
                                "correta": correta, "comentario": _texto(q.get("comentario"))})
    return f


def ler_ficha(pasta):
    arq = pasta / "apostila.json"
    if not arq.exists():
        return None
    try:
        return validar(json.loads(arq.read_text(encoding="utf-8")))
    except (ValueError, FichaInvalida):
        return None


def ja_vistos(pasta_disciplina, ate_semana):
    """Termos e autores das semanas anteriores, para a ficha nova não repetir."""
    termos, autores = [], []
    for sem in sorted(pasta_disciplina.glob("semana-*")):
        n = int(sem.name.split("-")[1])
        if n >= ate_semana:
            continue
        f = ler_ficha(sem)
        if f:
            termos += [c["termo"] for c in f["conceitos"]]
            autores += [a["nome"] for a in f["autores"]]
    if not termos and not autores:
        return "(nenhum: esta é a primeira semana da apostila)"
    return "Termos: " + "; ".join(termos) + "\nAutores: " + "; ".join(autores)


# --------------------------------------------------------------- dados

def nomes_das_disciplinas():
    try:
        dados = json.loads(DATA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    saida = {}
    for c in dados.get("courses") or []:
        nome = re.sub(r"\s*-\s*[A-Z]{3}\d{3}.*$", "", c.get("name") or "").strip()
        saida[(c.get("code") or "").lower()] = nome or c.get("code")
    return saida


def coletar(bimestre):
    base = ESTUDO / bimestre
    nomes = nomes_das_disciplinas()
    disciplinas = []
    reserva = iter(RESERVA)
    for pasta in sorted(p for p in base.iterdir() if p.is_dir()):
        semanas = []
        for sem in sorted(pasta.glob("semana-*")):
            ficha = ler_ficha(sem)
            if not ficha:
                continue
            inicio = None
            try:
                inicio = json.loads((sem / "manifest.json").read_text(encoding="utf-8")).get("inicio")
            except (OSError, ValueError):
                pass
            semanas.append({"n": int(sem.name.split("-")[1]), "inicio": inicio, **ficha})
        if semanas:
            cod = pasta.name
            disciplinas.append({"cod": cod, "nome": nomes.get(cod, cod.upper()),
                                "cor": CORES.get(cod) or next(reserva, "#495057"),
                                "semanas": semanas})
    return disciplinas


# --------------------------------------------------------------- HTML

def md(texto):
    """Escapa HTML e aceita só **negrito** e *itálico*."""
    t = html.escape(texto or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    return t


def quebrar_enunciado(texto):
    """Asserção-razão e "I, II e III" em linhas próprias, como na prova. A
    ficha costuma vir num parágrafo só ("I. ... PORQUE II. ...")."""
    t = re.sub(r"\s+(PORQUE)\s+", r"\n\1\n", texto or "")
    t = re.sub(r"(?<=[.:?!])\s+(?=(?:I{1,3}|IV|V)\.\s)", "\n", t)
    return re.sub(r"(?<=[.:?!])\s+(?=(?:A respeito|Assinale|Está correto|É correto|Com base))", "\n", t)


def md_bloco(texto):
    return "".join(f"<p>{md(p)}</p>" for p in re.split(r"\n\s*\n|\n", texto or "") if p.strip())


def data_curta(iso):
    try:
        d = date.fromisoformat(iso)
        return f"{d.day:02d} {MESES[d.month - 1]}"
    except (TypeError, ValueError):
        return ""


def iniciais(nome):
    partes = [p for p in re.split(r"[\s.]+", nome) if p and p[0].isalpha() and p.lower() not in ("de", "da", "do", "dos", "das", "e")]
    return ((partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")) if partes else "?").upper()


def secao_semana(d, s, modo="tela"):
    sid = f"{d['cod']}-s{s['n']:02d}"
    if modo == "treino":
        s = {**s, "ideia_central": "", "ler_por_conta": [], "conceitos": [], "autores": [],
             "comparacoes": [], "exemplos": [], "cobrado": [], "pegadinhas": []}
    elif modo == "resumo":
        s = {**s, "treino": []}
    h = [f'<section class="semana" id="{sid}" data-busca="">']
    h.append(f'''<header class="sem-head">
  <span class="sem-num">S{s["n"]}</span>
  <div class="sem-tit"><p class="kicker">{html.escape(d["cod"].upper())} · Semana {s["n"]}{" · " + data_curta(s["inicio"]) if s.get("inicio") else ""}</p>
  <h3>{md(s["tema"])}</h3></div>
  <label class="revisado no-print"><input type="checkbox" data-chave="{sid}"><span>revisada</span></label>
</header>''')
    if s["ideia_central"]:
        h.append(f'<p class="ideia">{md(s["ideia_central"])}</p>')
    if s["ler_por_conta"]:
        itens = "".join(f"<li>{md(x)}</li>" for x in s["ler_por_conta"])
        h.append(f'<aside class="ler"><p class="rot">Leia ou assista por conta própria</p><ul>{itens}</ul></aside>')
    if s["conceitos"]:
        cards = "".join(f'<article class="card"><h5>{md(c["termo"])}</h5><p>{md(c["definicao"])}</p></article>' for c in s["conceitos"])
        h.append(f'<h4>Conceitos-chave</h4><div class="grade">{cards}</div>')
    if s["autores"]:
        itens = "".join(
            f'<li><span class="ini" aria-hidden="true">{html.escape(iniciais(a["nome"]))}</span><div>'
            f'<p class="aut"><strong>{md(a["nome"])}</strong>{" <span class=ref>" + md(a["referencia"]) + "</span>" if a["referencia"] else ""}</p>'
            f'<p>{md(a["ideia"])}</p></div></li>' for a in s["autores"])
        h.append(f'<h4>Autores e referências</h4><ul class="autores">{itens}</ul>')
    for c in s["comparacoes"]:
        cab = "".join(f"<th>{md(x)}</th>" for x in c["colunas"])
        linhas = "".join("<tr>" + "".join((f"<th>{md(x)}</th>" if i == 0 else f"<td>{md(x)}</td>") for i, x in enumerate(l)) + "</tr>" for l in c["linhas"])
        h.append(f'<h4>{md(c["titulo"]) or "Compare"}</h4><div class="tabela"><table><thead><tr>{cab}</tr></thead><tbody>{linhas}</tbody></table></div>')
    if s["exemplos"]:
        itens = "".join(f'<div class="exemplo"><p class="ex">{md(e["exemplo"])}</p><p>{md(e["explicacao"])}</p></div>' for e in s["exemplos"])
        h.append(f'<h4>Exemplos que caem</h4>{itens}')
    if s["cobrado"]:
        itens = "".join(f"<li>{md(x)}</li>" for x in s["cobrado"])
        h.append(f'<h4>O que o questionário cobrou</h4><ul class="cobrado">{itens}</ul>')
    if s["pegadinhas"]:
        itens = "".join(f'<div class="peg"><p class="nao"><span>Não</span>{md(p["confusao"])}</p><p class="sim"><span>Sim</span>{md(p["certo"])}</p></div>' for p in s["pegadinhas"])
        h.append(f'<h4>Pegadinhas</h4><div class="pegs">{itens}</div>')
    if s["treino"]:
        qs = []
        for i, q in enumerate(s["treino"], 1):
            alts = "".join(f'<li><button type="button" data-letra="{LETRAS[j]}"><b>{LETRAS[j]}</b><span>{md(a)}</span></button></li>' for j, a in enumerate(q["alternativas"]))
            gab = "" if modo != "tela" else f'<details class="gab"><summary>Ver resposta</summary><p><strong>{q["correta"]}.</strong> {md(q["comentario"])}</p></details>'
            qs.append(f'<div class="questao" data-correta="{q["correta"]}"><div class="enun"><span class="qn">{i}</span><div>{md_bloco(quebrar_enunciado(q["enunciado"]))}</div></div><ol class="alts">{alts}</ol>{gab}</div>')
        h.append(f'<h4>Treino</h4>{"".join(qs)}')
    h.append("</section>")
    return "\n".join(h)


def gabarito(d):
    linhas = []
    for s in d["semanas"]:
        for i, q in enumerate(s["treino"], 1):
            linhas.append(f'<li><b>S{s["n"]}.{i} · {q["correta"]}</b> {md(q["comentario"])}</li>')
    if not linhas:
        return ""
    return f'<section class="gabarito"><h3>Gabarito do treino · {html.escape(d["cod"].upper())}</h3><ol>{"".join(linhas)}</ol></section>'


CSS = r"""
:root{--bg:#f6f4ef;--sup:#ffffff;--sup2:#fbfaf7;--tinta:#1c1c21;--suave:#5c5d68;--linha:#e5e1d8;
--ok:#2b8a3e;--ok-bg:#ebfbee;--erro:#c92a2a;--erro-bg:#fff5f5;--aviso:#b35c00;--aviso-bg:#fff4e6;
--sombra:0 1px 2px rgba(20,20,30,.06),0 4px 14px rgba(20,20,30,.05);--r:14px;
--serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-tema="claro"]){--bg:#111317;--sup:#1a1d23;--sup2:#16181d;
--tinta:#ececf1;--suave:#a3a6b1;--linha:#2c2f37;--ok:#69db7c;--ok-bg:#16301d;--erro:#ff8787;--erro-bg:#3a1c1c;
--aviso:#ffc078;--aviso-bg:#35260f;--sombra:0 1px 2px rgba(0,0,0,.4);color-scheme:dark}}
:root[data-tema="escuro"]{--bg:#111317;--sup:#1a1d23;--sup2:#16181d;--tinta:#ececf1;--suave:#a3a6b1;--linha:#2c2f37;
--ok:#69db7c;--ok-bg:#16301d;--erro:#ff8787;--erro-bg:#3a1c1c;--aviso:#ffc078;--aviso-bg:#35260f;--sombra:0 1px 2px rgba(0,0,0,.4);color-scheme:dark}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:72px}
body{margin:0;background:var(--bg);color:var(--tinta);font:16px/1.6 var(--sans);-webkit-font-smoothing:antialiased}
.disc{--acc-bg:color-mix(in srgb,var(--acc) 11%,var(--sup));--acc-linha:color-mix(in srgb,var(--acc) 35%,var(--linha))}
.topo{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:10px;padding:10px 16px;
background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--linha)}
.topo .marca{font-weight:700;letter-spacing:-.01em;white-space:nowrap}
.topo input{flex:1;min-width:0;padding:8px 12px;border:1px solid var(--linha);border-radius:10px;background:var(--sup);color:var(--tinta);font:inherit;font-size:15px}
.topo button{border:1px solid var(--linha);background:var(--sup);color:var(--tinta);border-radius:10px;padding:8px 11px;font:inherit;font-size:14px;cursor:pointer}
.casco{display:grid;grid-template-columns:260px minmax(0,1fr);gap:32px;max-width:1180px;margin:0 auto;padding:24px 16px 80px}
nav.sumario{position:sticky;top:76px;align-self:start;max-height:calc(100vh - 96px);overflow:auto;font-size:14px}
nav.sumario .nd{margin:0 0 14px}nav.sumario .nd>a{display:flex;align-items:center;gap:8px;font-weight:700;color:var(--tinta);text-decoration:none}
nav.sumario .bola{width:10px;height:10px;border-radius:50%;background:var(--acc);flex:none}
nav.sumario ul{list-style:none;margin:6px 0 0;padding:0 0 0 18px;border-left:2px solid var(--linha)}
nav.sumario li a{display:block;padding:3px 0;color:var(--suave);text-decoration:none;line-height:1.35}
nav.sumario li a:hover{color:var(--tinta)}nav.sumario li a.feita::after{content:" ✓";color:var(--ok)}
main{min-width:0}
.capa{padding:8px 0 28px}.capa h1{font:700 clamp(28px,5vw,42px)/1.1 var(--serif);letter-spacing:-.02em;margin:0 0 8px}
.capa p{color:var(--suave);margin:0 0 18px}
.chips{display:flex;flex-wrap:wrap;gap:10px}
.chip{display:flex;flex-direction:column;gap:6px;min-width:190px;flex:1;padding:12px 14px;border-radius:var(--r);background:var(--acc-bg);border:1px solid var(--acc-linha);text-decoration:none;color:var(--tinta)}
.chip b{font-size:13px;letter-spacing:.06em;color:var(--acc)}.chip span{font-size:14px;line-height:1.3}
.barra{height:6px;border-radius:9px;background:color-mix(in srgb,var(--acc) 18%,transparent);overflow:hidden}
.barra i{display:block;height:100%;width:0;background:var(--acc);transition:width .3s}
.chip small{color:var(--suave);font-size:12px}
.disc-cab{margin:48px 0 18px;padding:22px;border-radius:calc(var(--r) + 4px);background:linear-gradient(135deg,var(--acc),color-mix(in srgb,var(--acc) 70%,#000));color:#fff}
.disc-cab p{margin:0;opacity:.85;font-size:13px;letter-spacing:.08em;text-transform:uppercase;font-weight:600}
.disc-cab h2{margin:4px 0 0;font:700 clamp(22px,4vw,30px)/1.2 var(--serif)}
.semana{background:var(--sup);border:1px solid var(--linha);border-radius:calc(var(--r) + 4px);padding:22px 22px 8px;margin:0 0 22px;box-shadow:var(--sombra)}
.sem-head{display:flex;align-items:flex-start;gap:14px;margin-bottom:10px}
.sem-num{flex:none;display:grid;place-items:center;width:46px;height:46px;border-radius:12px;background:var(--acc);color:#fff;font-weight:800;font-size:17px}
.sem-tit{flex:1;min-width:0}.kicker{margin:0;font-size:12px;letter-spacing:.07em;text-transform:uppercase;color:var(--acc);font-weight:700}
.sem-head h3{margin:2px 0 0;font:700 21px/1.25 var(--serif);letter-spacing:-.01em}
.revisado{flex:none;display:flex;align-items:center;gap:6px;font-size:13px;color:var(--suave);cursor:pointer;user-select:none;padding:6px 10px;border:1px solid var(--linha);border-radius:999px}
.revisado input{accent-color:var(--acc);width:16px;height:16px;margin:0}
.ideia{margin:4px 0 16px;padding:14px 16px;border-radius:12px;background:var(--acc-bg);border-left:4px solid var(--acc);font:500 17px/1.5 var(--serif)}
h4{margin:22px 0 10px;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--suave)}
h4::before{content:"";display:inline-block;width:8px;height:8px;border-radius:2px;background:var(--acc);margin-right:8px;vertical-align:1px}
.grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}
.card{padding:12px 14px;border-radius:12px;background:var(--sup2);border:1px solid var(--linha)}
.card h5{margin:0 0 4px;font-size:15px;color:var(--acc)}.card p{margin:0;font-size:14.5px;line-height:1.5}
.autores{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.autores li{display:flex;gap:12px;align-items:flex-start}
.ini{flex:none;display:grid;place-items:center;width:36px;height:36px;border-radius:50%;background:var(--acc-bg);color:var(--acc);font-weight:800;font-size:13px;border:1px solid var(--acc-linha)}
.autores p{margin:0;font-size:14.5px}.aut{line-height:1.35}.ref{color:var(--suave);font-size:13px;margin-left:6px}
.tabela{overflow-x:auto;border:1px solid var(--linha);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--linha)}
thead th{background:var(--acc-bg);color:var(--acc);font-size:13px}tbody th{background:var(--sup2);font-weight:600;width:28%}
tr:last-child>*{border-bottom:0}
.exemplo{margin:0 0 10px;padding:12px 14px;border-radius:12px;border:1px dashed var(--acc-linha)}
.exemplo .ex{margin:0 0 4px;font:600 16px/1.4 var(--serif)}.exemplo .ex::before{content:"“";color:var(--acc)}.exemplo .ex::after{content:"”";color:var(--acc)}
.exemplo p{margin:0;font-size:14.5px}
.cobrado{margin:0;padding:0;list-style:none;display:grid;gap:7px}
.cobrado li{position:relative;padding:0 0 0 28px;font-size:15px}
.cobrado li::before{content:"✓";position:absolute;left:0;top:0;width:20px;height:20px;border-radius:6px;background:var(--ok-bg);color:var(--ok);display:grid;place-items:center;font-size:12px;font-weight:800}
.pegs{display:grid;gap:10px}.peg{border-radius:12px;overflow:hidden;border:1px solid var(--linha)}
.peg p{margin:0;padding:9px 12px;font-size:14.5px;display:flex;gap:10px}.peg span{flex:none;font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;padding:2px 7px;border-radius:6px;height:fit-content;margin-top:2px}
.peg .nao{background:var(--erro-bg)}.peg .nao span{background:var(--erro);color:#fff}
.peg .sim{background:var(--ok-bg)}.peg .sim span{background:var(--ok);color:#fff}
.ler{margin:0 0 6px;padding:12px 14px;border-radius:12px;background:var(--aviso-bg);border:1px solid color-mix(in srgb,var(--aviso) 35%,transparent)}
.ler .rot{margin:0 0 4px;font-weight:700;color:var(--aviso);font-size:13px;letter-spacing:.05em;text-transform:uppercase}
.ler ul{margin:0;padding-left:18px;font-size:14.5px}
.questao{margin:0 0 16px;padding:14px;border:1px solid var(--linha);border-radius:14px;background:var(--sup2)}
.enun{display:flex;gap:10px}.enun p{margin:0 0 8px;font-size:15px}
.qn{flex:none;display:grid;place-items:center;width:26px;height:26px;border-radius:8px;background:var(--acc);color:#fff;font-weight:800;font-size:13px}
.alts{list-style:none;margin:6px 0 0;padding:0;display:grid;gap:6px}
.alts button{width:100%;display:flex;gap:10px;align-items:flex-start;text-align:left;padding:9px 12px;border-radius:10px;border:1px solid var(--linha);background:var(--sup);color:var(--tinta);font:inherit;font-size:14.5px;line-height:1.45;cursor:pointer}
.alts button:hover{border-color:var(--acc)}.alts b{flex:none;color:var(--acc)}
.alts button.certa{background:var(--ok-bg);border-color:var(--ok)}.alts button.errada{background:var(--erro-bg);border-color:var(--erro)}
.gab{margin-top:8px;font-size:14.5px}.gab summary{cursor:pointer;color:var(--acc);font-weight:600}.gab p{margin:6px 0 0}
.gabarito{margin:28px 0}.gabarito ol{padding-left:0;list-style:none;display:grid;gap:6px;font-size:13.5px}
.vazio{display:none!important}
.rodape{margin-top:40px;color:var(--suave);font-size:13px;text-align:center}
.so-print{display:none}
@media (max-width:980px){.casco{grid-template-columns:1fr;gap:0}nav.sumario{display:none}}
@media (max-width:560px){.semana{padding:16px 14px 4px;border-radius:14px}.sem-head{flex-wrap:wrap}.revisado{order:3}
.sem-num{width:40px;height:40px}.sem-head h3{font-size:19px}.topo .marca{display:none}.disc-cab{padding:18px}}
@media print{
@page{size:A4;margin:11mm 12mm 12mm}
:root{--bg:#fff;--sup:#fff;--sup2:#fafafa;--tinta:#16161a;--suave:#555;--linha:#dcdcdc;--sombra:none}
body{font-size:11pt;line-height:1.45;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.topo,nav.sumario,.no-print,.gab,.capa .chips{display:none!important}
.casco{display:block;padding:0;max-width:none}.so-print{display:block}
.disc-cab{margin:0 0 12px;break-after:avoid}.disc+.disc{break-before:page}
.semana{box-shadow:none;border-radius:10px;padding:14px 14px 4px;margin:0 0 12px}
.card,.peg,.questao,.exemplo,.autores li,tr,.ler,.ideia{break-inside:avoid}
h4,.sem-head{break-after:avoid}.grade{grid-template-columns:repeat(2,1fr)}
.alts button{padding:5px 9px;font-size:10.5pt}.questao{padding:10px}
.gabarito{break-before:page}
html[data-modo="resumo"] body{font-size:9pt;line-height:1.32}
html[data-modo="resumo"] .capa{padding:0 0 4mm}html[data-modo="resumo"] .capa h1{font-size:15pt;margin:0}
html[data-modo="resumo"] .capa p{font-size:8pt;margin:1mm 0 0}
html[data-modo="resumo"] .disc-cab{padding:6px 12px;border-radius:8px;margin:0 0 4mm}
html[data-modo="resumo"] .disc-cab p{font-size:7pt}html[data-modo="resumo"] .disc-cab h2{font-size:13pt;margin:0}
html[data-modo="resumo"] .semana{border:0;border-top:2px solid var(--acc);border-radius:0;padding:2mm 0 0;margin:0 0 5mm}
html[data-modo="resumo"] .sem-head{gap:8px;margin:0 0 2mm}
html[data-modo="resumo"] .sem-num{width:24px;height:24px;border-radius:6px;font-size:9pt}
html[data-modo="resumo"] .kicker{font-size:6.5pt}html[data-modo="resumo"] .sem-head h3{font-size:11.5pt;margin:0}
html[data-modo="resumo"] .ideia{font:italic 9.5pt/1.35 var(--serif);padding:4px 8px;margin:0 0 2mm;border-left-width:3px;border-radius:4px}
html[data-modo="resumo"] h4{font-size:6.8pt;margin:2.5mm 0 1mm}
html[data-modo="resumo"] h4::before{width:6px;height:6px;margin-right:5px}
html[data-modo="resumo"] .grade,html[data-modo="resumo"] .autores,html[data-modo="resumo"] .cobrado{display:block;column-count:2;column-gap:6mm}
html[data-modo="resumo"] .card{border:0;background:none;padding:0;margin:0 0 1.2mm;border-radius:0}
html[data-modo="resumo"] .card h5{display:inline;font-size:9pt}html[data-modo="resumo"] .card h5::after{content:": ";color:var(--tinta)}
html[data-modo="resumo"] .card p{display:inline;font-size:9pt}
html[data-modo="resumo"] .autores li{display:block;margin:0 0 1.2mm;break-inside:avoid}html[data-modo="resumo"] .ini{display:none}
html[data-modo="resumo"] .autores li>div,html[data-modo="resumo"] .autores p{display:inline;font-size:9pt}
html[data-modo="resumo"] .ref{font-size:7.5pt;margin:0 3px}
html[data-modo="resumo"] .aut strong::after{content:""}
html[data-modo="resumo"] .cobrado li{padding-left:13px;margin:0 0 1mm;font-size:9pt;break-inside:avoid}
html[data-modo="resumo"] .cobrado li::before{width:9px;height:9px;font-size:6pt;border-radius:2px;top:2px}
html[data-modo="resumo"] table{font-size:8pt}html[data-modo="resumo"] th,html[data-modo="resumo"] td{padding:2px 6px}
html[data-modo="resumo"] .tabela{border-radius:4px}
html[data-modo="resumo"] .exemplo{padding:2px 8px;margin:0 0 1mm;border:0;border-left:2px solid var(--acc-linha);border-radius:0}
html[data-modo="resumo"] .exemplo .ex{display:inline;font-size:9pt}html[data-modo="resumo"] .exemplo .ex::after{content:"” "}
html[data-modo="resumo"] .exemplo p{display:inline;font-size:8.5pt;color:var(--suave)}
html[data-modo="resumo"] .pegs{gap:1mm}html[data-modo="resumo"] .peg{display:flex;border:0;border-radius:4px}
html[data-modo="resumo"] .peg p{flex:1;padding:2px 6px;font-size:8.5pt;gap:5px}
html[data-modo="resumo"] .peg span{font-size:6pt;padding:0 4px}
html[data-modo="resumo"] .ler{padding:2px 8px;margin:0 0 1mm;border-radius:4px}
html[data-modo="resumo"] .ler .rot{display:inline;font-size:6.8pt;margin-right:4px}
html[data-modo="resumo"] .ler ul{display:inline;padding:0;font-size:8pt}
html[data-modo="resumo"] .ler li{display:inline}html[data-modo="resumo"] .ler li+li::before{content:" · "}
html[data-modo="resumo"] .rodape{display:none}
html[data-modo="treino"] body{font-size:9.5pt;line-height:1.35}
html[data-modo="treino"] .capa h1{font-size:15pt;margin:0}html[data-modo="treino"] .capa p{font-size:8pt;margin:1mm 0 3mm}
html[data-modo="treino"] .disc-cab{padding:6px 12px;border-radius:8px;margin:0 0 4mm}html[data-modo="treino"] .disc-cab h2{font-size:13pt;margin:0}
html[data-modo="treino"] .semana{border:0;border-top:2px solid var(--acc);border-radius:0;padding:2mm 0 0;margin:0 0 3mm}
html[data-modo="treino"] .sem-num{width:22px;height:22px;font-size:8.5pt;border-radius:6px}html[data-modo="treino"] .sem-head h3{font-size:11pt;margin:0}
html[data-modo="treino"] .kicker{font-size:6.5pt}html[data-modo="treino"] h4{display:none}
html[data-modo="treino"] .questao{border:0;background:none;padding:0;margin:0 0 3mm}
html[data-modo="treino"] .qn{width:18px;height:18px;font-size:8pt;border-radius:5px}
html[data-modo="treino"] .enun p{margin:0 0 1mm;font-size:9.5pt}
html[data-modo="treino"] .alts{gap:0;margin:1mm 0 0 28px}
html[data-modo="treino"] .alts button{border:0;background:none;padding:0.4mm 0;font-size:9pt;gap:6px}
html[data-modo="treino"] .gabarito ol{font-size:8.5pt;gap:1.5mm}html[data-modo="treino"] .rodape{display:none}}
"""

JS = r"""
(function(){
  var raiz=document.documentElement, bim=raiz.getAttribute('data-bim');
  function ler(k){try{return localStorage.getItem(k)}catch(e){return null}}
  function gravar(k,v){try{if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v)}catch(e){}}
  var tema=ler('apostila-tema'); if(tema) raiz.setAttribute('data-tema',tema);
  var bt=document.getElementById('tema');
  if(bt) bt.addEventListener('click',function(){
    var escuro=raiz.getAttribute('data-tema')==='escuro'||(!raiz.getAttribute('data-tema')&&matchMedia('(prefers-color-scheme: dark)').matches);
    var novo=escuro?'claro':'escuro'; raiz.setAttribute('data-tema',novo); gravar('apostila-tema',novo);
  });
  function progresso(){
    document.querySelectorAll('.disc[data-cod]').forEach(function(d){
      var cx=d.querySelectorAll('.revisado input'), n=0;
      cx.forEach(function(c){if(c.checked)n++});
      var cod=d.getAttribute('data-cod'), pct=cx.length?Math.round(100*n/cx.length):0;
      document.querySelectorAll('[data-prog="'+cod+'"]').forEach(function(b){b.style.width=pct+'%'});
      document.querySelectorAll('[data-conta="'+cod+'"]').forEach(function(s){s.textContent=n+' de '+cx.length+' semanas revisadas'});
    });
  }
  document.querySelectorAll('.revisado input').forEach(function(c){
    var k='apostila:'+bim+':'+c.getAttribute('data-chave');
    c.checked=ler(k)==='1';
    var link=document.querySelector('nav.sumario a[href="#'+c.getAttribute('data-chave')+'"]');
    if(link) link.classList.toggle('feita',c.checked);
    c.addEventListener('change',function(){gravar(k,c.checked?'1':null); if(link) link.classList.toggle('feita',c.checked); progresso()});
  });
  progresso();
  document.querySelectorAll('.questao').forEach(function(q){
    var certa=q.getAttribute('data-correta');
    q.querySelectorAll('button[data-letra]').forEach(function(b){
      b.addEventListener('click',function(){
        q.querySelectorAll('button[data-letra]').forEach(function(x){x.classList.remove('certa','errada')});
        q.querySelector('button[data-letra="'+certa+'"]').classList.add('certa');
        if(b.getAttribute('data-letra')!==certa) b.classList.add('errada');
        var g=q.querySelector('details.gab'); if(g) g.open=true;
      });
    });
  });
  var busca=document.getElementById('busca');
  if(busca) busca.addEventListener('input',function(){
    var t=busca.value.trim().toLowerCase();
    document.querySelectorAll('.semana').forEach(function(s){
      s.classList.toggle('vazio', t.length>1 && s.textContent.toLowerCase().indexOf(t)<0);
    });
  });
})();
"""


def montar_html(bimestre, disciplinas, modo="tela"):
    agora = datetime.now()
    total = sum(len(d["semanas"]) for d in disciplinas)
    num_bim = re.search(r"(\d)bim", bimestre)
    ano = bimestre[:4]
    titulo = f"Apostila de prova · {num_bim.group(1)}º bimestre {ano}" if num_bim else f"Apostila {bimestre}"
    if modo == "treino":
        titulo = titulo.replace("Apostila de prova", "Caderno de treino")

    chips = "".join(
        f'<a class="chip disc" style="--acc:{d["cor"]}" href="#{d["cod"]}"><b>{d["cod"].upper()}</b>'
        f'<span>{html.escape(d["nome"])}</span><div class="barra"><i data-prog="{d["cod"]}"></i></div>'
        f'<small data-conta="{d["cod"]}">{len(d["semanas"])} semanas</small></a>' for d in disciplinas)
    sumario = "".join(
        f'<div class="nd disc" style="--acc:{d["cor"]}"><a href="#{d["cod"]}"><span class="bola"></span>{d["cod"].upper()}</a><ul>'
        + "".join(f'<li><a href="#{d["cod"]}-s{s["n"]:02d}">S{s["n"]} · {html.escape(s["tema"])}</a></li>' for s in d["semanas"])
        + "</ul></div>" for d in disciplinas)
    corpo = []
    for d in disciplinas:
        corpo.append(f'<div class="disc" id="{d["cod"]}" data-cod="{d["cod"]}" style="--acc:{d["cor"]}">')
        corpo.append(f'<header class="disc-cab"><p>{d["cod"].upper()} · {len(d["semanas"])} semanas</p><h2>{html.escape(d["nome"])}</h2></header>')
        corpo += [secao_semana(d, s, modo) for s in d["semanas"]]
        if modo == "treino":
            corpo.append(gabarito(d))
        corpo.append("</div>")

    return f"""<!doctype html>
<html lang="pt-BR" data-bim="{html.escape(bimestre)}" data-modo="{modo}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#f6f4ef" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#111317" media="(prefers-color-scheme: dark)">
<title>{html.escape(titulo)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="topo no-print"><span class="marca">Apostila</span>
<input id="busca" type="search" placeholder="Buscar termo, autor, exemplo..." aria-label="Buscar na apostila">
<button id="tema" type="button" aria-label="Alternar tema claro e escuro">Tema</button></div>
<div class="casco">
<nav class="sumario no-print" aria-label="Sumário">{sumario}</nav>
<main>
<section class="capa">
<h1>{html.escape(titulo)}</h1>
<p>{total} semanas até agora · atualizada em {agora:%d/%m/%Y às %H:%M} · montada a partir do AVA, semana a semana</p>
<div class="chips">{chips}</div>
</section>
{"".join(corpo)}
<p class="rodape">Montada pela revisão semanal (automacao/revisao_semanal.py). Material de estudo pessoal.</p>
</main></div>
<script>{JS}</script>
</body></html>"""


# --------------------------------------------------------------- saída

def gerar(bimestre, pdf=True):
    """Gera APOSTILA.html (tela) e, por disciplina, APOSTILA_<COD>.pdf (resumo,
    sem questões) e TREINO_<COD>.pdf (questões com gabarito no fim)."""
    base = ESTUDO / bimestre
    disciplinas = coletar(bimestre)
    if not disciplinas:
        return []
    # PDF de disciplina que ficou sem ficha válida sairia velho, desencontrado
    # do HTML (visto em 23/09/2026 ao refazer as fichas de SOC100).
    atuais = {d["cod"].upper() for d in disciplinas}
    for velho in list(base.glob("APOSTILA_*.pdf")) + list(base.glob("TREINO_*.pdf")):
        if velho.stem.split("_", 1)[1] not in atuais:
            velho.unlink(missing_ok=True)
    saida = base / "APOSTILA.html"
    saida.write_text(montar_html(bimestre, disciplinas), encoding="utf-8")
    feitos = [saida]
    if not pdf:
        return feitos
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        navegador = pw.chromium.launch(headless=True)
        page = navegador.new_page()
        for d in disciplinas:
            for modo, prefixo in (("resumo", "APOSTILA"), ("treino", "TREINO")):
                if modo == "treino" and not any(s["treino"] for s in d["semanas"]):
                    continue
                temp = base / f".apostila_{d['cod']}_{modo}.html"
                temp.write_text(montar_html(bimestre, [d], modo=modo), encoding="utf-8")
                page.goto(temp.as_uri())
                page.emulate_media(media="print")
                destino = base / f"{prefixo}_{d['cod'].upper()}.pdf"
                rotulo = "resumo" if modo == "resumo" else "treino"
                page.pdf(
                    path=str(destino), format="A4", print_background=True,
                    display_header_footer=True, header_template="<span></span>",
                    footer_template=(
                        '<div style="width:100%;font-size:7px;color:#888;padding:0 12mm;'
                        'display:flex;justify-content:space-between;font-family:system-ui,sans-serif">'
                        f'<span>{d["cod"].upper()} · {html.escape(d["nome"])} · {rotulo}</span>'
                        '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'),
                    margin={"top": "11mm", "bottom": "12mm", "left": "12mm", "right": "12mm"},
                )
                temp.unlink(missing_ok=True)
                feitos.append(destino)
        navegador.close()
    return feitos


def bimestre_mais_recente():
    pastas = sorted(p.name for p in ESTUDO.glob("*-*bim") if p.is_dir())
    return pastas[-1] if pastas else None


def main():
    ap = argparse.ArgumentParser(description="Monta a apostila de prova do bimestre.")
    ap.add_argument("--bimestre")
    ap.add_argument("--sem-pdf", action="store_true")
    args = ap.parse_args()
    bim = args.bimestre or bimestre_mais_recente()
    if not bim:
        print("nenhum bimestre em privado/estudo")
        return 3
    feitos = gerar(bim, pdf=not args.sem_pdf)
    if not feitos:
        print(f"{bim}: nenhuma ficha semanal (apostila.json) ainda")
        return 0
    for f in feitos:
        print(f"  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
