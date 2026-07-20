"""
Captura a sessao de login do AVA Univesp para uso pelo robo diario.

Abre um navegador de verdade. O USUARIO digita o proprio login e senha
na janela que abre - este script nunca le nem grava a senha em lugar
nenhum. Depois do login, salva so os cookies de sessao (storage_state)
em automacao/storage_state.json, que fica fora do git (.gitignore).

Rodar de novo sempre que o robo avisar que a sessao expirou.
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_PATH = Path(__file__).parent / "storage_state.json"
LOGIN_URL = "https://ava.univesp.br/my/"


def main():
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
            print("Login nao foi detectado em 5 minutos. Rode o script de novo.")
            browser.close()
            sys.exit(1)

        context.storage_state(path=str(OUT_PATH))
        browser.close()
        print(f"Sessao salva em {OUT_PATH}")
        print("Agora rode: python automacao/publicar_sessao_no_github.py")


if __name__ == "__main__":
    main()
