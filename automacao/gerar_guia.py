# -*- coding: utf-8 -*-
"""
Ponto de entrada do guia. Mantido com o mesmo nome de sempre pra nao quebrar
a GitHub Action.

  python automacao/gerar_guia.py                 entra no AVA e regera o site
  python automacao/gerar_guia.py --render-only    so regera o site (sem AVA)

O trabalho de verdade esta em:
  coletar.py  le o AVA (paginas, calendario, foruns, notificacoes, mensagens)
  render.py   monta o docs/index.html

Fora daqui, dois utilitarios de mao:
  salvar_credenciais.py  guarda AVA_USUARIO/AVA_SENHA no cofre do GitHub
  recado.py              escreve o recado da mentora em docs/revisao.json
"""
import sys

import coletar
import render


def main():
    if "--render-only" in sys.argv:
        return render.main()

    codigo = coletar.main()

    # Renderiza SEMPRE, inclusive quando a coleta veio incompleta: é
    # justamente aí que o site precisa exibir "não consegui ler o AVA". Antes
    # este return saía antes do render, então o aviso que o coletar gravou no
    # data.json nunca chegava à tela, nem o e-mail era enviado.
    saida = render.main()
    if saida:
        return saida

    # Coleta ruim não derruba o passo: o site e o e-mail ainda precisam sair
    # com o alerta. Quem falha a Action é o passo "Verificar saúde da coleta",
    # depois de publicar.
    if codigo:
        print("Coleta incompleta: site e e-mail vão sair com o aviso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
