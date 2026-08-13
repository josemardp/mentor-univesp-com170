# -*- coding: utf-8 -*-
"""Escreve o recado da mentora sem precisar editar JSON na mão.

O recado é a única parte do guia que não sai do AVA: é texto escrito por
quem revisou a semana. O arquivo (`docs/revisao.json`) tem campos que
importam e são fáceis de esquecer numa edição manual — a validade, e a lista
de atividades que precisam continuar pendentes para o recado ainda fazer
sentido. Sem eles, um recado errado fica no ar até alguém reparar.

  python automacao/recado.py "Josemar, o foco de hoje é..."
  python automacao/recado.py --arquivo recado.txt --ate 2026-08-15
  python automacao/recado.py --enquanto-pendente 215609 215612
  python automacao/recado.py --limpar
  python automacao/recado.py --ver

Depois, `python automacao/gerar_guia.py --render-only` republica o site.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from configuracao import BR_TZ, DATA_PATH
from persistencia import gravar_json

RECADO_PATH = DATA_PATH.parent / "revisao.json"
# Uma semana é o ritmo da revisão. Recado sem prazo é recado que envelhece no
# ar, e foi por isso que o campo existe desde o começo.
DIAS_DE_VALIDADE = 7


def _fim_do_dia(texto):
    """Aceita "2026-08-15" ou ISO completo; devolve ISO com fuso de Brasília."""
    try:
        quando = datetime.fromisoformat(texto)
    except ValueError:
        raise SystemExit(f"Não entendi a data {texto!r}. Use AAAA-MM-DD.")
    if quando.hour == quando.minute == 0:
        quando = quando.replace(hour=23, minute=59)
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=BR_TZ)
    return quando.isoformat()


def _cmids_conhecidos():
    """Os cmids que a última leitura viu, para avisar sobre número inventado."""
    try:
        dados = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return {
        str(item.get("cmid"))
        for curso in dados.get("courses", [])
        for secao in curso.get("sections", [])
        for item in secao.get("items", [])
        if item.get("cmid") is not None
    }


def escrever(texto, ate=None, enquanto_pendente=(), agora=None):
    texto = (texto or "").strip()
    if not texto:
        raise SystemExit("Recado vazio: nada a escrever.")
    agora = agora or datetime.now(BR_TZ)
    validade = (
        _fim_do_dia(ate)
        if ate
        else (agora + timedelta(days=DIAS_DE_VALIDADE)).replace(
            hour=23, minute=59, second=0, microsecond=0
        ).isoformat()
    )
    return {
        "text": texto,
        "written_at": agora.replace(microsecond=0).isoformat(),
        "kind": "revisao",
        "requires_pending_cmids": [str(c) for c in enquanto_pendente],
        "valid_until": validade,
    }


def _resumo(recado):
    linhas = [
        f"escrito em {recado['written_at'][:16].replace('T', ' ')}",
        f"vale até {recado['valid_until'][:16].replace('T', ' ')}",
    ]
    if recado["requires_pending_cmids"]:
        linhas.append(
            "some se estas atividades forem concluídas: "
            + ", ".join(recado["requires_pending_cmids"])
        )
    return " · ".join(linhas)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("texto", nargs="?", help="o recado, entre aspas")
    parser.add_argument("--arquivo", help="lê o recado de um arquivo .txt/.md")
    parser.add_argument("--ate", help="validade (AAAA-MM-DD); padrão: 7 dias")
    parser.add_argument(
        "--enquanto-pendente", nargs="*", default=[], metavar="CMID",
        help="cmids que precisam continuar pendentes para o recado valer",
    )
    parser.add_argument("--limpar", action="store_true",
                        help="apaga o recado atual")
    parser.add_argument("--ver", action="store_true",
                        help="mostra o recado que está no ar")
    args = parser.parse_args(argv)

    if args.ver:
        if not RECADO_PATH.exists():
            print("Não há recado escrito.")
            return 0
        atual = json.loads(RECADO_PATH.read_text(encoding="utf-8"))
        print(_resumo(atual) + "\n")
        print(atual.get("text", ""))
        return 0

    if args.limpar:
        if RECADO_PATH.exists():
            RECADO_PATH.unlink()
            print("Recado apagado. Rode --render-only para republicar.")
        else:
            print("Não havia recado para apagar.")
        return 0

    texto = args.texto
    if args.arquivo:
        texto = Path(args.arquivo).read_text(encoding="utf-8")
    if not texto:
        parser.error("passe o texto entre aspas ou use --arquivo")

    conhecidos = _cmids_conhecidos()
    desconhecidos = [
        c for c in args.enquanto_pendente
        if conhecidos and str(c) not in conhecidos
    ]
    if desconhecidos:
        # Aviso, não erro: a leitura pode estar velha. Mas cmid que ninguém
        # viu provavelmente é dígito trocado, e um gatilho que nunca dispara
        # é o mesmo que recado sem validade.
        print(f"Aviso: não achei {', '.join(desconhecidos)} na última leitura "
              "do AVA. Confira o número.")

    recado = escrever(texto, args.ate, args.enquanto_pendente)
    gravar_json(RECADO_PATH, recado)
    print(f"Recado gravado em {RECADO_PATH}.")
    print(_resumo(recado))
    print("Agora rode: python automacao/gerar_guia.py --render-only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
