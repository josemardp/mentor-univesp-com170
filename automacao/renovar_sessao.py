# -*- coding: utf-8 -*-
"""
Renovacao da sessao do AVA em um passo so.

Abre o navegador pra voce logar (nunca ve nem guarda sua senha), sobe a
sessao nova como segredo do GitHub, e dispara o robo na hora pra
confirmar que voltou a funcionar. Pensado pra rodar com um duplo clique
(veja renovar_sessao.bat), sem precisar abrir terminal nem lembrar de
dois comandos.
"""
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
STATE_PATH = ROOT / "storage_state.json"
REPO = "esdraaline/mentor-univesp-com170"
LOGIN_URL = "https://ava.univesp.br/my/"


def capturar():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(LOGIN_URL)

        print("\n>>> Faca login normalmente na janela que abriu.")
        print(">>> Este script NAO ve nem guarda sua senha.")
        print(">>> Assim que a pagina 'Painel' do AVA aparecer, ele continua sozinho.\n")

        try:
            page.wait_for_url("**/my/**", timeout=5 * 60 * 1000)
            page.wait_for_load_state("networkidle", timeout=30 * 1000)
        except Exception:
            print("Login nao foi detectado em 5 minutos. Feche a janela e tente de novo.")
            browser.close()
            return False

        context.storage_state(path=str(STATE_PATH))
        browser.close()
        print("Sessao capturada.")
        return True


def publicar():
    result = subprocess.run(
        ["gh", "secret", "set", "AVA_STORAGE_STATE", "--repo", REPO],
        stdin=open(STATE_PATH, "rb"),
    )
    if result.returncode != 0:
        print("Falha ao subir o segredo no GitHub. A copia local nao foi apagada.")
        return False
    STATE_PATH.unlink()
    print("Segredo atualizado no GitHub.")
    return True


def confirmar():
    print("Disparando o robo pra confirmar que a sessao nova funciona...")
    subprocess.run(["gh", "workflow", "run", "guia-diario.yml", "--repo", REPO])
    print("\nPronto! O robo esta rodando na nuvem com a sessao nova.")
    print("Confira em alguns minutos: https://esdraaline.github.io/mentor-univesp-com170/")
    print("Ou acompanhe agora: gh run watch --repo " + REPO)


def main():
    if not capturar():
        sys.exit(1)
    if not publicar():
        sys.exit(1)
    confirmar()


if __name__ == "__main__":
    main()
    input("\nPressione ENTER pra fechar esta janela...")
