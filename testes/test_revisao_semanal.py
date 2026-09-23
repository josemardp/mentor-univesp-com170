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
a1 = R.assinatura(manifest)
manifest["fontes"][0]["status"] = "lido"
checa(R.assinatura(manifest) != a1, "mudança de status muda a assinatura (remonta a revisão)")

print("\n" + "=" * 66)
if falhas:
    print(f"{len(falhas)} teste(s) falharam.")
    raise SystemExit(1)
print("Todos os testes da revisão semanal passaram.")
