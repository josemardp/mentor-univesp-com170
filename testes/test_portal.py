# -*- coding: utf-8 -*-
"""
O portal do aluno (SEI) é o segundo sistema da Univesp, com login próprio, e
até 15/08/2026 o guia não olhava para ele. Três coisas moravam só ali: a data
da prova presencial, a lista real de disciplinas matriculadas e os recados da
secretaria.

Os textos deste arquivo foram copiados das telas reais em 15/08/2026, com as
quebras de linha como o portal manda. É a regra da casa: teste de leitura de
tela alheia usa o texto do dia, não um exemplo gentil escrito por quem fez o
teste.

Rodar:  python testes/test_portal.py
"""
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

from dominio.acoes import disciplinas_so_no_portal, provas_do_portal  # noqa: E402
from fontes import portal  # noqa: E402
from fontes.portal import RE_ATIVIDADE, RE_TITULO_PROVA, _iso  # noqa: E402

falhas = []


def checa(cond, msg):
    print(("  ok    " if cond else "  FALHA") + " | " + msg)
    if not cond:
        falhas.append(msg)


# Copiado do Calendário de Atividades em 15/08/2026.
CALENDARIO = """ATIVIDADES
ATIVIDADES DISPONÍVEIS

CALENDÁRIO DE ATIVIDADES - A partir de 15/08/2026 09:54

Legenda:
Online
Presencial
Agosto de 2026

Suas atividades
Presencial
2026 - COM100 - PENSAMENTO COMPUTACIONAL - 3 BIMESTRE
De: 05/11 19:40
Até 05/11 23:50

Presencial
2026 - LET110 - LEITURA E PRODUÇÃO DE TEXTOS - 3 BIMESTRE
De: 05/11 19:40
Até 05/11 23:50

Presencial
2026 - SOC100 - ÉTICA CIDADANIA E SOCIEDADE - 3 BIMESTRE
De: 05/11 19:40
Até 05/11 23:50
"""

VAZIO = """ATIVIDADES
ATIVIDADES DISPONÍVEIS

CALENDÁRIO DE ATIVIDADES - A partir de 15/08/2026 09:56

Nenhuma atividade on-line disponível pra você!
"""


print("\n== calendário de atividades ==")

achadas = list(RE_ATIVIDADE.finditer(CALENDARIO))
checa(len(achadas) == 3, f"as três provas são lidas (vieram {len(achadas)})")

primeira = achadas[0].groups()
checa(primeira[0] == "Presencial", "a modalidade sai da linha de cima")
checa(primeira[2] == "05/11" and primeira[3] == "19:40",
      "início com dia e hora, do jeito que a tela escreve")

cabecalho = RE_TITULO_PROVA.match(primeira[1])
checa(bool(cabecalho), "o título casa com ano, código e nome")
checa(cabecalho.group(1) == "2026", "o ano vem do título, que é onde ele existe")
checa(cabecalho.group(2) == "COM100", "o código da disciplina é extraído")

checa(not list(RE_ATIVIDADE.finditer(VAZIO)),
      "tela sem atividade não inventa prova")

checa(_iso("05/11", "19:40", 2026).startswith("2026-11-05T19:40"),
      "a data vira ISO no fuso de Brasília")
checa(_iso("31/02", "19:40", 2026) is None,
      "data impossível devolve None em vez de chutar")


print("\n== prova vira compromisso na fila ==")

DADOS = {
    "courses": [{"code": "COM100"}, {"code": "SOC100"},
                {"code": "LET110"}, {"code": "COM170"}],
    "portal": {
        "provas": [
            {
                "codigo": "COM100",
                "titulo": "2026 - COM100 - PENSAMENTO COMPUTACIONAL - 3 BIMESTRE",
                "modalidade": "Presencial",
                "inicio": "2026-11-05T19:40:00-03:00",
                "fim": "2026-11-05T23:50:00-03:00",
            }
        ],
        "disciplinas": [
            {"codigo": "COM100", "nome": "Pensamento Computacional"},
            {"codigo": "MMB002", "nome": "Matemática Básica"},
            {"codigo": "INT100", "nome": "Projetos e métodos"},
        ],
    },
}
AGORA = datetime(2026, 8, 15, 10, 0, tzinfo=timezone(timedelta(hours=-3)))

acoes = provas_do_portal(DADOS, date(2026, 8, 15), agora=AGORA)
checa(len(acoes) == 1, "a prova entra na fila")
if acoes:
    a = acoes[0]
    checa(a["verbo"] == "Compareça", "prova presencial pede comparecer, não entregar")
    checa("acontece 05/11" in a["prazo_txt"],
          f"o texto trata como encontro, não como vencimento ({a['prazo_txt']})")
    checa(a["prazo_fonte"] == "Sistema de Provas (portal do aluno)",
          "a origem da data aparece, como toda data neste guia")
    checa(a["conta_nota"] is True, "prova vale nota")

# No dia seguinte à prova ela some sozinha, como a live que já aconteceu.
depois = provas_do_portal(
    DADOS, date(2026, 11, 6),
    agora=datetime(2026, 11, 6, 8, 0, tzinfo=timezone(timedelta(hours=-3))),
)
checa(not depois, "prova que já passou sai da fila")

sem_portal = provas_do_portal({"courses": []}, date(2026, 8, 15), agora=AGORA)
checa(sem_portal == [],
      "sem leitura do portal não aparece prova nenhuma, nem inventada")


print("\n== disciplina que só a secretaria conhece ==")

fora = disciplinas_so_no_portal(DADOS)
checa({d["codigo"] for d in fora} == {"MMB002", "INT100"},
      "as duas matrículas sem turma no AVA aparecem")

checa(disciplinas_so_no_portal({"courses": [], "portal": DADOS["portal"]}) == [],
      "sem disciplina lida no AVA não dá para comparar, então não acusa nada")

checa(disciplinas_so_no_portal({"courses": [{"code": "COM100"}]}) == [],
      "sem leitura do portal também não acusa nada")


print("\n== qual usuário o portal quer ==")

# A tela do SEI tem dois caminhos: "E-mail institucional" quer o endereço
# inteiro e cai no SSO da Microsoft; "Usuário" quer só o registro acadêmico. O
# gerenciador de senhas dele guarda as duas entradas separadas, e é a segunda
# que a automação usa.
for chave in ("PORTAL_USUARIO", "AVA_USUARIO"):
    os.environ.pop(chave, None)

os.environ["AVA_USUARIO"] = "90011122@aluno.univesp.br"
checa(portal._identidades() == ["90011122", "90011122@aluno.univesp.br"],
      "o registro acadêmico sai do e-mail e é tentado primeiro")

os.environ["AVA_USUARIO"] = "90011122"
checa(portal._identidades() == ["90011122"],
      "usuário já sem @ não vira duas tentativas iguais")

os.environ["PORTAL_USUARIO"] = "outro"
checa(portal._identidades()[0] == "outro",
      "PORTAL_USUARIO, quando existe, tem a palavra final")

for chave in ("PORTAL_USUARIO", "AVA_USUARIO"):
    os.environ.pop(chave, None)
checa(portal._identidades() == [],
      "sem nada configurado não há tentativa nenhuma")


print("\n" + ("FALHOU: " + str(len(falhas)) if falhas else "TUDO OK"))
sys.exit(1 if falhas else 0)
