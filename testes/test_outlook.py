# -*- coding: utf-8 -*-
"""
Outlook institucional: extração de prazo do e-mail e leitura degradada.

Não existe amostra real de ``aria-label`` aqui ainda — a mecânica de scroll e
o seletor vêm confirmados da skill `sec-hotmail` (mesmo produto Outlook web,
Univesp incluída, medido em 28/08/2026), mas o formato exato do texto de
cada linha só é confirmado depois da primeira captura de sessão de verdade
(``automacao/capturar_sessao_outlook.py``). Por isso os testes de extração de
prazo usam texto sintético no MESMO estilo de aviso que o resto do projeto já
lê (ver ``testes/test_prazos.py``), não uma cópia de tela real — e os testes
de leitura da caixa mockam a página, exercitando a lógica de rolagem/teto
sem depender do formato do rótulo.

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


print("\n== e-mail sem gatilho de prazo não vira nada ==")

DADOS_SEM_PRAZO = {
    "courses": [{"code": "COM100"}],
    "outlook": [{"texto": "Newsletter semanal da Univesp, sem data nenhuma"}],
}
acoes, confirmar = avisos_do_outlook(DADOS_SEM_PRAZO, HOJE, AGORA)
checa(acoes == [] and confirmar == [],
      "texto sem gatilho de prazo não gera cartão nem 'confirme se é prazo'")

checa(avisos_do_outlook({"courses": [], "outlook": []}, HOJE, AGORA) == ([], []),
      "caixa vazia não gera nada")


print("\n== prazo administrativo, sem disciplina, vai para 'confirme se é prazo' ==")

DADOS_BOLETO = {
    "courses": [{"code": "COM100"}, {"code": "SOC100"}],
    "outlook": [
        {"texto": "Prezado aluno, o boleto da mensalidade vence em 05/09/2026."}
    ],
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
    "outlook": [
        {
            "texto": (
                "Aviso da coordenação de SOC100: o prazo de entrega do "
                "Módulo 3 foi prorrogado para 10/09/2026."
            )
        }
    ],
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
    "outlook": [
        {
            "texto": (
                "Live de orientação\n"
                "A live de orientação de matrícula está marcada para "
                "01/09/2026 às 19h."
            )
        }
    ],
}
acoes, confirmar = avisos_do_outlook(DADOS_LIVE, HOJE, AGORA)
checa(any(a["tipo"] == "compromisso" for a in acoes),
      "encontro com hora marcada entra direto como compromisso, mesma regra dos avisos de fórum")
checa(confirmar == [], "compromisso não passa pelo filtro de 'confirme se é prazo'")


print("\n== a data de recebimento não vira prazo por engano ==")

DADOS_ARIA_LABEL_REAL = {
    "courses": [{"code": "COM100"}],
    "outlook": [
        {
            "texto": (
                "Não lidos COMUNICAÇÃO EMAIL/SMS/WHATSAPP Provas Regulares - "
                "3º Bimestre de 2026 Sex, 14/08 • 3º BIMESTRE - PROVAS DE "
                "14/09 A 25/09 • Olá, aluno! De 14 a 25 de setembro, das 18h "
                "às 22h, teremos nosso ciclo de provas Regulares."
            )
        }
    ],
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
    "outlook": [{"texto": "O boleto vencia em 01/01/2026."}],
}
acoes, confirmar = avisos_do_outlook(DADOS_VENCIDO, HOJE, AGORA)
checa(acoes == [] and confirmar == [], "data que já passou não entra na fila nem em confirmar")


print("\n== leitura da caixa: rolagem, estabilização e teto ==")


class PaginaFalsa:
    """Simula só o que ``_varrer_caixa``/``_abrir_caixa`` consultam."""

    def __init__(self, urls_login=(), rotulos=(), aria_setsize=None, rola=True):
        self._urls = list(urls_login) or ["https://outlook.cloud.microsoft/mail/"]
        self.url = self._urls[0]
        self._rotulos = list(rotulos)
        self._aria_setsize = aria_setsize if aria_setsize is not None else len(rotulos)
        self._rola = rola
        self.chamadas_rolar = 0

    def goto(self, *a, **k):
        pass

    def wait_for_timeout(self, *a):
        if len(self._urls) > 1:
            self._urls.pop(0)
        self.url = self._urls[0]

    def evaluate(self, js):
        if js == outlook_univesp.JS_TOTAL_OPCOES:
            return len(self._rotulos)
        if js == outlook_univesp.JS_ROTULOS:
            return list(self._rotulos)
        if js == outlook_univesp.JS_ARIA_SETSIZE:
            return self._aria_setsize
        if js == outlook_univesp.JS_ROLAR:
            self.chamadas_rolar += 1
            return self._rola
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


print("\n== resultado(): degradação sem quebrar o pipeline ==")

os.environ.pop("OUTLOOK_STORAGE_STATE", None)


class NavegadorFalso:
    def new_context(self, storage_state=None):
        raise AssertionError("não deveria abrir contexto sem sessão salva")


sem_sessao = outlook_univesp.resultado(NavegadorFalso(), "2026-08-28T10:00:00-03:00")
checa(sem_sessao.status == "nao_aplicavel",
      "sem OUTLOOK_STORAGE_STATE, a fonte se declara não aplicável, não falha")
checa(sem_sessao.dados == [], "e não inventa mensagem nenhuma")

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
contexto = ContextoFalso(PaginaFalsa(rotulos=ROTULOS_3))
navegador = NavegadorComSessao(contexto)
resultado_ok = outlook_univesp.resultado(navegador, "2026-08-28T10:00:00-03:00")
checa(resultado_ok.status == "live", "com sessão válida e caixa lida, a fonte sai 'live'")
checa(resultado_ok.quantidade_atual == 3, "a quantidade lida é reportada")
checa(navegador.storage_state_recebido == {"cookies": []},
      "a sessão salva é a que abre o contexto, não uma sessão nova do zero")
checa(contexto.fechado is True,
      "o contexto próprio do Outlook é fechado, sem vazar para as outras fontes")
os.environ.pop("OUTLOOK_STORAGE_STATE", None)


print("\n" + ("FALHOU: " + str(len(falhas)) if falhas else "TUDO OK"))
if __name__ == "__main__":
    sys.exit(1 if falhas else 0)
