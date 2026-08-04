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

ja_enviado_tela_edicao = (
    "Meu envio\nPortfólio - Josemar de Paula - Quinzena 1\n"
    "por JOSEMAR DE PAULA\nenviado em quarta-feira, 29 jul. 2026, 23:30\n"
    "portfolio_individual_josemar.pdf\nEditar envio\nExcluir envio"
)
checa(
    itens.envio_workshop(PaginaFalsa(ja_enviado_tela_edicao), "https://ava/workshop")
    is True,
    "presença de 'Editar envio'/'Excluir envio' (tela submission.php) é enviado=True",
)

# `view.php` é a página que o robô de fato visita (o link do curso aponta pra
# ela, não pra submission.php) e ela NÃO mostra "Editar envio"/"Excluir
# envio" - só a linha do tempo com "Tarefa realizada" e o carimbo "enviado
# em". Texto real lido do AVA em 30/07/2026, depois do envio de Josemar.
ja_enviado_view_php = (
    "Fase de envio\nLinha do tempo do laboratório de avaliação com 5 fases\n"
    "Fase de configuração\nFase de envio\nFase atual\nTarefa realizada\n"
    "Envie seu trabalho\nPrazo limite dos envios: sábado, 01 ago. 2026, 23:59\n"
    "Instruções para envio\n...\n"
    "Seu envio\nPortfólio - Josemar de Paula - Quinzena 1\nJD\n"
    "por JOSEMAR DE PAULA\nenviado em quarta-feira, 29 jul. 2026, 23:30"
)
checa(
    itens.envio_workshop(PaginaFalsa(ja_enviado_view_php), "https://ava/workshop")
    is True,
    "em view.php (sem os botões de editar/excluir), 'Tarefa realizada' + "
    "'enviado em' também é enviado=True",
)

nao_enviado_view_php = (
    "Fase de envio\nLinha do tempo do laboratório de avaliação com 5 fases\n"
    "Fase de configuração\nFase de envio\nFase atual\nTarefas a fazer\n"
    "Envie seu trabalho\nPrazo limite dos envios: sábado, 01 ago. 2026, 23:59\n"
    "Instruções para envio\n...\n"
    "Seu envio\nVocê não enviou seu trabalho ainda"
)
checa(
    itens.envio_workshop(PaginaFalsa(nao_enviado_view_php), "https://ava/workshop")
    is False,
    "em view.php antes do envio, 'Tarefas a fazer' (plural) não é confundido "
    "com 'Tarefa realizada'",
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


def cobra(acoes, verbo, dia):
    """Linhas que cobram este verbo neste dia, venham de aviso ou de item."""
    return [
        a
        for a in acoes
        if (a.get("verbo") or "").startswith(verbo)
        and (a.get("prazo") or "").startswith(dia)
    ]


dados_pendente = {"courses": [curso_com_workshop(enviado=None)]}
acoes, *_ = C.montar_acoes(dados_pendente, HOJE)
entregas = cobra(acoes, "Entregue", "2026-08-01")
checa(
    len(entregas) == 1,
    "antes do envio, a obrigação de entrega aparece — uma vez só",
)
checa(
    bool(entregas and entregas[0].get("url")),
    "e a linha que sobra é a que leva direto à atividade no AVA",
)
checa(
    len(cobra(acoes, "Avalie", "2026-08-04")) == 1,
    "antes do envio, a obrigação de avaliação por pares também aparece",
)

dados_enviado = {"courses": [curso_com_workshop(enviado=True)]}
acoes_env, *_ = C.montar_acoes(dados_enviado, HOJE)
checa(
    not cobra(acoes_env, "Entregue", "2026-08-01"),
    "depois do envio, a obrigação de ENTREGA some da fila",
)
checa(
    len(cobra(acoes_env, "Avalie", "2026-08-04")) == 1,
    "depois do envio, a obrigação de AVALIAR outro grupo continua (é outra fase)",
)

print("\n== Fase de avaliação por pares (o que quebrou em 04/08/2026) ==")

# A página do Laboratório em fase de avaliação diz, nas instruções, "O prazo de
# envio terminou e o sistema já lhe atribuiu o trabalho de um colega". Essa
# frase está na lista de encerramento usada por item_aberto, e mandou o M7 para
# "já encerrou" no dia em que a avaliação vencia.
em_avaliacao = (
    "Fase de avaliação\nFase atual\nTarefas a fazer\nAvaliar colegas\n"
    "total: 1pendente: 1\n"
    "Prazo limite da avaliação: terça-feira, 04 ago. 2026, 23:59\n"
    "Seu envio\nenviado em sexta-feira, 31 jul. 2026, 17:03\n"
    "Instruções para avaliação\n"
    "O prazo de envio terminou e o sistema já lhe atribuiu aleatoriamente "
    "o trabalho de um colega.\nAvaliar"
)
estado_av = itens.estado_workshop(PaginaFalsa(em_avaliacao), "https://ava/w")
checa(
    estado_av["aberto"] is True,
    "Laboratório com avaliação pendente não é dado como encerrado, mesmo "
    "com 'o prazo de envio terminou' na página",
)
checa(
    estado_av["avaliacao_pendente"] is True
    and estado_av["avaliacoes_pendentes"] == 1,
    "o contador 'total: 1 pendente: 1' é lido da linha do tempo",
)
avaliado = em_avaliacao.replace("total: 1pendente: 1", "total: 1pendente: 0")
checa(
    itens.estado_workshop(PaginaFalsa(avaliado), "https://ava/w")[
        "avaliacao_pendente"
    ]
    is False,
    "com 'pendente: 0' o robô sabe que a avaliação já foi feita",
)

curso_avaliando = curso_com_workshop(enviado=True)
item_lab = curso_avaliando["sections"][0]["items"][0]
item_lab["avaliacao_pendente"] = True
item_lab["avaliacoes_pendentes"] = 1
item_lab["prazo"] = "2026-08-04T23:59:00-03:00"
acoes_av, *_ = C.montar_acoes({"courses": [curso_avaliando]}, HOJE)
linhas_lab = [a for a in acoes_av if a["tipo"] == "workshop"]
checa(
    len(linhas_lab) == 1 and linhas_lab[0]["verbo"] == "Avalie",
    "entregou mas ainda falta avaliar: o Laboratório continua na fila, "
    "agora pedindo a avaliação",
)
checa(
    bool(linhas_lab and linhas_lab[0].get("url")),
    "e com o link do Laboratório, que é onde fica o botão Avaliar",
)

curso_fechado = curso_com_workshop(enviado=True)
curso_fechado["sections"][0]["items"][0]["avaliacao_pendente"] = False
acoes_fim, *_ = C.montar_acoes({"courses": [curso_fechado]}, HOJE)
checa(
    not [a for a in acoes_fim if a["tipo"] == "workshop"],
    "entregou e já avaliou: o Laboratório sai da fila inteiro",
)
checa(
    not cobra(acoes_fim, "Avalie", "2026-08-04"),
    "e o aviso do facilitador também para de cobrar a avaliação já feita",
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
