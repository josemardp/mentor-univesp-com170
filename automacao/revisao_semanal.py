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
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

PRIVADO = RAIZ / "privado"
DATA = RAIZ / "docs" / "data.json"
LOG_DIR = RAIZ / "tmp" / "log"
RESUMO = LOG_DIR / "revisao_resumo.txt"
PROMPT = Path(__file__).resolve().parent / "revisao_semanal_prompt.md"

# A automação nasceu para o 4º bimestre de 2026. Semanas anteriores só entram
# com --desde, para a primeira rodada não remontar o bimestre inteiro que já
# teve prova.
INICIO_PADRAO = date(2026, 9, 28)
# Questionário sem tentativa depois disto deixa de ser "pendente": a semana
# fecha registrando que não houve tentativa. O AVA fecha os da Univesp cerca
# de 16 dias depois do início da semana (conferido em SOC100 S7, 31/08 a 16/09).
DIAS_ATE_DESISTIR_DO_QUIZ = 21
TEMPO_CLAUDE_S = 25 * 60

SEMANA_RE = re.compile(r"^\s*semana\s+(\d+)\b", re.I)
BIMESTRE_RE = re.compile(r"/(\d{4})/cronograma_\w+?_(\d)\.html")
YOUTUBE_RE = re.compile(r"(?:youtube\.com/embed/|youtu\.be/|youtube\.com/watch\?v=)([\w-]{11})")
LEITOR_EXTERNO = ("login_mb", "bvirtual", "pearson", "minhabiblioteca", "/mod/lti/")


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


def cobertura_md(manifest):
    rotulo = {"lido": "lido", "nao_lido": "NÃO LIDO", "pendente": "pendente",
              "sem_tentativa": "sem tentativa", "falhou": "FALHOU"}
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
        linhas.append(
            f"| {titulo} | {f['tipo']} | {rotulo.get(f['status'], f['status'])} "
            f"| {f.get('arquivo') or ''} |"
        )
    return "\n".join(linhas) + "\n"


def assinatura(manifest):
    # Ordenada: na segunda passada as fontes derivadas de página já lida
    # entram no fim da lista, e a ordem diferente remontava a revisão à toa.
    base = sorted((f["chave"], f["status"], f.get("chars")) for f in manifest["fontes"])
    return hashlib.sha1(json.dumps(base, ensure_ascii=False).encode()).hexdigest()


# --------------------------------------------------------------- leitura AVA

JS_PAGINA = """() => {
  const main = document.querySelector('#region-main') || document.body;
  return {
    texto: main.innerText || '',
    links: [...main.querySelectorAll('a[href]')].map(a => [(a.innerText||'').trim(), a.href]),
    iframes: [...document.querySelectorAll('iframe')].map(f => f.src || ''),
  };
}"""

JS_QUESTOES = """() => [...document.querySelectorAll('.que')].map(q => q.innerText).join('\\n\\n----\\n\\n')"""


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
        return f"fontes/{nome}", len(texto)

    def pdf(self, url, titulo):
        nome = slug(Path(url.split("?")[0]).stem)
        resp = self.page.request.get(url, timeout=60000)
        if not resp.ok:
            return {"status": "falhou", "erro": f"HTTP {resp.status}"}
        destino = self.fontes_dir / f"{nome}.pdf"
        destino.write_bytes(resp.body())
        import fitz
        with fitz.open(destino) as doc:
            texto = "\n".join(p.get_text() for p in doc)
        arquivo, chars = self._gravar(f"{nome}.pdf.txt", f"# {titulo}\nFonte: {url}\n\n{texto}")
        return {"status": "lido", "arquivo": arquivo, "chars": chars}

    def video(self, vid, titulo):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                [sys.executable, "-m", "yt_dlp", "--skip-download", "--write-auto-sub",
                 "--sub-lang", "pt", "--sub-format", "vtt", "-q", "--no-warnings",
                 "-o", str(Path(tmp) / "v.%(ext)s"), f"https://www.youtube.com/watch?v={vid}"],
                capture_output=True, timeout=180,
            )
            vtts = list(Path(tmp).glob("*.vtt"))
            if not vtts:
                return {"status": "falhou", "erro": "sem legenda automática"}
            texto = limpar_vtt(vtts[0].read_text(encoding="utf-8", errors="replace"))
        arquivo, chars = self._gravar(
            f"video-{vid}.txt",
            f"# {titulo}\nFonte: https://youtu.be/{vid} (legenda automática: "
            f"nome próprio pode vir errado)\n\n{texto}")
        return {"status": "lido", "arquivo": arquivo, "chars": chars}

    def quiz(self, item, inicio, hoje):
        info = self._abrir(item["url"])
        revisoes = sorted({h for _, h in info["links"] if "/mod/quiz/review.php" in h})
        if not revisoes:
            if hoje > inicio + timedelta(days=DIAS_ATE_DESISTIR_DO_QUIZ):
                return {"status": "sem_tentativa"}
            return {"status": "pendente"}
        blocos = []
        for n, url in enumerate(revisoes, 1):
            self.page.goto(url, timeout=60000)
            self.page.wait_for_timeout(1500)
            blocos.append(f"## Tentativa {n}\n\n" + self.page.evaluate(JS_QUESTOES))
        arquivo, chars = self._gravar(
            f"quiz-{item['cmid']}.txt",
            f"# {item['label']}\nRevisão de {len(revisoes)} tentativa(s). "
            f"Fonte: {item['url']}\n\n" + "\n\n".join(blocos))
        return {"status": "lido", "arquivo": arquivo, "chars": chars}

    def pagina(self, item):
        """Lê a página e devolve (resultado, fontes derivadas: vídeos, PDFs, leitores)."""
        info = self._abrir(item["url"])
        texto = texto_util(info["texto"])
        arquivo, chars = self._gravar(
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
            if tipo in ("pdf", "leitor"):
                nome = Path(href.split("?")[0]).name
                derivadas.append((tipo, href, rotulo or f"Slides {nome}" if tipo == "pdf" else rotulo or item["label"]))
        return {"status": "lido", "arquivo": arquivo, "chars": chars}, derivadas

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
        if velho and velho["status"] in ("lido", "nao_lido", "sem_tentativa"):
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
        novas.append(base)

    def derivar(tipo, alvo, titulo, origem):
        if tipo == "youtube":
            registrar(f"yt:{alvo}", "videoaula", titulo, f"https://youtu.be/{alvo}",
                      lambda: coletor.video(alvo, titulo), origem)
        elif tipo == "pdf":
            registrar(f"pdf:{alvo}", "pdf", titulo, alvo, lambda: coletor.pdf(alvo, titulo), origem)
        elif tipo == "leitor":
            registrar(f"leitor:{alvo}", "leitor externo", titulo, alvo, lambda: {"status": "nao_lido"}, origem)

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
                lido = alvo_tipo in ("pdf", "youtube")
                return {"status": "lido" if lido else "nao_lido", "alvo": alvo, "alvo_tipo": alvo_tipo}
            registrar(chave, "link", rotulo, url, ler_link)
            reg = next((f for f in novas if f["chave"] == chave), {})
            if reg.get("alvo_tipo") == "youtube":
                derivar("youtube", YOUTUBE_RE.search(reg["alvo"]).group(1), rotulo, chave)
            elif reg.get("alvo_tipo") == "pdf":
                derivar("pdf", reg["alvo"], rotulo, chave)
        elif tipo == "quiz":
            registrar(chave, "questionário", rotulo, url, lambda item=item: coletor.quiz(item, inicio, hoje))
        elif tipo == "lti" and "live" not in rotulo.lower():
            registrar(chave, "leitor externo", rotulo, url, lambda: {"status": "nao_lido"})
        # fórum fica de fora de propósito: tem nome e texto de colega.

    # Fonte derivada de página já lida não é redescoberta (a página não é
    # reaberta), então ela é mantida daqui. Derivada de página que foi relida
    # e não apareceu mais cai fora: era sujeira ou o AVA tirou.
    for chave, antiga in anteriores.items():
        if chave not in vistos and antiga.get("origem") in puladas:
            novas.append(antiga)

    manifest.update({
        "disciplina": curso["code"],
        "semana": n,
        "inicio": inicio.isoformat(),
        "coletado_em": datetime.now().isoformat(timespec="minutes"),
        "fontes": novas,
    })
    manifest["fechada"] = not any(f["status"] in ("pendente", "falhou") for f in novas)
    return manifest


# --------------------------------------------------------------- montagem

def montar_com_claude(pasta, manifest):
    """Pede ao Claude a REVISAO.md da semana. Devolve (ok, mensagem)."""
    instrucoes = PROMPT.read_text(encoding="utf-8").format(
        disciplina=manifest["disciplina"], semana=manifest["semana"])
    alvo = pasta / "REVISAO.md"
    antes = alvo.stat().st_mtime if alvo.exists() else 0
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
    if alvo.exists() and alvo.stat().st_mtime > antes:
        return True, "revisão montada"
    return False, f"Claude não escreveu a REVISAO.md (código {proc.returncode}): {(proc.stdout or proc.stderr)[-300:]}"


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
    if not DATA.exists():
        print("docs/data.json não existe: a rodada diária ainda não gerou o retrato do AVA")
        return 3
    dados = json.loads(DATA.read_text(encoding="utf-8"))

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
            if manifest.get("fechada") and manifest.get("montado_hash") == assinatura(manifest) \
                    and not args.semana:
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
            conta = {}
            for f in manifest["fontes"]:
                conta[f["status"]] = conta.get(f["status"], 0) + 1
            print("   " + ", ".join(f"{v} {k}" for k, v in sorted(conta.items())))
            resumo.append([curso["code"], n, conta, pasta, manifest])
        navegador.close()

    linhas = []
    for codigo, n, conta, pasta, manifest in resumo:
        situacao = "coletada"
        if not args.sem_montar and conta.get("lido"):
            if manifest.get("montado_hash") != assinatura(manifest):
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
        extra = []
        if conta.get("pendente"):
            extra.append("questionário pendente")
        if conta.get("nao_lido"):
            extra.append(f"{conta['nao_lido']} não lido(s)")
        if conta.get("falhou"):
            extra.append(f"{conta['falhou']} falha(s)")
        linhas.append(f"{codigo} S{n}: {situacao}" + (f" ({', '.join(extra)})" if extra else ""))

    RESUMO.parent.mkdir(parents=True, exist_ok=True)
    RESUMO.write_text("\n".join(linhas), encoding="utf-8")
    print("\n".join(linhas))
    return 1 if any("NÃO montada" in l for l in linhas) else 0


if __name__ == "__main__":
    sys.exit(main())
