# -*- coding: utf-8 -*-
"""Primitivas comuns do Moodle e erros operacionais normalizados."""
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class FalhaFonte(RuntimeError):
    """Falha operacional conhecida que permite usar o último cache válido."""


class SessaoExpirada(FalhaFonte):
    """Caiu para a tela de login. Insistir não resolve, só gasta orçamento."""


JS_API = """
async ([nome, args]) => {
  const sk = (window.M && M.cfg && M.cfg.sesskey) || null;
  if (!sk) return { error: true, motivo: 'sem sesskey' };
  const r = await fetch('/lib/ajax/service.php?sesskey=' + sk + '&info=' + nome, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify([{ index: 0, methodname: nome, args: args }]),
  });
  const j = await r.json();
  return j[0];
}
"""


def api(page, metodo, args):
    try:
        resposta = page.evaluate(JS_API, [metodo, args])
    except (PlaywrightTimeoutError, PlaywrightError, TimeoutError) as erro:
        raise FalhaFonte(
            f"API {metodo} não executou ({type(erro).__name__})"
        ) from erro
    if not resposta:
        raise FalhaFonte(f"API {metodo} não respondeu")
    if resposta.get("error"):
        excecao = resposta.get("exception") or {}
        motivo = (
            excecao.get("message")
            or resposta.get("motivo")
            or "sem detalhe"
        )
        raise FalhaFonte(f"API {metodo} recusou: {str(motivo)[:160]}")
    return resposta.get("data")


def api_opcional(page, metodo, args):
    """Compatibilidade: falha operacional vira ``None`` e fica visível no log."""
    try:
        return api(page, metodo, args)
    except FalhaFonte as erro:
        print(f"  aviso: {erro}")
        return None


def user_id(page):
    try:
        return page.evaluate(
            "() => (window.M && M.cfg && M.cfg.userId) || null"
        )
    except (PlaywrightTimeoutError, PlaywrightError, TimeoutError):
        return None


def deslogado(page):
    return "/login" in page.url or "univesp_login.php" in page.url


def navegar(page, url, timeout=45000, espera_ms=0):
    """Navega convertendo somente falhas do navegador em ``FalhaFonte``."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        if espera_ms:
            page.wait_for_timeout(espera_ms)
    except (PlaywrightTimeoutError, PlaywrightError, TimeoutError) as erro:
        raise FalhaFonte(
            f"não consegui abrir {url} ({type(erro).__name__})"
        ) from erro
    if deslogado(page):
        raise SessaoExpirada(f"sessão expirou ao abrir {url}")


def navegar_insistindo(
    page, url, timeout=45000, espera_ms=0, tentativas=3, rotulo=None
):
    """Uma soneca de rede não pode custar a leitura inteira daquela página.

    Em 09/08/2026 uma única falha em 34 fóruns marcou a rodada como degradada,
    deixou a Action vermelha e o site anunciando "leitura parcial" — por um
    tropeço que a segunda tentativa teria resolvido. Só falha transitória é
    repetida: sessão expirada não melhora insistindo, e cada tentativa a mais
    gastaria o orçamento de páginas que ainda dá para ler logadas.

    Cada tentativa perdida é impressa: falha silenciosa foi o que impediu
    descobrir, pelo log da nuvem, qual fórum tinha caído.
    """
    ultima = None
    for tentativa in range(1, max(1, tentativas) + 1):
        try:
            navegar(page, url, timeout=timeout, espera_ms=espera_ms)
            if tentativa > 1:
                print(f"    ok na {tentativa}ª tentativa: {rotulo or url}")
            return
        except SessaoExpirada:
            raise
        except FalhaFonte as erro:
            ultima = erro
            print(
                f"    tentativa {tentativa}/{tentativas} falhou em "
                f"{rotulo or url}: {erro}"
            )
            if tentativa < tentativas:
                page.wait_for_timeout(1500 * tentativa)
    raise ultima
