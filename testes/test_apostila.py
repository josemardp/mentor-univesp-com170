# -*- coding: utf-8 -*-
"""
Apostila de prova (automacao/apostila.py), pedida por Josemar em 23/09/2026:
bonita, colorida, funcional, na medida exata, engordando toda semana.

O que este teste protege, em ordem de importância:

1. **Ficha ruim não quebra a apostila.** A ficha vem de IA; excesso é cortado,
   questão malformada cai fora, ficha sem tema é recusada.
2. **Texto da ficha não vira HTML.** Só **negrito** e *itálico* passam; o resto
   é escapado.
3. **Impresso tem gabarito, tela não entrega a resposta de cara.** O PDF leva
   o gabarito no fim da disciplina; a tela esconde a resposta até o clique.
4. **Não repetir entre semanas.** A ficha nova recebe o que as anteriores já
   definiram.

Rodar:  python testes/test_apostila.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

import apostila as A  # noqa: E402

falhas = []


def checa(cond, msg):
    print(("  ok    " if cond else "  FALHA") + " | " + msg)
    if not cond:
        falhas.append(msg)


def ficha(**extra):
    base = {
        "tema": "Cultura e moral",
        "ideia_central": "A moral nasce da **cultura**, que é dinâmica.",
        "conceitos": [{"termo": f"Termo {i}", "definicao": "def"} for i in range(12)],
        "autores": [{"nome": "Clifford Geertz", "referencia": "1978", "ideia": "cultura como teia de significados"}],
        "comparacoes": [{"titulo": "Tylor x Geertz", "colunas": ["", "Tylor", "Geertz"],
                         "linhas": [["Cultura", "todo complexo"]]}],
        "exemplos": [], "cobrado": ["a", "b"], "pegadinhas": [{"confusao": "x", "certo": "y"}],
        "treino": [
            {"enunciado": "Q1", "alternativas": list("abcde"), "correta": "c", "comentario": "porque"},
            {"enunciado": "Q2 malformada", "alternativas": list("abc"), "correta": "A"},
            {"enunciado": "Q3", "alternativas": list("abcde"), "correta": "Z"},
        ],
        "ler_por_conta": ["Livro X, cap. 2"],
    }
    base.update(extra)
    return base


# ---------------------------------------------------------------------------
print("\n== validação da ficha ==")
f = A.validar(ficha())
checa(len(f["conceitos"]) == 8, "conceitos cortados no limite de 8")
checa(len(f["treino"]) == 1 and f["treino"][0]["correta"] == "C",
      "só a questão bem-formada fica, com a letra normalizada")
checa(f["comparacoes"][0]["linhas"][0] == ["Cultura", "todo complexo", ""],
      "linha curta da comparação é completada")
try:
    A.validar(ficha(tema=""))
    checa(False, "ficha sem tema é recusada")
except A.FichaInvalida:
    checa(True, "ficha sem tema é recusada")

# ---------------------------------------------------------------------------
print("\n== texto seguro ==")
checa(A.md("<script>x</script> **forte** e *leve*") ==
      "&lt;script&gt;x&lt;/script&gt; <strong>forte</strong> e <em>leve</em>",
      "HTML escapado, negrito e itálico aceitos")
checa(A.md("2 * 3 * 4") == "2 * 3 * 4", "asterisco solto não vira itálico")
checa(A.quebrar_enunciado("Leia. I. Uma. PORQUE II. Duas. A respeito delas, assinale.").split("\n") ==
      ["Leia.", "I. Uma.", "PORQUE", "II. Duas.", "A respeito delas, assinale."],
      "asserção-razão em linhas próprias, como na prova")
checa(A.iniciais("Clifford Geertz") == "CG" and A.iniciais("Eni Puccinelli Orlandi") == "EO", "iniciais do autor")

# ---------------------------------------------------------------------------
print("\n== montagem ==")
with tempfile.TemporaryDirectory() as tmp:
    A.ESTUDO = Path(tmp)
    for disc, n in [("soc100", 2), ("soc100", 4), ("let110", 1)]:
        p = Path(tmp) / "2026-4bim" / disc / f"semana-{n:02d}"
        p.mkdir(parents=True)
        (p / "apostila.json").write_text(json.dumps(ficha(tema=f"Tema {disc} {n}")), encoding="utf-8")
        (p / "manifest.json").write_text(json.dumps({"inicio": "2026-10-05"}), encoding="utf-8")
    ruim = Path(tmp) / "2026-4bim" / "soc100" / "semana-05"
    ruim.mkdir()
    (ruim / "apostila.json").write_text("{ isso não é json", encoding="utf-8")

    discs = A.coletar("2026-4bim")
    checa([d["cod"] for d in discs] == ["let110", "soc100"], "disciplinas em ordem")
    checa([s["n"] for s in discs[1]["semanas"]] == [2, 4], "ficha quebrada é pulada, as outras entram")

    tela = A.montar_html("2026-4bim", discs)
    checa('id="soc100-s04"' in tela and 'id="let110-s01"' in tela, "cada semana tem âncora para o sumário")
    checa("Apostila de prova · 4º bimestre 2026" in tela, "título do bimestre")
    checa('<details class="gab">' in tela and "Gabarito do treino" not in tela,
          "na tela a resposta fica escondida até o clique")
    checa("Leia ou assista por conta própria" in tela, "o que não foi lido aparece na semana")
    checa("—" not in tela, "sem travessão no texto da apostila")

    papel = A.montar_html("2026-4bim", [discs[1]], imprimir=True)
    checa("Gabarito do treino · SOC100" in papel and '<details class="gab">' not in papel,
          "impresso leva o gabarito no fim e não o botão")

    vistos = A.ja_vistos(Path(tmp) / "2026-4bim" / "soc100", 4)
    checa("Termo 0" in vistos and "Clifford Geertz" in vistos, "semana 4 recebe o que a semana 2 já definiu")
    checa("primeira semana" in A.ja_vistos(Path(tmp) / "2026-4bim" / "soc100", 2), "primeira semana não herda nada")

print("\n" + "=" * 66)
if falhas:
    print(f"{len(falhas)} teste(s) falharam.")
    raise SystemExit(1)
print("Todos os testes da apostila passaram.")
