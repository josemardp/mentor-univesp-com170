# -*- coding: utf-8 -*-
"""
Revisão semanal (automacao/revisao_semanal.py), criada em 22/09/2026 para a
revisão de prova não ficar toda para a véspera.

O que este teste protege, em ordem de importância:

1. **Só semana encerrada entra.** Semana em andamento revisada pela metade
   vira falsa sensação de cobertura.
2. **Vídeo não é transcrito três vezes.** A página de videoaulas tem a mesma
   aula em iframe, "Audiodescrição" e "Vídeo sem Libras"; só o iframe conta.
3. **Navegação não vira fonte.** O rodapé "Página anterior" aponta para outra
   atividade do AVA e entrava na cobertura como "leitor externo não lido".
4. **Legenda automática sem repetição.** Ela repete cada frase em duas ou três
   deixas, e sem limpar o texto triplica.
5. **Tabela de cobertura não quebra** com o "| Autor" dos títulos de texto-base.
6. **Gabarito só do AVA** (auditoria de 26/10/2026): a coleta guarda a
   alternativa marcada, a resposta oficial e o comentário, e o gabarito sai
   sem IA. Antes a revisão "deduzia" a marcada e escrevia como fato.
7. **Fonte melhor não rebaixa a lida, falha volta a ser tentada**: o vídeo
   com HTTP 429 vindo de página já lida ficava parado em "tentativas 1".

Rodar:  python testes/test_revisao_semanal.py
"""
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

import revisao_semanal as R  # noqa: E402

falhas = []


def checa(cond, msg):
    print(("  ok    " if cond else "  FALHA") + " | " + msg)
    if not cond:
        falhas.append(msg)


CURSO = {
    "code": "SOC100",
    "cronograma": {
        "fonte": "https://assets.univesp.br/cronograma/2026/cronograma_regular_4.html",
        "semanas": [
            {"n": 1, "inicio": "2026-09-28"},
            {"n": 2, "inicio": "2026-10-05"},
            {"n": 3, "inicio": "2026-10-12"},
        ],
    },
    "sections": [
        {"title": "Geral", "items": []},
        {"title": "Semana 1", "items": []},
        {"title": "Semana 2", "items": []},
        {"title": "Semana 3", "items": []},
        {"title": "Revisão e Orientações", "items": []},
    ],
}

# ---------------------------------------------------------------------------
print("\n== quais semanas entram ==")
nums = lambda hoje, desde=date(2026, 9, 28): [n for n, _, _ in R.semanas_encerradas(CURSO, hoje, desde)]
checa(nums(date(2026, 9, 28)) == [], "na segunda em que a semana 1 começa, nada")
checa(nums(date(2026, 10, 5)) == [1], "na segunda seguinte, só a semana 1")
checa(nums(date(2026, 10, 11)) == [1], "domingo ainda não fecha a semana 2")
checa(nums(date(2026, 10, 19)) == [1, 2, 3], "atrasado, pega todas as encerradas")
checa(nums(date(2026, 10, 19), desde=date(2026, 10, 5)) == [2, 3], "--desde corta as anteriores")
checa(R.bimestre_de(CURSO) == "2026-4bim", "bimestre sai do nome do cronograma")
checa(R.bimestre_de({"code": "COM170", "cronograma": None}) is None,
      "sem cronograma semanal (COM170 quinzenal) fica de fora")
checa(R.retrato_em_dia({"checked_at": "2026-10-05T13:00:00+00:00"}, date(2026, 10, 5)),
      "retrato do mesmo dia libera a revisão")
checa(not R.retrato_em_dia({"checked_at": "2026-10-04T13:00:00+00:00"}, date(2026, 10, 5)),
      "retrato antigo não marca semana como feita")
rotina = (ROOT / "automacao" / "rodar_diario.ps1").read_text(encoding="utf-8")
trecho = rotina.split("$resumoArq = Join-Path $logDir 'revisao_resumo.txt'", 1)[1]
checa(trecho.index("Remove-Item -LiteralPath $resumoArq") < trecho.index("Invoca 'revisao_semanal'"),
      "falha inicial da rodada não reenvia resumo antigo")

# ---------------------------------------------------------------------------
print("\n== classificação de link ==")
checa(R.classificar_link("https://assets.univesp.br/disciplinas/SOC100/pdf/s7_videoaula13.pdf") == "pdf", "slide é pdf")
checa(R.classificar_link("https://www.youtube.com/embed/opUF3DG6TQ8?enablejsapi=1") == "youtube", "iframe do YouTube")
checa(R.classificar_link("https://acesso.univesp.br/login_mb?bookUrl=9788595029576&pageid=212") == "leitor",
      "Minha Biblioteca é leitor externo")
checa(R.classificar_link("https://plataforma.bvirtual.com.br/Leitor/Publicacao/1420/pdf/274") == "leitor",
      "Biblioteca Virtual é leitor, mesmo com 'pdf' no caminho")
checa(R.classificar_link("https://assets.univesp.br/videoaulas/download.php?disciplina=soc100&video=a.mp4") is None,
      "download do mp4 é ignorado")
checa(R.classificar_link("javascript:void(0);") is None, "javascript é ignorado")
checa(R.classificar_link("https://br.freepik.com/fotos-gratis/enfermeira.htm") is None,
      "crédito de imagem não vira fonte")
checa(R.classificar_link("https://seer.ufrgs.br/organon/article/view/81461/48749") == "externo",
      "artigo de revista é link externo (tentado como PDF)")
checa(R.OJS_RE.sub(r"/article/download/\1/\2", "https://seer.ufrgs.br/organon/article/view/81461/48749")
      == "https://seer.ufrgs.br/organon/article/download/81461/48749", "OJS: view vira download")

# ---------------------------------------------------------------------------
print("\n== página: vídeo só pelo iframe, navegação fora ==")


class PaginaFalsa:
    def __init__(self, info):
        self.info = info

    def goto(self, *a, **k):
        pass

    def wait_for_timeout(self, *a):
        pass

    def evaluate(self, js):
        return self.info


import tempfile  # noqa: E402
import json  # noqa: E402
from unittest.mock import patch  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    info = {
        "texto": "Condições de conclusão\n Concluído\nVideoaula 13\nSlides de Apoio\nPágina anterior\nS7 - Texto-base",
        "links": [
            ["Audiodescrição", "https://youtu.be/-Gy8ozNIh2o"],
            ["Vídeo sem Libras", "https://www.youtube.com/embed/h3DFle6I8IU"],
            ["Slides de Apoio", "https://assets.univesp.br/disciplinas/SOC100/pdf/s7_videoaula13.pdf"],
            ["", "https://assets.univesp.br/disciplinas/SOC100/pdf/s7_videoaula14.pdf"],
            ["Página anterior\nS7 - Texto-base", "https://ava.univesp.br/mod/lti/view.php?id=168851"],
            ["Pearson", "https://login.univesp.br/simplesaml/module.php/core/pearson.php"],
        ],
        "iframes": ["https://www.youtube.com/embed/opUF3DG6TQ8?enablejsapi=1",
                    "https://ava.univesp.br/mod/lti/view.php?id=222094"],
    }
    col = R.Coletor(PaginaFalsa(info), Path(tmp))
    res, deriv = col.pagina({"cmid": "1", "label": "S7 - Videoaulas", "url": "u"})
    videos = [d for d in deriv if d[0] == "youtube"]
    checa([v[1] for v in videos] == ["opUF3DG6TQ8"], "um vídeo só, o do iframe")
    checa(sum(1 for d in deriv if d[0] == "pdf") == 2, "os dois slides entram")
    checa(not any(d[0] == "leitor" for d in deriv), "rodapé do AVA e portal da Pearson não viram fonte")
    checa(any(d[2] == "Slides s7_videoaula14.pdf" for d in deriv), "slide sem texto no link ganha nome do arquivo")
    texto = (Path(tmp) / res["arquivo"]).read_text(encoding="utf-8")
    checa("Página anterior" not in texto and "Condições de conclusão" not in texto,
          "texto da página sem rodapé de navegação nem caixa de conclusão")

# ---------------------------------------------------------------------------
print("\n== legenda e cobertura ==")
vtt = """WEBVTT
Kind: captions
Language: pt

00:00:01.000 --> 00:00:03.000
olá<00:00:01.500><c> pessoal</c>

00:00:03.000 --> 00:00:04.000
olá pessoal

00:00:04.000 --> 00:00:06.000
hoje falamos de ética
"""
checa(R.limpar_vtt(vtt) == "olá pessoal hoje falamos de ética", "legenda sem tag, sem tempo e sem repetição")

manifest = {
    "disciplina": "SOC100", "semana": 7, "inicio": "2026-08-31", "coletado_em": "x",
    "fontes": [{"chave": "cm:1", "titulo": "S7 - Texto-base | Sílvio Gallo", "tipo": "leitor externo",
                "status": "nao_lido"}],
}
linha = [l for l in R.cobertura_md(manifest).splitlines() if "Gallo" in l][0]
checa(linha.count("|") == 5, "título com '|' não abre coluna a mais")
checa("NÃO LIDO" in linha, "não lido aparece em destaque")
manifest["fontes"].append({"chave": "yt:x", "titulo": "S1 - Início (vídeo x)", "tipo": "videoaula",
                           "status": "sem_legenda"})
checa("SEM LEGENDA" in R.cobertura_md(manifest), "vídeo sem legenda aparece para ele assistir")
a1 = R.assinatura(manifest)
manifest["fontes"][0]["status"] = "lido"
checa(R.assinatura(manifest) != a1, "mudança de status muda a assinatura (remonta a revisão)")

# ---------------------------------------------------------------------------
print("\n== falhas de coleta e retomada ==")
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp)
    col = R.Coletor(PaginaFalsa({"texto": "", "links": [], "iframes": []}), pasta)
    vazio, _ = col.pagina({"cmid": "1", "label": "Página sintética", "url": "https://exemplo.test/page"})
    checa(vazio["status"] == "falhou", "página vazia não conta como lida")

    with patch.object(R.subprocess, "run") as run:
        run.return_value.returncode = 1
        run.return_value.stderr = b"falha de rede"
        checa(col.video("abcdefghijk", "Vídeo sintético")["status"] == "falhou",
              "erro do yt-dlp volta na próxima rodada, sem virar sem legenda")

    class QuizFalso(PaginaFalsa):
        def evaluate(self, js):
            return {"links": [["Revisão", "https://ava.exemplo.test/mod/quiz/review.php?attempt=1"]]} if js == R.JS_PAGINA else ""

    quiz = R.Coletor(QuizFalso({}), pasta).quiz(
        {"cmid": "7", "label": "Quiz sintético", "url": "https://ava.exemplo.test/quiz"},
        date(2026, 9, 28), date(2026, 10, 5))
    checa(quiz["status"] == "falhou", "revisão sem .que não fecha o questionário")

    fontes = [{"chave": "cm:1", "status": "lido", "sha256": "a"}]
    base = {"fontes": fontes, "fechada": True, "inventario": R.inventario({"items": []})}
    base["montado_hash"] = R.assinatura(base)
    rev = pasta / "REVISAO.md"
    rev.write_text("Revisão sintética", encoding="utf-8")
    base["ficha_de"] = R.hash_arquivo(rev)
    (pasta / "apostila.json").write_text(json.dumps({"tema": "Tema sintético"}), encoding="utf-8")
    checa(R.semana_em_dia(base, pasta, {"items": []}), "semana íntegra é pulada")
    checa(not R.semana_em_dia(base, pasta, {"items": [{"cmid": 2}]}),
          "item novo no AVA reabre a semana")
    fontes[0]["sha256"] = "b"
    checa(not R.semana_em_dia(base, pasta, {"items": []}),
          "fonte alterada com o mesmo tamanho remonta a revisão")
    fontes[0]["sha256"] = "a"
    (pasta / "apostila.json").write_text("{quebrado", encoding="utf-8")
    checa(not R.semana_em_dia(base, pasta, {"items": []}), "ficha corrompida é refeita")
    (pasta / "apostila.json").unlink()
    checa(not R.semana_em_dia(base, pasta, {"items": []}), "ficha apagada é refeita")

    import pymupdf as fitz
    pdf = fitz.open()
    pdf.new_page().insert_text((50, 50), "Texto sintetico")
    corpo = pdf.tobytes()
    pdf.close()
    p1 = col._ler_pdf(corpo, "https://exemplo.test/a/slides.pdf", "Slides A")
    p2 = col._ler_pdf(corpo, "https://exemplo.test/b/slides.pdf", "Slides B")
    checa(p1["arquivo"] != p2["arquivo"] and (pasta / p1["arquivo"]).exists(),
          "PDFs homônimos preservam os dois textos")
    vazio_pdf = fitz.open()
    vazio_pdf.new_page()
    sem_texto = col._ler_pdf(vazio_pdf.tobytes(), "https://exemplo.test/scan.pdf", "PDF sintético")
    vazio_pdf.close()
    checa(sem_texto["status"] == "nao_lido", "PDF sem texto extraível não conta como fonte lida")

    def escreveu_e_falhou(*args, **kwargs):
        (pasta / "REVISAO.md").write_text("saída sintética", encoding="utf-8")
        return type("Processo", (), {"returncode": 1, "stdout": "erro", "stderr": ""})()

    rev.unlink()
    with patch.object(R.subprocess, "run", side_effect=escreveu_e_falhou):
        ok, _ = R._chamar_claude_uma_vez(pasta, "instrução sintética", "REVISAO.md")
    checa(not ok, "Claude com código de erro não confirma saída parcial")

# ---------------------------------------------------------------------------
print("\n== desistir de fonte quebrada e uma máquina só ==")
f1 = R.aplicar_tentativas({"status": "falhou", "erro": "HTTP 404"}, None)
f2 = R.aplicar_tentativas({"status": "falhou", "erro": "HTTP 404"}, f1)
f3 = R.aplicar_tentativas({"status": "falhou", "erro": "HTTP 404"}, f2)
checa(f1["status"] == f2["status"] == "falhou", "duas primeiras falhas ainda tentam de novo")
checa(f3["status"] == "nao_lido" and "3 rodadas" in f3["erro"],
      "na terceira falha a fonte vira não lido, sem prender a semana para sempre")
checa("tentativas" not in R.aplicar_tentativas({"status": "lido"}, f2), "leitura boa zera o contador")
with tempfile.TemporaryDirectory() as tmp:
    arq = Path(tmp) / "MAQUINA_DA_REVISAO.txt"
    checa(R.maquina_responsavel(arq, "LAPTOP-A") == (True, "LAPTOP-A"), "a primeira máquina assume")
    checa(R.maquina_responsavel(arq, "laptop-a")[0], "a dona continua fazendo")
    checa(R.maquina_responsavel(arq, "PC-CASA") == (False, "LAPTOP-A"), "a outra máquina sai quieta")
checa("if ($codigo -eq 4)" in rotina and R.AGUARDA_RETRATO == 4,
      "retrato do dia atrasado espera em silêncio, sem alarme de problema")

# ---------------------------------------------------------------------------
# Auditoria de 26/10/2026: o que a coleta perdia ou inventava.
print("\n== fórmulas, páginas e HTML ==")
checa(R.tex_legivel(r"\frac{a^{7}}{a^{3}}") == "a⁷/a³", "fração com expoente vira a⁷/a³")
checa(R.tex_legivel(r"8,5 \times 10^{6}") == "8,5 × 10⁶", "notação científica legível")
checa(R.tex_legivel(r"\mathbb{Z}^{*}") == "Z*", "conjunto dos inteiros não nulos")
checa(R.tex_legivel(r"\frac{3}{4}+\frac{5}{8}") == "3/4+5/8", "soma de frações")
checa(R.com_formulas("R$ 110,00 e ⟦\\frac{1}{4}⟧ ingerida") == "R$ 110,00 e 1/4 ingerida",
      "marca de fórmula trocada sem mexer no cifrão")
checa(R.intervalo_paginas('Fundamentos (Leia o Capítulo "Porcentagem", p. 145 - 153) | Luciana') == (145, 153),
      "páginas com espaço em volta do hífen")
checa(R.intervalo_paginas("Encontros de aritmética (Leia as páginas 37-62)") == (37, 62), "'Leia as páginas'")
checa(R.intervalo_paginas("Fundamentos (p. 111–119)") == (111, 119), "travessão curto entre páginas")
checa(R.intervalo_paginas("Metodologia científica (Leia a seção 1.3)") is None, "seção sem página não inventa intervalo")
pagina_epub = ('<html><body><nav epub:type="toc"><ol><li>1.1 Sumário</li></ol></nav>'
               '<h1>1.1 O conhecimento</h1><p>Há quatro&nbsp;níveis.</p><script>x=1</script></body></html>')
with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"leitor_livros": None}):
    sem = R.Coletor(PaginaFalsa({}), Path(tmp)).leitor("https://ava.exemplo.test/mod/lti/view.php?id=1", "Texto-base")
    checa(sem["status"] == "nao_lido" and "leitor_v" not in sem,
          "sem o leitor privado, texto-base fica não lido e é tentado de novo quando ele aparecer")
with tempfile.TemporaryDirectory() as tmp:
    geo = R.Coletor(PaginaFalsa({}), Path(tmp))._pagina_externa("https://www.geogebra.org/m/wukttfzq", "GeoGebra")
    checa(geo["status"] == "nao_lido" and "interativa" in geo["erro"], "GeoGebra é atividade interativa, não texto")
checa(R.html_para_texto(pagina_epub) == "1.1 O conhecimento\n\nHá quatro níveis.",
      "HTML vira texto sem o menu e sem script")

print("\n== questionário: marcada, resposta oficial e gabarito sem IA ==")


def questao(enun, alts, marcada, nota, maximo=2.5, correta="", feedback=""):
    return {"numero": "1", "tipo": "multichoice", "estado": "Completo", "nota": nota, "nota_max": maximo,
            "enunciado": enun, "imagens": [], "selects": [], "campos": [], "feedback": feedback,
            "correta": correta,
            "alternativas": [{"letra": "ABCDE"[i], "texto": a, "marcada": a == marcada} for i, a in enumerate(alts)]}


ALTS = ["I, apenas.", "II, apenas.", "II e III, apenas.", "I e III, apenas.", "III, apenas."]
t1 = [questao("Sobre a pesquisa científica, avalie.", ALTS, "II e III, apenas.", 0)]
t2 = [questao("Sobre a pesquisa científica, avalie.", list(reversed(ALTS)), "II, apenas.", 2.5)]
q = R.consolidar_questoes([t1, t2])
checa(len(q) == 1, "a mesma questão em duas tentativas, com alternativas embaralhadas, conta uma vez")
checa(q[0]["resposta"] == ["II, apenas."] and q[0]["como"] == "nota",
      "sem resposta oficial, vale a marcada da tentativa com nota cheia")
checa(q[0]["eliminadas"] == ["II e III, apenas."], "marcada com nota zero fica como errada com certeza")
oficial = R.consolidar_questoes([[questao("Q", ALTS, "I, apenas.", 0, correta="A resposta correta é: II, apenas.")]])
checa(oficial[0]["resposta"] == ["II, apenas."] and oficial[0]["como"] == "oficial",
      "resposta oficial do AVA ganha da dedução")
varias = R.consolidar_questoes([[questao("Q", ALTS, "I, apenas.", 2.5,
                                         correta="As respostas corretas são: I, apenas., III, apenas.")]])
checa(sorted(varias[0]["resposta"]) == ["I, apenas.", "III, apenas."] and varias[0]["como"] == "oficial_varias",
      "questão em que o AVA aceitou mais de uma, sem casar 'II, apenas' dentro de 'III, apenas'")
CONJ = ["1-Z+; 2-Z-; 3-Z0", "1-Z+; 2-Z0; 3-Z-", "1-Z+; 2-Z*; 3-Z0", "1-Z+; 2-Z-; 3-Z*", "1-Z0; 2-Z*; 3-Z+"]
um = R.consolidar_questoes([[questao("Q", CONJ, "1-Z+; 2-Z-; 3-Z*", 2, 2,
                                     correta="A resposta correta é: 1-Z+; 2-Z-; 3-Z*")]])
checa(um[0]["resposta"] == ["1-Z+; 2-Z-; 3-Z*"], "alternativas que só diferem no símbolo (Z-, Z*, Z0) não se confundem")
anulada = R.consolidar_questoes([[questao(
    "Q", CONJ, "1-Z+; 2-Z-; 3-Z*", 2, 2, correta="As respostas corretas são: " + ", ".join(CONJ),
    feedback="Sua resposta está correta. A alternativa “1-Z+; 2-Z-; 3-Z*” está correta, pois ... "
             "As demais estão incorretas: A alternativa “1-Z+; 2-Z0; 3-Z-” está incorreta...")]])
checa(anulada[0]["como"] == "anulada" and anulada[0]["resposta"] == ["1-Z+; 2-Z-; 3-Z*"],
      "questão anulada (AVA aceitou todas): a certa sai do comentário, não da lista de aceitas")
checa(R.tex_legivel("\\mathbb{Z}_\u00ad") == "Z-" and R.tex_legivel("\\mathbb{Z}_+") == "Z+",
      "índice de conjunto: Z- (hífen invisível) e Z+")
nada = R.consolidar_questoes([[questao("Q", ALTS, "I, apenas.", 0)]])
checa(nada[0]["resposta"] == [] and nada[0]["como"] is None, "nota zero e sem oficial: resposta desconhecida")


class RevisaoFalsa(PaginaFalsa):
    def evaluate(self, js):
        if js == R.JS_PAGINA:
            return {"links": [["Revisão", "https://ava.exemplo.test/mod/quiz/review.php?attempt=1"]]}
        return [questao("Quanto é ⟦\\frac{1}{2}⟧ de 10?", ["5", "2"], "5", 1.25, 1.25,
                        correta="A resposta correta é: 5", feedback="Metade de 10 é 5.")]


with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp)
    res = R.Coletor(RevisaoFalsa({}), pasta).quiz(
        {"cmid": "9", "label": "S1 - Atividade Avaliativa", "url": "https://ava.exemplo.test/quiz"},
        date(2026, 9, 28), date(2026, 10, 20))
    texto = (pasta / res["arquivo"]).read_text(encoding="utf-8")
    checa(res["formato"] == R.QUIZ_V and res["gabarito_oficial"], "questionário novo marca formato e gabarito oficial")
    checa("A) 5  (MARCADA)" in texto and "Resposta oficial do AVA: 5" in texto and "Metade de 10" in texto,
          "texto da revisão traz a marcada, a resposta oficial e o comentário")
    checa("1/2 de 10" in texto, "fórmula do enunciado sai legível")
    man = {"disciplina": "MMB002", "semana": 1, "fontes": [
        {"tipo": "questionário", "status": "lido", "arquivo": res["arquivo"], "titulo": "S1 - Atividade", "url": "u"}]}
    R.montar_gabarito(pasta, man)
    gab = (pasta / "GABARITO.md").read_text(encoding="utf-8")
    checa("**Resposta:** A) 5 (resposta oficial do AVA)" in gab, "GABARITO.md diz a certa e de onde ela vem")
    checa(json.loads((pasta / "gabarito.json").read_text(encoding="utf-8"))[0]["questoes"][0]["resposta"] == ["5"],
          "gabarito.json para a apostila")

print("\n== reler o que a versão nova lê melhor ==")
ini, hj = date(2026, 9, 28), date(2026, 10, 26)
checa(R.precisa_reler({"tipo": "questionário", "status": "lido"}, ini, hj),
      "questionário lido sem a marcada é relido")
checa(R.precisa_reler({"tipo": "questionário", "status": "lido", "formato": R.QUIZ_V, "gabarito_oficial": False}, ini, hj),
      "questionário sem resposta oficial é relido enquanto o AVA pode mostrá-la")
checa(not R.precisa_reler({"tipo": "questionário", "status": "lido", "formato": R.QUIZ_V, "gabarito_oficial": False},
                          ini, ini + timedelta(days=40)), "e depois do prazo para de tentar")
checa(R.precisa_reler({"tipo": "videoaula", "status": "lido"}, ini, hj), "vídeo da legenda automática antiga é relido")
checa(not R.precisa_reler({"tipo": "videoaula", "status": "lido", "legenda": "automatica"}, ini, hj),
      "vídeo sem legenda revisada não é relido toda rodada")
checa(R.precisa_reler({"tipo": "leitor externo", "status": "nao_lido"}, ini, hj), "texto-base do LTI ganha a tentativa nova")
checa(not R.precisa_reler({"tipo": "leitor externo", "status": "nao_lido", "leitor_v": R.LEITOR_V}, ini, hj),
      "e não fica tentando para sempre")


class ColetorFalso:
    """Registra o que a coleta pediu de novo; cada leitura devolve o combinado."""
    def __init__(self, video=None):
        self.pedidos = []
        self.res_video = video or {"status": "lido", "arquivo": "fontes/v.txt", "chars": 9, "sha256": "n", "legenda": "univesp"}

    def video(self, vid, titulo):
        self.pedidos.append(("video", vid))
        return dict(self.res_video)

    def externo(self, url, titulo):
        self.pedidos.append(("externo", url))
        return {"status": "nao_lido", "ext_v": 1}

    def pagina(self, item):
        self.pedidos.append(("pagina", item["cmid"]))
        return {"status": "lido"}, []


secao = {"items": [{"cmid": "1", "type": "page", "label": "S1 - Início", "url": "https://ava.exemplo.test/page"}]}
anterior = {"fontes": [
    {"chave": "cm:1", "tipo": "página", "titulo": "S1 - Início", "url": "u", "status": "lido", "sha256": "p"},
    {"chave": "yt:falhou00001", "tipo": "videoaula", "titulo": "vídeo", "url": "https://youtu.be/falhou00001",
     "status": "falhou", "tentativas": 1, "origem": "cm:1"},
    {"chave": "yt:automatico", "tipo": "videoaula", "titulo": "vídeo", "url": "https://youtu.be/automatico",
     "status": "lido", "sha256": "velho", "origem": "cm:1"},
    {"chave": "ext:https://stock.adobe.com/br/search?k=x", "tipo": "link externo", "titulo": "Adobe Stock, c2024",
     "url": "https://stock.adobe.com/br/search?k=x", "status": "falhou", "origem": "cm:1"},
]}
col = ColetorFalso(video={"status": "falhou", "erro": "HTTP Error 429", "sem_manual": True})
man = R.coletar_semana(col, {"code": "INT100"}, 2, ini, secao, json.loads(json.dumps(anterior)), hj)
por = {f["chave"]: f for f in man["fontes"]}
checa(("video", "falhou00001") in col.pedidos and por["yt:falhou00001"]["tentativas"] == 2,
      "vídeo que falhou, vindo de página já lida, é tentado de novo e conta a tentativa")
checa(por["yt:automatico"]["status"] == "lido" and por["yt:automatico"]["sha256"] == "velho"
      and por["yt:automatico"]["legenda"] == "automatica",
      "releitura que falha não apaga o vídeo já lido, e ele não é retentado toda rodada")
checa(not any("stock.adobe" in k for k in por), "crédito de imagem do Adobe Stock sai da cobertura")
checa(("pagina", "1") not in col.pedidos, "página já lida não é reaberta")

with tempfile.TemporaryDirectory() as tmp:
    chamadas = []

    def yt_falso(cmd, **kwargs):
        chamadas.append(cmd)
        saida = Path(cmd[cmd.index("-o") + 1]).parent
        if "--write-subs" in cmd:
            (saida / "v.pt-BR.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nOLÁ, PESSOAL.\n",
                                               encoding="utf-8")
        return type("Processo", (), {"returncode": 0, "stderr": b""})()

    with patch.object(R.subprocess, "run", side_effect=yt_falso):
        v = R.Coletor(PaginaFalsa({}), Path(tmp)).video("abcdefghijk", "S1 - Videoaula")
    checa(v["legenda"] == "univesp" and len(chamadas) == 1,
          "legenda revisada da Univesp primeiro, sem pedir a automática ao YouTube")
    checa("revisada" in (Path(tmp) / v["arquivo"]).read_text(encoding="utf-8"), "cabeçalho diz que a legenda é revisada")

import apostila as A  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp)
    (pasta / "gabarito.json").write_text(json.dumps([{"titulo": "S1", "questoes": [
        {"enunciado": "Quanto é 1/2 de 10?", "alternativas": ["2", "5"], "resposta": ["5"], "como": "oficial",
         "feedback": "Metade.", "eliminadas": ["2"]}]}]), encoding="utf-8")
    ava = A.ler_ava(pasta)
    checa(ava and ava[0]["certas"] == ["B"] and ava[0]["eliminadas"] == ["A"], "apostila lê as questões do AVA com a letra certa")
    s = {"n": 1, "inicio": None, "tema": "T", "ideia_central": "", "ler_por_conta": [], "conceitos": [], "autores": [],
         "comparacoes": [], "exemplos": [], "cobrado": [], "pegadinhas": [], "treino": [], "ava": ava}
    d = {"cod": "mmb002", "nome": "Matemática", "cor": "#2b8a3e", "semanas": [s]}
    checa('data-correta="B"' in A.secao_semana(d, s, "tela") and "resposta oficial do AVA" in A.secao_semana(d, s, "tela"),
          "questão do AVA clicável na tela, com a origem do gabarito")
    checa("Questões do AVA" not in A.secao_semana(d, s, "resumo"), "resumo de uma página não leva as questões")
    checa("S1 AVA 1 · B" in A.gabarito(d), "gabarito do PDF de treino inclui as questões do AVA")

print("\n" + "=" * 66)
if falhas:
    print(f"{len(falhas)} teste(s) falharam.")
    raise SystemExit(1)
print("Todos os testes da revisão semanal passaram.")
