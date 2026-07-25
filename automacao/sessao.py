# -*- coding: utf-8 -*-
"""
Garante que o robo esteja logado no AVA, sem depender de ninguem.

Ordem que ele tenta:
  1. Sessao salva (storage_state), que e o caminho rapido.
  2. Se a sessao caiu, faz login com AVA_USUARIO e AVA_SENHA, lidos do
     ambiente. Na nuvem isso vem dos Secrets do GitHub; na sua maquina,
     de variaveis de ambiente. A senha NUNCA e escrita em arquivo, nem
     no repositorio, nem em log.

Por que existe: antes, quando a sessao vencia, o robo parava e ficava
esperando alguem renovar na mao. Agora ele mesmo resolve.

Nunca imprima o conteudo de AVA_SENHA aqui. As mensagens de erro deste
modulo sao escritas pra dizer o que houve sem vazar credencial.
"""
import os
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent / "storage_state.json"
AVA = "https://ava.univesp.br"
LOGIN_URL = f"{AVA}/login/index.php"
PAINEL_URL = f"{AVA}/my/"

CAMPOS_USUARIO = ['input[name="username"]', "#username",
                  'input[type="text"][autocomplete*="user"]']
CAMPOS_SENHA = ['input[name="password"]', "#password", 'input[type="password"]']
BOTOES = ["#loginbtn", 'button[type="submit"]', 'input[type="submit"]',
          'button:has-text("Acessar")', 'button:has-text("Entrar")']

ERROS_LOGIN = ["invalid login", "nome de usuário ou senha", "usuário ou senha",
               "credenciais inválidas", "senha incorreta"]


def novo_contexto(navegador):
    """Contexto do navegador, reaproveitando a sessao salva quando houver."""
    if STATE_PATH.exists():
        try:
            return navegador.new_context(storage_state=str(STATE_PATH))
        except Exception:
            pass  # arquivo corrompido: segue sem ele, o login resolve
    return navegador.new_context()


def esta_logado(page):
    url = page.url or ""
    return "/login" not in url and "univesp_login.php" not in url


def _primeiro(page, seletores):
    """Primeiro seletor que existe de verdade na pagina."""
    for sel in seletores:
        alvo = page.locator(sel).first
        try:
            if alvo.count() and alvo.is_visible():
                return alvo
        except Exception:
            continue
    return None


def _tem_credenciais():
    return bool(os.environ.get("AVA_USUARIO") and os.environ.get("AVA_SENHA"))


def _fazer_login(page):
    """Preenche o formulario do AVA. Devolve (ok, motivo)."""
    usuario = os.environ.get("AVA_USUARIO")
    senha = os.environ.get("AVA_SENHA")
    if not (usuario and senha):
        return False, ("sem AVA_USUARIO/AVA_SENHA configurados "
                       "(rode automacao/salvar_credenciais.bat)")

    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1200)
    except Exception as e:
        return False, f"nao consegui abrir a tela de login ({type(e).__name__})"

    campo_usuario = _primeiro(page, CAMPOS_USUARIO)
    campo_senha = _primeiro(page, CAMPOS_SENHA)
    if not campo_usuario or not campo_senha:
        return False, ("a tela de login mudou de formato, nao achei os campos "
                       f"(URL: {page.url})")

    try:
        campo_usuario.fill(usuario)
        campo_senha.fill(senha)          # o valor nao vai pra log
        botao = _primeiro(page, BOTOES)
        if botao:
            botao.click()
        else:
            campo_senha.press("Enter")
        page.wait_for_timeout(3500)
        page.wait_for_load_state("domcontentloaded", timeout=45000)
    except Exception as e:
        return False, f"falhei ao enviar o formulario ({type(e).__name__})"

    # A recusa aparece na resposta do proprio formulario. Se formos direto pro
    # painel, o AVA redireciona pro login limpo e a mensagem some, entao a
    # leitura do erro precisa vir antes de qualquer navegacao.
    corpo = ""
    try:
        corpo = page.locator("body").inner_text()[:2000].lower()
    except Exception:
        pass
    if any(e in corpo for e in ERROS_LOGIN):
        return False, ("o AVA recusou usuario ou senha. A senha da Univesp pode ter "
                       "mudado: rode automacao/salvar_credenciais.bat pra atualizar")

    # o AVA as vezes cai numa pagina intermediaria; confirma pelo painel
    try:
        page.goto(PAINEL_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
    except Exception:
        pass

    if esta_logado(page):
        return True, "login feito"
    return False, "enviei o login mas o AVA nao abriu o painel"


def garantir(page):
    """Deixa a pagina logada no AVA.

    Devolve (ok, como): 'sessao' quando a sessao salva ainda valia,
    'login' quando precisou logar, e None com o motivo quando nao deu.
    """
    try:
        page.goto(PAINEL_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1200)
    except Exception as e:
        return False, f"nao consegui abrir o AVA ({type(e).__name__})"

    if esta_logado(page):
        return True, "sessao"

    if not _tem_credenciais():
        return False, ("a sessao expirou e nao ha credenciais configuradas. "
                       "Rode automacao/salvar_credenciais.bat pra o robo "
                       "passar a se virar sozinho")

    print("  sessao expirada, fazendo login com as credenciais salvas...")
    ok, motivo = _fazer_login(page)
    if not ok:
        return False, motivo
    return True, "login"


def salvar_sessao(contexto):
    """Guarda a sessao renovada pro proximo run comecar rapido."""
    try:
        contexto.storage_state(path=str(STATE_PATH))
    except Exception:
        pass
