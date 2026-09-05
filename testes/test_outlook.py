# -*- coding: utf-8 -*-
"""
Outlook institucional: extração de prazo do e-mail e leitura degradada.

A mecânica de scroll e o seletor vêm confirmados da skill `sec-hotmail`
(mesmo produto Outlook web, Univesp incluída, medido em 28/08/2026). Os
testes de extração de prazo usam texto sintético no MESMO estilo de aviso
que o resto do projeto já lê (ver ``testes/test_prazos.py``); os de leitura
da caixa mockam a página, exercitando a lógica de rolagem/teto/pasta sem
depender do formato do rótulo. O reconhecimento de "não lida" é conferido
contra a amostra real de ``tmp/amostra_outlook.json`` (capturada em
28/08/2026), onde a mensagem lida não tem prefixo nenhum e a não lida
começa com "Não lidos ".

Rodar:  python testes/test_outlook.py
"""
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

from dominio.acoes import avisos_do_outlook  # noqa: E402
from fontes import outlook_univesp  # noqa: E402

falhas = []


def checa(cond, msg):
    print(("  ok    " if cond else "  FALHA") + " | " + msg)
    if not cond:
        falhas.append(msg)


HOJE = date(2026, 8, 28)
AGORA = datetime(2026, 8, 28, 10, 0, tzinfo=timezone(timedelta(hours=-3)))


print("\n== _eh_nao_lida / _resumo_pasta: contra a amostra real ==")

LIDA_REAL = (
    "COMUNICAÇÃO EMAIL/SMS/WHATSAPP O seu Portal do Aluno (Sistema "
    "Acadêmico SEI) vai mudar!  Qui, 20/08 ..."
)
NAO_LIDA_REAL = (
    "Não lidos Remetente externo ChatGPT Pergunte o que quiser. Sério. "
    "Seg, 17/08 ..."
)
checa(outlook_univesp._eh_nao_lida(LIDA_REAL) is False,
      "mensagem sem o prefixo 'Não lidos' é lida")
checa(outlook_univesp._eh_nao_lida(NAO_LIDA_REAL) is True,
      "mensagem com o prefixo 'Não lidos' é reconhecida como não lida")

resumo = outlook_univesp._resumo_pasta(
    [{"texto": NAO_LIDA_REAL}, {"texto": LIDA_REAL}]
)
checa(resumo["total"] == 2, "o resumo conta o total de mensagens da pasta")
checa(resumo["nao_lidas"] == 1, "o resumo conta só as não lidas")
checa(resumo["ultima"] == {"texto": NAO_LIDA_REAL},
      "a 'última' é a primeira mensagem da lista (a mais recente)")
checa(outlook_univesp._resumo_pasta([])["ultima"] is None,
      "pasta vazia não inventa 'última' mensagem")


print("\n== _resumo_erro: mensagem de verdade, não só o nome genérico da classe ==")

checa(
    outlook_univesp._resumo_erro(
        Exception("Execution context was destroyed, most likely because of a navigation")
    ) == "Execution context was destroyed, most likely because of a navigation",
    "a primeira linha da mensagem real do erro é o que sai, não 'Error'",
)
checa(
    outlook_univesp._resumo_erro(
        Exception("Timeout 45000ms exceeded.\nCall log:\n  - navigating to ...")
    ) == "Timeout 45000ms exceeded.",
    "só a primeira linha sai — o 'Call log' que o Playwright anexa fica de fora",
)
checa(outlook_univesp._resumo_erro(Exception("")) == "Exception",
      "erro sem mensagem nenhuma cai de volta no nome da classe, nunca fica em branco")


def _outlook(inbox=(), lixo=()):
    """Monta o formato publicado por ``outlook_univesp.resultado()``."""
    return {
        "inbox": {"mensagens": [{"texto": t} for t in inbox]},
        "lixo_eletronico": {"mensagens": [{"texto": t} for t in lixo]},
    }


print("\n== e-mail sem gatilho de prazo não vira nada ==")

DADOS_SEM_PRAZO = {
    "courses": [{"code": "COM100"}],
    "outlook": _outlook(inbox=["Newsletter semanal da Univesp, sem data nenhuma"]),
}
acoes, confirmar = avisos_do_outlook(DADOS_SEM_PRAZO, HOJE, AGORA)
checa(acoes == [] and confirmar == [],
      "texto sem gatilho de prazo não gera cartão nem 'confirme se é prazo'")

checa(avisos_do_outlook({"courses": [], "outlook": _outlook()}, HOJE, AGORA) == ([], []),
      "caixa vazia não gera nada")
checa(avisos_do_outlook({"courses": []}, HOJE, AGORA) == ([], []),
      "sem a chave 'outlook' também não quebra (fonte não aplicável)")


print("\n== prazo escondido no Lixo Eletrônico não passa batido ==")

DADOS_NO_LIXO = {
    "courses": [{"code": "COM100"}, {"code": "SOC100"}],
    "outlook": _outlook(
        lixo=[
            "Aviso da coordenação de SOC100: o prazo de entrega do "
            "Módulo 3 foi prorrogado para 10/09/2026."
        ]
    ),
}
acoes, confirmar = avisos_do_outlook(DADOS_NO_LIXO, HOJE, AGORA)
checa(len(acoes) == 1,
      "um prazo com escopo forte que caiu no Lixo Eletrônico ainda vira cobrança")
if acoes:
    checa(acoes[0]["curso"] == "SOC100",
          "o código citado no e-mail do lixo eletrônico casa com o curso certo")


print("\n== prazo administrativo, sem disciplina, vai para 'confirme se é prazo' ==")

DADOS_BOLETO = {
    "courses": [{"code": "COM100"}, {"code": "SOC100"}],
    "outlook": _outlook(
        inbox=["Prezado aluno, o boleto da mensalidade vence em 05/09/2026."]
    ),
}
acoes, confirmar = avisos_do_outlook(DADOS_BOLETO, HOJE, AGORA)
checa(acoes == [], "sem escopo forte (Módulo/Semana/Quinzena), não vira cobrança direta")
checa(len(confirmar) == 1, "o prazo aparece em 'confirme se é prazo'")
if confirmar:
    item = confirmar[0]
    checa(item["curso"] == "Secretaria",
          "sem código de disciplina no texto, o rótulo é 'Secretaria', não um curso inventado")
    checa(item["quando"].startswith("2026-09-05"), "a data extraída é a do boleto")
    checa(item["autoridade"] == "institucional",
          "vem do e-mail institucional, então a origem é declarada institucional")


print("\n== disciplina citada no texto casa o cartão com o código certo ==")

DADOS_COM_DISCIPLINA = {
    "courses": [{"code": "COM100"}, {"code": "SOC100"}],
    "outlook": _outlook(
        inbox=[
            "Aviso da coordenação de SOC100: o prazo de entrega do "
            "Módulo 3 foi prorrogado para 10/09/2026."
        ]
    ),
}
acoes, confirmar = avisos_do_outlook(DADOS_COM_DISCIPLINA, HOJE, AGORA)
checa(len(acoes) == 1,
      "escopo forte ('Módulo 3') e disciplina reconhecida viram cobrança direta")
if acoes:
    checa(acoes[0]["curso"] == "SOC100", "o código citado no e-mail vira o curso do cartão")
    checa(acoes[0]["prazo_fonte"] == "e-mail institucional (Outlook)",
          "a origem do prazo é declarada, como em toda fonte deste guia")
    checa(acoes[0]["verbo"] == "Resolva", "prazo administrativo pede resolver, não entregar tarefa")


print("\n== live/encontro anunciado por e-mail vira compromisso, não pergunta ==")

DADOS_LIVE = {
    "courses": [{"code": "COM100"}],
    "outlook": _outlook(
        inbox=[
            "Live de orientação\n"
            "A live de orientação de matrícula está marcada para "
            "01/09/2026 às 19h."
        ]
    ),
}
acoes, confirmar = avisos_do_outlook(DADOS_LIVE, HOJE, AGORA)
checa(any(a["tipo"] == "compromisso" for a in acoes),
      "encontro com hora marcada entra direto como compromisso, mesma regra dos avisos de fórum")
checa(confirmar == [], "compromisso não passa pelo filtro de 'confirme se é prazo'")


print("\n== a data de recebimento não vira prazo por engano ==")

DADOS_ARIA_LABEL_REAL = {
    "courses": [{"code": "COM100"}],
    "outlook": _outlook(
        inbox=[
            "Não lidos COMUNICAÇÃO EMAIL/SMS/WHATSAPP Provas Regulares - "
            "3º Bimestre de 2026 Sex, 14/08 • 3º BIMESTRE - PROVAS DE "
            "14/09 A 25/09 • Olá, aluno! De 14 a 25 de setembro, das 18h "
            "às 22h, teremos nosso ciclo de provas Regulares."
        ]
    ),
}
acoes, confirmar = avisos_do_outlook(DADOS_ARIA_LABEL_REAL, HOJE, AGORA)
datas = {item["quando"][:10] for item in acoes + confirmar}
checa("2026-08-14" not in datas,
      "a data de recebimento (Sex, 14/08) colada no aria-label não vira prazo")
checa({"2026-09-14", "2026-09-25"} <= datas,
      "as duas datas reais do ciclo de provas (14/09 e 25/09) continuam saindo")


print("\n== prazo vencido não aparece ==")

DADOS_VENCIDO = {
    "courses": [{"code": "COM100"}],
    "outlook": _outlook(inbox=["O boleto vencia em 01/01/2026."]),
}
acoes, confirmar = avisos_do_outlook(DADOS_VENCIDO, HOJE, AGORA)
checa(acoes == [] and confirmar == [], "data que já passou não entra na fila nem em confirmar")


print("\n== leitura da caixa: rolagem, estabilização e teto ==")


class PaginaFalsa:
    """Simula só o que ``_varrer_caixa``/``_abrir_caixa`` consultam.

    ``rotulos`` é a caixa de entrada; ``rotulos_lixo`` é o Lixo Eletrônico
    (igual à caixa de entrada por padrão, quando o teste não precisa
    diferenciar as duas). ``goto`` escolhe a pasta atual pela URL, do mesmo
    jeito que ``resultado()`` navega entre elas.
    """

    def __init__(self, urls_login=(), rotulos=(), aria_setsize=None, rola=True,
                 rotulos_lixo=None, aria_setsize_lixo=None, falha_goto=(),
                 pasta_vazia_lixo=False, falhas_montagem=0, texto_da_tela="",
                 iframes=0):
        self._urls = list(urls_login) or ["https://outlook.cloud.microsoft/mail/"]
        self.url = self._urls[0]
        self._rotulos_por_pasta = {
            "inbox": list(rotulos),
            "lixo": list(rotulos_lixo) if rotulos_lixo is not None else list(rotulos),
        }
        self._aria_setsize_por_pasta = {
            "inbox": aria_setsize if aria_setsize is not None else len(rotulos),
            "lixo": (
                aria_setsize_lixo if aria_setsize_lixo is not None
                else len(self._rotulos_por_pasta["lixo"])
            ),
        }
        self._pasta = "inbox"
        self._rola = rola
        self.chamadas_rolar = 0
        self._falha_goto = set(falha_goto)
        self._pasta_vazia_lixo = pasta_vazia_lixo
        self._falhas_montagem = falhas_montagem
        self._texto_da_tela = texto_da_tela
        self._iframes = iframes

    def goto(self, url, *a, **k):
        if any(trecho in url for trecho in self._falha_goto):
            raise outlook_univesp.PlaywrightError("boom")
        self._pasta = "lixo" if "junkemail" in url else "inbox"

    def wait_for_timeout(self, *a):
        if len(self._urls) > 1:
            self._urls.pop(0)
        self.url = self._urls[0]

    def evaluate(self, js):
        rotulos = self._rotulos_por_pasta[self._pasta]
        if js == outlook_univesp.JS_TOTAL_OPCOES:
            if self._falhas_montagem > 0:
                self._falhas_montagem -= 1
                raise outlook_univesp.PlaywrightError(
                    "Execution context was destroyed, most likely because "
                    "of a navigation"
                )
            return len(rotulos)
        if js == outlook_univesp.JS_ROTULOS:
            return list(rotulos)
        if js == outlook_univesp.JS_ARIA_SETSIZE:
            return self._aria_setsize_por_pasta[self._pasta]
        if js == outlook_univesp.JS_ROLAR:
            self.chamadas_rolar += 1
            return self._rola
        if js == outlook_univesp.JS_PASTA_VAZIA:
            return self._pasta == "lixo" and self._pasta_vazia_lixo
        if js == outlook_univesp.JS_DIAGNOSTICO:
            return {
                "endereco": self.url.split("?")[0],
                "texto": self._texto_da_tela,
                "iframes": self._iframes,
                "opcoes": len(rotulos),
            }
        raise AssertionError(f"evaluate inesperado: {js[:60]}")


ROTULOS_3 = [f"Remetente {i}, Assunto {i}, prévia {i}" for i in range(3)]

pagina = PaginaFalsa(rotulos=ROTULOS_3)
mensagens, aviso = outlook_univesp._varrer_caixa(pagina, teto=40)
checa(mensagens is not None and len(mensagens) == 3, "as três mensagens são coletadas")
checa(aviso is None, "sem discrepância de contagem, não há aviso")

pagina_incompleta = PaginaFalsa(rotulos=ROTULOS_3, aria_setsize=10)
mensagens, aviso = outlook_univesp._varrer_caixa(pagina_incompleta, teto=40)
checa(len(mensagens) == 3 and aviso is not None,
      "quando a rolagem não alcança o aria-setsize, o que foi lido é mantido "
      "e a discrepância vira aviso, sem travar a rodada")

pagina_teto = PaginaFalsa(rotulos=ROTULOS_3, aria_setsize=3)
mensagens, aviso = outlook_univesp._varrer_caixa(pagina_teto, teto=2)
checa(len(mensagens) == 2, "o teto por rodada é respeitado")
checa(aviso is not None and "teto" in aviso, "o corte pelo teto é declarado, não silencioso")

pagina_vazia = PaginaFalsa(rotulos=[])
mensagens, aviso = outlook_univesp._varrer_caixa(pagina_vazia, teto=40)
checa(mensagens is None and "não montou" in aviso,
      "lista que nunca aparece no DOM é leitura falhada, não caixa vazia")

# Achado ao vivo em 30/08/2026 no runner do GitHub Actions: a primeira
# tentativa de ler a lista pode pegar a página no meio de uma navegação
# (`Execution context was destroyed`) mesmo com a sessão já logada — isso não
# pode contar como "a lista não montou", só como "tenta de novo".
pagina_navegando = PaginaFalsa(rotulos=ROTULOS_3, falhas_montagem=2)
mensagens, aviso = outlook_univesp._varrer_caixa(pagina_navegando, teto=40)
checa(mensagens is not None and len(mensagens) == 3,
      "duas falhas de 'Execution context destroyed' na primeira leitura não derrubam a varredura")
checa(aviso is None, "depois de estabilizar, a leitura sai normal, sem aviso sobrando")

pagina_nunca_estabiliza = PaginaFalsa(rotulos=ROTULOS_3, falhas_montagem=999)
mensagens, aviso = outlook_univesp._varrer_caixa(pagina_nunca_estabiliza, teto=40)
checa(mensagens is None and "não montou" in aviso,
      "se a navegação nunca estabiliza, ainda desiste com 'não montou' depois de 30 tentativas, sem propagar a exceção")


print("\n== diagnóstico da tela: diz o que apareceu, sem publicar o conteúdo ==")
# A fonte morreu três vezes com a mesma frase ("a lista de mensagens não
# montou"), que não distingue login, erro do Outlook e shell vazio. O
# diagnóstico separa os três, e não pode vazar o que está escrito na tela:
# docs/data.json é público.

pagina_login_no_app = PaginaFalsa(
    rotulos=[],
    texto_da_tela="Entrar em sua conta\nEmail, telefone ou Skype\nPróxima",
)
diag = outlook_univesp._diagnostico_da_tela(pagina_login_no_app)
checa("tela de login dentro do app" in diag,
      "tela de login renderizada dentro do domínio do Outlook é reconhecida pelo marcador")
checa("Entrar em sua conta" not in diag and "Skype" not in diag,
      "o texto da tela NUNCA entra no diagnóstico (docs/data.json é público)")
checa("outlook.cloud.microsoft/mail/" in diag,
      "o endereço onde a página parou entra, porque é ele que diz se caiu de domínio")

pagina_shell_vazio = PaginaFalsa(rotulos=[], texto_da_tela="", iframes=3)
diag_vazio = outlook_univesp._diagnostico_da_tela(pagina_shell_vazio)
checa("nenhum marcador conhecido" in diag_vazio,
      "shell que carrega e fica vazio se declara assim, em vez de fingir diagnóstico")
checa("3 iframe(s)" in diag_vazio,
      "a contagem de iframes entra: é por iframe que o MSAL tenta renovar o token calado")


class PaginaQueNaoInspeciona(PaginaFalsa):
    def evaluate(self, js):
        if js == outlook_univesp.JS_DIAGNOSTICO:
            raise outlook_univesp.PlaywrightError("Target page, context or browser has been closed")
        return super().evaluate(js)


diag_falho = outlook_univesp._diagnostico_da_tela(PaginaQueNaoInspeciona(rotulos=[]))
checa("não consegui inspecionar a tela" in diag_falho,
      "se nem o diagnóstico roda, ele diz isso em vez de explodir e derrubar a fonte")

print("\n== login: sessão salva expirada é reconhecida ==")

pagina_login_vencido = PaginaFalsa(
    urls_login=["https://login.microsoftonline.com/common/oauth2/..."] * 25
)
ok, motivo = outlook_univesp._abrir_caixa(pagina_login_vencido)
checa(not ok, "cair e ficar na tela de login é reconhecido como sessão vencida")
checa("capturar_sessao_outlook" in motivo,
      "a mensagem de erro já diz o comando que resolve")

pagina_logada = PaginaFalsa(
    urls_login=[
        "https://login.microsoftonline.com/common/oauth2/...",
        "https://outlook.cloud.microsoft/mail/",
    ]
)
ok, motivo = outlook_univesp._abrir_caixa(pagina_logada)
checa(ok, "sessão que resolve o login sozinha (SSO válido) é reconhecida")

# A causa da recaída de 31/08 a 05/09/2026, medida ao vivo: a página começa em
# outlook.office.com (ainda não redirecionou), e é EXATAMENTE nesse instante
# que a conferência caía. Uma amostra só dava "logado", `_abrir_caixa`
# devolvia sucesso, e a sessão vencida ia morrer 30s depois na varredura com a
# mensagem errada. A tela real tinha parado em
# login.microsoftonline.com/common/oauth2/v2.0/authorize.
pagina_redireciona_depois = PaginaFalsa(
    urls_login=(
        ["https://outlook.office.com/mail/"]
        + ["https://login.microsoftonline.com/common/oauth2/v2.0/authorize"] * 30
    )
)
ok, motivo = outlook_univesp._abrir_caixa(pagina_redireciona_depois)
checa(not ok,
      "sessão vencida que só redireciona para o login DEPOIS do primeiro instante é pega")
checa("capturar_sessao_outlook" in motivo,
      "e o motivo é o conserto de verdade (recapturar a sessão), não 'a lista não montou'")



print("\n== resultado(): degradação sem quebrar o pipeline ==")

os.environ.pop("OUTLOOK_STORAGE_STATE", None)


class NavegadorFalso:
    def new_context(self, storage_state=None):
        raise AssertionError("não deveria abrir contexto sem sessão salva")


sem_sessao = outlook_univesp.resultado(NavegadorFalso(), "2026-08-28T10:00:00-03:00")
checa(sem_sessao.status == "nao_aplicavel",
      "sem OUTLOOK_STORAGE_STATE, a fonte se declara não aplicável, não falha")
checa(sem_sessao.dados == {}, "e não inventa mensagem nenhuma")

os.environ["OUTLOOK_STORAGE_STATE"] = "isto não é json"
invalida = outlook_univesp.resultado(NavegadorFalso(), "2026-08-28T10:00:00-03:00")
checa(invalida.status == "falhou", "Secret corrompido falha declarado, não derruba o robô")
os.environ.pop("OUTLOOK_STORAGE_STATE", None)


class ContextoFalso:
    def __init__(self, pagina):
        self._pagina = pagina
        self.fechado = False

    def new_page(self):
        return self._pagina

    def close(self):
        self.fechado = True


class NavegadorComSessao:
    def __init__(self, contexto):
        self._contexto = contexto
        self.storage_state_recebido = None

    def new_context(self, storage_state=None):
        self.storage_state_recebido = storage_state
        return self._contexto


os.environ["OUTLOOK_STORAGE_STATE"] = '{"cookies": []}'
# Lixo eletrônico com uma mensagem só, não vazio: pasta genuinamente vazia
# nunca monta ``div[role="option"]`` nenhum, e ``_varrer_caixa`` já trata
# isso como leitura falhada ("a lista não montou"), não caixa confirmada
# vazia — o mesmo vale pra pasta principal, não é peculiaridade daqui.
contexto = ContextoFalso(
    PaginaFalsa(rotulos=ROTULOS_3, rotulos_lixo=["Mensagem qualquer no lixo eletrônico"])
)
navegador = NavegadorComSessao(contexto)
resultado_ok = outlook_univesp.resultado(navegador, "2026-08-28T10:00:00-03:00")
checa(resultado_ok.status == "live", "com sessão válida e caixa lida, a fonte sai 'live'")
checa(resultado_ok.quantidade_atual == 4,
      "a quantidade lida soma caixa de entrada (3) e lixo eletrônico (1)")
checa(resultado_ok.dados["inbox"]["mensagens"] == [{"texto": t} for t in ROTULOS_3],
      "as mensagens da caixa de entrada vêm no formato {texto: ...} já usado no resto do guia")
checa(navegador.storage_state_recebido == {"cookies": []},
      "a sessão salva é a que abre o contexto, não uma sessão nova do zero")
checa(contexto.fechado is True,
      "o contexto próprio do Outlook é fechado, sem vazar para as outras fontes")
os.environ.pop("OUTLOOK_STORAGE_STATE", None)


print("\n== resultado(): resumo de cada pasta (última mensagem e não lidas) ==")

os.environ["OUTLOOK_STORAGE_STATE"] = '{"cookies": []}'
INBOX_MISTA = [
    "Não lidos Sender A, Assunto novo, prévia",
    "Sender B, Assunto já lido, prévia",
]
LIXO_MISTO = [
    "Não lidos Promoção suspeita, isto parece phishing",
]
pagina_duas_pastas = PaginaFalsa(rotulos=INBOX_MISTA, rotulos_lixo=LIXO_MISTO)
contexto2 = ContextoFalso(pagina_duas_pastas)
navegador2 = NavegadorComSessao(contexto2)
resultado2 = outlook_univesp.resultado(navegador2, "2026-08-28T10:00:00-03:00")
checa(resultado2.status == "live", "as duas pastas lidas sem aviso saem 'live'")
checa(resultado2.dados["inbox"]["ultima"]["texto"] == INBOX_MISTA[0],
      "a 'última' é a primeira mensagem lida na caixa de entrada (a mais recente)")
checa(resultado2.dados["inbox"]["nao_lidas"] == 1,
      "a contagem de não lidas da caixa de entrada bate com o prefixo 'Não lidos'")
checa(resultado2.dados["lixo_eletronico"]["total"] == 1
      and resultado2.dados["lixo_eletronico"]["nao_lidas"] == 1,
      "o lixo eletrônico também sai resumido, com total e não lidas")
checa(resultado2.quantidade_atual == 3, "a quantidade soma as duas pastas")
os.environ.pop("OUTLOOK_STORAGE_STATE", None)


print("\n== resultado(): Lixo Eletrônico falho não derruba a caixa de entrada ==")

os.environ["OUTLOOK_STORAGE_STATE"] = '{"cookies": []}'
pagina_lixo_falho = PaginaFalsa(rotulos=ROTULOS_3, falha_goto={"junkemail"})
contexto3 = ContextoFalso(pagina_lixo_falho)
navegador3 = NavegadorComSessao(contexto3)
resultado3 = outlook_univesp.resultado(navegador3, "2026-08-28T10:00:00-03:00")
checa(resultado3.status == "parcial",
      "caixa de entrada lida e Lixo Eletrônico falho vira 'parcial', não 'falhou'")
checa(resultado3.dados["inbox"]["total"] == 3,
      "a caixa de entrada continua completa mesmo com o lixo eletrônico falhando")
checa(resultado3.dados["lixo_eletronico"]["mensagens"] == [],
      "sem leitura do lixo eletrônico, a lista vem vazia, nunca inventada")
checa(any("lixo eletrônico" in p for p in resultado3.problemas),
      "o problema nomeia a pasta que falhou, não fica genérico")
os.environ.pop("OUTLOOK_STORAGE_STATE", None)


print("\n== resultado(): Lixo Eletrônico genuinamente vazio não vira aviso de falha ==")
# Confirmado ao vivo em 30/08/2026: a pasta pode estar mesmo vazia (o caso
# bom), e isso não pode soar como "não consegui ler".

os.environ["OUTLOOK_STORAGE_STATE"] = '{"cookies": []}'
pagina_lixo_vazio = PaginaFalsa(
    rotulos=ROTULOS_3, rotulos_lixo=[], pasta_vazia_lixo=True
)
contexto4 = ContextoFalso(pagina_lixo_vazio)
navegador4 = NavegadorComSessao(contexto4)
resultado4 = outlook_univesp.resultado(navegador4, "2026-08-28T10:00:00-03:00")
checa(resultado4.status == "live",
      "Lixo Eletrônico confirmado vazio não derruba o status pra 'parcial'")
checa(resultado4.dados["lixo_eletronico"]["mensagens"] == [],
      "e a lista sai vazia mesmo, sem inventar mensagem")
checa(resultado4.problemas == [],
      "pasta vazia confirmada não gera problema nenhum")
os.environ.pop("OUTLOOK_STORAGE_STATE", None)


print("\n== resultado(): Lixo Eletrônico que só travou (sem o texto de vazio) continua falha ==")

os.environ["OUTLOOK_STORAGE_STATE"] = '{"cookies": []}'
pagina_lixo_travado = PaginaFalsa(
    rotulos=ROTULOS_3, rotulos_lixo=[], pasta_vazia_lixo=False
)
contexto5 = ContextoFalso(pagina_lixo_travado)
navegador5 = NavegadorComSessao(contexto5)
resultado5 = outlook_univesp.resultado(navegador5, "2026-08-28T10:00:00-03:00")
checa(resultado5.status == "parcial",
      "sem o texto de pasta vazia na tela, a leitura que não montou continua avisando")
checa(any("lixo eletrônico" in p for p in resultado5.problemas),
      "o aviso de leitura travada continua saindo quando não é vazio confirmado")
os.environ.pop("OUTLOOK_STORAGE_STATE", None)


print("\n== resultado(): a falha da caixa de entrada sai com o diagnóstico junto ==")
# Regressão da recaída achada em 05/09/2026: a fonte ficou 5 dias publicando
# só "a lista de mensagens não montou", frase que serve para três defeitos
# diferentes e não ajudava a escolher nenhum conserto.

os.environ["OUTLOOK_STORAGE_STATE"] = '{"cookies": []}'
pagina_inbox_morta = PaginaFalsa(
    rotulos=[], texto_da_tela="Algo deu errado. Tente novamente mais tarde."
)
resultado_morto = outlook_univesp.resultado(
    NavegadorComSessao(ContextoFalso(pagina_inbox_morta)),
    "2026-09-05T10:00:00-03:00",
)
checa(resultado_morto.status == "falhou",
      "caixa de entrada que não monta continua sendo falha declarada")
checa(any("não montou" in p and "erro do próprio Outlook" in p
          for p in resultado_morto.problemas),
      "o problema publicado junta o sintoma e o diagnóstico numa linha só")
checa(not any("Tente novamente" in p for p in resultado_morto.problemas),
      "e o texto da tela continua fora do que vai para o data.json público")

# Rede de segurança: o redirecionamento para o login pode acontecer depois de
# `_abrir_caixa` já ter dado a caixa como aberta. Aí quem tem que reconhecer a
# sessão vencida é o caminho de falha da varredura.
pagina_login_tardio = PaginaFalsa(
    rotulos=[],
    urls_login=(
        ["https://outlook.office.com/mail/"] * 4
        + ["https://login.microsoftonline.com/common/oauth2/v2.0/authorize"] * 60
    ),
    texto_da_tela="Entrar em sua conta",
)
resultado_tardio = outlook_univesp.resultado(
    NavegadorComSessao(ContextoFalso(pagina_login_tardio)),
    "2026-09-05T13:00:00-03:00",
)
checa(resultado_tardio.status == "falhou", "sessão vencida continua sendo falha declarada")
checa(any("capturar_sessao_outlook" in p for p in resultado_tardio.problemas),
      "redirecionamento para o login depois da caixa aberta ainda vira 'recapture a sessão'")
os.environ.pop("OUTLOOK_STORAGE_STATE", None)


print("\n" + ("FALHOU: " + str(len(falhas)) if falhas else "TUDO OK"))
if __name__ == "__main__":
    sys.exit(1 if falhas else 0)
