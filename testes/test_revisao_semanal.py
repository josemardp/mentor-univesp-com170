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

Rodar:  python testes/test_revisao_semanal.py
"""
import sys
from datetime import date
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

    import fitz
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

print("\n" + "=" * 66)
if falhas:
    print(f"{len(falhas)} teste(s) falharam.")
    raise SystemExit(1)
print("Todos os testes da revisão semanal passaram.")
