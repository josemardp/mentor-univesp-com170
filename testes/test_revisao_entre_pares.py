# -*- coding: utf-8 -*-
"""
A revisão entre pares é a segunda obrigação do Laboratório, com prazo próprio,
e até 14/08/2026 ela só aparecia no guia depois que o Moodle abria a fase.

Funcionava, mas avisava em cima da hora: a janela da Quinzena 2 abre domingo
16/08 às 00:00 e fecha terça 18/08 às 23:59. Quem só descobre no domingo perde
o sábado para se organizar, e a descoberta depende de um contador de texto
("Avaliar colegas — total: N pendente: N") que, se mudar de redação, some sem
erro nenhum.

Os dados aqui são os eventos reais lidos do calendário do AVA em 14/08/2026,
com os tipos declarados pelo próprio Moodle.

Rodar:  python testes/test_revisao_entre_pares.py
"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

from dominio.acoes import (  # noqa: E402
    cmids_com_revisao_feita,
    cmids_sem_envio_atribuido,
    revisoes_entre_pares,
    tarefas_do_calendario,
    VERBOS_DE_REVISAO,
)

falhas = []


def checa(cond, msg):
    print(("  ok    " if cond else "  FALHA") + " | " + msg)
    if not cond:
        falhas.append(msg)


CURSOS = [{"id": "18922", "code": "COM170"}]

# Copiado do docs/data.json da rodada das 22:33 de 14/08/2026.
EVENTOS = [
    {
        "nome": "Q2 M6 - Revisão entre pares (Portfólio Individual) - prazo limite de envios",
        "quando": "2026-08-15T23:59:00-03:00",
        "curso_id": "18922",
        "atividade": "Q2 M6 - Revisão entre pares (Portfólio Individual)",
        "url": "https://ava.univesp.br/mod/workshop/view.php?id=215609",
        "cmid": "215609",
        "tipo": "closesubmission",
    },
    {
        "nome": "Q2 M6 - Revisão entre pares (Portfólio Individual) - início para avaliação",
        "quando": "2026-08-16T00:00:00-03:00",
        "curso_id": "18922",
        "atividade": "Q2 M6 - Revisão entre pares (Portfólio Individual) - início para avaliação",
        "url": "https://ava.univesp.br/mod/workshop/view.php?id=215609",
        "cmid": "215609",
        "tipo": "openassessment",
    },
    {
        "nome": "Q2 M6 - Revisão entre pares (Portfólio Individual) - prazo limite para avaliação",
        "quando": "2026-08-18T23:59:00-03:00",
        "curso_id": "18922",
        "atividade": "Q2 M6 - Revisão entre pares (Portfólio Individual)",
        "url": "https://ava.univesp.br/mod/workshop/view.php?id=215609",
        "cmid": "215609",
        "tipo": "closeassessment",
    },
    {
        "nome": "Q2 M7 - Revisão entre pares (Portfólio em grupo) - prazo limite para avaliação",
        "quando": "2026-08-18T23:59:00-03:00",
        "curso_id": "18922",
        "atividade": "Q2 M7 - Revisão entre pares (Portfólio em grupo)",
        "url": "https://ava.univesp.br/mod/workshop/view.php?id=215612",
        "cmid": "215612",
        "tipo": "closeassessment",
    },
    {
        "nome": "Q2 M7 - Revisão entre pares (Portfólio em grupo) - início para avaliação",
        "quando": "2026-08-16T00:00:00-03:00",
        "curso_id": "18922",
        "atividade": "Q2 M7 - Revisão entre pares (Portfólio em grupo) - início para avaliação",
        "url": "https://ava.univesp.br/mod/workshop/view.php?id=215612",
        "cmid": "215612",
        "tipo": "openassessment",
    },
    # Quinzena 1, já vencida: não pode voltar como tarefa.
    {
        "nome": "M6 - Revisão entre pares (Portfólio Individual) - prazo limite para avaliação",
        "quando": "2026-08-04T23:59:00-03:00",
        "curso_id": "18922",
        "atividade": "M6 - Revisão entre pares (Portfólio Individual)",
        "url": "https://ava.univesp.br/mod/workshop/view.php?id=173854",
        "cmid": "173854",
        "tipo": "closeassessment",
    },
]

DADOS = {"courses": CURSOS, "eventos": EVENTOS}


print("\n== antes de abrir: anuncia a revisão com o prazo real ==")

saida = revisoes_entre_pares(DADOS, date(2026, 8, 14), set())
por_cmid = {r["url"].rsplit("=", 1)[1]: r for r in saida}

checa(len(saida) == 2, f"dois Laboratórios da Q2 na fila (veio {len(saida)})")
checa("173854" not in por_cmid, "a revisão vencida da Quinzena 1 não volta")

m6 = por_cmid.get("215609") or {}
checa(m6.get("prazo") == "2026-08-18T23:59:00-03:00",
      f"o prazo é o fechamento da avaliação, não o do envio (veio {m6.get('prazo')})")
checa(m6.get("abre_em") == "2026-08-16T00:00:00-03:00",
      f"o cartão diz quando a fase abre (veio {m6.get('abre_em')})")
checa(m6.get("verbo") == "Avalie", "o verbo é avaliar, não entregar")
checa(m6.get("conta_nota") is True, "vale nota: são 2 dos 10 itens da quinzena")
checa(m6.get("o_que") == "Q2 M6 - Revisão entre pares (Portfólio Individual)",
      f"o nome sai sem o sufixo de fase (veio {m6.get('o_que')!r})")
checa(m6.get("curso") == "COM170", "achou o código do curso pelo curso_id")
checa(m6.get("prazo_fonte") == "calendário do AVA", "a origem da data aparece")


print("\n== depois de aberta: continua na fila, sem dizer que vai abrir ==")

aberta = revisoes_entre_pares(DADOS, date(2026, 8, 16), set())
checa(len(aberta) == 2, "os dois seguem na fila no dia em que a fase abre")
checa(all("abre_em" not in r for r in aberta),
      "some o aviso de abertura: a fase que abre hoje já está aberta")


print("\n== a leitura da página manda: não duplica a mesma tarefa ==")

sem_duplicar = revisoes_entre_pares(DADOS, date(2026, 8, 16), {"215609"})
checa(len(sem_duplicar) == 1,
      "o Laboratório que a página já pôs na fila como 'Avalie' não repete")
checa(sem_duplicar[0]["url"].endswith("215612"), "o que sobra é o outro")


print("\n== depois do prazo: não cobra o que venceu ==")

vencida = revisoes_entre_pares(DADOS, date(2026, 8, 19), set())
checa(vencida == [], "revisão vencida sai da fila em vez de virar cobrança")


print("\n== nada atribuído à conta dele: confirma, não cobra (17/08) ==")

# O Q2 M7 é laboratório de grupo. Quem recebe o trabalho da outra equipe é o
# representante, e a página dizia "Você não recebeu nenhum envio para avaliar"
# enquanto a fila cobrava "Avalie o trabalho do colega, vence amanhã".
sem_nada = revisoes_entre_pares(DADOS, date(2026, 8, 16), set(), {"215612"})
grupo = {r["url"].rsplit("=", 1)[1]: r for r in sem_nada}["215612"]
individual = {r["url"].rsplit("=", 1)[1]: r for r in sem_nada}["215609"]
checa(grupo["verbo"] == "Confirme com o grupo",
      f"revisão sem envio atribuído não vira cobrança (veio {grupo['verbo']!r})")
checa("representante" in (grupo.get("explicacao") or ""),
      "e o cartão diz por que, em vez de deixar o silêncio explicar")
checa(grupo["prazo"] == "2026-08-18T23:59:00-03:00",
      "o prazo continua à vista: ele ainda precisa cobrar o representante")
checa(individual["verbo"] == "Avalie",
      "o laboratório individual, esse sim, segue sendo cobrança")


print("\n== sem evento de avaliação: não inventa tarefa ==")

so_envio = {
    "courses": CURSOS,
    "eventos": [e for e in EVENTOS if e["tipo"] == "closesubmission"],
}
checa(revisoes_entre_pares(so_envio, date(2026, 8, 14), set()) == [],
      "sem closeassessment no calendário, nada é afirmado")


print("\n== 18/08: a rede de seguranca do calendario nao pode cobrar sozinha ==")

# Este e o defeito que a correcao de 17/08 nao pegou, achado em 18/08 com a
# pagina do Q2 M7 aberta ao vivo dizendo "Voce nao recebeu nenhum envio para
# avaliar". Com a Quinzena 2 encerrada, o item nao chega a fila pelo caminho
# normal, e quem o publica e `tarefas_do_calendario`. Ela nao consultava a
# regra: o cartao saia "Avalie o trabalho do colega: Q2 M7, vence hoje as
# 23:59", cobranca do que e do representante. E como ela ocupa o cmid antes,
# `revisoes_entre_pares` pulava o item e a regra certa nunca rodava.
DADOS_COM_ITEM = {
    "courses": [
        {
            "id": "18922",
            "code": "COM170",
            "sections": [
                {
                    "title": "Q2 Módulo 7",
                    "items": [
                        {
                            "cmid": "215612",
                            "type": "workshop",
                            "label": "Q2 M7 - Revisão entre pares (grupo)",
                            "url": "https://ava.univesp.br/mod/workshop/"
                                   "view.php?id=215612",
                            "status": "Pendente",
                            "sem_envio_atribuido": True,
                        }
                    ],
                }
            ],
        }
    ],
    "eventos": EVENTOS,
}

checa(cmids_sem_envio_atribuido(DADOS_COM_ITEM) == {"215612"},
      "o item lido do AVA entrega o cmid de quem nao recebeu envio")

resgatadas = tarefas_do_calendario(
    DADOS_COM_ITEM, date(2026, 8, 18), set(),
    cmids_sem_envio_atribuido(DADOS_COM_ITEM),
)
m7 = [t for t in resgatadas if t["url"].endswith("215612")]
checa(len(m7) == 1, "o prazo continua sendo resgatado do calendario")
checa(m7 and m7[0]["verbo"] == "Confirme com o grupo",
      "a rede de seguranca aplica a mesma regra da fila"
      + (f" (veio {m7[0]['verbo']!r})" if m7 else ""))
checa(m7 and "representante" in (m7[0].get("explicacao") or ""),
      "e explica no cartao por que nao e cobranca")
checa(m7 and m7[0]["prazo"] == "2026-08-18T23:59:00-03:00",
      "sem perder o prazo: ele ainda precisa cobrar o representante hoje")

# Sem o campo, nada muda: leitura que falhou nao vira nem cobranca nem alivio.
sem_campo = {
    "courses": [
        {
            **DADOS_COM_ITEM["courses"][0],
            "sections": [
                {
                    "title": "Q2 Módulo 7",
                    "items": [
                        {
                            **DADOS_COM_ITEM["courses"][0]["sections"][0]
                            ["items"][0],
                            "sem_envio_atribuido": None,
                        }
                    ],
                }
            ],
        }
    ],
    "eventos": EVENTOS,
}
checa(cmids_sem_envio_atribuido(sem_campo) == set(),
      "leitura que nao afirmou nada nao entra na lista")
cru = tarefas_do_calendario(sem_campo, date(2026, 8, 18), set(), set())
checa([t for t in cru if t["url"].endswith("215612")][0]["verbo"] == "Avalie",
      "sem a afirmacao da pagina, o resgate segue cobrando como antes")


# A dedupe entre os dois caminhos olhava o verbo "Avalie", e quando o cartao do
# calendario passou a virar "Confirme com o grupo" ela deixou de reconhece-lo:
# na rodada das 13:10 de 18/08 o Q2 M7 saiu duas vezes na fila, com o mesmo
# texto e o mesmo prazo. Corrigir um cartao nao pode custar a dedupe dele.
fila = tarefas_do_calendario(
    DADOS_COM_ITEM, date(2026, 8, 18), set(),
    cmids_sem_envio_atribuido(DADOS_COM_ITEM),
)
ja_na_fila = {
    acao["url"].rsplit("=", 1)[1]
    for acao in fila
    if acao["verbo"] in VERBOS_DE_REVISAO
}
checa("215612" in ja_na_fila,
      "o cartao de confirmacao conta como revisao ja publicada")
resto = revisoes_entre_pares(
    DADOS_COM_ITEM, date(2026, 8, 18), ja_na_fila,
    cmids_sem_envio_atribuido(DADOS_COM_ITEM),
)
checa(not [r for r in resto if r["url"].endswith("215612")],
      "e por isso o mesmo Laboratorio nao sai duas vezes")


print("\n== 18/08, 10h40: revisao feita nao pode voltar pela rede ==")

# O Josemar avaliou o colega no Q2 M6, a pagina passou a dizer "total: 1,
# pendente: 0", e a rodada seguinte publicou de novo "Avalie o trabalho do
# colega, vence hoje as 23:59". A leitura da pagina some da fila quando o
# trabalho e feito, e a rede de seguranca ressuscitava a cobranca justamente
# porque a fila tinha ficado (corretamente) vazia. Cobranca que sobrevive a
# entrega e o defeito mais antigo deste projeto.
def _curso_com(item_extra):
    return {
        "courses": [
            {
                "id": "18922",
                "code": "COM170",
                "sections": [
                    {
                        "title": "Q2 Módulo 6",
                        "items": [
                            {
                                "cmid": "215609",
                                "type": "workshop",
                                "label": "Q2 M6 - Revisão entre pares",
                                "url": "https://ava.univesp.br/mod/workshop/"
                                       "view.php?id=215609",
                                "status": "Pendente",
                                **item_extra,
                            }
                        ],
                    }
                ],
            }
        ],
        "eventos": EVENTOS,
    }


feito = _curso_com({"avaliacao_pendente": False})
checa(cmids_com_revisao_feita(feito) == {"215609"},
      "pagina que diz 'pendente: 0' afirma que a revisao foi feita")
sobra = revisoes_entre_pares(
    feito, date(2026, 8, 18), set(), set(), cmids_com_revisao_feita(feito)
)
checa(not [r for r in sobra if r["url"].endswith("215609")],
      "e por isso ela nao volta a ser cobrada")
resgate = tarefas_do_calendario(
    feito, date(2026, 8, 18), set(), set(), cmids_com_revisao_feita(feito)
)
checa(not [r for r in resgate if r["url"].endswith("215609")],
      "nem pelo resgate cru do calendario")

# "Nao sei" continua valendo como antes: leitura que falhou nao apaga tarefa.
nao_sei = _curso_com({"avaliacao_pendente": None})
checa(cmids_com_revisao_feita(nao_sei) == set(),
      "leitura que nao leu o contador nao afirma que a revisao foi feita")
checa([r for r in revisoes_entre_pares(nao_sei, date(2026, 8, 18), set())
       if r["url"].endswith("215609")],
      "e a tarefa segue a vista, que e o desenho desde 14/08")

# Zero pendente por nada atribuido nao e "ja avaliei": aquele tem cartao proprio.
sem_nada = _curso_com(
    {"avaliacao_pendente": False, "sem_envio_atribuido": True}
)
checa(cmids_com_revisao_feita(sem_nada) == set(),
      "zero pendente por nada atribuido nao conta como revisao feita")


print("\n== 29/08: questionario ja respondido nao pode voltar pela rede ==")

# Achado ao vivo em 29/08/2026: LET110 e SOC100 tinham nota 10/10 desde o dia
# anterior, e o selo "Concluido" do Moodle continuava fechado (o item ainda
# mostrava o botao "Marcar como feito"). A rede de seguranca so olhava esse
# selo e `cmids_com_revisao_feita` (que e so pra workshop), entao ressuscitava
# os dois questionarios como "Conclua... Termino de S5" mesmo ja respondidos.
EVENTOS_QUIZ = [
    {
        "nome": "S5 - Atividade Avaliativa - fechamento",
        "quando": "2026-08-30T23:59:00-03:00",
        "curso_id": "18893",
        "atividade": "S5 - Atividade Avaliativa",
        "url": "https://ava.univesp.br/mod/quiz/view.php?id=165208",
        "cmid": "165208",
        "tipo": "closesubmission",
    },
]
QUIZ_RESPONDIDO = {
    "courses": [
        {
            "id": "18893",
            "code": "LET110",
            "sections": [
                {
                    "title": "Semana 5",
                    "items": [
                        {
                            "cmid": "165208",
                            "type": "quiz",
                            "label": "S5 - Atividade Avaliativa",
                            "url": "https://ava.univesp.br/mod/quiz/"
                                   "view.php?id=165208",
                            "status": "Pendente",
                            "entrega_confirmada": True,
                        }
                    ],
                }
            ],
        }
    ],
    "eventos": EVENTOS_QUIZ,
}
resgate_quiz = tarefas_do_calendario(
    QUIZ_RESPONDIDO, date(2026, 8, 29), set(), set(), set()
)
checa(not [r for r in resgate_quiz if r["url"].endswith("165208")],
      "questionario com entrega confirmada na propria pagina nao volta "
      "pela rede, mesmo com o selo do Moodle ainda 'Pendente'")

# Sem a leitura da pagina, o resgate continua protegendo como antes.
QUIZ_SEM_LEITURA = {
    **QUIZ_RESPONDIDO,
    "courses": [
        {
            **QUIZ_RESPONDIDO["courses"][0],
            "sections": [
                {
                    "title": "Semana 5",
                    "items": [
                        {
                            **QUIZ_RESPONDIDO["courses"][0]["sections"][0]
                            ["items"][0],
                            "entrega_confirmada": None,
                        }
                    ],
                }
            ],
        }
    ],
}
resgate_sem_leitura = tarefas_do_calendario(
    QUIZ_SEM_LEITURA, date(2026, 8, 29), set(), set(), set()
)
checa([r for r in resgate_sem_leitura if r["url"].endswith("165208")],
      "sem a confirmacao da pagina, o resgate continua cobrando como antes")


print("\n" + ("FALHOU: " + str(len(falhas)) if falhas else "TUDO OK"))
if __name__ == "__main__":
    sys.exit(1 if falhas else 0)
