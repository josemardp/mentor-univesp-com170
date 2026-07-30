# -*- coding: utf-8 -*-
"""
Regressão do bug relatado por Josemar em 30/07/2026: o guia continuava
cobrando "Módulo 6" depois dele já ter enviado o colega no
Laboratório de Avaliação. Causa raiz, achada lendo o código com ele:

1. A ação nascida do aviso do facilitador (Módulo 6 · Fechamento das
   submissões) nunca abre a atividade — só compara data do aviso com hoje.
2. A ação nascida do item (Entregue e avalie: M6 - ...) confiava no selo
   "Concluído" do Moodle, que só fecha quando as 5 fases do workshop
   terminam pro aluno (inclusive avaliar o trabalho de outro grupo em
   04/08) — não quando ele só entrega a parte dele.

Rodar:  python testes/test_workshop_enviado.py
"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

import coletar as C  # noqa: E402
from fontes import itens  # noqa: E402

falhas = []


def checa(cond, msg):
    print(("  ok    " if cond else "  FALHA") + " | " + msg)
    if not cond:
        falhas.append(msg)


HOJE = date(2026, 7, 30)


class PaginaFalsa:
    """Só o suficiente de Playwright.Page pra exercitar envio_workshop."""

    def __init__(self, texto):
        self._texto = texto

    def goto(self, *args, **kwargs):
        pass

    def wait_for_timeout(self, *args, **kwargs):
        pass

    def locator(self, _seletor):
        return self

    def inner_text(self):
        return self._texto


print("\n== fontes.itens.envio_workshop: lê a página 'Meu envio' de verdade ==")

nao_enviado = (
    "Fase de envio\nEnvie seu trabalho\nSeu envio\n"
    "Você não enviou seu trabalho ainda"
)
checa(
    itens.envio_workshop(PaginaFalsa(nao_enviado), "https://ava/workshop") is False,
    "'Você não enviou seu trabalho ainda' é enviado=False",
)

ja_enviado = (
    "Meu envio\nPortfólio - Josemar de Paula - Quinzena 1\n"
    "por JOSEMAR DE PAULA\nenviado em quarta-feira, 29 jul. 2026, 23:30\n"
    "portfolio_individual_josemar.pdf\nEditar envio\nExcluir envio"
)
checa(
    itens.envio_workshop(PaginaFalsa(ja_enviado), "https://ava/workshop") is True,
    "presença de 'Editar envio'/'Excluir envio' é enviado=True",
)

login = "Você precisa fazer login para continuar."
checa(
    itens.envio_workshop(PaginaFalsa(login), "https://ava/workshop") is None,
    "página de login não afirma nada sobre o envio (indefinido)",
)

checa(
    itens.envio_workshop(None, "") is None,
    "sem URL não tenta navegar",
)


def curso_com_workshop(enviado, com_item_prazo=True):
    item = {
        "cmid": "173854",
        "label": "M6 - Revisão entre pares (colega)",
        "type": "workshop",
        "status": "Pendente",
        "conta_nota": True,
        "aberto": True,
        "enviado": enviado,
        "url": "https://ava/mod/workshop/view.php?id=173854",
        "prazo": "2026-08-01T23:59:00-03:00" if com_item_prazo else None,
        "prazo_fonte": "calendário do AVA" if com_item_prazo else None,
        "carencia": None,
    }
    aviso_entrega = {
        "rotulo": "Fechamento das submissões",
        "quando": "2026-08-01T23:59:00-03:00",
        "trecho": "",
        "tipo": "fim",
        "hora_certa": True,
        "frase": "Fechamento das submissões",
        "confianca": "alta",
        "escopo": {"familia": "modulo", "numeros": [6], "txt": ""},
    }
    aviso_avaliacao = {
        "rotulo": "Fechamento das avaliações por pares",
        "quando": "2026-08-04T23:59:00-03:00",
        "trecho": "",
        "tipo": "fim",
        "hora_certa": True,
        "frase": "Fechamento das avaliações por pares",
        "confianca": "alta",
        "escopo": {"familia": "modulo", "numeros": [6], "txt": ""},
    }
    return {
        "id": 18922, "code": "COM170", "modelo": "quinzenal",
        "avisos": [{
            "autor": "formador", "url": "https://ava/aviso",
            "autoridade": "institucional",
            "prazos": [aviso_entrega, aviso_avaliacao],
        }],
        "sections": [{
            "id": "s6", "title": "Módulo 6", "fase": "regular", "locked": None,
            "items": [item],
        }],
    }


print("\n== Aviso do facilitador (Módulo 6 · Fechamento das submissões) ==")

dados_pendente = {"courses": [curso_com_workshop(enviado=None)]}
acoes, *_ = C.montar_acoes(dados_pendente, HOJE)
rotulos = {a["o_que"] for a in acoes if a["tipo"] == "obrigacao"}
checa(
    "Módulo 6 · Fechamento das submissões" in rotulos,
    "antes do envio, a obrigação de entrega aparece normalmente",
)
checa(
    "Módulo 6 · Fechamento das avaliações por pares" in rotulos,
    "antes do envio, a obrigação de avaliação por pares também aparece",
)

dados_enviado = {"courses": [curso_com_workshop(enviado=True)]}
acoes_env, *_ = C.montar_acoes(dados_enviado, HOJE)
rotulos_env = {a["o_que"] for a in acoes_env if a["tipo"] == "obrigacao"}
checa(
    "Módulo 6 · Fechamento das submissões" not in rotulos_env,
    "depois do envio, a obrigação de ENTREGA some da fila",
)
checa(
    "Módulo 6 · Fechamento das avaliações por pares" in rotulos_env,
    "depois do envio, a obrigação de AVALIAR outro grupo continua (é outra fase)",
)

print("\n== Ação por item (Entregue e avalie: M6 - ...) ==")

itens_labels_pendente = {a["o_que"] for a in acoes if a["tipo"] == "workshop"}
checa(
    "M6 - Revisão entre pares (colega)" in itens_labels_pendente,
    "sem 'enviado', a ação do item aparece (comportamento de antes, preservado)",
)

itens_labels_enviado = {a["o_que"] for a in acoes_env if a["tipo"] == "workshop"}
checa(
    "M6 - Revisão entre pares (colega)" not in itens_labels_enviado,
    "com enviado=True, a ação do item some mesmo com selo 'Pendente' do Moodle",
)

dados_nao_enviado = {"courses": [curso_com_workshop(enviado=False)]}
acoes_nao, *_ = C.montar_acoes(dados_nao_enviado, HOJE)
itens_labels_nao = {a["o_que"] for a in acoes_nao if a["tipo"] == "workshop"}
checa(
    "M6 - Revisão entre pares (colega)" in itens_labels_nao,
    "com enviado=False (confirmado que não enviou), a ação continua na fila",
)

print("\n" + "=" * 66)
if falhas:
    print(f"{len(falhas)} teste(s) falharam.")
    raise SystemExit(1)
print("Todos os testes de envio_workshop passaram.")
