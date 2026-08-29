# -*- coding: utf-8 -*-
"""
Sessão do Outlook institucional pro robô, feita uma vez, com você aprovando
o MFA no celular.

Por que existe: o Outlook (conta-academica@exemplo.edu.br) federa pro mesmo SSO
do AVA, mas passa pelo Microsoft Entra ID antes, e essa conta tem aprovação
por push do Authenticator configurada ali — a cada sessão nova, não só na
primeira vez. O AVA e o Portal do aluno nunca passam pelo Entra ID e nunca
pedem isso; o Outlook pede sempre. O robô roda sozinho na nuvem, cinco vezes
por dia, sem ninguém com o celular na mão pra aprovar.

A saída é a mesma que este projeto já usa pro Sistema de Provas, que fica
atrás de verificação anti-robô: não contornar, e sim guardar uma sessão já
aprovada por você, uma vez, pro robô reaproveitar. Ela dura enquanto a
Microsoft mantiver "conectado" — costuma ser semanas, não um dia. Quando
vencer, a fonte "outlook" do guia passa a dizer isso sozinha (fica em
"falhou", com a mensagem pedindo pra rodar este script de novo), e o resto
do guia continua normal, do jeito que já continua sem o Portal quando ele
cai.

O que este script faz:
  1. Abre um Chrome VISÍVEL — você precisa ver a tela pra aprovar o MFA.
  2. Você faz o login à mão: aprova no Authenticator e clica em
     "Sim" / "Manter-me conectado" quando a Microsoft perguntar. É esse
     "sim" que faz a sessão durar semanas em vez de um dia.
  3. Assim que a caixa de entrada aparecer na tela, aperte ENTER aqui no
     terminal. O script confere que saiu da tela de login antes de salvar.
  4. A sessão (só cookies, nunca a senha) vai direto pro cofre de Secrets do
     GitHub, como OUTLOOK_STORAGE_STATE. Não fica gravada em arquivo nenhum
     deste computador.

Rode com:  python automacao/capturar_sessao_outlook.py
"""
import json
import subprocess
import sys

from playwright.sync_api import sync_playwright

REPO = "esdraaline/mentor-univesp-com170"
MAIL_URL = "https://outlook.office.com/mail/"
DOMINIOS_DE_LOGIN = (
    "login.microsoftonline.com",
    "login.univesp.br",
    "login.live.com",
)


def gh_ok():
    try:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def gravar(nome, valor):
    """Manda pro GitHub via stdin, pro valor não aparecer na linha de comando."""
    r = subprocess.run(
        ["gh", "secret", "set", nome, "--repo", REPO],
        input=valor, text=True, capture_output=True,
    )
    if r.returncode != 0:
        # a saída do gh não contém o valor, só o nome do segredo
        print(f"  falhou ao gravar {nome}: {r.stderr.strip()[:300]}")
        return False
    print(f"  {nome} guardado no cofre.")
    return True


def main():
    print("\n=== Sessão do Outlook institucional ===\n")
    if not gh_ok():
        print("O GitHub CLI não está conectado nesta máquina.")
        print("Abra o terminal, rode 'gh auth login', e depois tente de novo.")
        return 1

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=False)
        contexto = navegador.new_context()
        page = contexto.new_page()
        try:
            page.goto(MAIL_URL, wait_until="domcontentloaded", timeout=45000)
        except Exception as erro:
            print(f"Não consegui abrir o Outlook ({type(erro).__name__}).")
            navegador.close()
            return 1

        print("Uma janela do Chrome abriu. Faça o login com a conta")
        print("conta-academica@exemplo.edu.br: aprove o pedido no Authenticator e")
        print('clique em "Sim" quando ele perguntar se quer continuar')
        print("conectado. Deixe a janela aberta até a caixa de e-mail aparecer.\n")
        input("Pressione ENTER aqui quando a caixa de e-mail estiver na tela... ")

        pronto = False
        for _ in range(5):
            url = page.url or ""
            if not any(dominio in url for dominio in DOMINIOS_DE_LOGIN):
                pronto = True
                break
            print("Ainda parece estar na tela de login. Aguardando mais um pouco...")
            page.wait_for_timeout(3000)

        if not pronto:
            print("\nNão consegui confirmar que o login terminou. Cancelei, nada foi salvo.")
            navegador.close()
            return 1

        estado = contexto.storage_state()
        navegador.close()

    # Secret do GitHub tem teto de ~64KB. A sessão inteira (cookies +
    # localStorage de cada origem) passa disso fácil — o grosso é cache de
    # app do próprio Outlook (React, feature flags), que não autentica nada.
    # Quem prova a sessão pro Entra ID/Univesp são os cookies; sem eles não
    # tem MFA persistido, e é exatamente isso que este script existe pra
    # guardar. Sessão sem os cookies certos falha na primeira leitura do
    # robô, e falha declarado (ver fontes/outlook_univesp.py) — não falha
    # silenciosa.
    estado_compacto = {"cookies": estado.get("cookies", [])}
    valor = json.dumps(estado_compacto)
    print(
        f"\nSessão inteira tinha {len(json.dumps(estado))} caracteres; só os "
        f"cookies (o que autentica) são {len(valor)}. Gravando no cofre do GitHub..."
    )
    ok = gravar("OUTLOOK_STORAGE_STATE", valor)
    valor = None  # some da memória assim que possível
    if not ok:
        return 1

    print("\nPronto. O robô já pode ler o Outlook institucional.")
    print('Quando a sessão vencer, a fonte "outlook" do guia vai avisar')
    print("sozinha (fica em falhou); aí é só rodar este script de novo.\n")
    return 0


if __name__ == "__main__":
    codigo = main()
    input("\nPressione ENTER pra fechar esta janela...")
    sys.exit(codigo)
