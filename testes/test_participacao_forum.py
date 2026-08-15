# -*- coding: utf-8 -*-
"""
Nas disciplinas regulares a participação nos fóruns temáticos compõe a nota,
mas até 14/08/2026 o guia só sabia se o fórum estava marcado como concluído.
A marcação é manual, então mente nos dois sentidos: quatro fóruns ficaram
parados desde a Semana 2 sem aparecer em lugar nenhum, e duas avaliativas
apareceram "Concluído" sem uma única tentativa.

A prova passou a vir da lista de mensagens do próprio aluno na disciplina
(``fontes/meus_posts.py``). O campo ``postei`` tem três estados, e o terceiro
é o que importa: ``None`` quer dizer que a leitura não funcionou, e leitura
que falhou nunca vira cobrança.

Rodar:  python testes/test_participacao_forum.py
"""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

from dominio.acoes import montar_acoes  # noqa: E402
from fontes.meus_posts import chave_forum  # noqa: E402

falhas = []


def checa(cond, msg):
    print(("  ok    " if cond else "  FALHA") + " | " + msg)
    if not cond:
        falhas.append(msg)


HOJE = date(2026, 8, 14)
AGORA = datetime(2026, 8, 14, 20, 0, tzinfo=timezone(timedelta(hours=-3)))


def montar(postei, status=None, modelo="regular", label="S3 - Fórum temático"):
    dados = {
        "courses": [
            {
                "id": "18870",
                "code": "COM100",
                "modelo": modelo,
                "avisos": [],
                "sections": [
                    {
                        "id": "1",
                        "title": "Semana 3",
                        "items": [
                            {
                                "cmid": "160798",
                                "label": label,
                                "type": "forum",
                                "url": "https://ava.univesp.br/mod/forum/view.php?id=160798",
                                "status": status,
                                "conta_nota": False,
                                "postei": postei,
                                "prazo": None,
                            }
                        ],
                    }
                ],
            }
        ],
        "eventos": [],
    }
    acoes, encerrados, higiene, confirmar = montar_acoes(
        dados, HOJE, agora=AGORA
    )
    return acoes, higiene


print("\n== não postou: vira cobrança de verdade, não higiene ==")

acoes, higiene = montar(postei=False)
checa(len(acoes) == 1, f"o fórum entra na fila de ações (veio {len(acoes)})")
checa(not higiene, "e não fica no balde de higiene")
if acoes:
    a = acoes[0]
    checa(a.get("conta_nota") is True, "sai marcado como algo que vale nota")
    checa(a.get("prazo") is None, "sem prazo inventado: o AVA não publica um")
    checa("participação" in (a.get("explicacao") or ""),
          "o cartão explica por que está ali")
    checa(a.get("verbo") == "Participe", "o verbo é participar")


print("\n== postou: some da fila, mesmo sem o Moodle marcar ==")

acoes, higiene = montar(postei=True)
checa(not acoes, "quem já escreveu não é cobrado")
checa(not higiene, "e nem sobra como pendência de higiene")


print("\n== marcado como concluído mas sem post: continua cobrando ==")

acoes, _ = montar(postei=False, status="Concluído")
checa(len(acoes) == 1,
      "o selo manual do Moodle não encerra o que a nota ainda cobra")


print("\n== postou e o Moodle marcou: silêncio ==")

acoes, higiene = montar(postei=True, status="Concluído")
checa(not acoes and not higiene, "nada a dizer quando as duas provas batem")


print("\n== leitura falhou (None): não acusa ninguém ==")

acoes, higiene = montar(postei=None)
checa(not acoes, "sem prova, não vira cobrança")
checa(not higiene,
      "e nem inventa pendência: sem status no Moodle e sem leitura, cala")

acoes, higiene = montar(postei=None, status="Marcar como feito")
checa(not acoes, "com o Moodle pedindo marcação, ainda assim não cobra nota")
checa(len(higiene) == 1,
      "volta ao comportamento antigo, como pendência de higiene")


print("\n== fórum de dúvidas não é cobrado ==")

acoes, _ = montar(postei=False, label="S3 - Fórum de dúvidas gerais")
checa(not acoes, "ninguém é cobrado por não ter dúvida")


print("\n== disciplina de quinzena (COM170) segue outra regra ==")

acoes, _ = montar(postei=False, modelo="quinzena")
checa(not acoes,
      "a regra de participação por fórum temático é das disciplinas regulares")


print("\n== casamento de nome de fórum ==")

checa(chave_forum("S3 - Fórum temático") == chave_forum("S3 - Forum tematico "),
      "acento, caixa e espaço sobrando não separam o mesmo fórum")
checa(chave_forum("S3 - Fórum  temático") == chave_forum("S3 - Fórum temático"),
      "espaço duplicado no meio também não")
checa(chave_forum("S3 - Fórum temático") != chave_forum("S4 - Fórum temático"),
      "semanas diferentes continuam diferentes")


print("\n" + ("FALHOU: " + str(len(falhas)) if falhas else "TUDO OK"))
sys.exit(1 if falhas else 0)
