"""Lab 01 (guiado): referencia, excecao, arquivo, decorador e context manager.

Rode assim, no PowerShell:
    python C:\\projetos\\formacao-ia-automacao\\01-python\\laboratorios\\lab01_guiado.py

Leia cada bloco ANTES de olhar a saida. Tente prever o resultado de cabeca.
Quando a saida for diferente do que voce previu, pare e entenda por que.
Esse momento e o unico que ensina alguma coisa aqui.
"""

from __future__ import annotations

import contextlib
import csv
import functools
import math
import os
import time
from pathlib import Path

PASTA = Path(__file__).parent / "saida"


# ---------------------------------------------------------------------------
# PASSO 1: etiqueta, nao caixa
# ---------------------------------------------------------------------------
def passo1_referencia() -> None:
    print("\n=== PASSO 1: referencia ===")

    lista = [1, 2, 3]
    outra = lista          # NAO copia. Cola uma segunda etiqueta no mesmo objeto
    outra.append(4)

    print(f"lista  = {lista}")            # PREVEJA antes de rodar
    print(f"outra  = {outra}")
    print(f"mesmo objeto? {lista is outra}")

    texto = "abc"
    copia = texto
    copia += "d"           # str e imutavel: cria objeto novo, move a etiqueta

    print(f"texto  = {texto}")
    print(f"copia  = {copia}")
    print(f"mesmo objeto? {texto is copia}")

    # Cópia de verdade
    segura = lista.copy()
    segura.append(99)
    print(f"lista  = {lista}   (intacta)")
    print(f"segura = {segura}")

    # Cópia rasa NAO protege o segundo nivel
    aninhada = [{"preco": 10}]
    rasa = aninhada.copy()
    rasa[0]["preco"] = 999
    print(f"aninhada = {aninhada}   <- mudou, porque copy() e rasa")


# ---------------------------------------------------------------------------
# PASSO 2: a armadilha do argumento padrao mutavel
# ---------------------------------------------------------------------------
def errado(item, lista=[]):          # noqa: B006  (o erro e de proposito)
    lista.append(item)
    return lista


def certo(item, lista=None):
    if lista is None:
        lista = []
    lista.append(item)
    return lista


def passo2_argumento_padrao() -> None:
    print("\n=== PASSO 2: argumento padrao mutavel ===")
    print(f"errado('a') = {errado('a')}")
    print(f"errado('b') = {errado('b')}   <- a lista sobreviveu entre chamadas")
    print(f"certo('a')  = {certo('a')}")
    print(f"certo('b')  = {certo('b')}    <- lista nova a cada chamada")


# ---------------------------------------------------------------------------
# PASSO 3: validacao defensiva (reimplementacao do quote_float do seu projeto)
# ---------------------------------------------------------------------------
def quote_float(value, default: float = 0.0) -> float:
    if value in {None, ""}:
        return default
    try:
        numero = float(str(value).replace(",", "."))
    except ValueError:
        return default
    # NaN e infinito sao floats validos e contaminam qualquer conta seguinte
    # em silencio, porque TODA comparacao com NaN e falsa.
    if math.isnan(numero) or math.isinf(numero):
        return default
    return numero


def passo3_validacao() -> None:
    print("\n=== PASSO 3: validacao defensiva ===")
    casos = ["10,50", "10", 10, None, "", "abc", "nan", "inf", "-5,5", "1.234,56"]
    for caso in casos:
        print(f"  quote_float({caso!r:12}) = {quote_float(caso)}")

    print(f"\n  float('nan') == float('nan') -> {float('nan') == float('nan')}")
    print("  Por isso NaN nunca pode entrar num ranking sem ser tratado.")

    print("\n  ATENCAO ao ultimo caso da lista acima:")
    print("    '1.234,56' devolveu 0.0, nao 1234.56.")
    print("    replace(',', '.') transforma em '1.234.56', que nao e float valido,")
    print("    cai no except e volta como default. NAO levanta erro: devolve ZERO.")
    print("    Uma funcao defensiva que devolve default em vez de erro ESCONDE o problema.")
    print("    Voce vai consertar isso no exercicio 1 do lab02.")


# ---------------------------------------------------------------------------
# PASSO 4: context manager
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def cronometro(nome: str):
    inicio = time.time()
    try:
        yield                                  # aqui roda o bloco do `with`
    finally:
        # `finally` roda com erro ou sem. E por isso que o context manager
        # serve para garantir limpeza.
        print(f"  [{nome}] levou {time.time() - inicio:.3f}s")


def passo4_context_manager() -> None:
    print("\n=== PASSO 4: context manager ===")

    with cronometro("soma de 1 milhao"):
        sum(range(1_000_000))

    print("  agora com erro no meio:")
    try:
        with cronometro("vai falhar"):
            raise ValueError("erro de proposito")
    except ValueError as e:
        print(f"  erro capturado: {e}  <- mas o cronometro imprimiu assim mesmo")


# ---------------------------------------------------------------------------
# PASSO 5: decorador
# ---------------------------------------------------------------------------
def repetir(vezes: int):
    """Decorador COM argumento: precisa de tres niveis de funcao."""
    def decorador(func):
        @functools.wraps(func)                 # sem isso, __name__ vira 'wrapped'
        def wrapped(*args, **kwargs):
            for tentativa in range(1, vezes + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"  tentativa {tentativa} falhou: {e}")
                    if tentativa == vezes:
                        raise
        return wrapped
    return decorador


_contador = {"n": 0}


@repetir(3)
def instavel() -> str:
    _contador["n"] += 1
    if _contador["n"] < 3:
        raise RuntimeError("ainda nao")
    return "funcionou na terceira"


def passo5_decorador() -> None:
    print("\n=== PASSO 5: decorador ===")
    print(f"  {instavel()}")
    print(f"  instavel.__name__ = {instavel.__name__}  <- graças ao functools.wraps")


# ---------------------------------------------------------------------------
# PASSO 6: arquivo, encoding e escrita atomica
# ---------------------------------------------------------------------------
def atomic_write_text(path: Path, text: str) -> None:
    """Grava por temporario e troca de uma vez so.

    Abrir em modo "w" TRUNCA o arquivo antes de escrever. Um Ctrl+C no meio
    deixa o arquivo vazio. `os.replace` e atomico no Windows e no POSIX.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporario = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporario.open("w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())     # flush vai para o buffer do SO; fsync vai para o disco
        os.replace(temporario, path)
    except BaseException:            # pega Ctrl+C tambem: a limpeza precisa rodar
        temporario.unlink(missing_ok=True)
        raise                        # e relanca, sem engolir


def passo6_arquivo() -> None:
    print("\n=== PASSO 6: arquivo e escrita atomica ===")
    PASTA.mkdir(parents=True, exist_ok=True)

    alvo = PASTA / "cotacoes.csv"
    # Repare: os precos aqui estao SEM separador de milhar, que e o formato
    # que o quote_float realmente aceita (ver passo 3).
    linhas = [
        ["loja", "preco", "frete"],
        ["Loja A", "1200,00", "0"],
        ["Loja B", "1150,50", "89,90"],
    ]

    import io
    buffer = io.StringIO()
    escritor = csv.writer(buffer, lineterminator="\n")   # LF, nao CRLF
    escritor.writerows(linhas)
    atomic_write_text(alvo, buffer.getvalue())
    print(f"  gravado: {alvo}")

    with alvo.open(encoding="utf-8", newline="") as f:
        for registro in csv.DictReader(f):
            total = quote_float(registro["preco"]) + quote_float(registro["frete"])
            print(f"  {registro['loja']:8} custo total = R$ {total:.2f}")


if __name__ == "__main__":
    passo1_referencia()
    passo2_argumento_padrao()
    passo3_validacao()
    passo4_context_manager()
    passo5_decorador()
    passo6_arquivo()
    print("\nFim do lab guiado. Proximo: lab02_sem_tutorial.py (sem IA).")
