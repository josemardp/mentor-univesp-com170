# -*- coding: utf-8 -*-
"""Revisão semanal: toda segunda, junta o material da semana que terminou e
monta o corpo de revisão, para a prova não virar maratona na véspera.

Por que existe: o guia da prova de 22/09/2026 foi montado na última hora e
cobriu 6 de 19 questões. A Regra de revisão (CLAUDE.md) diz o que faltou:
fonte inteira e questionários primeiro. Este script cumpre a regra uma semana
de cada vez, sozinho, pela tarefa "Univesp - revisao semanal" do Agendador.

O que faz, por disciplina de cronograma semanal:
  1. acha as semanas já encerradas (início + 7 dias <= hoje) que ainda não
     estão fechadas no manifest;
  2. lê cada item da semana no AVA: texto das páginas, slides em PDF, legenda
     das videoaulas (yt-dlp) e a revisão de todas as tentativas do
     questionário. Leitor externo (Biblioteca Virtual, Minha Biblioteca, LTI)
     fica anotado como "não lido", nunca omitido;
  3. chama o Claude sem janela, preso à pasta da semana, para escrever a
     REVISAO.md; refaz o CORPO_REVISAO.md da disciplina juntando as semanas.

Questionário ainda não feito fica "pendente" e é tentado de novo na segunda
seguinte; quando entra, a revisão da semana é remontada. Semana só fecha
quando não sobra pendência.

Tudo vai para privado/ (Drive), nunca para o git: é conteúdo do AVA e
gabarito. O repositório é público.

  python automacao/revisao_semanal.py                 rodada normal
  python automacao/revisao_semanal.py --sem-montar    só coleta
  python automacao/revisao_semanal.py --disciplina SOC100 --semana 7 --desde 2026-07-01
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Código que não pode ser público (leitor dos textos-base) fica no Drive.
sys.path.append(str(RAIZ / "privado" / "automacao"))

PRIVADO = RAIZ / "privado"
DATA = RAIZ / "docs" / "data.json"
LOG_DIR = RAIZ / "tmp" / "log"
RESUMO = LOG_DIR / "revisao_resumo.txt"
PROMPT = Path(__file__).resolve().parent / "revisao_semanal_prompt.md"
PROMPT_FICHA = Path(__file__).resolve().parent / "apostila_prompt.md"

# A automação nasceu para o 4º bimestre de 2026. Semanas anteriores só entram
# com --desde, para a primeira rodada não remontar o bimestre inteiro que já
# teve prova.
INICIO_PADRAO = date(2026, 9, 28)
# Questionário sem tentativa depois disto deixa de ser "pendente": a semana
# fecha registrando que não houve tentativa. O AVA fecha os da Univesp cerca
# de 16 dias depois do início da semana (conferido em SOC100 S7, 31/08 a 16/09).
DIAS_ATE_DESISTIR_DO_QUIZ = 21
TEMPO_CLAUDE_S = 25 * 60
# Fonte que falha em tantas rodadas seguidas vira "não lido" com o motivo.
# Sem isto, um PDF que saiu do ar deixava a semana aberta para sempre e cada
# desbloqueio de tela, depois de 3 h, relia o AVA e avisava "problema" (revisão
# da auditoria do Codex, 23/09/2026).
MAX_TENTATIVAS_FONTE = 3
# Código de saída "o retrato do dia ainda não saiu": não é falha, é espera.
AGUARDA_RETRATO = 4
MAQUINA = RAIZ / "privado" / "estudo" / "MAQUINA_DA_REVISAO.txt"
LIMITE_ATINGIDO = False

SEMANA_RE = re.compile(r"^\s*semana\s+(\d+)\b", re.I)
BIMESTRE_RE = re.compile(r"/(\d{4})/cronograma_\w+?_(\d)\.html")
YOUTUBE_RE = re.compile(r"(?:youtube\.com/embed/|youtu\.be/|youtube\.com/watch\?v=)([\w-]{11})")
LEITOR_EXTERNO = ("login_mb", "bvirtual", "pearson", "minhabiblioteca", "/mod/lti/")
# Link de página que não é material: crédito de imagem e rede social.
LIXO_EXTERNO = ("freepik", "unsplash", "pixabay", "pexels", "flaticon", "creativecommons",
                "shutterstock", "istockphoto", "stock.adobe.com", "facebook.com", "instagram.com",
                "linkedin.com", "twitter.com", "x.com/", "accessibility/resetall")
# Revista acadêmica em OJS: ".../article/view/ARTIGO/ARQUIVO" é a página do
# leitor; o PDF sai trocando "view" por "download" (LET110 S5, 23/09/2026).
OJS_RE = re.compile(r"/article/view/(\d+)/(\d+)")

# Versões do coletor. Fonte resolvida por uma versão antiga é relida uma vez
# pela nova (auditoria de 26/10/2026, ver precisa_reler):
#   questionário 2: alternativa marcada, resposta oficial e comentário do AVA
#   questionário 3: número das afirmativas em lista (<ol type="I">)
#   questionário 4: índice de fórmula (Z+, Z-) e questão anulada
#   leitor 1 a 3: texto-base aberto pelo LTI (privado/automacao/leitor_livros.py)
#   externo 1: página HTML de fora do AVA lida como texto
#   externo 2: conteúdo escondido em aba e PDF ligado na página (REA Univesp)
#   pdf 1: marca de página no texto extraído
QUIZ_V, LEITOR_V, EXT_V, PDF_V = 4, 3, 2, 1
# O AVA só mostra a resposta certa e o comentário depois que o questionário
# fecha (uns 16 dias depois do início da semana). Até lá a revisão tem só a
# nota; a coleta volta a ler o questionário até a resposta oficial aparecer.
DIAS_ATE_GABARITO = 35
# "(Leia o Capítulo 1, ..., p. 11-20)", "p. 111–119", "Leia as páginas 37-62"
PAGINAS_RE = re.compile(r"\b(?:p\.|págs?\.?|páginas?)\s*(\d+)\s*(?:-|–|—|a|até)\s*(\d+)", re.I)
# Texto mínimo para uma página externa contar como lida (GeoGebra e Khan
# Academy são atividades interativas: sobra só o menu).
EXT_MIN_CHARS = 1500
# Atividade para fazer clicando: o texto que sobra é menu e aviso de cookie
# (GeoGebra em MMB002 S3, 26/10/2026). Fica "não lido" com o motivo.
INTERATIVO = ("geogebra.org", "khanacademy.org", "phet.colorado.edu", "wordwall.net")


# --------------------------------------------------------------- utilidades

def hoje_br():
    return datetime.now().date()


def slug(texto, limite=50):
    texto = re.sub(r"[^\w\s-]", "", texto or "", flags=re.U).strip().lower()
    return re.sub(r"[\s_-]+", "-", texto)[:limite].strip("-") or "item"


def bimestre_de(curso):
    fonte = (curso.get("cronograma") or {}).get("fonte") or ""
    m = BIMESTRE_RE.search(fonte)
    return f"{m.group(1)}-{m.group(2)}bim" if m else None


def semanas_encerradas(curso, hoje, desde):
    """[(n, inicio, secao)] das semanas que já terminaram, na ordem."""
    inicios = {}
    for s in (curso.get("cronograma") or {}).get("semanas") or []:
        try:
            inicios[int(s["n"])] = date.fromisoformat(s["inicio"])
        except (KeyError, TypeError, ValueError):
            continue
    saida = []
    for secao in curso.get("sections") or []:
        m = SEMANA_RE.match(secao.get("title") or "")
        if not m:
            continue
        n = int(m.group(1))
        inicio = inicios.get(n)
        if inicio and inicio >= desde and inicio + timedelta(days=7) <= hoje:
            saida.append((n, inicio, secao))
    return sorted(saida, key=lambda x: x[0])


def classificar_link(href):
    h = (href or "").lower()
    if not h.startswith("http"):
        return None
    if YOUTUBE_RE.search(h):
        return "youtube"
    if any(x in h for x in LEITOR_EXTERNO):
        return "leitor"
    if "download.php" in h and ".mp4" in h:
        return None  # o vídeo em si; a legenda vem do YouTube
    if h.split("?")[0].endswith(".pdf"):
        return "pdf"
    if any(x in h for x in LIXO_EXTERNO):
        return None
    return "externo"


def limpar_vtt(bruto):
    """Texto corrido de uma legenda automática do YouTube.

    A legenda automática repete cada frase em duas ou três deixas seguidas;
    sem tirar a repetição, o texto triplica e o resumo sai torto.
    """
    linhas, anterior = [], None
    for linha in bruto.splitlines():
        linha = linha.strip()
        if (not linha or linha.startswith(("WEBVTT", "Kind:", "Language:", "NOTE"))
                or "-->" in linha or linha.isdigit()):
            continue
        linha = re.sub(r"<[^>]+>", "", linha).strip()
        if linha and linha != anterior:
            linhas.append(linha)
            anterior = linha
    return " ".join(linhas)


def texto_util(bruto):
    """Corta o rodapé de navegação e a caixa de conclusão do Moodle."""
    texto = bruto.split("\nPágina anterior")[0]
    texto = re.sub(r"^Condições de conclusão\s*\n[^\n]*\n", "", texto)
    return texto.strip()


TEX_SIMBOLOS = {
    r"\times": "×", r"\cdot": "·", r"\div": "÷", r"\pm": "±", r"\leq": "≤", r"\geq": "≥",
    r"\le": "≤", r"\ge": "≥", r"\neq": "≠", r"\ne": "≠", r"\approx": "≈", r"\infty": "∞",
    r"\in": "∈", r"\notin": "∉", r"\subset": "⊂", r"\subseteq": "⊆", r"\supset": "⊃",
    r"\cup": "∪", r"\cap": "∩", r"\emptyset": "∅", r"\varnothing": "∅", r"\pi": "π",
    r"\%": "%", r"\,": " ", r"\;": " ", r"\!": "", r"\quad": " ", r"\ldots": "...",
    r"\cdots": "...", r"\to": "→", r"\Rightarrow": "⇒", r"\left": "", r"\right": "",
}
SOBRESCRITO = str.maketrans("0123456789+-n*", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁿ*")


def tex_legivel(tex):
    """Fórmula do MathJax em texto de ler: \\frac{3}{4} vira 3/4, a^{7} vira a⁷.

    26/10/2026: a revisão do questionário de MMB002 lida pelo innerText
    trazia cada símbolo numa linha ("1\\n−\\nZ\\n+"). O TeX original fica no
    <script type="math/tex"> ao lado do desenho; este é o texto que vale."""
    # Hífen invisível no TeX é o sinal de menos do índice (Z_­ é Z-, MMB002 S2).
    t = tex.strip().replace("­", "-")
    for _ in range(4):  # de dentro para fora: expoente antes da fração que o contém
        t = re.sub(r"\\(?:mathbb|mathbf|mathrm|text|textbf|mbox)\{([^{}]*)\}", r"\1", t)
        t = re.sub(r"\^\{([0-9+\-n*]+)\}|\^([0-9n*])",
                   lambda m: (m.group(1) or m.group(2)).translate(SOBRESCRITO), t)
        t = re.sub(r"\^\{([^{}]*)\}", r"^(\1)", t)
        t = re.sub(r"_\{([^{}]*)\}|_([^\s{}\\])", lambda m: m.group(1) or m.group(2), t)
        t = re.sub(r"\\sqrt\{([^{}]*)\}", r"√(\1)", t)
        t = re.sub(r"\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}",
                   lambda m: (m.group(1) if re.fullmatch(r"[\w,.]+", m.group(1)) else f"({m.group(1)})") + "/" +
                             (m.group(2) if re.fullmatch(r"[\w,.]+", m.group(2)) else f"({m.group(2)})"), t)
    for k in sorted(TEX_SIMBOLOS, key=len, reverse=True):
        t = re.sub(re.escape(k) + r"(?![a-zA-Z])", lambda _m, v=TEX_SIMBOLOS[k]: v, t)
    t = t.replace("{", "").replace("}", "").replace("\\", "")
    return re.sub(r"\s+", " ", t).strip()


def com_formulas(texto):
    """Troca as marcas ⟦TeX⟧ que o JavaScript deixa pelo texto legível."""
    t = re.sub(r"⟦(.*?)⟧", lambda m: tex_legivel(m.group(1)), texto or "", flags=re.S)
    return t.replace("\u00ad", "")


class _ExtratorTexto(HTMLParser):
    BLOCOS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section",
              "blockquote", "table", "figcaption", "article", "header", "footer", "dd", "dt"}
    PULAR = {"script", "style", "nav", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__()
        self.partes, self.pular = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.PULAR:
            self.pular += 1
        elif tag in self.BLOCOS:
            self.partes.append("\n")

    def handle_endtag(self, tag):
        if tag in self.PULAR:
            self.pular = max(0, self.pular - 1)
        elif tag in self.BLOCOS:
            self.partes.append("\n")

    def handle_data(self, dado):
        if not self.pular:
            self.partes.append(dado)


def html_para_texto(bruto):
    """Texto corrido de uma página HTML, sem script, estilo e menu <nav>."""
    p = _ExtratorTexto()
    p.feed(bruto or "")
    t = re.sub(r"[ \t\r\f\v\u00a0]+", " ", "".join(p.partes))
    t = re.sub(r" *\n *", "\n", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def intervalo_paginas(titulo):
    """(início, fim) das páginas que o título manda ler, ou None."""
    m = PAGINAS_RE.search(titulo or "")
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if 0 < a <= b <= a + 80:
            return a, b
    return None


def precisa_reler(fonte, inicio, hoje):
    """Fonte já resolvida que a versão atual do coletor lê melhor.

    Auditoria de 26/10/2026: o questionário era lido sem a alternativa
    marcada e antes de o AVA mostrar a resposta certa; a videoaula vinha da
    legenda automática quando a Univesp publica legenda revisada; o texto-base
    do LTI e as páginas HTML de fora do AVA ficavam "não lido" sem tentativa."""
    tipo, st = fonte.get("tipo"), fonte.get("status")
    if tipo == "questionário" and st == "lido":
        if fonte.get("formato", 1) < QUIZ_V:
            return True
        return not fonte.get("gabarito_oficial") and hoje <= inicio + timedelta(days=DIAS_ATE_GABARITO)
    if tipo == "videoaula" and st == "lido":
        return "legenda" not in fonte
    if tipo == "pdf" and st == "lido":
        return fonte.get("pdf_v", 0) < PDF_V
    if tipo == "leitor externo" and st == "nao_lido":
        return fonte.get("leitor_v", 0) < LEITOR_V
    if tipo == "link externo" and st in ("nao_lido", "lido"):
        return fonte.get("ext_v", 0) < EXT_V
    return False


def cobertura_md(manifest):
    rotulo = {"lido": "lido", "nao_lido": "NÃO LIDO", "pendente": "pendente",
              "sem_tentativa": "sem tentativa", "sem_legenda": "SEM LEGENDA (assistir)",
              "revisao_fechada": "feito, mas o AVA não mostra a revisão",
              "encaminhado": "ver a fonte abaixo",
              "falhou": "FALHOU"}
    linhas = [
        f"# Cobertura: {manifest['disciplina']} semana {manifest['semana']:02d}",
        "",
        f"Início da semana: {manifest['inicio']}. Última coleta: {manifest['coletado_em']}.",
        "",
        "| Item | Tipo | Situação | Arquivo |",
        "|---|---|---|---|",
    ]
    for f in manifest["fontes"]:
        # Título de texto-base traz "| Autor", que abriria uma coluna a mais.
        titulo = f["titulo"].replace("|", "·")
        situacao = rotulo.get(f["status"], f["status"])
        if f["status"] in ("nao_lido", "falhou") and f.get("erro"):
            # O motivo decide o que fazer: "atividade interativa" é para
            # abrir no navegador, "ler no AVA" é para ler no AVA.
            situacao += " (" + " ".join(str(f["erro"]).split()).replace("|", "/")[:110] + ")"
        linhas.append(f"| {titulo} | {f['tipo']} | {situacao} | {f.get('arquivo') or ''} |")
    return "\n".join(linhas) + "\n"


def assinatura(manifest):
    # Ordenada: na segunda passada as fontes derivadas de página já lida
    # entram no fim da lista, e a ordem diferente remontava a revisão à toa.
    base = sorted((f["chave"], f["status"], f.get("sha256") or f.get("chars"))
                  for f in manifest["fontes"])
    # Instrução nova ao Claude também desatualiza a revisão (26/10/2026: o
    # prompt passou a exigir o GABARITO.md e os textos-base).
    base.append(("prompt", hashlib.sha1(PROMPT.read_bytes()).hexdigest() if PROMPT.exists() else ""))
    return hashlib.sha1(json.dumps(base, ensure_ascii=False).encode()).hexdigest()


def inventario(secao):
    """Detecta material novo no retrato diário sem reler toda semana fechada."""
    itens = [(i.get("cmid"), i.get("type"), i.get("label"), i.get("url"))
             for i in secao.get("items") or []]
    return hashlib.sha256(json.dumps(itens, ensure_ascii=False).encode()).hexdigest()


def semana_em_dia(manifest, pasta, secao, hoje=None):
    """O manifesto sozinho não prova que a revisão e a ficha ainda existem."""
    if not manifest.get("fechada") or manifest.get("inventario") != inventario(secao):
        return False
    try:
        inicio = date.fromisoformat(manifest.get("inicio") or "")
    except ValueError:
        inicio = None
    if inicio and any(precisa_reler(f, inicio, hoje or hoje_br()) for f in manifest.get("fontes", [])):
        return False
    revisao = pasta / "REVISAO.md"
    if not revisao.is_file() or not revisao.stat().st_size:
        return False
    if manifest.get("montado_hash") != assinatura(manifest):
        return False
    import apostila
    return (manifest.get("ficha_de") == hash_arquivo(revisao)
            and apostila.ler_ficha(pasta) is not None)


def aplicar_tentativas(fonte, anterior):
    """Conta as falhas seguidas de uma fonte; na terceira, desiste dela e a
    deixa como "não lido", para ele ler por conta própria."""
    if fonte.get("status") != "falhou":
        fonte.pop("tentativas", None)
        return fonte
    fonte["tentativas"] = ((anterior or {}).get("tentativas") or 0) + 1
    if fonte["tentativas"] >= MAX_TENTATIVAS_FONTE:
        fonte["status"] = "nao_lido"
        fonte["erro"] = f"falhou em {fonte['tentativas']} rodadas: {fonte.get('erro', '')}"[:200]
    return fonte


def maquina_responsavel(arquivo, esta):
    """Só uma máquina faz a revisão: as duas escrevem na mesma pasta do Drive,
    e duas rodadas juntas gastariam o dobro da cota do Claude. A primeira que
    rodar assume; para trocar, basta editar o arquivo."""
    try:
        dona = arquivo.read_text(encoding="utf-8").strip()
    except OSError:
        dona = ""
    if not dona:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(esta + "\n", encoding="utf-8")
        return True, esta
    return dona.upper() == esta.upper(), dona


def retrato_em_dia(dados, hoje):
    """A lista de seções vem da rodada diária, não do AVA aberto aqui."""
    try:
        carimbo = datetime.fromisoformat(dados["checked_at"])
        return carimbo.astimezone().date() == hoje
    except (KeyError, TypeError, ValueError):
        return False


# --------------------------------------------------------------- gabarito

def com_formulas_em(obj):
    if isinstance(obj, str):
        return com_formulas(obj)
    if isinstance(obj, list):
        return [com_formulas_em(x) for x in obj]
    if isinstance(obj, dict):
        return {k: com_formulas_em(v) for k, v in obj.items()}
    return obj


def _nota(v):
    return "?" if v is None else f"{v:.2f}".replace(".", ",")


def quiz_texto(item, tentativas):
    """Revisão do questionário em texto, uma tentativa depois da outra."""
    linhas = [f"# {item['label']}",
              f"Revisão de {len(tentativas)} tentativa(s). Fonte: {item['url']}",
              "(MARCADA) é a alternativa escolhida naquela tentativa; a nota da questão diz se acertou.", ""]
    for n, questoes in enumerate(tentativas, 1):
        linhas += [f"## Tentativa {n}", ""]
        for q in questoes:
            linhas += [f"### Questão {q.get('numero') or '?'} · nota {_nota(q.get('nota'))} de {_nota(q.get('nota_max'))}", "",
                       q.get("enunciado") or "(sem enunciado)"]
            linhas += [f"[imagem no enunciado: {i}]" for i in q.get("imagens") or []]
            linhas.append("")
            for i, a in enumerate(q.get("alternativas") or []):
                letra = a.get("letra") or "ABCDEFGH"[i]
                linhas.append(f"{letra}) {a.get('texto')}" + ("  (MARCADA)" if a.get("marcada") else ""))
            for i, s in enumerate(q.get("selects") or [], 1):
                linhas.append(f"Lacuna {i}: escolhida \"{s.get('escolha') or '(vazia)'}\" "
                              f"(opções: {' / '.join(s.get('opcoes') or [])})")
            if q.get("correta"):
                linhas += ["", "Resposta oficial do AVA: " + re.sub(
                    r"^\s*As? respostas? corretas? (?:é|são)\s*:\s*", "", q["correta"], flags=re.I).strip()]
            if q.get("feedback"):
                linhas += ["", f"Comentário do AVA: {q['feedback']}"]
            linhas += ["", "----", ""]
    return "\n".join(linhas)


def _norm(texto):
    """Texto para comparar alternativas: sem caixa, pontuação e caractere
    invisível, mas com símbolo de matemática. 26/10/2026: tirar tudo que não
    é letra deixava "1-Z+; 2-Z-; 3-Z0" igual a "1-Z+; 2-Z*; 3-Z0"."""
    t = re.sub(r"[­​⁣﻿]", "", (texto or "").lower())
    t = re.sub(r"[.,;:!?\"“”'‘’()]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def consolidar_questoes(tentativas):
    """Questões distintas das tentativas, cada uma com a resposta e de onde
    ela vem. Sem IA: "oficial" é a resposta que o AVA mostra depois que o
    questionário fecha; "nota" é a alternativa marcada numa tentativa que
    levou a nota cheia; "eliminadas" são as marcadas que levaram zero."""
    vistas = {}
    for n, questoes in enumerate(tentativas, 1):
        for q in questoes:
            alts = [a.get("texto") or "" for a in q.get("alternativas") or []]
            # As alternativas mudam de ordem entre tentativas: a chave usa o
            # conjunto delas, e a marcada é guardada pelo texto, não pela letra.
            chave = _norm(q.get("enunciado"))[:500] + "|" + "|".join(sorted(_norm(a) for a in alts))
            reg = vistas.setdefault(chave, {
                "enunciado": q.get("enunciado") or "", "imagens": q.get("imagens") or [],
                "alternativas": alts, "lacunas": [s.get("opcoes") or [] for s in q.get("selects") or []],
                "tentativas": [], "correta": "", "feedback": ""})
            reg["tentativas"].append({
                "tentativa": n, "nota": q.get("nota"), "nota_max": q.get("nota_max"),
                "marcadas": [a.get("texto") or "" for a in q.get("alternativas") or [] if a.get("marcada")],
                "lacunas": [s.get("escolha") or "" for s in q.get("selects") or []]})
            reg["correta"] = reg["correta"] or q.get("correta") or ""
            reg["feedback"] = reg["feedback"] or q.get("feedback") or ""
    return [_resolver(r) for r in vistas.values()]


def _resolver(reg):
    alts = reg["alternativas"]
    reg.update({"resposta": [], "resposta_texto": "", "como": None, "eliminadas": []})
    oficial = re.sub(r"^\s*As? respostas? corretas? (?:é|são)\s*:\s*", "", reg["correta"], flags=re.I).strip()
    if reg["correta"] and oficial:
        varias = reg["correta"].strip().lower().startswith("as respostas corretas")
        iguais = [a for a in alts if _norm(a) == _norm(oficial)]
        if varias or not iguais:
            # Com espaço nas pontas: "II, apenas" não pode casar dentro de "III, apenas".
            iguais = [a for a in alts if _norm(a) and f" {_norm(a)} " in f" {_norm(oficial)} "]
        reg["resposta"] = iguais
        reg["resposta_texto"] = oficial
        # "As respostas corretas são: ..." com várias alternativas: o AVA
        # aceitou mais de uma (questão anulada ou corrigida depois).
        reg["como"] = "oficial_varias" if varias and len(iguais) > 1 else "oficial"
        if varias and alts and len(iguais) == len(alts):
            # Aceitou todas: questão anulada (MMB002 S2, questões 1 e 2). A
            # certa é a que o comentário do AVA diz estar correta, antes da
            # parte "as demais estão incorretas", que cita todas as outras.
            corte = re.split(r"incorret", reg["feedback"], maxsplit=1, flags=re.I)[0]
            pelo = [a for a in alts if _norm(a) and f" {_norm(a)} " in f" {_norm(corte)} "]
            reg["resposta"] = pelo if len(pelo) == 1 else []
            reg["como"] = "anulada"
    else:
        cheia = [t for t in reg["tentativas"] if t["nota"] is not None and t["nota_max"]
                 and abs(t["nota"] - t["nota_max"]) < 1e-6 and len(t["marcadas"]) == 1]
        if cheia:
            reg["resposta"] = cheia[0]["marcadas"]
            reg["como"] = "nota"
        elif any(t["lacunas"] for t in reg["tentativas"]):
            cheias = [t for t in reg["tentativas"] if t["nota"] is not None and t["nota_max"]
                      and abs(t["nota"] - t["nota_max"]) < 1e-6]
            if cheias:
                reg["resposta_texto"] = "; ".join(cheias[0]["lacunas"])
                reg["como"] = "nota"
    reg["eliminadas"] = sorted({m for t in reg["tentativas"] if t["nota"] == 0 and t["nota_max"]
                                for m in t["marcadas"] if m not in reg["resposta"]})
    return reg


def letra_de(reg, texto):
    try:
        return "ABCDEFGH"[reg["alternativas"].index(texto)]
    except ValueError:
        return "?"


def montar_gabarito(pasta, manifest):
    """GABARITO.md (para a revisão) e gabarito.json (para a apostila), feitos
    só com o que o AVA mostrou. A revisão de 26/10/2026 encontrou "marcada X:
    errada" e "correta Y (acertou)" escritos pela IA sem que a coleta tivesse
    a marcada: este arquivo é a fonte da verdade sobre resposta."""
    blocos = []
    for f in manifest.get("fontes", []):
        if f.get("tipo") != "questionário" or f.get("status") != "lido" or not f.get("arquivo"):
            continue
        arq = pasta / f["arquivo"].replace(".txt", ".json")
        if not arq.exists():
            continue  # coletado pelo formato antigo, ainda sem a marcada
        dados = json.loads(arq.read_text(encoding="utf-8"))
        blocos.append({"titulo": f["titulo"], "url": f.get("url"),
                       "questoes": consolidar_questoes(dados.get("tentativas") or [])})
    (pasta / "gabarito.json").write_text(json.dumps(blocos, ensure_ascii=False, indent=1), encoding="utf-8")

    rot = {"oficial": "resposta oficial do AVA", "oficial_varias": "o AVA aceitou mais de uma (questão anulada ou corrigida)",
           "nota": "alternativa marcada numa tentativa com nota cheia",
           "anulada": "questão anulada, o AVA aceitou todas; esta é a que o comentário do AVA dá como certa"}
    linhas = [f"# Gabarito dos questionários: {manifest.get('disciplina')} semana {manifest.get('semana', 0):02d}", "",
              "Montado pelo robô a partir da revisão do AVA, sem IA. É a única fonte sobre qual alternativa "
              "foi marcada e qual é a certa.", ""]
    if not blocos:
        linhas.append("Nenhum questionário com revisão lida nesta semana.")
    for b in blocos:
        linhas += [f"## {b['titulo']}", ""]
        for i, q in enumerate(b["questoes"], 1):
            linhas += [f"### Questão {i}", "", q["enunciado"]]
            linhas += [f"[imagem no enunciado: {x}]" for x in q["imagens"]]
            linhas.append("")
            for a in q["alternativas"]:
                linhas.append(f"{letra_de(q, a)}) {a}")
            linhas.append("")
            if q["resposta"]:
                certas = ", ".join(f"{letra_de(q, a)}) {a}" for a in q["resposta"])
                linhas.append(f"**Resposta:** {certas} ({rot[q['como']]})")
            elif q["como"] == "anulada":
                linhas.append("**Resposta:** questão anulada, o AVA aceitou todas. O comentário do AVA, abaixo, "
                              "diz o que é verdadeiro; tire dele a alternativa certa.")
            elif q["resposta_texto"]:
                linhas.append(f"**Resposta:** {q['resposta_texto']} ({rot.get(q['como'], 'AVA')})")
            else:
                linhas.append("**Resposta:** sem gabarito do AVA ainda.")
            if q["eliminadas"]:
                linhas.append("Erradas com certeza (marcadas e com nota zero): "
                              + "; ".join(f"{letra_de(q, a)}) {a}" for a in q["eliminadas"]))
            notas = "; ".join(f"tentativa {t['tentativa']}: "
                              + (", ".join(letra_de(q, m) for m in t["marcadas"]) or "; ".join(t["lacunas"]) or "nada")
                              + f", nota {_nota(t['nota'])} de {_nota(t['nota_max'])}" for t in q["tentativas"])
            linhas.append(f"Marcadas: {notas}.")
            if q["feedback"]:
                linhas += ["", f"Comentário do AVA: {q['feedback']}"]
            linhas += ["", "---", ""]
    (pasta / "GABARITO.md").write_text("\n".join(linhas), encoding="utf-8")
    return blocos


# --------------------------------------------------------------- leitura AVA

JS_PAGINA = """() => {
  const main = document.querySelector('#region-main') || document.body;
  return {
    texto: main.innerText || '',
    links: [...main.querySelectorAll('a[href]')].map(a => [(a.innerText||'').trim(), a.href]),
    iframes: [...document.querySelectorAll('iframe')].map(f => f.src || ''),
  };
}"""

# Revisão do questionário questão a questão. 26/10/2026: o innerText puro
# perdia a alternativa marcada (o "checked" do rádio não é texto), picava
# fórmula do MathJax em um símbolo por linha e colava as opções da lacuna no
# enunciado. Sem a marcada, a revisão da semana "deduzia" qual tinha sido e
# escrevia como fato.
JS_QUESTOES = r"""() => {
  const txt = el => el ? (el.innerText || '').replace(/ /g, ' ').trim() : '';
  const ESTADOS = ['que', 'deferredfeedback', 'immediatefeedback', 'interactive', 'adaptive',
    'adaptivenopenalty', 'complete', 'notyetanswered', 'answersaved', 'correct', 'incorrect',
    'partiallycorrect', 'notanswered', 'gradedright', 'gradedwrong', 'gradedpartial',
    'invalidanswer', 'requiresgrading'];
  // Fórmula: o TeX original fica num <script type="math/tex">; o desenho do
  // MathJax some e entra o TeX entre ⟦ ⟧, que o Python deixa legível.
  document.querySelectorAll('.que script[type^="math/tex"]').forEach(s => {
    const m = document.createElement('span');
    m.textContent = '⟦' + s.textContent + '⟧';
    s.after(m);
  });
  document.querySelectorAll('.que .MathJax_Preview, .que .MathJax, .que .MathJax_CHTML, .que .MathJax_Display, .que .MJX_Assistive_MathML, .que mjx-container')
    .forEach(e => { e.style.display = 'none'; });
  // Afirmativa em <ol type="I">: o "I." que a tela mostra não é texto, e sem
  // ele "Está correto o que se afirma em: I e II" não tem referência
  // (MMB002 S1, questão dos conjuntos, 26/10/2026).
  const romano = n => [[10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I']]
    .reduce((s, [v, r]) => { while (n >= v) { s += r; n -= v; } return s; }, '');
  const marcador = (tipo, n) => ({
    'I': romano(n), 'upper-roman': romano(n), 'i': romano(n).toLowerCase(), 'lower-roman': romano(n).toLowerCase(),
    'A': String.fromCharCode(64 + n), 'upper-alpha': String.fromCharCode(64 + n), 'upper-latin': String.fromCharCode(64 + n),
    'a': String.fromCharCode(96 + n), 'lower-alpha': String.fromCharCode(96 + n), 'lower-latin': String.fromCharCode(96 + n),
    'none': '',
  })[tipo] ?? String(n);
  document.querySelectorAll('.que .qtext ol, .que .qtext ul, .que .outcome ol, .que .outcome ul').forEach(lista => {
    const tipo = lista.getAttribute('type') || getComputedStyle(lista).listStyleType;
    let n = parseInt(lista.getAttribute('start') || '1', 10);
    [...lista.children].filter(li => li.tagName === 'LI').forEach(li => {
      const m = lista.tagName === 'OL' ? marcador(tipo, n++) : (tipo === 'none' ? '' : '•');
      if (m) li.insertAdjacentText('afterbegin', m === '•' ? '• ' : m + '. ');
    });
  });
  return [...document.querySelectorAll('.que')].map(q => {
    const qtext = q.querySelector('.qtext');
    const selects = [...q.querySelectorAll('.formulation select')].map(s => ({
      escolha: s.value ? s.options[s.selectedIndex].text.trim() : '',
      opcoes: [...s.options].map(o => o.text.trim()).filter(Boolean),
    }));
    if (qtext) qtext.querySelectorAll('select').forEach((s, i) => {
      const m = document.createElement('span');
      m.textContent = ` [lacuna ${i + 1}] `;
      s.style.display = 'none';
      s.after(m);
    });
    const alternativas = [...q.querySelectorAll('.answer input[type=radio], .answer input[type=checkbox]')].map(inp => {
      const rot = document.getElementById(inp.getAttribute('aria-labelledby') || '') || inp.closest('div');
      return {
        letra: txt(rot && rot.querySelector('.answernumber')).replace(/[^a-zA-Z]/g, '').toUpperCase(),
        texto: txt(rot && (rot.querySelector('.flex-fill') || rot)),
        marcada: inp.checked,
      };
    });
    const grade = txt(q.querySelector('.info .grade'));
    const m = grade.match(/([\d.,]+)\s+de\s+([\d.,]+)/);
    return {
      numero: txt(q.querySelector('.info .qno')),
      tipo: [...q.classList].find(c => !ESTADOS.includes(c)) || '',
      estado: txt(q.querySelector('.info .state')),
      nota: m ? parseFloat(m[1].replace(',', '.')) : null,
      nota_max: m ? parseFloat(m[2].replace(',', '.')) : null,
      enunciado: txt(qtext),
      imagens: qtext ? [...qtext.querySelectorAll('img')].map(i => i.alt || i.title || 'imagem') : [],
      alternativas,
      selects,
      campos: [...q.querySelectorAll('.formulation input[type=text]')].map(i => i.value),
      feedback: [txt(q.querySelector('.outcome .specificfeedback')),
                 txt(q.querySelector('.outcome .generalfeedback'))].filter(Boolean).join('\n'),
      correta: txt(q.querySelector('.outcome .rightanswer')),
    };
  });
}"""


class Coletor:
    def __init__(self, page, pasta):
        self.page = page
        self.pasta = pasta
        self.fontes_dir = pasta / "fontes"
        self.fontes_dir.mkdir(parents=True, exist_ok=True)

    def _abrir(self, url):
        self.page.goto(url, timeout=60000)
        self.page.wait_for_timeout(1200)
        return self.page.evaluate(JS_PAGINA)

    def _gravar(self, nome, texto):
        caminho = self.fontes_dir / nome
        caminho.write_text(texto, encoding="utf-8")
        return f"fontes/{nome}", len(texto), hashlib.sha256(texto.encode("utf-8")).hexdigest()

    def _baixar(self, url):
        # Site de universidade com certificado vencido é comum (UFPB, 22/09/2026);
        # é material público, a checagem de certificado só impedia a leitura.
        return self.page.request.get(url, timeout=60000, ignore_https_errors=True)

    def pdf(self, url, titulo):
        resp = self._baixar(url)
        if not resp.ok:
            return {"status": "falhou", "erro": f"HTTP {resp.status}"}
        return self._ler_pdf(resp.body(), url, titulo)

    def externo(self, url, titulo):
        """Link para fora do AVA: lê se for PDF (inclusive artigo de revista
        OJS), senão fica "não lido" e aparece na cobertura."""
        m = OJS_RE.search(url)
        if m:
            # O download de revista OJS é sempre PDF. O servidor da INEP
            # devolveu página comum em vez do PDF de forma intermitente
            # (texto-base da Orlandi, LET110 S6, 23/09/2026): três tentativas,
            # e se nenhuma trouxer PDF é falha a repetir, nunca "não lido".
            baixar = OJS_RE.sub(r"/article/download/\1/\2", url)
            erro = None
            for tentativa in range(3):
                try:
                    resp = self._baixar(baixar)
                    corpo = resp.body() if resp.ok else b""
                    if corpo[:5] == b"%PDF-":
                        return self._ler_pdf(corpo, baixar, titulo)
                    erro = f"HTTP {resp.status}, {resp.headers.get('content-type')}"
                except Exception as e:
                    erro = f"{type(e).__name__}: {e}"
                self.page.wait_for_timeout(3000)
            return {"status": "falhou", "erro": f"revista não entregou o PDF: {erro}"[:200]}
        alvos = [url]
        respondeu, erro = False, None
        for alvo in alvos:
            try:
                resp = self._baixar(alvo)
            except Exception as e:
                erro = e
                continue
            if not resp.ok:
                # Erro do servidor (5xx, 429) é passageiro como queda de rede.
                erro = f"HTTP {resp.status}"
                continue
            respondeu = True
            corpo = resp.body()
            if corpo[:5] == b"%PDF-" or "pdf" in (resp.headers.get("content-type") or ""):
                return self._ler_pdf(corpo, alvo, titulo)
        # Rede que falhou não é "não lido": o texto da Orlandi (LET110 S6)
        # ficou de fora assim em 23/09/2026 e isolado baixava normal. Falha é
        # tentada de novo na rodada seguinte; "não lido" é definitivo.
        if not respondeu:
            return {"status": "falhou", "ext_v": EXT_V,
                    "erro": str(erro)[:200] if isinstance(erro, str) else f"{type(erro).__name__}: {erro}"[:200]}
        return self._pagina_externa(url, titulo)

    def _pagina_externa(self, url, titulo):
        """Página HTML de fora do AVA (REA da Univesp, blog da OBMEP, matéria
        de jornal). Até 26/10/2026 ficava "não lido" sem tentativa; atividade
        interativa (GeoGebra, Khan Academy) continua "não lido", com o motivo."""
        if any(x in url.lower() for x in INTERATIVO):
            return {"status": "nao_lido", "ext_v": EXT_V, "erro": "atividade interativa: fazer no navegador"}
        try:
            self.page.goto(url, timeout=45000, wait_until="domcontentloaded")
            self.page.wait_for_timeout(3000)
            # Pelo HTML, não pelo innerText: o REA da Univesp guarda o conteúdo
            # em abas e janelas escondidas, e o innerText só via a capa.
            bruto = self.page.evaluate(
                "() => { document.querySelectorAll('[id*=cookie i], [class*=cookie i], [id*=consent i],"
                " [class*=consent i], #onetrust-banner-sdk, header nav, footer').forEach(e => e.remove());"
                " const m = document.querySelector('article, main, [role=main], .entry-content, #content');"
                " return (m && m.textContent.length > 800 ? m : document.body).outerHTML; }")
        except Exception as e:
            return {"status": "falhou", "ext_v": EXT_V, "erro": f"{type(e).__name__}: {e}"[:200]}
        texto = html_para_texto(bruto)
        if len(texto) < 3 * EXT_MIN_CHARS:
            # O REA da Univesp mostra a capa e põe o conteúdo num PDF ("Salvar
            # resumo das estratégias", no Google Drive). Página curta com PDF
            # vale pelo PDF.
            for href in re.findall(r'href="([^"]+)"', bruto):
                drive = re.search(r"drive\.google\.com/file/d/([\w-]+)", href)
                alvo = f"https://drive.google.com/uc?export=download&id={drive.group(1)}" if drive else (
                    href if href.lower().split("?")[0].endswith(".pdf") else None)
                if not alvo:
                    continue
                try:
                    resp = self._baixar(alvo)
                    if resp.ok and resp.body()[:5] == b"%PDF-":
                        res = self._ler_pdf(resp.body(), alvo, f"{titulo} (PDF da página)")
                        if res["status"] == "lido":
                            return {**res, "ext_v": EXT_V}
                except Exception:
                    continue
        if len(texto) < EXT_MIN_CHARS:
            return {"status": "nao_lido", "ext_v": EXT_V,
                    "erro": f"página interativa ou curta ({len(texto)} caracteres): abrir no navegador"}
        nome = f"web-{slug(titulo, 40)}-{hashlib.sha256(url.encode()).hexdigest()[:8]}.txt"
        arquivo, chars, sha256 = self._gravar(nome, f"# {titulo}\nFonte: {url}\n\n{texto}")
        return {"status": "lido", "arquivo": arquivo, "chars": chars, "sha256": sha256, "ext_v": EXT_V}

    def _ler_pdf(self, corpo, url, titulo):
        # 23/09/2026: slides e textos-base distintos podem ter o mesmo nome
        # de arquivo. A URL na chave evita que um sobrescreva a fonte do outro.
        nome = f"{slug(Path(url.split('?')[0]).stem)}-{hashlib.sha256(url.encode()).hexdigest()[:10]}"
        destino = self.fontes_dir / f"{nome}.pdf"
        destino.write_bytes(corpo)
        # PyMuPDF 2 mantém o módulo legado ``fitz`` só por compatibilidade.
        # Usar o nome atual evita aviso a cada rodada e prepara a remoção dele.
        import pymupdf as fitz
        with fitz.open(destino) as doc:
            paginas = [(p.get_label() or str(i + 1), p.get_text()) for i, p in enumerate(doc)]
        if not any(t.strip() for _, t in paginas):
            # 23/09/2026: PDF sem camada de texto não foi lido de verdade.
            return {"status": "nao_lido", "erro": "PDF sem texto extraível; ler por conta própria"}
        # Marca de página: o AVA manda ler "as páginas 37-62" de um PDF de 169
        # mil caracteres (MMB002 S1 e S3); sem marca, não dá para achar o trecho.
        texto = "\n".join(f"[pág. {r}]\n{t}" for r, t in paginas)
        trecho = intervalo_paginas(titulo)
        aviso = (f"O AVA manda ler as páginas {trecho[0]} a {trecho[1]} (numeração impressa; "
                 f"a marca [pág. N] é a do arquivo).\n") if trecho else ""
        arquivo, chars, sha256 = self._gravar(f"{nome}.pdf.txt", f"# {titulo}\nFonte: {url}\n{aviso}\n{texto}")
        return {"status": "lido", "arquivo": arquivo, "chars": chars, "sha256": sha256, "pdf_v": PDF_V}

    def video(self, vid, titulo):
        """Legenda da videoaula. 26/10/2026: as videoaulas da Univesp têm
        legenda pt-BR revisada (nome de autor certo, pontuação), e o coletor só
        pedia a automática, que escreveu "períodos" no lugar de "periódicos".
        A automática fica para vídeo de fora (OBMEP, Khan Academy)."""
        sem_manual = False
        for origem, flag, idiomas in (("univesp", "--write-subs", "pt-BR,pt"),
                                      ("automatica", "--write-auto-subs", "pt")):
            with tempfile.TemporaryDirectory() as tmp:
                proc = subprocess.run(
                    [sys.executable, "-m", "yt_dlp", "--skip-download", flag,
                     "--sub-langs", idiomas, "--sub-format", "vtt", "-q", "--no-warnings",
                     "-o", str(Path(tmp) / "v.%(ext)s"), f"https://www.youtube.com/watch?v={vid}"],
                    capture_output=True, timeout=180,
                )
                if proc.returncode != 0:
                    # 23/09/2026: erro de rede/login não equivale a vídeo sem legenda.
                    erro = (proc.stderr or b"erro do yt-dlp")[-200:].decode("utf-8", errors="replace")
                    return {"status": "falhou", "erro": erro, **({"sem_manual": True} if sem_manual else {})}
                vtts = sorted(Path(tmp).glob("*.vtt"), key=lambda p: ".pt-BR." not in p.name)
                if vtts:
                    texto = limpar_vtt(vtts[0].read_text(encoding="utf-8", errors="replace"))
                    break
            sem_manual = True
        else:
            # Vídeo curto de abertura costuma não ter legenda. Não é falha
            # a repetir toda segunda: fica registrado e a semana fecha.
            return {"status": "sem_legenda"}
        nota = ("legenda revisada publicada pela Univesp" if origem == "univesp"
                else "legenda automática: nome próprio pode vir errado")
        arquivo, chars, sha256 = self._gravar(
            f"video-{vid}.txt", f"# {titulo}\nFonte: https://youtu.be/{vid} ({nota})\n\n{texto}")
        return {"status": "lido", "arquivo": arquivo, "chars": chars, "sha256": sha256, "legenda": origem}

    # ----------------------------------------------------------- livros (LTI)

    def leitor(self, url, titulo):
        """Texto-base atrás do LTI (leitor de livro que o AVA abre).

        O leitor mora em privado/automacao/leitor_livros.py, fora do git:
        decisão de 26/10/2026, porque este repositório é público. Sem ele, o
        texto-base fica "não lido", como era até então, e é tentado de novo
        quando o arquivo aparecer (sem marca de versão)."""
        try:
            import leitor_livros
        except ImportError:
            return {"status": "nao_lido", "erro": "leitor de livros não instalado nesta máquina: ler no AVA"}
        return leitor_livros.ler(self, url, titulo, sys.modules[__name__])

    def quiz(self, item, inicio, hoje):
        info = self._abrir(item["url"])
        revisoes = sorted({h for _, h in info["links"] if "/mod/quiz/review.php" in h})
        if not revisoes:
            # Tentativa feita sem link de revisão: o questionário esconde a
            # revisão (COM100 S1, conferido em 23/09/2026: "Feito: Fazer
            # tentativas: 1", nota 10, nenhum link). Pode abrir depois do
            # fechamento, então só desiste no mesmo prazo do "sem tentativa".
            texto = (info.get("texto") or "").lower()
            tentou = "feito: fazer tentativas" in texto or "resumo das suas tentativas" in texto
            if hoje > inicio + timedelta(days=DIAS_ATE_DESISTIR_DO_QUIZ):
                return {"status": "revisao_fechada" if tentou else "sem_tentativa"}
            return {"status": "pendente"}
        tentativas = []
        for n, url in enumerate(revisoes, 1):
            self.page.goto(url, timeout=60000)
            self.page.wait_for_timeout(1500)
            questoes = self.page.evaluate(JS_QUESTOES)
            if not questoes:
                # 23/09/2026: mudança no seletor .que não pode fechar o quiz.
                return {"status": "falhou", "erro": f"revisão da tentativa {n} sem questões"}
            tentativas.append(com_formulas_em(questoes))
        nome = f"quiz-{item['cmid']}"
        (self.fontes_dir / f"{nome}.json").write_text(json.dumps(
            {"titulo": item["label"], "url": item["url"], "tentativas": tentativas},
            ensure_ascii=False, indent=1), encoding="utf-8")
        arquivo, chars, sha256 = self._gravar(f"{nome}.txt", quiz_texto(item, tentativas))
        return {"status": "lido", "arquivo": arquivo, "chars": chars, "sha256": sha256, "formato": QUIZ_V,
                "gabarito_oficial": all(q.get("correta") for t in tentativas for q in t)}

    def pagina(self, item):
        """Lê a página e devolve (resultado, fontes derivadas: vídeos, PDFs, leitores)."""
        info = self._abrir(item["url"])
        texto = texto_util(info["texto"])
        if not texto:
            return {"status": "falhou", "erro": "página sem texto; verificar layout ou sessão"}, []
        arquivo, chars, sha256 = self._gravar(
            f"pagina-{item['cmid']}.txt", f"# {item['label']}\nFonte: {item['url']}\n\n{texto}")
        derivadas = []
        # Vídeo só pelo iframe: os links "Audiodescrição" e "Vídeo sem Libras"
        # são a mesma aula em outra versão, e transcrever as três triplica o texto.
        for src in info["iframes"]:
            m = YOUTUBE_RE.search(src)
            if m:
                derivadas.append(("youtube", m.group(1), f"{item['label']} (vídeo {m.group(1)})"))
        for rotulo, href in info["links"]:
            # Link para outra atividade do AVA (inclusive o rodapé "Página
            # anterior") é navegação, não material; o portal de login da
            # Pearson é porta de entrada, o livro vem no link seguinte.
            if ("ava.univesp.br" in href and ".pdf" not in href.lower()) or "simplesaml" in href:
                continue
            tipo = classificar_link(href)
            if tipo in ("pdf", "leitor", "externo"):
                nome = Path(href.split("?")[0]).name
                derivadas.append((tipo, href, rotulo or f"Slides {nome}" if tipo == "pdf" else rotulo or item["label"]))
        return {"status": "lido", "arquivo": arquivo, "chars": chars, "sha256": sha256}, derivadas

    def alvo_de_url(self, item):
        """O link externo que um item "url" do Moodle abre."""
        info = self._abrir(item["url"])
        for _, href in info["links"]:
            tipo = classificar_link(href)
            if tipo and "ava.univesp.br" not in href:
                return tipo, href
        return None, None


def coletar_semana(coletor, curso, n, inicio, secao, manifest, hoje):
    """Atualiza o manifest da semana; só retenta o que não está lido."""
    anteriores = {f["chave"]: f for f in manifest.get("fontes", [])}
    novas, vistos = [], set()

    puladas = set()  # páginas já lidas que não foram reabertas

    def registrar(chave, tipo, titulo, url, fazer, origem=None):
        if chave in vistos:
            return
        vistos.add(chave)
        velho = anteriores.get(chave)
        if velho and velho["status"] in ("lido", "nao_lido", "sem_tentativa", "sem_legenda",
                                         "revisao_fechada", "encaminhado") \
                and not precisa_reler(velho, inicio, hoje):
            novas.append(velho)
            puladas.add(chave)
            return
        base = {"chave": chave, "tipo": tipo, "titulo": " ".join(titulo.split()), "url": url}
        if origem:
            base["origem"] = origem
        try:
            base.update(fazer())
        except Exception as erro:  # uma fonte ruim não derruba a semana
            base.update({"status": "falhou", "erro": f"{type(erro).__name__}: {erro}"[:200]})
        if velho and velho["status"] == "lido" and base["status"] != "lido":
            # Releitura de melhoria que não deu certo (YouTube com 429, AVA
            # fora do ar) não pode apagar o que já estava lido. Vídeo sem
            # legenda revisada fica marcado para não tentar toda rodada.
            mantido = dict(velho)
            if base.get("sem_manual"):
                mantido["legenda"] = "automatica"
            for marca in ("ext_v", "pdf_v"):
                if marca in base and base["status"] != "falhou":
                    mantido[marca] = base[marca]
            novas.append(mantido)
            return
        novas.append(aplicar_tentativas(base, velho))

    def derivar(tipo, alvo, titulo, origem):
        if tipo == "youtube":
            registrar(f"yt:{alvo}", "videoaula", titulo, f"https://youtu.be/{alvo}",
                      lambda: coletor.video(alvo, titulo), origem)
        elif tipo == "pdf":
            registrar(f"pdf:{alvo}", "pdf", titulo, alvo, lambda: coletor.pdf(alvo, titulo), origem)
        elif tipo == "leitor":
            registrar(f"leitor:{alvo}", "leitor externo", titulo, alvo, lambda: coletor.leitor(alvo, titulo), origem)
        elif tipo == "externo":
            registrar(f"ext:{alvo}", "link externo", titulo, alvo, lambda: coletor.externo(alvo, titulo), origem)

    for item in secao.get("items") or []:
        tipo, rotulo, url = item.get("type"), item.get("label") or "", item.get("url")
        if not url:
            continue
        chave = f"cm:{item.get('cmid')}"
        if tipo == "page":
            derivadas = []

            def ler_pagina(item=item):
                resultado, deriv = coletor.pagina(item)
                derivadas.extend(deriv)
                return resultado
            registrar(chave, "página", rotulo, url, ler_pagina)
            for d in derivadas:
                derivar(*d, chave)
        elif tipo == "url":
            # O item "url" é só um ponteiro: o conteúdo vem do alvo, que vira
            # fonte própria. Leitor externo e site qualquer ficam "não lido".
            def ler_link(item=item):
                alvo_tipo, alvo = coletor.alvo_de_url(item)
                # Ponteiro para pdf, vídeo ou site: o conteúdo (e a situação
                # real) fica na fonte derivada, na linha seguinte da cobertura.
                encaminha = alvo_tipo in ("pdf", "youtube", "externo")
                return {"status": "encaminhado" if encaminha else "nao_lido", "alvo": alvo, "alvo_tipo": alvo_tipo}
            registrar(chave, "link", rotulo, url, ler_link)
            reg = next((f for f in novas if f["chave"] == chave), {})
            if reg.get("alvo_tipo") == "youtube":
                derivar("youtube", YOUTUBE_RE.search(reg["alvo"]).group(1), rotulo, chave)
            elif reg.get("alvo_tipo") in ("pdf", "externo"):
                derivar(reg["alvo_tipo"], reg["alvo"], rotulo, chave)
        elif tipo == "quiz":
            registrar(chave, "questionário", rotulo, url, lambda item=item: coletor.quiz(item, inicio, hoje))
        elif tipo == "lti" and "live" not in rotulo.lower():
            registrar(chave, "leitor externo", rotulo, url,
                      lambda item=item: coletor.leitor(item["url"], item.get("label") or ""))
        # fórum fica de fora de propósito: tem nome e texto de colega.

    # Fonte derivada de página já lida não é redescoberta (a página não é
    # reaberta), então ela é mantida daqui. Derivada de página que foi relida
    # e não apareceu mais cai fora: era sujeira ou o AVA tirou.
    refazer = {"videoaula": "youtube", "pdf": "pdf", "leitor externo": "leitor", "link externo": "externo"}
    for chave, antiga in anteriores.items():
        if chave in vistos or antiga.get("origem") not in puladas:
            continue
        if antiga.get("tipo") == "link externo" and not classificar_link(antiga.get("url")):
            continue  # crédito de imagem que entrou antes do filtro (Adobe Stock, MMB002 S1)
        # 26/10/2026: derivada que tinha falhado era copiada daqui sem nova
        # tentativa (o vídeo com HTTP 429 de INT100 S2 ficou em "tentativas 1"
        # por duas semanas) e a semana nunca fechava. Falha volta a ser tentada.
        if (antiga.get("status") == "falhou" or precisa_reler(antiga, inicio, hoje)) \
                and antiga.get("tipo") in refazer:
            alvo = chave[3:] if antiga["tipo"] == "videoaula" else antiga["url"]
            derivar(refazer[antiga["tipo"]], alvo, antiga["titulo"], antiga["origem"])
        else:
            novas.append(antiga)

    manifest.update({
        "disciplina": curso["code"],
        "semana": n,
        "inicio": inicio.isoformat(),
        "coletado_em": datetime.now().isoformat(timespec="minutes"),
        "inventario": inventario(secao),
        "fontes": novas,
    })
    manifest["fechada"] = not any(f["status"] in ("pendente", "falhou") for f in novas)
    return manifest


# --------------------------------------------------------------- montagem

def montar_com_claude(pasta, manifest):
    """Pede ao Claude a REVISAO.md da semana. Devolve (ok, mensagem)."""
    instrucoes = PROMPT.read_text(encoding="utf-8").format(
        disciplina=manifest["disciplina"], semana=manifest["semana"])
    ok, msg = chamar_claude(pasta, instrucoes, "REVISAO.md")
    return ok, ("revisão montada" if ok else msg)


def montar_ficha(pasta, manifest):
    """Ficha curta da semana para a apostila (apostila.json), destilada da
    REVISAO.md. Recebe o que as semanas anteriores já definiram, para não
    repetir. Ficha que não passa na validação conta como não montada."""
    import apostila
    instrucoes = PROMPT_FICHA.read_text(encoding="utf-8").format(
        disciplina=manifest["disciplina"], semana=manifest["semana"],
        ja_vistos=apostila.ja_vistos(pasta.parent, manifest["semana"]))
    ok, msg = chamar_claude(pasta, instrucoes, "apostila.json")
    if not ok:
        return False, msg
    try:
        apostila.validar(json.loads((pasta / "apostila.json").read_text(encoding="utf-8")))
    except (ValueError, apostila.FichaInvalida) as erro:
        return False, f"ficha da apostila inválida: {erro}"
    return True, "ficha da apostila montada"


def chamar_claude(pasta, instrucoes, nome_alvo, tentativas=2):
    """Roda o Claude sem janela na pasta da semana. Ok = ele gravou o alvo.

    Em 22 e 23/09/2026, em lotes de várias semanas seguidas, algumas chamadas
    falharam e a mesma semana, rodada de novo minutos depois, saiu normal.
    Por isso uma segunda tentativa depois de 2 minutos."""
    import time
    global LIMITE_ATINGIDO
    if LIMITE_ATINGIDO:
        return False, "limite de uso do plano do Claude atingido nesta rodada"
    for vez in range(tentativas):
        ok, msg = _chamar_claude_uma_vez(pasta, instrucoes, nome_alvo)
        # Limite de uso do plano ("You've hit your session limit · resets
        # 5pm", 23/09/2026) não volta em minutos: era ele por trás das falhas
        # "intermitentes" dos lotes. Para a rodada inteira de chamar o Claude;
        # a guarda do rodar_diario.ps1 repete em 3 h.
        if not ok and "limit" in msg.lower():
            LIMITE_ATINGIDO = True
            return False, "limite de uso do plano do Claude atingido: " + msg.split(": ", 1)[-1][:120]
        if ok or vez == tentativas - 1:
            return ok, msg
        print(f"   {nome_alvo}: {msg}; tento de novo em 2 min")
        time.sleep(120)


def _chamar_claude_uma_vez(pasta, instrucoes, nome_alvo):
    alvo = pasta / nome_alvo
    antes = alvo.stat().st_mtime_ns if alvo.exists() else 0
    # As instruções vão pela entrada padrão: texto de várias linhas não
    # sobrevive à linha de comando do Windows. As ferramentas ficam restritas
    # a ler e escrever arquivo, e a pasta da semana é a única liberada.
    try:
        proc = subprocess.run(
            ["claude", "-p",
             "--allowedTools", "Read,Write,Edit,Glob,Grep",
             "--permission-mode", "acceptEdits",
             "--add-dir", str(pasta)],
            input=instrucoes, cwd=str(pasta), capture_output=True, text=True,
            encoding="utf-8", timeout=TEMPO_CLAUDE_S,
        )
    except FileNotFoundError:
        return False, "comando claude não encontrado"
    except subprocess.TimeoutExpired:
        return False, f"Claude passou de {TEMPO_CLAUDE_S // 60} min"
    if proc.returncode == 0 and alvo.exists() and alvo.stat().st_size and alvo.stat().st_mtime_ns > antes:
        return True, "ok"
    return False, f"Claude não escreveu {nome_alvo} (código {proc.returncode}): {(proc.stdout or proc.stderr)[-300:]}"


def hash_arquivo(caminho):
    return hashlib.sha1(caminho.read_bytes()).hexdigest() if caminho.exists() else None


def refazer_corpo(pasta_disciplina, codigo):
    semanas = sorted(pasta_disciplina.glob("semana-*/REVISAO.md"))
    partes = [
        f"# Corpo de revisão: {codigo}",
        "",
        "Montado semana a semana pela revisão semanal (automacao/revisao_semanal.py).",
        "Cada semana tem a própria pasta com as fontes lidas e a COBERTURA.md.",
        "",
    ]
    for r in semanas:
        partes += [f"\n\n<!-- {r.parent.name} -->\n", r.read_text(encoding="utf-8")]
    (pasta_disciplina / "CORPO_REVISAO.md").write_text("\n".join(partes), encoding="utf-8")


# --------------------------------------------------------------- principal

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hoje", type=date.fromisoformat, default=None)
    ap.add_argument("--desde", type=date.fromisoformat, default=INICIO_PADRAO)
    ap.add_argument("--disciplina")
    ap.add_argument("--semana", type=int)
    ap.add_argument("--sem-montar", action="store_true")
    args = ap.parse_args()
    hoje = args.hoje or hoje_br()

    if not PRIVADO.exists():
        print("privado/ não existe: rode automacao\\configurar_local.ps1 (Google Drive montado?)")
        return 3
    manual = bool(args.semana or args.disciplina or args.hoje)
    if not manual:
        eu, dona = maquina_responsavel(MAQUINA, platform.node())
        if not eu:
            print(f"a revisão semanal é feita por {dona} (privado/estudo/MAQUINA_DA_REVISAO.txt)")
            return 0
    if not DATA.exists():
        print("docs/data.json não existe: a rodada diária ainda não gerou o retrato do AVA")
        return 3
    dados = json.loads(DATA.read_text(encoding="utf-8"))
    if not args.hoje and not retrato_em_dia(dados, hoje):
        # 23/09/2026: no logon após suspensão, a revisão pode ganhar a trava
        # antes da rodada diária e ler uma lista de semanas desatualizada.
        # O código próprio faz o rodar_diario.ps1 esperar em silêncio, sem
        # marcar a semana como feita e sem avisar "problema".
        print("docs/data.json ainda não foi atualizado hoje; aguardo a rodada diária")
        return AGUARDA_RETRATO

    alvos = []
    for curso in dados.get("courses") or []:
        if args.disciplina and curso.get("code") != args.disciplina.upper():
            continue
        bim = bimestre_de(curso)
        if not bim:
            continue  # sem cronograma semanal (COM170 é por quinzena e não tem prova)
        for n, inicio, secao in semanas_encerradas(curso, hoje, args.desde):
            if args.semana and n != args.semana:
                continue
            pasta = PRIVADO / "estudo" / bim / curso["code"].lower() / f"semana-{n:02d}"
            arq = pasta / "manifest.json"
            manifest = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
            if semana_em_dia(manifest, pasta, secao, hoje) and not args.semana:
                continue
            alvos.append((curso, n, inicio, secao, pasta, manifest))

    resumo = []
    if not alvos:
        print("nenhuma semana nova ou pendente para revisar")
        RESUMO.parent.mkdir(parents=True, exist_ok=True)
        RESUMO.write_text("", encoding="utf-8")
        return 0

    from playwright.sync_api import sync_playwright
    import sessao
    with sync_playwright() as pw:
        navegador = pw.chromium.launch(headless=True)
        contexto = sessao.novo_contexto(navegador)
        page = contexto.new_page()
        ok, como = sessao.garantir(page)
        if not ok:
            print(f"não entrei no AVA: {como}")
            navegador.close()
            return 2
        if como == "login":
            sessao.salvar_sessao(contexto)
        for curso, n, inicio, secao, pasta, manifest in alvos:
            print(f"{curso['code']} semana {n} (início {inicio:%d/%m})")
            manifest = coletar_semana(Coletor(page, pasta), curso, n, inicio, secao, manifest, hoje)
            (pasta / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
            (pasta / "COBERTURA.md").write_text(cobertura_md(manifest), encoding="utf-8")
            montar_gabarito(pasta, manifest)
            conta = {}
            for f in manifest["fontes"]:
                conta[f["status"]] = conta.get(f["status"], 0) + 1
            print("   " + ", ".join(f"{v} {k}" for k, v in sorted(conta.items())))
            resumo.append([curso["code"], n, conta, pasta, manifest])
        navegador.close()

    linhas = []
    bimestres_mudados = set()
    for codigo, n, conta, pasta, manifest in resumo:
        situacao = "coletada"
        if not args.sem_montar and conta.get("lido"):
            if (manifest.get("montado_hash") != assinatura(manifest)
                    or not (pasta / "REVISAO.md").is_file()
                    or not (pasta / "REVISAO.md").stat().st_size):
                ok, msg = montar_com_claude(pasta, manifest)
                print(f"   {codigo} S{n}: {msg}")
                if ok:
                    manifest["montado_hash"] = assinatura(manifest)
                    (pasta / "manifest.json").write_text(
                        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
                    refazer_corpo(pasta.parent, codigo)
                    situacao = "revisão montada"
                else:
                    situacao = "revisão NÃO montada"
            else:
                situacao = "revisão já em dia"
            # Ficha da apostila: refeita quando a REVISAO.md muda ou quando
            # não existe ficha válida (inclusive a de semana montada antes
            # de a apostila existir).
            revisao = pasta / "REVISAO.md"
            import apostila
            if revisao.exists() and (manifest.get("ficha_de") != hash_arquivo(revisao)
                                     or apostila.ler_ficha(pasta) is None):
                ok, msg = montar_ficha(pasta, manifest)
                print(f"   {codigo} S{n}: {msg}")
                if ok:
                    manifest["ficha_de"] = hash_arquivo(revisao)
                    (pasta / "manifest.json").write_text(
                        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
                    bimestres_mudados.add(pasta.parent.parent.name)
                else:
                    situacao += ", ficha da apostila NÃO montada"
        extra = []
        if conta.get("pendente"):
            extra.append("questionário pendente")
        if conta.get("nao_lido"):
            extra.append(f"{conta['nao_lido']} não lido(s)")
        if conta.get("falhou"):
            extra.append(f"{conta['falhou']} falha(s)")
        linhas.append(f"{codigo} S{n}: {situacao}" + (f" ({', '.join(extra)})" if extra else ""))

    for bim in sorted(bimestres_mudados):
        import apostila
        try:
            feitos = apostila.gerar(bim)
            linhas.append(f"Apostila {bim} atualizada ({len(feitos) - 1} PDF)")
        except Exception as erro:  # a apostila não derruba a revisão
            linhas.append(f"Apostila {bim} NÃO montada: {type(erro).__name__}: {erro}"[:200])

    RESUMO.parent.mkdir(parents=True, exist_ok=True)
    RESUMO.write_text("\n".join(linhas), encoding="utf-8")
    print("\n".join(linhas))
    # 23/09/2026: a guarda semanal só repete em 3 h se o processo falhar.
    # Fonte com falha não pode marcar a revisão como feita por sete dias.
    return 1 if any("NÃO montada" in l or "falha(s)" in l for l in linhas) else 0


if __name__ == "__main__":
    sys.exit(main())
