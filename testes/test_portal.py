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

import json  # noqa: E402

from dominio.acoes import (  # noqa: E402
    disciplinas_so_no_portal,
    montar_acoes,
    provas_do_portal,
)
from fontes import portal  # noqa: E402
from fontes.portal import (  # noqa: E402
    RE_ATIVIDADE,
    RE_RA,
    RE_TELA_DE_PROVAS,
    RE_TITULO_PROVA,
    _iso,
)

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
De: 03/12 14:05
Até 03/12 18:15

Presencial
2026 - LET110 - LEITURA E PRODUÇÃO DE TEXTOS - 3 BIMESTRE
De: 03/12 14:05
Até 03/12 18:15

Presencial
2026 - SOC100 - ÉTICA CIDADANIA E SOCIEDADE - 3 BIMESTRE
De: 03/12 14:05
Até 03/12 18:15
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
checa(primeira[2] == "03/12" and primeira[3] == "14:05",
      "início com dia e hora, do jeito que a tela escreve")

cabecalho = RE_TITULO_PROVA.match(primeira[1])
checa(bool(cabecalho), "o título casa com ano, código e nome")
checa(cabecalho.group(1) == "2026", "o ano vem do título, que é onde ele existe")
checa(cabecalho.group(2) == "COM100", "o código da disciplina é extraído")

checa(not list(RE_ATIVIDADE.finditer(VAZIO)),
      "tela sem atividade não inventa prova")

# A aba nasce numa página de espera antes de chegar ao calendário. Ler cedo
# demais devolvia "nenhuma prova", que é diferente de "não consegui ler".
ESPERA = "Prezados estudantes, estamos redirecionando para sistemas de provas."
checa(bool(RE_TELA_DE_PROVAS.search(CALENDARIO)),
      "a tela do calendário é reconhecida")
checa(bool(RE_TELA_DE_PROVAS.search(VAZIO)),
      '"nenhuma atividade" também é o calendário, e é resposta legítima')
checa(not RE_TELA_DE_PROVAS.search(ESPERA),
      "a página de redirecionamento não passa por calendário vazio")

checa(_iso("03/12", "14:05", 2026).startswith("2026-12-03T14:05"),
      "a data vira ISO no fuso de Brasília")
checa(_iso("31/02", "14:05", 2026) is None,
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
                "inicio": "2026-12-03T14:05:00-03:00",
                "fim": "2026-12-03T18:15:00-03:00",
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
    checa("acontece 03/12" in a["prazo_txt"],
          f"o texto trata como encontro, não como vencimento ({a['prazo_txt']})")
    checa(a["prazo_fonte"] == "Sistema de Provas (portal do aluno)",
          "a origem da data aparece, como toda data neste guia")
    checa(a["conta_nota"] is True, "prova vale nota")

# No dia seguinte à prova ela some sozinha, como a live que já aconteceu.
depois = provas_do_portal(
    DADOS, date(2026, 12, 4),
    agora=datetime(2026, 12, 4, 8, 0, tzinfo=timezone(timedelta(hours=-3))),
)
checa(not depois, "prova que já passou sai da fila")

sem_portal = provas_do_portal({"courses": []}, date(2026, 8, 15), agora=AGORA)
checa(sem_portal == [],
      "sem leitura do portal não aparece prova nenhuma, nem inventada")


print("\n== boletim da secretaria ==")

# Linhas copiadas da tela nova em 29/08/2026, célula a célula. A tabela agora
# tem só quatro colunas (Disciplina, Avaliações, Média Final, Situação; a
# frequência saiu do boletim) e a célula da disciplina traz "CH: Nh" colado
# no nome, na mesma célula. A primeira linha é ruído (uma tabela de
# coordenadas que a página deixa por perto), e serve para provar que linha
# sem disciplina não vira registro.
LINHAS_REAIS = [
    ["X", "Y", "largura", "altura"],
    ["SOC100 - Ética, cidadania e Sociedade CH: 40h",
     "ATIVIDADE AVA -- PROVA -- MÉDIA PARCIAL -- EXAME --", "",
     "(Em Recuperação)"],
    ["COM170 - Inteligência Artificial na Prática Acadêmica e Profissional CH: 80h",
     "ATIVIDADE AVA --", "", "Cursando"],
]


class PaginaDeNotas:
    """A tela só monta a tabela depois que o seletor dispara ``change``."""

    def __init__(self, linhas, precisa_cutucar=True):
        self.linhas = linhas
        self.precisa_cutucar = precisa_cutucar
        self.cutucou = False

    def goto(self, *a, **k):
        pass

    def wait_for_timeout(self, *a):
        pass

    def evaluate(self, js):
        if "dispatchEvent" in js:
            self.cutucou = True
            return None
        if self.precisa_cutucar and not self.cutucou:
            return [["X", "Y", "largura", "altura"]]
        return self.linhas


tela = PaginaDeNotas(LINHAS_REAIS)
notas = portal.ler_notas(tela)
checa(tela.cutucou,
      "a tabela não vem pela URL: o seletor de ano/semestre é acionado")
checa([n["codigo"] for n in notas] == ["SOC100", "COM170"],
      "a disciplina é achada mesmo com ruído na primeira linha")
checa(notas[0]["nome"] == "Ética, cidadania e Sociedade",
      "o 'CH: 40h' colado no nome pela tela nova não entra no nome")
checa(notas[0]["situacao"] == "(Em Recuperação)",
      "a situação real é publicada, mesmo vindo sozinha (sem 'Cursando' junto)")
checa(notas[1]["situacao"] == "Cursando", "'Cursando' sozinho também é situação")
checa(notas[0]["frequencia"] == "",
      "a tabela nova não tem coluna de frequência: fica vazio, não inventado")
checa(list(notas[0]["parcelas"]) ==
      ["ATIVIDADE AVA", "PROVA", "MÉDIA PARCIAL", "EXAME"],
      "as quatro parcelas do bimestre são lidas")
checa(list(notas[1]["parcelas"]) == ["ATIVIDADE AVA"],
      "COM170 tem só a parcela do AVA, e isso é dado, não falha de leitura")

# Layout estreito da tabela responsiva injeta "Disciplina " na frente da
# célula (a coluna que só aparece nesse layout). A leitura não pode depender
# do tamanho de tela do headless.
COM_ROTULO_MOBILE = [["Disciplina COM100 - Pensamento Computacional CH: 80h",
                      "ATIVIDADE AVA 5,40 PROVA 8,50 MÉDIA PARCIAL 7,26 EXAME --",
                      "7,26", "Aprovado"]]
com_nota = portal.ler_notas(PaginaDeNotas(COM_ROTULO_MOBILE))[0]
checa(com_nota["codigo"] == "COM100" and com_nota["nome"] == "Pensamento Computacional",
      "o rótulo 'Disciplina ' do layout estreito não impede a leitura")
checa(com_nota["parcelas"]["PROVA"] == "8,50"
      and com_nota["parcelas"]["ATIVIDADE AVA"] == "5,40",
      "com nota preenchida, cada valor fica no seu rótulo")

# O pareamento é por par rótulo/valor, não por posição: uma linha nova entre
# os dois deixa de virar nota. Antes, "Peso 4" viraria a nota do AVA.
RUIDO = [["COM100 - Pensamento Computacional CH: 80h",
          "ATIVIDADE AVA Peso 4 5,40 PROVA 8,50", "", "Cursando"]]
ruido = portal.ler_notas(PaginaDeNotas(RUIDO))[0]
checa(ruido["parcelas"].get("ATIVIDADE AVA") is None
      and ruido["parcelas"]["PROVA"] == "8,50",
      "texto estranho entre rótulo e valor não vira nota inventada")

checa(portal.ler_notas(PaginaDeNotas([["X", "Y", "largura", "altura"]],
                                     precisa_cutucar=False)) is None,
      "tabela que não veio devolve None: vazio aqui seria uma afirmação falsa")


print("\n== de onde veio a data da prova ==")

# O Sistema de Provas fica atrás de verificação anti-robô, que não se contorna
# aqui. Então a data pode vir de uma conferência humana, e o cartão precisa
# dizer isso: as duas origens decidem o mesmo dia, mas envelhecem diferente.
A_MAO = {
    "courses": [{"code": "COM100"}],
    "portal": {
        **DADOS["portal"],
        "provas_origem": "conferido à mão",
        "provas_conferido_em": "2026-08-15",
    },
}
fonte_manual = provas_do_portal(A_MAO, date(2026, 8, 15), agora=AGORA)[0]
checa(fonte_manual["prazo_fonte"] == "Sistema de Provas, conferido à mão em 15/08",
      "conferência à mão aparece com a data em que foi feita")

fonte_viva = provas_do_portal(DADOS, date(2026, 8, 15), agora=AGORA)[0]
checa(fonte_viva["prazo_fonte"] == "Sistema de Provas (portal do aluno)",
      "leitura ao vivo continua se apresentando como leitura ao vivo")

SEM_DATA = {
    "courses": [{"code": "COM100"}],
    "portal": {**DADOS["portal"], "provas_origem": "conferido à mão"},
}
checa(
    provas_do_portal(SEM_DATA, date(2026, 8, 15), agora=AGORA)[0]["prazo_fonte"]
    == "Sistema de Provas, conferido à mão",
    "sem saber quando foi conferido, não inventa uma data de conferência",
)


print("\n== disciplina que só a secretaria conhece ==")

fora = disciplinas_so_no_portal(DADOS)
checa({d["codigo"] for d in fora} == {"MMB002", "INT100"},
      "as duas matrículas sem turma no AVA aparecem")

checa(disciplinas_so_no_portal({"courses": [], "portal": DADOS["portal"]}) == [],
      "sem disciplina lida no AVA não dá para comparar, então não acusa nada")

checa(disciplinas_so_no_portal({"courses": [{"code": "COM100"}]}) == [],
      "sem leitura do portal também não acusa nada")


print("\n== entrega de grupo não é falta de quem não é representante ==")

GRUPO = {
    "courses": [{
        "id": "18922", "code": "COM170", "modelo": "quinzena", "avisos": [],
        "sections": [{
            "id": "q2m7", "title": "Q2 Módulo 7",
            "items": [{
                "cmid": "215612",
                "label": "Q2 M7 - Revisão entre pares (Portfólio em grupo)",
                "type": "workshop",
                "url": "https://ava.univesp.br/mod/workshop/view.php?id=215612",
                "status": "Pendente", "conta_nota": True,
                "enviado": False, "avaliacao_pendente": None,
                "prazo": "2026-08-15T23:59:00-03:00",
            }],
        }],
    }],
    "eventos": [],
}
acoes_grupo, _, _, _ = montar_acoes(
    GRUPO, date(2026, 8, 15),
    agora=datetime(2026, 8, 15, 10, 0, tzinfo=timezone(timedelta(hours=-3))),
)
cartao = acoes_grupo[0]
checa(cartao["verbo"] == "Confirme com o grupo",
      "o pedido é confirmar com quem envia, não entregar")
checa("representante" in (cartao.get("explicacao") or ""),
      "e o cartão explica que o envio é do representante")
# O guia não sabe quem representa o grupo nesta quinzena. Dizer só "confirme
# com o representante" cala justo na quinzena em que o representante é ele,
# que foi o caso da Quinzena 1: ele enviou o M7 em 31/07.
checa("Se for você, o envio é seu" in (cartao.get("explicacao") or ""),
      "e cobre o caso de o representante ser ele mesmo")
checa(cartao.get("entrega_nao_confirmada") is not True,
      "não sai marcado como entrega faltando, porque não é falta dele")

INDIVIDUAL = json.loads(json.dumps(GRUPO))
item = INDIVIDUAL["courses"][0]["sections"][0]["items"][0]
item["label"] = "Q2 M6 - Revisão entre pares (Portfólio Individual)"
acoes_ind, _, _, _ = montar_acoes(
    INDIVIDUAL, date(2026, 8, 15),
    agora=datetime(2026, 8, 15, 10, 0, tzinfo=timezone(timedelta(hours=-3))),
)
checa(acoes_ind[0]["verbo"] != "Confirme com o grupo",
      "a entrega individual continua sendo cobrança dele, como sempre foi")


print("\n== qual usuário o portal quer ==")

# O portão único (acesso.univesp.br) tem um campo só, e o caminho confirmado
# ao vivo em 29/08/2026 foi o e-mail institucional completo — o mesmo que o
# SSO do AVA usa. RA sozinho ganha o domínio, pra não virar mais um segredo
# a manter em dia.
for chave in ("PORTAL_USUARIO", "AVA_USUARIO"):
    os.environ.pop(chave, None)

os.environ["AVA_USUARIO"] = "90011122@aluno.univesp.br"
checa(portal._identidade() == "90011122@aluno.univesp.br",
      "e-mail institucional completo vai direto pro campo único")

os.environ["AVA_USUARIO"] = "90011122"
checa(portal._identidade() == "90011122@aluno.univesp.br",
      "RA sozinho ganha o domínio institucional")

os.environ["PORTAL_USUARIO"] = "outro@aluno.univesp.br"
checa(portal._identidade() == "outro@aluno.univesp.br",
      "PORTAL_USUARIO, quando existe, tem a palavra final")

for chave in ("PORTAL_USUARIO", "AVA_USUARIO"):
    os.environ.pop(chave, None)
checa(portal._identidade() == "", "sem nada configurado não há identidade")


print("\n== tela inicial: disciplinas e RA no formato novo ==")

# Copiado da tela real em 29/08/2026: o rótulo virou "RA:" (era "Registro
# Acadêmico:") e a situação da disciplina vem sozinha na linha seguinte
# ("CURSANDO", maiúsculo), não mais precedida de "Situação:".
# O RA e o nome abaixo sao sinteticos de proposito: formato valido, valor que
# nao existe. O RA real e dado pessoal e nao entra em fixture (regra de
# 12/09/2026). Trocar por um marcador tipo "RA_OCULTO" quebra o parser, que
# exige digitos, e foi o que deixou esta suite vermelha ate 13/09/2026.
TELA_INICIAL_REAL = """ALUNO DE TESTE
RA: 00000000
Início
COM170 - Inteligência Artificial na Prática Acadêmica e Profissional
CURSANDO
Período Estudo: 22/06/2026 à 19/12/2026
Média: -
EAD
Conteúdo
Moodle
MMB002 - Matemática Básica
CURSANDO
Período Estudo: 22/06/2026 à 19/12/2026
Média: -
"""

checa(RE_RA.search(TELA_INICIAL_REAL).group(1) == "00000000",
      "o RA é lido no formato novo ('RA: <digitos>')")


class PaginaDeTelaInicial:
    def __init__(self, texto, contador=9):
        self.texto = texto
        self.contador = contador

    def goto(self, *a, **k):
        pass

    def wait_for_timeout(self, *a):
        pass

    class _Corpo:
        def __init__(self, texto):
            self._texto = texto

        def inner_text(self):
            return self._texto

    def locator(self, seletor):
        assert seletor == "body"
        return self._Corpo(self.texto)

    def evaluate(self, js):
        return str(self.contador)


tela_inicial = portal.ler_tela_inicial(PaginaDeTelaInicial(TELA_INICIAL_REAL))
checa(tela_inicial["ra"] == "00000000", "o RA sai junto com o resto da leitura")
checa([d["codigo"] for d in tela_inicial["disciplinas"]] == ["COM170", "MMB002"],
      "as duas disciplinas são achadas")
checa(all(d["situacao"] == "CURSANDO" for d in tela_inicial["disciplinas"]),
      "'CURSANDO' maiúsculo e sozinho é reconhecido como situação")
checa(tela_inicial["recados_nao_lidos"] == 9,
      "o contador de recados sai do badge do ícone de mensagens")


print("\n" + ("FALHOU: " + str(len(falhas)) if falhas else "TUDO OK"))
if __name__ == "__main__":
    sys.exit(1 if falhas else 0)
