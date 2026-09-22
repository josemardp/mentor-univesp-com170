"""Lab 03: 6 bugs plantados. Ache e corrija.

REGRA: IA PROIBIDA. Documentacao liberada.

Rode e veja falhar:
    python C:\\projetos\\formacao-ia-automacao\\01-python\\laboratorios\\lab03_bugs.py

Cada bug e de uma familia diferente, todas cobertas na secao 13 do modulo.
Alguns quebram na cara. Outros dao resultado ERRADO sem erro nenhum, que e o
tipo que chega em producao. Nao confie so no traceback: leia o resultado.

Quando achar um, escreva o numero e a familia num comentario ali em cima,
ANTES de corrigir. Anotar o diagnostico antes da correcao e o habito que
separa depurar de tentar coisa ate parar de reclamar.
"""

from __future__ import annotations

import math
from pathlib import Path


# --- BUG 1 -----------------------------------------------------------------
def acumular(item, historico=[]):
    historico.append(item)
    return historico


# --- BUG 2 -----------------------------------------------------------------
def ler_config(caminho):
    try:
        with open(caminho) as f:
            return f.read()
    except:
        pass


# --- BUG 3 -----------------------------------------------------------------
def media(valores):
    return sum(valores) / len(valores)


# --- BUG 4 -----------------------------------------------------------------
def duplicar_cotacoes(cotacoes):
    """Devolve copia para trabalhar sem sujar o original."""
    copia = cotacoes.copy()
    for c in copia:
        c["preco"] = c["preco"] * 2
    return copia


# --- BUG 5 -----------------------------------------------------------------
def validar_preco(valor):
    try:
        numero = float(valor)
    except ValueError:
        return 0.0
    return numero


# --- BUG 6 -----------------------------------------------------------------
def remover_invalidas(cotacoes):
    """Tira da lista as cotacoes sem preco."""
    for c in cotacoes:
        if "preco" not in c:
            cotacoes.remove(c)
    return cotacoes


# ===========================================================================
# TESTES. Nao edite. Quando os 6 passarem, acabou.
# ===========================================================================
def _testes():
    import tempfile

    ok = ruim = 0

    def checar(n, nome, condicao):
        nonlocal ok, ruim
        if condicao:
            ok += 1
            print(f"  OK   bug {n}: {nome}")
        else:
            ruim += 1
            print(f"  FALHOU  bug {n}: {nome}")

    checar(1, "historico nao vaza entre chamadas",
           (acumular("a"), acumular("b"))[1] == ["b"])

    with tempfile.TemporaryDirectory() as tmp:
        inexistente = Path(tmp) / "nao_existe.txt"
        try:
            ler_config(inexistente)
            achou_erro = False
        except Exception:
            achou_erro = True
        checar(2, "erro nao e engolido em silencio", achou_erro)

    try:
        media([])
        tratou = False
    except ZeroDivisionError:
        tratou = False
    except Exception:
        tratou = True
    else:
        tratou = True
    checar(3, "lista vazia e tratada", tratou)

    original = [{"loja": "A", "preco": 100}]
    duplicar_cotacoes(original)
    checar(4, "original nao foi alterado", original[0]["preco"] == 100)

    checar(5, "NaN e infinito viram 0.0",
           validar_preco("nan") == 0.0 and validar_preco("inf") == 0.0)

    entrada = [
        {"loja": "A"},
        {"loja": "B"},
        {"loja": "C", "preco": 10},
        {"loja": "D"},
    ]
    restante = remover_invalidas(entrada)
    lojas = sorted(c["loja"] for c in restante)
    checar(6, "remove TODAS as invalidas", lojas == ["C"])

    print(f"\n  corrigidos: {ok}   faltando: {ruim}")
    if ruim == 0:
        print("  Os 6. Anote no DIARIO_DE_ESTUDOS.md quais te enganaram mais.")


if __name__ == "__main__":
    _testes()
