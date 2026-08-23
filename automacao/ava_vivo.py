# -*- coding: utf-8 -*-
"""
Mantem um Chrome de pe, logado no AVA, para o agente dirigir por CDP.

Por que existe: o AVA usa cookie de SESSAO (MoodleSession, sem validade).
O Chrome descarta cookie de sessao ao fechar, entao a rotina antiga
("abra o nav-login, logue, feche, o headless assume") nunca funcionou pro
AVA nem pro SEI, por mais que o login desse certo. Medido em 23/08/2026:
depois de fechar a janela, o MoodleSession nao existe mais no banco de
cookies do perfil. Nao e o servidor da Univesp derrubando, e o navegador
jogando fora o que nao e persistente.

A solucao e nao fechar o navegador. Este script:
  1. sobe um Chrome headless com porta de depuracao, se ainda nao houver um;
  2. conecta nele por CDP e garante o login, reusando automacao/sessao.py;
  3. sai, deixando o navegador de pe.

O servidor MCP `nav-ava` se pluga na mesma porta e enxerga a sessao viva.
Se a sessao cair no meio de uma tarefa, basta rodar este script de novo:
ele reloga no MESMO navegador, sem reiniciar o agente.

Uso:
    python automacao/ava_vivo.py            sobe e loga (idempotente)
    python automacao/ava_vivo.py --status   so diz como esta, nao mexe
    python automacao/ava_vivo.py --parar    encerra o navegador

A senha nunca e impressa. As mensagens daqui dizem o que houve sem vazar
credencial, mesma regra de sessao.py.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sessao  # noqa: E402

PORTA = 9222
PERFIL = Path(os.environ["USERPROFILE"]) / ".claude-browser" / "perfil-ava"
CDP = f"http://127.0.0.1:{PORTA}"

CHROMES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]


def _credenciais_do_registro():
    """Le AVA_USUARIO/AVA_SENHA do ambiente do usuario no Windows.

    Variavel definida com SetEnvironmentVariable(...,'User') so aparece em
    processos abertos DEPOIS. Como este script costuma ser chamado por um
    agente que ja estava rodando, lemos direto do registro para nao exigir
    que ele reinicie so por causa disso.
    """
    if os.environ.get("AVA_USUARIO") and os.environ.get("AVA_SENHA"):
        return
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            for nome in ("AVA_USUARIO", "AVA_SENHA"):
                if not os.environ.get(nome):
                    try:
                        os.environ[nome] = winreg.QueryValueEx(k, nome)[0]
                    except FileNotFoundError:
                        pass
    except Exception:
        pass  # sem registro acessivel, segue com o que houver no ambiente


def cdp_vivo():
    try:
        with urllib.request.urlopen(f"{CDP}/json/version", timeout=2) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def achar_chrome():
    for c in CHROMES:
        if Path(c).exists():
            return c
    return None


def subir_chrome():
    chrome = achar_chrome()
    if not chrome:
        return False, "Chrome nao encontrado nos caminhos padrao"
    PERFIL.mkdir(parents=True, exist_ok=True)
    args = [
        chrome,
        f"--remote-debugging-port={PORTA}",
        f"--user-data-dir={PERFIL}",
        "--headless=new",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-timer-throttling",
        "about:blank",
    ]
    # DETACHED_PROCESS: o navegador precisa sobreviver ao fim deste script e
    # ao fim da sessao do agente que o chamou.
    flags = 0x00000008 | 0x00000200 if os.name == "nt" else 0
    subprocess.Popen(args, creationflags=flags,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(1)
        if cdp_vivo():
            return True, "navegador de pe"
    return False, "subi o Chrome mas a porta de depuracao nao respondeu"


def garantir_login():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        navegador = p.chromium.connect_over_cdp(CDP)
        ctx = navegador.contexts[0] if navegador.contexts else navegador.new_context()
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        ok, como = sessao.garantir(page)
        if ok:
            # guarda o retrato pro robo diario comecar rapido tambem
            try:
                sessao.salvar_sessao(ctx)
            except Exception:
                pass
        return ok, como


def parar():
    """Encerra SO os chrome.exe deste perfil.

    Nada de filtro generico aqui: um taskkill largo derrubaria o navegador
    de outra identidade, ou o Chrome pessoal dele. O alvo e a linha de
    comando que contem o caminho do perfil-ava, e nada mais.
    """
    if not cdp_vivo():
        return "nao havia navegador de pe"
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
        f"Where-Object {{ $_.CommandLine -like '*{PERFIL.name}*' }} | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   capture_output=True)
    time.sleep(2)
    return "navegador encerrado" if not cdp_vivo() else "ainda respondendo na porta"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status", action="store_true", help="so relata, nao mexe")
    ap.add_argument("--parar", action="store_true", help="encerra o navegador")
    a = ap.parse_args()

    if a.parar:
        print(parar())
        return 0

    info = cdp_vivo()
    if a.status:
        print(f"porta {PORTA}: {'viva' if info else 'sem resposta'}")
        if info:
            print(f"  {info.get('Browser', '?')}")
        _credenciais_do_registro()
        tem = bool(os.environ.get("AVA_USUARIO") and os.environ.get("AVA_SENHA"))
        print(f"credenciais no ambiente: {'sim' if tem else 'NAO'}")
        print(f"perfil: {PERFIL}")
        return 0

    _credenciais_do_registro()
    if not (os.environ.get("AVA_USUARIO") and os.environ.get("AVA_SENHA")):
        print("[X] sem AVA_USUARIO/AVA_SENHA no ambiente do usuario.")
        print("    Grave as duas e rode de novo.")
        return 1

    if not info:
        ok, motivo = subir_chrome()
        print(f"  {motivo}")
        if not ok:
            return 1
    else:
        print("  navegador ja estava de pe")

    ok, como = garantir_login()
    if not ok:
        print(f"[X] {como}")
        return 1
    print(f"[ok] AVA logado ({como}). CDP em {CDP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
