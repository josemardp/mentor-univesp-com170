# -*- coding: utf-8 -*-
"""
Ponto de entrada do guia. Mantido com o mesmo nome de sempre pra nao quebrar
o renovar_sessao.bat nem a GitHub Action.

  python automacao/gerar_guia.py                 entra no AVA e regera o site
  python automacao/gerar_guia.py --render-only    so regera o site (sem AVA)

O trabalho de verdade esta em:
  coletar.py  le o AVA (paginas, calendario, foruns, notificacoes, mensagens)
  render.py   monta o docs/index.html
"""
import sys

import coletar
import render


def main():
    if "--render-only" in sys.argv:
        return render.main()
    codigo = coletar.main()
    if codigo:
        return codigo
    return render.main()


if __name__ == "__main__":
    raise SystemExit(main())
