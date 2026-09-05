# -*- coding: utf-8 -*-
"""Outlook institucional (``conta-academica@exemplo.edu.br``), quarto sistema, com
um jeito de logar que os outros três não têm.

Lê duas pastas: a caixa de entrada e o Lixo Eletrônico. A segunda existe
porque um aviso de prazo pode cair ali por engano do filtro de spam, e sem
olhar essa pasta o guia nunca saberia. Uma falha ao ler o Lixo Eletrônico não
derruba a leitura da caixa de entrada — cada pasta é uma leitura própria,
mesma filosofia de fonte independente do resto do pipeline.

O AVA e o Portal do aluno também passam pelo SSO da Univesp
(``login.univesp.br``), e por isso reaproveitam ``AVA_USUARIO``/``AVA_SENHA``
sem segredo novo — confirmado ao vivo em 28/08/2026, abrindo
``outlook.office.com/mail/`` num contexto limpo e vendo o redirecionamento
cair no mesmo ``login.univesp.br``. Até aí, mesma família de ``fontes/portal.py``.

A diferença que muda tudo: o Outlook é produto Microsoft 365, então o
caminho passa pelo Microsoft Entra ID antes de chegar à Univesp, e esta
conta tem MFA por push obrigatório configurado ali (aprovação no
Authenticator, a cada sessão nova). O AVA e o Portal nunca passam pelo Entra
ID, e por isso nunca viram essa tela. Não existe jeito de aprovar push sem
alguém com o celular na mão, e o robô roda sozinho, cinco vezes por dia, sem
ninguém olhando.

A saída é a mesma que este projeto já usa pro Sistema de Provas, que fica
atrás de verificação anti-robô (ver ``fontes/portal.py``): não contornar.
Em vez de logar do zero a cada rodada, esta fonte reaproveita uma sessão já
aprovada por um humano uma vez, salva pelo
``automacao/capturar_sessao_outlook.py`` no Secret ``OUTLOOK_STORAGE_STATE``.
Sem esse Secret, ou quando a sessão salva vence, a fonte devolve
``nao_aplicavel``/``falhou`` com a instrução de rodar a captura de novo — o
guia segue publicando as outras fontes normalmente, do mesmo jeito que já
segue sem o Portal quando ele cai.

Precaução deliberada: esta fonte **nunca** guarda o texto das mensagens em
cache entre rodadas (ver ``resultado``). O cache de outras fontes (boletim,
notas do portal) vive em ``docs/estado.json``, que é commitado no repositório
público — correto para nota e disciplina, que são dados dele sobre o próprio
curso, mas não para o conteúdo de uma caixa de e-mail, que pode trazer dado
de terceiro. Cada rodada lê ao vivo ou devolve vazio; nada de e-mail antigo
fica gravado no histórico do git por causa desta fonte.
"""
import json
import os
import re

from playwright.sync_api import Error as PlaywrightError

from configuracao import MAX_MENSAGENS_LIXO_OUTLOOK, MAX_MENSAGENS_OUTLOOK
from dominio.datas import sem_acento
from modelos import SourceResult

MAIL_URL = "https://outlook.office.com/mail/"
# Rota padrão do OWA para o Lixo Eletrônico (mesmo id que a Graph API usa:
# "junkemail"). Mesmo shell, mesma mecânica de leitura da caixa de entrada.
JUNK_URL = "https://outlook.office.com/mail/junkemail"
DOMINIOS_DE_LOGIN = (
    "login.microsoftonline.com",
    "login.univesp.br",
    "login.live.com",
)

# Onde a mecânica de leitura foi levantada e testada: sec-hotmail/references/
# outlook-web-mecanica.md (skill separada, mesma família de produto — Outlook
# web). Confirmado em 28/08/2026 que a Univesp usa o mesmo shell e os mesmos
# seletores do Hotmail pessoal: div[role="option"] com aria-label e
# aria-setsize, dois div.customScrollBar dos quais só um rola de verdade.
JS_TOTAL_OPCOES = 'document.querySelectorAll(\'div[role="option"]\').length'
JS_ROTULOS = (
    '[...document.querySelectorAll(\'div[role="option"]\')]'
    ".map(e => e.getAttribute('aria-label')).filter(Boolean)"
)
JS_ARIA_SETSIZE = """() => {
    const el = document.querySelector('div[role="option"]');
    return el ? parseInt(el.getAttribute('aria-setsize') || '0', 10) : 0;
}"""
JS_ROLAR = """() => {
    const sc = [...document.querySelectorAll('div.customScrollBar')]
        .filter(e => e.querySelectorAll('div[role="option"]').length > 0)
        .filter(e => e.scrollHeight > e.clientHeight + 10)[0];
    if (!sc) return false;
    sc.scrollTop = Math.min(sc.scrollTop + sc.clientHeight * 0.6, sc.scrollHeight);
    return true;
}"""
# Confirmado ao vivo em 30/08/2026 no Lixo Eletrônico (que estava genuinamente
# vazio): sem isto, ``_varrer_caixa`` não distingue "pasta vazia" de "leitura
# travou" — as duas chegam como "nenhum div[role=option] apareceu", e sem essa
# distinção uma pasta vazia (o caso bom) virava aviso de falha no site.
JS_PASTA_VAZIA = """() => (
    document.querySelectorAll('div[role="option"]').length === 0
    && /Nenhum conteúdo em/.test(document.body.innerText)
)"""

# Quando a lista não monta, "a lista de mensagens não montou" não diz o que a
# tela está mostrando, e foi por isso que esta fonte já morreu três vezes sem
# ninguém saber o motivo (30/08, 31/08 e a recaída achada em 05/09/2026).
#
# O diagnóstico vai parar em ``docs/data.json``, que é PÚBLICO (Pages + git).
# Por isso ele nunca publica o texto da página nem o título: publica só o
# endereço (origem + caminho, sem query), quais marcadores desta lista fixa
# casaram, e três contagens genéricas. Marcador é vocabulário fechado — nada
# do que estiver escrito na tela vaza por ele.
MARCADORES_DE_TELA = (
    ("tela de login dentro do app", (
        "entrar em sua conta", "escolha uma conta", "pick an account",
        "sign in", "insira a senha", "manter-me conectado",
    )),
    ("sessão expirada", (
        "sua sessao expirou", "session has expired", "faca login novamente",
        "sign in again", "sua sessao terminou",
    )),
    ("erro do próprio Outlook", (
        "algo deu errado", "something went wrong", "nao foi possivel carregar",
        "couldn't load", "tente novamente mais tarde",
    )),
    ("verificação anti-robô", (
        "verificacao de seguranca", "captcha", "confirme que voce",
    )),
    ("acesso negado", (
        "nao tem permissao", "access denied", "acesso negado",
    )),
)

JS_DIAGNOSTICO = """() => ({
    endereco: location.origin + location.pathname,
    texto: (document.body && document.body.innerText) || '',
    iframes: document.querySelectorAll('iframe').length,
    opcoes: document.querySelectorAll('div[role="option"]').length,
})"""


def _tem_sessao_persistida():
    return bool(os.environ.get("OUTLOOK_STORAGE_STATE"))


def _logado(page):
    url = page.url or ""
    return not any(dominio in url for dominio in DOMINIOS_DE_LOGIN)


def _resumo_erro(erro):
    """Primeira linha da mensagem, sem o "Call log" que o Playwright anexa.

    Antes só saía ``type(erro).__name__`` — quase sempre "Error", a classe
    genérica do Playwright, que não diz nada sobre o que realmente parou a
    leitura. Confirmado em 30/08/2026: duas rodadas seguidas falharam com
    esse nome sozinho, e não deu pra saber se foi timeout, navegação
    interrompida ou outra coisa sem essa linha.
    """
    primeira_linha = str(erro).strip().splitlines()[0] if str(erro).strip() else ""
    return primeira_linha[:160] or type(erro).__name__


SESSAO_VENCIDA = (
    "a sessão salva do Outlook não vale mais (parou na tela de login). "
    "Rode automacao/capturar_sessao_outlook.py de novo e atualize o Secret "
    "OUTLOOK_STORAGE_STATE"
)

# Quantas amostras seguidas fora do domínio de login provam que a página
# assentou. Uma só não prova nada — ver `_abrir_caixa`.
CONFIRMACOES_FORA_DO_LOGIN = 3


def _abrir_caixa(page, url=MAIL_URL):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except PlaywrightError as erro:
        return False, f"não consegui abrir o Outlook ({_resumo_erro(erro)})"

    # A conferência era uma amostra só: bastava UM instante fora do domínio de
    # login para a fonte se declarar logada, e o primeiro instante é logo
    # depois do `domcontentloaded`, quando a página ainda está em
    # outlook.office.com e o redirecionamento para o login sequer começou.
    # Resultado: sessão vencida passava por aqui como boa e ia morrer 30s
    # adiante em `_varrer_caixa`, publicando "a lista de mensagens não montou"
    # — sintoma genérico — em vez desta mensagem, que já existia e diz o que
    # fazer. Foi assim que a fonte passou cinco dias pedindo o conserto errado.
    #
    # Medido ao vivo em 05/09/2026, com o diagnóstico novo: a tela tinha
    # parado em login.microsoftonline.com/common/oauth2/v2.0/authorize.
    #
    # Agora a página precisa ficar fora do login em amostras seguidas. Sessão
    # boa assenta fora do login e alcança; sessão vencida assenta NO login e
    # nunca alcança. O redirecionamento no meio do caminho deixa de enganar.
    seguidas = 0
    for _ in range(20):
        seguidas = seguidas + 1 if _logado(page) else 0
        if seguidas >= CONFIRMACOES_FORA_DO_LOGIN:
            return True, ""
        page.wait_for_timeout(1000)
    return False, SESSAO_VENCIDA


def _varrer_caixa(page, teto=MAX_MENSAGENS_OUTLOOK):
    """Junta os ``aria-label`` da lista, rolando até estabilizar ou até o teto.

    Chaveado por ``aria-label`` (nunca por ``aria-posinset``, que vem "0" em
    quase toda linha — armadilha registrada na referência do sec-hotmail).
    Devolve ``(mensagens, aviso)``: ``aviso`` não é ``None`` quando a lista
    não montou, ou quando o teto foi atingido, ou quando a contagem final
    ficou abaixo do que a própria caixa anuncia via ``aria-setsize`` — nesse
    último caso não trava a rodada, só registra a discrepância, mesma
    filosofia do teto de conferência em ``pipeline.py``.
    """
    try:
        # 30 tentativas de 1s, tolerando navegação em andamento: confirmado em
        # 30/08/2026, com o diagnóstico de erro melhorado, que a falha real no
        # runner do GitHub Actions era "Execution context was destroyed, most
        # likely because of a navigation" — `_abrir_caixa` já tinha saído da
        # tela de login, mas a página ainda estava trocando de URL (do
        # `outlook.office.com` genérico para a URL de sessão do
        # `outlook.cloud.microsoft`) bem na hora do primeiro
        # ``page.evaluate``, e esse erro específico não é "a lista não
        # montou": é "ainda não dá pra saber, a página está no meio de uma
        # troca". Capturado aqui dentro do laço e tratado como "tenta de
        # novo", não como falha — o try/except de fora continua protegendo
        # contra qualquer outro erro genuíno.
        for _ in range(30):
            try:
                montou = page.evaluate(JS_TOTAL_OPCOES)
            except PlaywrightError:
                montou = False
            if montou:
                break
            page.wait_for_timeout(1000)
        else:
            return None, "a lista de mensagens não montou"

        coletadas, estaveis = {}, 0
        while len(coletadas) < teto:
            antes = len(coletadas)
            for rotulo in page.evaluate(JS_ROTULOS):
                coletadas[rotulo] = True
            if len(coletadas) == antes:
                estaveis += 1
            else:
                estaveis = 0
            if estaveis >= 5:
                break
            if not page.evaluate(JS_ROLAR):
                break
            page.wait_for_timeout(700)

        aria_setsize = page.evaluate(JS_ARIA_SETSIZE)
    except PlaywrightError as erro:
        return None, f"a leitura da caixa parou no meio ({_resumo_erro(erro)})"

    mensagens = [{"texto": rotulo} for rotulo in list(coletadas)[:teto]]
    aviso = None
    if len(mensagens) >= teto:
        aviso = f"parei em {teto} mensagem(ns) (teto da rodada)"
    elif aria_setsize and len(mensagens) < aria_setsize:
        aviso = (
            f"a caixa anuncia {aria_setsize} mensagem(ns) e só consegui "
            f"reunir {len(mensagens)}"
        )
    return mensagens, aviso


def _eh_nao_lida(texto):
    """A linha carrega o próprio estado de leitura no início do rótulo.

    Confirmado na amostra real (``tmp/amostra_outlook.json``): mensagem não
    lida começa com "Não lidos ...", mensagem já lida começa direto pelo
    remetente/assunto.
    """
    return sem_acento(texto).strip().startswith("nao lid")


def _pasta_vazia(page):
    """A pasta está mesmo vazia, ou a leitura só travou?

    Só entra depois que ``_varrer_caixa`` já desistiu de achar
    ``div[role="option"]``: aqui é decidir se aquilo foi pasta vazia de
    verdade (Outlook mostra "Nenhum conteúdo em <pasta>") ou uma leitura que
    não carregou por outro motivo.
    """
    try:
        return bool(page.evaluate(JS_PASTA_VAZIA))
    except PlaywrightError:
        return False


def _diagnostico_da_tela(page):
    """O que a tela mostra quando a lista não monta, sem vazar conteúdo.

    Só entra no caminho de falha da caixa de entrada. Devolve uma frase curta
    para grudar na mensagem de erro: endereço onde a página parou, marcadores
    conhecidos que casaram (ver ``MARCADORES_DE_TELA``) e o tamanho do texto
    da tela. Texto curto com zero marcador é a assinatura de "shell carregou e
    ficou vazio", que é diferente de "caiu no login" e de "o Outlook mostrou
    erro" — e essas três pedem conserto diferente.
    """
    try:
        bruto = page.evaluate(JS_DIAGNOSTICO)
    except PlaywrightError as erro:
        return f"não consegui inspecionar a tela ({_resumo_erro(erro)})"
    if not isinstance(bruto, dict):
        return "não consegui inspecionar a tela (resposta inesperada)"

    texto = sem_acento(bruto.get("texto") or "")
    achados = [
        nome for nome, termos in MARCADORES_DE_TELA
        if any(termo in texto for termo in termos)
    ]
    return (
        f"a tela parou em {bruto.get('endereco') or 'endereço desconhecido'} "
        f"({', '.join(achados) if achados else 'nenhum marcador conhecido'}; "
        f"{len(texto)} caractere(s) de texto, "
        f"{bruto.get('iframes', 0)} iframe(s))"
    )


def _resumo_pasta(mensagens):
    return {
        "total": len(mensagens),
        "nao_lidas": sum(
            1 for m in mensagens if _eh_nao_lida(m.get("texto") or "")
        ),
        "ultima": mensagens[0] if mensagens else None,
        "mensagens": mensagens,
    }


def resultado(navegador, checked_at, cache=None):
    """Lê o Outlook institucional num contexto próprio, sem tocar no do AVA.

    ``cache`` aqui é só o retrato desta mesma rodada em memória — ver o aviso
    de privacidade no topo do arquivo sobre por que esta fonte não persiste
    conteúdo de e-mail em ``docs/estado.json`` entre rodadas.
    """
    if not _tem_sessao_persistida():
        return SourceResult(
            status="nao_aplicavel",
            dados={},
            problemas=[
                "sem sessão salva do Outlook (rode "
                "automacao/capturar_sessao_outlook.py uma vez)"
            ],
            checked_at=checked_at,
        )

    try:
        estado_sessao = json.loads(os.environ["OUTLOOK_STORAGE_STATE"])
    except (KeyError, ValueError, TypeError):
        return SourceResult(
            status="falhou",
            dados={},
            problemas=["o Secret OUTLOOK_STORAGE_STATE não é um JSON válido"],
            checked_at=checked_at,
        )

    try:
        contexto = navegador.new_context(storage_state=estado_sessao)
    except PlaywrightError as erro:
        return SourceResult(
            status="falhou",
            dados={},
            problemas=[f"não consegui abrir a sessão do Outlook ({_resumo_erro(erro)})"],
            checked_at=checked_at,
        )

    try:
        page = contexto.new_page()
        ok, motivo = _abrir_caixa(page, MAIL_URL)
        if not ok:
            return SourceResult(
                status="falhou", dados={}, problemas=[motivo], checked_at=checked_at
            )
        mensagens_inbox, aviso_inbox = _varrer_caixa(page, teto=MAX_MENSAGENS_OUTLOOK)
        if mensagens_inbox is None:
            # Rede de segurança do conserto em `_abrir_caixa`: se o
            # redirecionamento para o login acontecer DEPOIS que a caixa foi
            # dada como aberta, quem descobre é aqui. Sessão vencida tem
            # conserto conhecido, e a mensagem precisa dizer qual é.
            motivo = (
                SESSAO_VENCIDA if not _logado(page)
                else f"{aviso_inbox} — {_diagnostico_da_tela(page)}"
            )
            return SourceResult(
                status="falhou",
                dados={},
                problemas=[motivo],
                checked_at=checked_at,
            )

        problemas = [aviso_inbox] if aviso_inbox else []

        # O Lixo Eletrônico é a segunda leitura, deliberadamente tolerante: se
        # ela falhar, a caixa de entrada já lida continua valendo, e a rodada
        # só fica "parcial", nunca "falhou" por causa de uma pasta que nem é
        # a principal.
        ok_lixo, motivo_lixo = _abrir_caixa(page, JUNK_URL)
        if ok_lixo:
            mensagens_lixo, aviso_lixo = _varrer_caixa(
                page, teto=MAX_MENSAGENS_LIXO_OUTLOOK
            )
            if mensagens_lixo is None:
                mensagens_lixo = []
                if not _pasta_vazia(page):
                    problemas.append(f"lixo eletrônico: {aviso_lixo}")
            elif aviso_lixo:
                problemas.append(f"lixo eletrônico: {aviso_lixo}")
        else:
            mensagens_lixo = []
            problemas.append(f"lixo eletrônico: {motivo_lixo}")

        dados = {
            "inbox": _resumo_pasta(mensagens_inbox),
            "lixo_eletronico": _resumo_pasta(mensagens_lixo),
        }
        return SourceResult(
            status="parcial" if problemas else "live",
            dados=dados,
            problemas=problemas,
            checked_at=checked_at,
            quantidade_atual=len(mensagens_inbox) + len(mensagens_lixo),
            last_live_at=checked_at,
        )
    finally:
        try:
            contexto.close()
        except PlaywrightError:
            pass
