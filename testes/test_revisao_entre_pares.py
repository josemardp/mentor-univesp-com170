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

from dominio.acoes import revisoes_entre_pares  # noqa: E402

falhas = []


def checa(cond, msg):
    print(("  ok    " if cond else "  FALHA") + " | " + msg)
    if not cond:
        falhas.append(msg)


CURSOS = [{"id": "18922", "code": "COM170"}]

# Copiado do docs/data.json da rodada das 22:33 de 14/08/2026.
EVENTOS = [
    {
        "nome": "Q2 M6 - Revisão entre pares (colega) - prazo limite de envios",
        "quando": "2026-08-15T23:59:00-03:00",
        "curso_id": "18922",
        "atividade": "Q2 M6 - Revisão entre pares (colega)",
        "url": "https://ava.univesp.br/mod/workshop/view.php?id=215609",
        "cmid": "215609",
        "tipo": "closesubmission",
    },
    {
        "nome": "Q2 M6 - Revisão entre pares (colega) - início para avaliação",
        "quando": "2026-08-16T00:00:00-03:00",
        "curso_id": "18922",
        "atividade": "Q2 M6 - Revisão entre pares (colega) - início para avaliação",
        "url": "https://ava.univesp.br/mod/workshop/view.php?id=215609",
        "cmid": "215609",
        "tipo": "openassessment",
    },
    {
        "nome": "Q2 M6 - Revisão entre pares (colega) - prazo limite para avaliação",
        "quando": "2026-08-18T23:59:00-03:00",
        "curso_id": "18922",
        "atividade": "Q2 M6 - Revisão entre pares (colega)",
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
        "nome": "M6 - Revisão entre pares (colega) - prazo limite para avaliação",
        "quando": "2026-08-04T23:59:00-03:00",
        "curso_id": "18922",
        "atividade": "M6 - Revisão entre pares (colega)",
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
checa(m6.get("o_que") == "Q2 M6 - Revisão entre pares (colega)",
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


print("\n== sem evento de avaliação: não inventa tarefa ==")

so_envio = {
    "courses": CURSOS,
    "eventos": [e for e in EVENTOS if e["tipo"] == "closesubmission"],
}
checa(revisoes_entre_pares(so_envio, date(2026, 8, 14), set()) == [],
      "sem closeassessment no calendário, nada é afirmado")


print("\n" + ("FALHOU: " + str(len(falhas)) if falhas else "TUDO OK"))
sys.exit(1 if falhas else 0)
