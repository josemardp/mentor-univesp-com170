# -*- coding: utf-8 -*-
"""
Testa o login automatico contra uma copia local das telas de login.

Rodar:  python testes/test_login.py

Nao usa a senha real do Josemar: sobe um servidor de mentira que aceita um
usuario/senha ficticios, e confere se o sessao.py preenche o formulario,
entra, detecta senha errada e detecta falta de credencial.
"""
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "automacao"))
import sessao as S
from playwright.sync_api import sync_playwright

USUARIO_OK, SENHA_OK = "aluno123", "senha-de-mentira"
PORTA = 8791
BASE = f"http://127.0.0.1:{PORTA}"

PAGINA_LOGIN = """<!doctype html><html><head><title>Univesp AVA</title></head><body>
<h1>Acesso ao AVA</h1>{erro}
<form action="/login/index.php" method="post">
  <input type="text" name="username" id="username" placeholder="Usuario">
  <input type="password" name="password" id="password" placeholder="Senha">
  <button type="submit" id="loginbtn">Acessar</button>
</form></body></html>"""

# Copia do fluxo real da Univesp: etapa 1 pede so o e-mail e a senha fica
# escondida; ao clicar em Continuar, vai pro SSO, onde a senha aparece.
ETAPA1 = """<!doctype html><html><head><title>Univesp</title></head><body>
<h1>Login</h1>
<form id="login-form" action="/login/index.php" method="post">
  <input type="text" name="username" id="username" placeholder="CPF ou E-mail">
  <input type="password" name="password" id="password"
         placeholder="Senha" style="display:none">
  <button type="button" id="login-button-default">Continuar</button>
</form>
<script>
document.getElementById('login-button-default').onclick = function () {
  var u = document.getElementById('username').value;
  location.href = '/sso/loginuserpass.php?username=' + encodeURIComponent(u);
};
</script></body></html>"""

ETAPA2 = """<!doctype html><html><head><title>SSO Univesp</title></head><body>
<h1>Sistema Operacional Univesp</h1>{erro}
<form action="/sso/loginuserpass.php" method="post">
  <input type="text" name="username" id="username" value="{usuario}"
         style="display:none">
  <input type="password" name="password" id="password">
  <input type="hidden" name="AuthState" value="abc123">
  <button type="button">visibility</button>
  <button type="submit">ENTRAR</button>
</form></body></html>"""

PAINEL = """<!doctype html><html><head><title>Painel</title></head>
<body><h1>Painel</h1><p>Bem-vindo</p></body></html>"""


DOIS_PASSOS = [False]   # alternado pelos cenarios de teste


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _logado(self):
        return "logado=1" in (self.headers.get("Cookie") or "")

    def do_GET(self):
        if self.path.startswith("/my"):
            if self._logado():
                self._html(PAINEL)
            else:
                self._redir("/login/index.php")
        elif self.path.startswith("/sso/"):
            usuario = parse_qs(self.path.split("?", 1)[-1]).get("username", [""])[0]
            self._html(ETAPA2.format(erro="", usuario=usuario))
        elif self.path.startswith("/login"):
            self._html(ETAPA1 if DOIS_PASSOS[0] else PAGINA_LOGIN.format(erro=""))
        else:
            self._redir("/my/")

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        campos = parse_qs(self.rfile.read(n).decode())
        u = (campos.get("username") or [""])[0]
        s = (campos.get("password") or [""])[0]
        if u == USUARIO_OK and s == SENHA_OK:
            self.send_response(302)
            self.send_header("Set-Cookie", "logado=1; Path=/")
            self.send_header("Location", "/my/")
            self.end_headers()
        elif DOIS_PASSOS[0]:
            self._html(ETAPA2.format(
                erro="<p>Senha incorreta</p>", usuario=u))
        else:
            self._html(PAGINA_LOGIN.format(
                erro="<p>Nome de usuário ou senha inválidos</p>"))

    def _html(self, corpo):
        dados = corpo.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def _redir(self, destino):
        self.send_response(302)
        self.send_header("Location", destino)
        self.end_headers()


falhas = []


def ok(cond, msg):
    print(("  OK   " if cond else "  FALHA") + " | " + msg)
    if not cond:
        falhas.append(msg)


def cenario(navegador, usuario, senha, rotulo):
    for chave in ("AVA_USUARIO", "AVA_SENHA"):
        os.environ.pop(chave, None)
    if usuario:
        os.environ["AVA_USUARIO"] = usuario
    if senha:
        os.environ["AVA_SENHA"] = senha
    ctx = navegador.new_context()
    page = ctx.new_page()
    resultado = S.garantir(page)
    ctx.close()
    print(f"  [{rotulo}] -> {resultado}")
    return resultado


servidor = HTTPServer(("127.0.0.1", PORTA), Fake)
threading.Thread(target=servidor.serve_forever, daemon=True).start()

# aponta o modulo pro servidor de mentira
S.LOGIN_URL = f"{BASE}/login/index.php"
S.PAINEL_URL = f"{BASE}/my/"
S.STATE_PATH = S.STATE_PATH.parent / "nao_existe_state.json"

print("\n== Login de UMA etapa (Moodle padrao) ==")
with sync_playwright() as p:
    nav = p.chromium.launch()

    okk, como = cenario(nav, USUARIO_OK, SENHA_OK, "credencial certa")
    ok(okk and como == "login", "com credencial certa, loga sozinho")

    okk, motivo = cenario(nav, USUARIO_OK, "senha-errada", "senha errada")
    ok(not okk, "com senha errada, nao entra")
    ok("recusou" in motivo, "senha errada da mensagem clara de recusa")
    ok(SENHA_OK not in motivo and "senha-errada" not in motivo,
       "a mensagem de erro NAO contem a senha")

    okk, motivo = cenario(nav, None, None, "sem credencial")
    ok(not okk, "sem credencial, nao entra")
    ok("salvar_credenciais" in motivo, "sem credencial, ensina como resolver")

    # É o fluxo real da Univesp: e-mail numa tela, senha na seguinte, com a
    # senha escondida na primeira. Foi exatamente aqui que o robô falhou.
    print("\n== Login de DUAS etapas (fluxo Univesp/SSO) ==")
    DOIS_PASSOS[0] = True

    okk, como = cenario(nav, USUARIO_OK, SENHA_OK, "duas etapas, credencial certa")
    ok(okk and como == "login", "passa da tela do e-mail e loga no SSO")

    okk, motivo = cenario(nav, USUARIO_OK, "senha-errada", "duas etapas, senha errada")
    ok(not okk, "duas etapas: senha errada nao entra")
    ok("recusou" in motivo, "duas etapas: erro de senha e reconhecido")
    ok(SENHA_OK not in motivo and "senha-errada" not in motivo,
       "duas etapas: mensagem nao contem a senha")

    nav.close()
servidor.shutdown()

print("\n== Vazamento de senha no codigo ==")
fonte = (Path(__file__).resolve().parent.parent / "automacao" / "sessao.py").read_text(encoding="utf-8")
ok("print" not in fonte.split("def _fazer_login")[1].split("def garantir")[0],
   "_fazer_login nao imprime nada")
ok("AVA_SENHA" in fonte and 'os.environ.get("AVA_SENHA")' in fonte,
   "senha vem do ambiente, nao de arquivo")

print("\n" + "=" * 58)
if falhas:
    print(f"{len(falhas)} FALHA(S):")
    for f in falhas:
        print("  - " + f)
    sys.exit(1)
print("Login automatico validado.")
