"""Lab 02 (sem tutorial): voce escreve, os testes julgam.

REGRA: IA PROIBIDA NESTE ARQUIVO.
  Proibido: ChatGPT, Claude, Gemini, Copilot, Antigravity, Cursor, autocomplete de IA.
  Permitido: docs.python.org e nada mais.
  Se travar 15 minutos numa funcao, escreva "travei" num comentario e siga.
  Travar e dado util. Colar resposta de IA nao e.

Como rodar:
    python C:\\projetos\\formacao-ia-automacao\\01-python\\laboratorios\\lab02_sem_tutorial.py

Rode antes de escrever qualquer coisa: todos os testes vao falhar. E o esperado.
Vá implementando uma funcao por vez ate ficar tudo verde.
"""

from __future__ import annotations

from pathlib import Path


# ===========================================================================
# EXERCICIO 1
# Some uma lista de precos em formato brasileiro ("1.234,56") e devolva float.
# Valor invalido ou vazio conta como zero. Nao pode quebrar.
# ===========================================================================
def somar_precos(precos: list[str]) -> float:
    raise NotImplementedError("escreva aqui")


# ===========================================================================
# EXERCICIO 2
# Devolva uma copia do dicionario com as chaves em maiusculas.
# O dicionario original NAO pode ser alterado.
# ===========================================================================
def chaves_maiusculas(dados: dict) -> dict:
    raise NotImplementedError("escreva aqui")


# ===========================================================================
# EXERCICIO 3
# Conte quantas linhas do arquivo nao estao vazias (linha so com espaco conta
# como vazia). Arquivo inexistente devolve 0, sem levantar excecao.
# ===========================================================================
def contar_linhas(caminho: Path) -> int:
    raise NotImplementedError("escreva aqui")


# ===========================================================================
# EXERCICIO 4
# Escreva um DECORADOR que mede o tempo da funcao e guarda o resultado em
# `TEMPOS[nome_da_funcao]`. O nome original da funcao precisa ser preservado.
# ===========================================================================
TEMPOS: dict[str, float] = {}


def cronometrado(func):
    raise NotImplementedError("escreva aqui")


# ===========================================================================
# EXERCICIO 5
# Escreva um CONTEXT MANAGER `silenciar(TipoDeErro)` que engole SO aquele tipo
# de erro dentro do bloco `with`, e deixa os outros passarem.
#
#   with silenciar(ValueError):
#       int("abc")          # engolido
#   with silenciar(ValueError):
#       1 / 0               # ZeroDivisionError passa direto
# ===========================================================================
def silenciar(tipo_erro):
    raise NotImplementedError("escreva aqui")


# ===========================================================================
# EXERCICIO 6
# Dada uma lista de cotacoes, devolva a de menor custo total (preco + frete).
# Trate: lista vazia (devolve None), chave ausente, valor invalido, NaN,
# infinito e preco em formato brasileiro.
# ===========================================================================
def melhor_cotacao(cotacoes: list[dict]) -> dict | None:
    raise NotImplementedError("escreva aqui")


# ===========================================================================
# TESTES. Nao edite daqui para baixo.
# ===========================================================================
def _testes() -> None:
    import math
    import tempfile

    passou = falhou = 0

    def checar(nome, condicao):
        nonlocal passou, falhou
        if condicao:
            passou += 1
            print(f"  OK   {nome}")
        else:
            falhou += 1
            print(f"  FALHOU  {nome}")

    def tentar(nome, func):
        try:
            func()
        except NotImplementedError:
            nonlocal falhou
            falhou += 1
            print(f"  NAO IMPLEMENTADO  {nome}")
        except Exception as e:
            falhou += 1
            print(f"  EXPLODIU  {nome}: {type(e).__name__}: {e}")

    print("\n--- Exercicio 1: somar_precos ---")
    tentar("1", lambda: (
        checar("soma brasileira", abs(somar_precos(["1.234,56", "10,00"]) - 1244.56) < 0.01),
        checar("vazio vira 0", somar_precos([]) == 0),
        checar("invalido vira 0", somar_precos(["abc", "10"]) == 10.0),
    ))

    print("\n--- Exercicio 2: chaves_maiusculas ---")
    tentar("2", lambda: (
        checar("converte", chaves_maiusculas({"a": 1, "b": 2}) == {"A": 1, "B": 2}),
        checar("nao altera original", (
            lambda d: (chaves_maiusculas(d), d == {"x": 1})[1]
        )({"x": 1})),
    ))

    print("\n--- Exercicio 3: contar_linhas ---")

    def teste3():
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.txt"
            p.write_text("a\n\n b \n\n   \nc\n", encoding="utf-8")
            checar("conta nao vazias", contar_linhas(p) == 3)
            checar("inexistente vira 0", contar_linhas(Path(tmp) / "nao_existe.txt") == 0)

    tentar("3", teste3)

    print("\n--- Exercicio 4: cronometrado ---")

    def teste4():
        TEMPOS.clear()

        @cronometrado
        def lenta():
            """docstring original"""
            return sum(range(10000))

        lenta()
        checar("registrou tempo", "lenta" in TEMPOS)
        checar("preservou __name__", lenta.__name__ == "lenta")
        checar("preservou __doc__", lenta.__doc__ == "docstring original")

    tentar("4", teste4)

    print("\n--- Exercicio 5: silenciar ---")

    def teste5():
        engoliu = True
        try:
            with silenciar(ValueError):
                int("abc")
        except ValueError:
            engoliu = False
        checar("engole o tipo certo", engoliu)

        passou_outro = False
        try:
            with silenciar(ValueError):
                1 / 0
        except ZeroDivisionError:
            passou_outro = True
        checar("deixa outro passar", passou_outro)

    tentar("5", teste5)

    print("\n--- Exercicio 6: melhor_cotacao ---")

    def teste6():
        dados = [
            {"loja": "A", "preco": "1.200,00", "frete": "0"},
            {"loja": "B", "preco": "1.150,50", "frete": "89,90"},
            {"loja": "C", "preco": "1.100,00", "frete": "150,00"},
        ]
        r = melhor_cotacao(dados)
        checar("escolhe menor total", r is not None and r["loja"] == "B")
        checar("lista vazia vira None", melhor_cotacao([]) is None)

        sujos = [
            {"loja": "X", "preco": float("nan"), "frete": 0},
            {"loja": "Y", "preco": "10,00", "frete": 0},
            {"loja": "Z"},
        ]
        r2 = melhor_cotacao(sujos)
        checar("ignora NaN e chave faltando", r2 is not None and r2["loja"] in {"Y", "Z"})

    tentar("6", teste6)

    print(f"\n{'=' * 46}")
    print(f"  passou: {passou}   falhou: {falhou}")
    if falhou == 0:
        print("  Tudo verde. Anote no DIARIO_DE_ESTUDOS.md quanto tempo levou.")
    else:
        print("  Ainda falta. Sem IA.")
    print("=" * 46)


if __name__ == "__main__":
    _testes()
