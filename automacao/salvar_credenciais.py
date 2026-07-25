# -*- coding: utf-8 -*-
"""
Guarda seu login do AVA no cofre de Secrets do GitHub, uma vez so.

Depois disso o robo se vira sozinho: quando a sessao vencer, ele loga de
novo e segue. Voce nao precisa mais renovar nada na mao.

Como funciona, e por que e seguro:
  - a senha e digitada sem aparecer na tela (nem asteriscos);
  - ela NAO e gravada em arquivo nenhum, nem entra no repositorio;
  - vai direto pro cofre de Secrets do GitHub, que e criptografado e
    separado do codigo. Nem eu nem ninguem le o valor depois de salvo;
  - o repositorio e publico, entao senha em arquivo estaria a vista de
    todo mundo. Por isso o cofre, e so o cofre.

Rode com 2 cliques em salvar_credenciais.bat.
"""
import getpass
import subprocess
import sys

REPO = "esdraaline/mentor-univesp-com170"


def gh_ok():
    try:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def gravar(nome, valor):
    """Manda pro GitHub via stdin, pra o valor nao aparecer na linha de comando."""
    r = subprocess.run(
        ["gh", "secret", "set", nome, "--repo", REPO],
        input=valor, text=True, capture_output=True,
    )
    if r.returncode != 0:
        # a saida do gh nao contem o valor, so o nome do segredo
        print(f"  falhou ao gravar {nome}: {r.stderr.strip()[:200]}")
        return False
    print(f"  {nome} guardado no cofre.")
    return True


def main():
    print("\n=== Credenciais do AVA ===\n")
    print("Isso guarda seu login no cofre do GitHub pra o robo nunca mais parar")
    print("por sessao vencida. A senha nao aparece na tela e nao vai pra arquivo.\n")

    if not gh_ok():
        print("O GitHub CLI nao esta conectado nesta maquina.")
        print("Abra o terminal, rode 'gh auth login', e depois tente de novo.")
        return 1

    usuario = input("Usuario do AVA (o mesmo que voce digita no site): ").strip()
    if not usuario:
        print("Usuario vazio. Cancelei, nada foi gravado.")
        return 1

    senha = getpass.getpass("Senha do AVA (nao vai aparecer nada enquanto digita): ")
    if not senha:
        print("Senha vazia. Cancelei, nada foi gravado.")
        return 1
    confere = getpass.getpass("Digite a senha de novo pra conferir: ")
    if senha != confere:
        print("As duas senhas nao bateram. Cancelei, nada foi gravado.")
        return 1

    print("\nGravando no cofre do GitHub...")
    if not gravar("AVA_USUARIO", usuario):
        return 1
    if not gravar("AVA_SENHA", senha):
        return 1

    # some da memoria assim que possivel
    senha = confere = None

    print("\nPronto. O robo agora loga sozinho quando a sessao vencer.")
    print("Se voce trocar a senha da Univesp um dia, rode este script de novo.\n")

    resposta = input("Quer disparar o robo agora pra testar? [S/n] ").strip().lower()
    if resposta in ("", "s", "sim", "y"):
        subprocess.run(["gh", "workflow", "run", "guia-diario.yml", "--repo", REPO])
        print("\nRobo disparado. Acompanhe com:")
        print(f"  gh run watch --repo {REPO}")
        print("Ou veja o site em alguns minutos:")
        print("  https://esdraaline.github.io/mentor-univesp-com170/")
    return 0


if __name__ == "__main__":
    codigo = main()
    input("\nPressione ENTER pra fechar esta janela...")
    sys.exit(codigo)
