# -*- coding: utf-8 -*-
"""
Testes da lógica de prazos, ações e cobertura.

Rodar:  python testes/test_prazos.py

Não entram no AVA: usam textos reais já lidos de avisos e estruturas mínimas
de curso. Cada teste aqui nasceu de um erro que chegou a ir pro ar, então
não apague nenhum sem entender qual falha ele evita.
"""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "automacao"))
import coletar as C  # noqa: E402
from dominio.datas import sem_acento  # noqa: E402
from dominio.prazos import eh_saudacao  # noqa: E402
from fontes.instrucoes import (  # noqa: E402
    _chave_do_prazo as chave_do_prazo,
    _como_aviso as como_aviso,
    _completar_pelo_texto,
    consequencia_do_prazo,
    hora_declarada,
    lives_anunciadas,
)

BR = timezone(timedelta(hours=-3))
HOJE = date(2026, 7, 25)
REF = datetime(2026, 7, 24, 20, 8, tzinfo=BR)

falhas = []


def checa(cond, msg):
    print(("  ok    " if cond else "  FALHA") + " | " + msg)
    if not cond:
        falhas.append(msg)


def quando(prazos):
    return {datetime.fromisoformat(p["quando"]).strftime("%d/%m %H:%M") for p in prazos}


# ---------------------------------------------------------------------------
print("\n== Datas em texto livre ==")

casos = [
    ("entregue até 26/07", "26/07", False),
    ("entrega até 26/07 às 18h30", "26/07", True),
    ("prazo: 01 ago. 2026, 23:59", "01/08", True),
    ("entregar até 1º de agosto", "01/08", False),
    ("prazo até 26 de julho", "26/07", False),
]
for texto, dia, tem_hora in casos:
    achados = C.achar_datas(texto, REF)
    ok = any(d.strftime("%d/%m") == dia for d, _, _, _ in achados)
    checa(ok, f"lê data em {texto!r}")
    if ok:
        certa = [h for d, _, h, _ in achados if d.strftime("%d/%m") == dia][0]
        checa(certa == tem_hora,
              f"hora_certa={tem_hora} em {texto!r} (não inventa horário)")

# virada de ano: aviso de dezembro falando em janeiro
ref_dez = datetime(2026, 12, 20, 10, 0, tzinfo=BR)
achados = C.achar_datas("entregar até 10 de janeiro", ref_dez)
checa(any(d.year == 2027 for d, _, _, _ in achados),
      "aviso de dezembro que cita janeiro cai no ano seguinte")

# ---------------------------------------------------------------------------
print("\n== Abertura não é prazo ==")

AVISO = """O Módulo 4 é diferente. A atividade final precisa ser entregue até o primeiro
domingo da quinzena, dia 26/07 às 23h59.
Módulo 5: atividade individual, com prazo a confirmar.
Módulo 6 e 7: início da atividade em grupo com entrega e revisão entre pares:
Abertura das submissões: segunda-feira, 27 jul. 2026, 00:00
Fechamento das submissões: sábado, 01 ago. 2026, 23:59
Abertura das avaliações por pares: domingo, 02 ago. 2026, 00:00
Fechamento das avaliações por pares: terça-feira, 04 ago. 2026, 23:59"""

prazos = C.extrair_prazos(AVISO, REF)
tipos = {datetime.fromisoformat(p["quando"]).strftime("%d/%m"): p["tipo"] for p in prazos}
checa(tipos.get("27/07") == "inicio", "27/07 é abertura, não prazo")
checa(tipos.get("01/08") == "fim", "01/08 é fechamento da entrega")
checa(tipos.get("02/08") == "inicio", "02/08 é abertura da avaliação por pares")
checa(tipos.get("04/08") == "fim", "04/08 é fechamento da avaliação por pares")
checa(tipos.get("26/07") == "fim", "26/07 é prazo do Módulo 4")

# a armadilha que foi pro ar: "inicia" casando dentro de "LIVE INICIAL"
p_live = C.extrair_prazos("LIVE INICIAL: prazo para assistir é 30/07", REF)
checa(all(p["tipo"] == "fim" for p in p_live),
      "'LIVE INICIAL' não vira abertura ('inicia' não casa dentro de 'inicial')")

# ruído não pode virar prazo
ruido = "Bora começar! O livro do Russell e Norvig, 4. ed., 2025, está na biblioteca."
checa(len(C.extrair_prazos(ruido, REF)) == 0, "conversa de fórum não vira prazo")

# ---------------------------------------------------------------------------
print("\n== Escopo: a qual módulo o prazo pertence ==")

por_secao = lambda t: quando(C.casar_prazos(t, prazos))  # noqa: E731
checa("01/08 23:59" in por_secao("Módulo 6"), "Módulo 6 recebe o fechamento da entrega")
checa("04/08 23:59" in por_secao("Módulo 6"), "Módulo 6 recebe a avaliação por pares")
checa("04/08 23:59" in por_secao("Módulo 7"), "Módulo 7 também é coberto por 'Módulo 6 e 7'")
checa("26/07 23:59" in por_secao("Módulo 4"), "Módulo 4 recebe o próprio prazo")
checa("26/07 23:59" not in por_secao("Módulo 6"), "prazo do Módulo 4 não vaza pro 6")
checa(all(p["tipo"] != "inicio" for p in C.casar_prazos("Módulo 6", prazos)),
      "abertura nunca vira prazo de seção")

# ---------------------------------------------------------------------------
print("\n== Ações: fases, itens e prazo que não contamina ==")

def curso_teste():
    return {"courses": [{
        "code": "COM170", "modelo": "quinzenal",
        "avisos": [{"autor": "formador", "url": "https://ava/x", "prazos": prazos}],
        "sections": [
            {"title": "Módulo 1", "fase": "regular", "locked": None, "items": [
                {"label": "M1 - Quiz", "type": "scorm", "status": "Pendente",
                 "conta_nota": True, "aberto": True, "url": "#"},
                {"label": "M1 - Leitura opcional", "type": "page",
                 "status": "Marcar como feito", "conta_nota": False,
                 "aberto": True, "url": "#"}]},
            {"title": "Módulo 2", "fase": "regular",
             "locked": "libera quando A atividade M1 - Quiz esteja marcada como concluída",
             "items": []},
            {"title": "Módulo 3", "fase": "regular",
             "locked": "libera quando A atividade M2 - Como a IA aprende esteja marcada como concluída",
             "items": []},
            {"title": "Módulo 4", "fase": "regular",
             "locked": "libera quando A atividade M3 - O custo invisível esteja marcada como concluída",
             "items": []},
            {"title": "Módulo 6", "fase": "regular", "locked": None, "items": [
                {"label": "M6 - Material de apoio", "type": "page",
                 "status": "Marcar como feito", "conta_nota": False,
                 "aberto": True, "url": "#"}]},
        ]}]}

# Módulos travados vêm sem itens do Moodle: a cadeia precisa ser andada
# pelos textos de bloqueio, não pelos itens.
dados = curso_teste()
acoes, encerrados, higiene, confirmar = C.montar_acoes(dados, HOJE)

def acao(trecho):
    return next((a for a in acoes if trecho.lower() in a["o_que"].lower()), None)

checa(any("avali" in a["o_que"].lower() or "Avalie" == a["verbo"] for a in acoes),
      "a fase de avaliação por pares virou ação própria")
fases_m6 = [a for a in acoes if a["secao"] == "Módulo 6" and a["tipo"] == "obrigacao"]
checa(len(fases_m6) >= 2, "Módulo 6 gera uma ação por fase (entrega e avaliação)")

apoio = acao("Material de apoio")
checa(apoio is None or not apoio.get("prazo"),
      "material de apoio NÃO herda o prazo da seção")

quiz = acao("M1 - Quiz")
checa(quiz is not None, "o quiz do Módulo 1 aparece na fila")
checa(quiz and not quiz.get("prazo"), "o quiz não ganha prazo inventado")
checa(quiz and quiz.get("prioridade_ate"), "o quiz herda PRIORIDADE da etapa travada")
checa(quiz and quiz.get("destrava"), "o quiz diz qual etapa ele destrava")
checa(quiz and quiz["urgencia"] in ("hoje", "amanha"),
      "o quiz sobe pro topo por causa do prazo do Módulo 4")

opcional = acao("Leitura opcional")
checa(opcional is None or not opcional.get("prioridade_ate"),
      "item sem dependência declarada não herda prioridade")

# ---------------------------------------------------------------------------
print("\n== Rótulo e duplicata da obrigação ==")

# o facilitador repete o mesmo prazo em mais de um aviso
dados2 = curso_teste()
dados2["courses"][0]["avisos"].append(
    {"autor": "formador", "url": "https://ava/y", "prazos": prazos})
acoes2, _, _, _ = C.montar_acoes(dados2, HOJE)
obrig = [a for a in acoes2 if a["tipo"] == "obrigacao"]
chaves = {(a["secao"], a["prazo"], a["verbo"]) for a in obrig}
checa(len(obrig) == len(chaves), "prazo repetido em dois avisos não duplica a ação")
checa(not [a for a in obrig if len(a["o_que"]) > 80],
      "rótulo da fase é curto e legível")

# o bloco cita entrega E revisão entre pares; o rótulo é que decide o verbo
verbo_por_data = {a["prazo"][:10]: a["verbo"] for a in obrig}
checa(verbo_por_data.get("2026-08-01") == "Entregue",
      "fechamento das submissões vira 'Entregue', não 'Avalie'")
checa(verbo_por_data.get("2026-08-04") == "Avalie",
      "fechamento das avaliações por pares vira 'Avalie'")

# ---------------------------------------------------------------------------
print("\n== Falhar fechado ==")

def curso(cid, code):
    return {"id": cid, "code": code, "sections": [{"items": [{"label": "x"}]}]}


ok, probs = C.validar_cobertura({"courses": []}, {"courses": [{"id": 1, "code": "X"}]})
checa(not ok, "coleta sem nenhuma disciplina é recusada")
checa(any("disciplina" in p for p in probs), "e explica o motivo")

anterior = {"courses": [curso(i, c) for i, c in enumerate("ABCD", 1)]}

# O limiar antigo era "< metade", então perder 1 ou 2 de 4 passava calado.
for n in (3, 2, 1):
    nova = {"courses": [curso(i, c) for i, c in enumerate("ABCD"[:n], 1)]}
    ok, _ = C.validar_cobertura(nova, anterior)
    checa(not ok, f"queda de 4 para {n} disciplina(s) é recusada")

ok, _ = C.validar_cobertura(anterior, anterior)
checa(ok, "coleta saudável passa")

# virada de bimestre: as antigas somem E entram novas
virada = {"courses": [curso(i, c) for i, c in enumerate("EFGH", 90)]}
ok, _ = C.validar_cobertura(virada, anterior)
checa(ok, "troca de bimestre (todas somem e novas entram) é aceita")

ok, probs = C.validar_cobertura(
    {"courses": [{"id": 1, "code": "A", "sections": []}]}, None)
checa(not ok, "disciplina sem seção nenhuma é recusada")

# ---------------------------------------------------------------------------
print("\n== Achados da auditoria rodada 2 ==")

# escopo não pode vazar para o assunto seguinte
texto_misto = ("Módulo 4: o trabalho precisa ser entregue até 26/07.\n"
               "LIVE MAGNA: será realizada em 30/07.\n"
               "Prova presencial: acontece em 10/09.")
pz_misto = C.extrair_prazos(texto_misto, REF)
m4 = C.casar_prazos("Módulo 4", pz_misto)
checa(len(m4) == 1 and m4[0]["quando"][:10] == "2026-07-26",
      "assunto novo encerra o escopo: live e prova não viram prazo do Módulo 4")

# abertura e fechamento na mesma frase
p_par = C.extrair_prazos("A abertura ocorre em 27/07 e o prazo fecha em 01/08.", REF)
t_par = {p["quando"][:10]: p["tipo"] for p in p_par}
checa(t_par.get("2026-07-27") == "inicio", "na mesma frase, 27/07 é abertura")
checa(t_par.get("2026-08-01") == "fim", "na mesma frase, 01/08 é fechamento")

# "abre/fecha" precisam passar no pré-filtro
p_ab = C.extrair_prazos("A atividade abre em 27/07 e fecha em 01/08.", REF)
checa(len(p_ab) == 2, "'abre em ... e fecha em ...' não é descartado pelo filtro")

# duas obrigações distintas com mesmo horário e mesmo verbo
def _pz(rot, quando_iso):
    return {"rotulo": rot, "quando": quando_iso, "trecho": "", "tipo": "fim",
            "hora_certa": True, "frase": rot,
            "escopo": {"familia": "modulo", "numeros": [6], "txt": rot}}

dois = [_pz("Fechamento da submissão individual", "2026-08-01T23:59:00-03:00"),
        _pz("Fechamento da submissão do grupo", "2026-08-01T23:59:00-03:00")]
d3 = {"courses": [{"code": "COM170", "modelo": "quinzenal",
      "avisos": [{"autor": "formador", "url": "u", "prazos": dois}],
      "sections": [{"title": "Módulo 6", "fase": "regular", "locked": None,
                    "items": []}]}]}
obrig3 = [a for a in C.montar_acoes(d3, HOJE)[0] if a["tipo"] == "obrigacao"]
checa(len(obrig3) == 2,
      "entrega individual e de grupo, mesmo horário, não colapsam numa só")

# item_aberto: texto real do workshop e páginas que não deixam ver
checa(any(s in C.sem_acento("Submissões fechadas. Avaliações fechadas.")
          for s in C.SINAIS_FECHADO), "'Submissões fechadas' conta como fechado")
checa(any(s in C.sem_acento("O prazo de envio terminou.")
          for s in C.SINAIS_FECHADO), "'prazo de envio terminou' conta como fechado")
checa(any(s in C.sem_acento("Você precisa fazer login para continuar.")
          for s in C.SINAIS_INDEFINIDO), "página de login não afirma nada sobre a atividade")
checa(any(s in C.sem_acento("Você não tem permissão para visualizar.")
          for s in C.SINAIS_INDEFINIDO), "página sem permissão não afirma nada")

# ---------------------------------------------------------------------------
print("\n== Achados da auditoria rodada 3 ==")

# negação não pode virar obrigação
checa(C.extrair_prazos("Não haverá entrega em 30/07.", REF) == [],
      "frase que NEGA a entrega não vira prazo")
checa(C.extrair_prazos("Sem entrega em 30/07.", REF) == [],
      "'sem entrega' também não vira prazo")

# mudança de assunto sem dois pontos
pz_live = C.extrair_prazos(
    "Módulo 4: entrega até 26/07.\nLIVE MAGNA será realizada em 30/07.", REF)
m4 = C.casar_prazos("Módulo 4", pz_live)
checa([p["quando"][:10] for p in m4] == ["2026-07-26"],
      "título em caixa alta encerra o escopo mesmo sem dois pontos")
checa(any(p["tipo"] == "compromisso" and p["quando"][:10] == "2026-07-30"
          for p in pz_live), "a data da live vira compromisso, não prazo")
checa(all(p["tipo"] != "compromisso" for p in m4),
      "compromisso não entra na fila de entrega do módulo")

# fechamento depois da data: não pode virar abertura silenciosa
pz_par = C.extrair_prazos(
    "27/07 (abertura das inscrições), 01/08 (fechamento das inscrições).", REF)
checa(all(p["confianca"] == "baixa" for p in pz_par),
      "gatilho antes e depois discordando marca o prazo como duvidoso")
checa(C.casar_prazos("Módulo 4", pz_par) == [],
      "prazo duvidoso não entra na fila como se fosse certo")

# subtítulo que não é fase
pz_grupo = C.extrair_prazos(
    "Módulo 4: orientações.\nGrupo A: entrega até 26/07.", REF)
checa(pz_grupo and pz_grupo[0]["confianca"] == "baixa",
      "subtítulo desconhecido rebaixa a confiança em vez de perder o prazo")

# o aviso real não pode regredir
altas = [p for p in prazos if p["confianca"] == "alta"]
checa({p["quando"][:10] for p in altas} >= {"2026-07-26", "2026-08-01", "2026-08-04"},
      "aviso real: os três prazos de verdade seguem confiáveis")

# cobertura: disciplina nova não perdoa disciplina perdida
ant2 = {"courses": [{"id": 1, "code": "A"}, {"id": 2, "code": "B"}]}
nova2 = {"courses": [curso(2, "B"), curso(3, "C")]}
ok, _ = C.validar_cobertura(nova2, ant2)
checa(not ok, "entrar disciplina nova não mascara a perda de outra")

sem_ids = {"courses": [{"code": "A"}, {"code": "B"}]}
ok, _ = C.validar_cobertura({"courses": [curso(None, "A")]}, sem_ids)
checa(not ok, "sem id no histórico, a checagem cai pro código em vez de desligar")

# dedup por rótulo inteiro
longos = [_pz("Entrega da atividade final para composição da avaliação do módulo individual",
              "2026-08-01T23:59:00-03:00"),
          _pz("Entrega da atividade final para composição da avaliação do módulo em grupo",
              "2026-08-01T23:59:00-03:00")]
d4 = {"courses": [{"code": "COM170", "modelo": "quinzenal",
      "avisos": [{"autor": "L", "url": "u", "prazos": longos}],
      "sections": [{"title": "Módulo 6", "fase": "regular", "locked": None, "items": []}]}]}
checa(len([a for a in C.montar_acoes(d4, HOJE)[0] if a["tipo"] == "obrigacao"]) == 2,
      "rótulos longos que só diferem no fim não colapsam")

# item que não deu pra verificar vai marcado
d5 = {"courses": [{"code": "COM100", "modelo": "regular", "avisos": [],
     "sections": [{"title": "Semana 1", "fase": "regular", "locked": None, "items": [
        {"label": "S1 - Atividade Avaliativa", "type": "quiz", "status": "Pendente",
         "conta_nota": True, "aberto": None, "url": "#"}]}]}]}
a5 = C.montar_acoes(d5, HOJE)[0][0]
checa(a5.get("verificacao") == "indefinida",
      "item que o robô não conseguiu abrir sai marcado como não verificado")

# higiene sai da fila principal
d6 = {"courses": [{"code": "COM100", "modelo": "regular", "avisos": [],
     "sections": [{"title": "Semana 1", "fase": "regular", "locked": None, "items": [
        {"label": "S1 - Início", "type": "page", "status": "Marcar como feito",
         "conta_nota": False, "aberto": True, "url": "#"}]}]}]}
ac6, _, hig6, _ = C.montar_acoes(d6, HOJE)
checa(not ac6 and len(hig6) == 1,
      "item sem prazo e sem nota vai pra higiene, não pra fila principal")

# ---------------------------------------------------------------------------
print("\n== Achados da auditoria rodada 4 ==")

# a saúde precisa olhar as FONTES DE PRAZO, não só o Moodle ter aberto
def curso_sem_prazo():
    return {"id": 1, "code": "COM170", "modelo": "quinzenal", "avisos": [],
            "cronograma": None,
            "sections": [{"title": "Módulo 1", "fase": "regular", "locked": None,
                          "items": [{"label": "M2 - Material-base", "type": "page",
                                     "status": "Pendente", "conta_nota": True,
                                     "aberto": True, "url": "#", "prazo": None}]}]}


ontem = {"courses": [{"id": 1, "code": "COM170"}],
         "fontes": {"avisos": 12, "eventos_calendario": 3, "cronograma": 3,
                    "itens_com_prazo": 15}}
ok, probs = C.validar_cobertura(
    {"courses": [curso_sem_prazo()], "eventos": [], "notificacoes": []}, ontem)
checa(not ok, "perder TODAS as fontes de prazo não passa mais como saudável")
checa(any("prazo" in p for p in probs), "e o motivo cita a perda dos prazos")

vivo = curso_sem_prazo()
vivo["avisos"] = [{"titulo": "x"}] * 12
vivo["cronograma"] = {"semanas": []}
vivo["sections"][0]["items"][0]["prazo"] = "2026-08-01T23:59:00-03:00"
ontem_vivo = {"courses": ontem["courses"],
              "fontes": {"avisos": 12, "eventos_calendario": 3,
                          "cronograma": 1, "itens_com_prazo": 1}}
ok, _ = C.validar_cobertura(
    {"courses": [vivo], "eventos": [1, 2, 3], "notificacoes": []}, ontem_vivo)
checa(ok, "coleta com as fontes vivas continua passando")

# telemetria não pode contar cronograma que a disciplina não tem
f = C.resumo_fontes({"courses": [{"code": "A", "cronograma": {"semanas": []},
                                  "sections": []},
                                 {"code": "B", "cronograma": None, "sections": []}]})
checa(f["cronograma"] == 1, "telemetria conta só a disciplina que tem cronograma")

# identidade de novidade pelo cmid, não pelo rótulo: o AVA repete o mesmo
# rótulo em atividades diferentes, e o guia não pode confundi-las
ant4 = {"courses": [{"code": "X", "sections": [
    {"items": [{"label": "S1 - Videoaulas", "cmid": "1", "status": "Pendente"},
               {"label": "S1 - Videoaulas", "cmid": "2", "status": "Pendente"}]}]}]}
ago4 = {"courses": [{"code": "X", "sections": [
    {"items": [{"label": "S1 - Videoaulas", "cmid": "1", "status": "Concluído"},
               {"label": "S1 - Videoaulas", "cmid": "2", "status": "Pendente"},
               {"label": "S1 - Videoaulas", "cmid": "3", "status": "Pendente"}]}]}]}
nov4 = C.novidades(ant4, ago4)
checa(len(nov4) == 1 and nov4[0]["cmid"] == "3",
      "dois itens de mesmo rótulo não mascaram a mudança um do outro")

# escrita atômica não deixa arquivo pela metade
import json as _json          # noqa: E402
import tempfile               # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    alvo = Path(tmp) / "d.json"
    C.gravar_json(alvo, {"a": 1})
    checa(_json.loads(alvo.read_text(encoding="utf-8")) == {"a": 1},
          "gravar_json escreve e substitui de uma vez")
    checa(not list(Path(tmp).glob("*.tmp")), "não deixa arquivo temporário para trás")

# ---------------------------------------------------------------------------
print("\n== Urgência ==")

for iso, esperado in [
    ("2026-07-25T23:59:00-03:00", "hoje"),
    ("2026-07-26T23:59:00-03:00", "amanha"),
    ("2026-07-29T23:59:00-03:00", "semana"),
    ("2026-08-30T23:59:00-03:00", "depois"),
    ("2026-06-28T23:59:00-03:00", "vencido"),
    (None, "sem_prazo"),
]:
    urg, _ = C.urgencia_de(iso, HOJE)
    checa(urg == esperado, f"urgência de {str(iso)[:10]} = {esperado}")

_, txt = C.urgencia_de("2026-07-26T23:59:00-03:00", HOJE, hora_certa=False)
checa("horário não informado" in txt, "sem hora na fonte, o texto avisa em vez de inventar")

# ---------------------------------------------------------------------------
print("\n== Mês da célula no calendário da quinzena (17/08) ==")

# A legenda da Quinzena 3 atravessa dois meses e o código pegava o último mês
# escrito: os prazos de 23 e 29 de agosto foram para o ar como 23/09 e 29/09,
# com confiança alta, na fila e no e-mail.
from fontes.instrucoes import data_da_celula, janela_da_legenda  # noqa: E402

Q3 = janela_da_legenda(
    "Calendário da Quinzena 3, de 16 de agosto a 1º de setembro de 2026, "
    "com as etapas e os prazos."
)
checa(Q3 is not None, "legenda que atravessa dois meses continua sendo lida")
checa(data_da_celula(23, Q3) == (2026, 8),
      "o dia 23 da Quinzena 3 é de agosto, não de setembro")
checa(data_da_celula(29, Q3) == (2026, 8),
      "a entrega do dia 29 é de agosto, não de setembro")
checa(data_da_celula(1, Q3) == (2026, 9),
      "o dia 1º, esse sim, é do mês do fim do intervalo")
checa(data_da_celula(10, Q3) is None,
      "dia fora do intervalo declarado não vira data chutada")

Q2 = janela_da_legenda(
    "Calendário da Quinzena 2, de 3 a 18 de agosto de 2026, com as etapas "
    "e os prazos."
)
checa(Q2 is not None and Q2["numero"] == 2,
      "legenda de um mês só continua lida, com o número da quinzena")
checa(data_da_celula(9, Q2) == (2026, 8) and data_da_celula(15, Q2) == (2026, 8),
      "os prazos da Quinzena 2 seguem em agosto")
checa(data_da_celula(25, Q2) is None,
      "dia depois do fim do intervalo não entra")

VIRADA = janela_da_legenda(
    "Calendário da Semana 7, de 28 de dezembro a 3 de janeiro de 2027."
)
checa(VIRADA and data_da_celula(30, VIRADA) == (2026, 12),
      "quinzena que vira o ano guarda dezembro em 2026")
checa(VIRADA and data_da_celula(2, VIRADA) == (2027, 1),
      "e janeiro em 2027")

# ---------------------------------------------------------------------------
print("\n" + "=" * 62)
if falhas:
    print(f"{len(falhas)} FALHA(S):")
    for f in falhas:
        print("  - " + f)
    sys.exit(1)
print("Todos os testes passaram.")


# ---------------------------------------------------------------------------
print("\n== Status poluído pelo balão de ajuda do Moodle (25/07) ==")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "automacao"))
from fontes.disciplinas import normalizar_status  # noqa: E402

sujo = ("Concluído\n\n\n   Você deve\n\n   Feito:\n   "
        "Ver M1 - O que é (e o que não é) IA")
checa(normalizar_status(sujo) == "Concluído",
      "'Concluído' seguido do balão de ajuda continua sendo Concluído")
checa(normalizar_status("Pendente\n Você deve\n Feito:") == "Pendente",
      "'Pendente' com texto extra continua sendo Pendente")
checa(normalizar_status("Marcar como feito") == "Marcar como feito",
      "'Marcar como feito' não é alterado")
checa(normalizar_status(None) is None, "sem bloco de conclusão continua None")

# ---------------------------------------------------------------------------
# Live perdida em 30/07/2026: o aviso dizia "está marcada para (30/07), às 19h"
# e o robô extraiu zero prazos. Três defeitos somados, um teste para cada.
# ---------------------------------------------------------------------------
AVISO_LIVE = (
    "Prezados,\n\nEstá marcada para a quinta-feira (30/07), às 19h, a "
    "primeira live da turma com os facilitadores.\n\nSegue link de acesso: "
    "https://lti.elos.vc/rooms/abc\n\nConto com a presença de todos!"
)
pz_perdida = C.extrair_prazos(
    AVISO_LIVE, datetime(2026, 7, 28, 10, 0, tzinfo=BR)
)
checa(len(pz_perdida) == 1 and pz_perdida[0]["tipo"] == "compromisso",
      "'está marcada para' é anúncio de live, não frase sem prazo")
checa(pz_perdida and pz_perdida[0]["quando"][11:16] == "19:00",
      "hora escrita como '19h' vale 19:00, não 23:59")

AGENDA = (
    "Envio o cronograma de lives da Quinzena 2, que inicia na próxima "
    "semana (3/8).\n\nAgenda das Lives\n\nGabrieli e Uebert\n"
    "04/08/2026 - 14h\nhttps://lti.elos.vc/rooms/aaa\n\nCauê e participante\n"
    "05/08/2026 - 11h\nhttps://lti.elos.vc/rooms/bbb\n\nLyon\n"
    "05/08/2026 - 18h\nhttps://lti.elos.vc/rooms/ccc"
)
pz_agenda = C.extrair_prazos(
    AGENDA, datetime(2026, 7, 31, 9, 47, tzinfo=BR)
)
lives = [p for p in pz_agenda if p["tipo"] == "compromisso"]
checa(len(lives) == 3,
      "o link entre as datas não pode cortar a agenda na primeira live")
checa([p["quando"][11:16] for p in lives] == ["14:00", "11:00", "18:00"],
      "cada live guarda a sua própria hora")
checa(any(p.get("titulo_evento") == "Cauê e participante" for p in lives),
      "quem apresenta vem da linha antes da data")
checa(all(p["tipo"] != "compromisso" for p in pz_agenda
          if p["quando"][:10] == "2026-08-03"),
      "início de quinzena sem hora não é live")

# Bug latente: data sem ano sumia calada quando a referência era um date.
checa(C.achar_datas("dia 30/07", date(2026, 7, 28)),
      "data sem ano sobrevive mesmo com referência sem hora")

# ---------------------------------------------------------------------------
print("\n== 18/08: o aviso que desmarca a live, e o guia marcando a live ==")

# Texto copiado do post real do facilitador do LET110, publicado em 17/08 as
# 19:26 no "Forum de duvidas gerais" e repetido em "Avisos". O guia publicou
# "Assista ao vivo: Prezados/as - acontece hoje (horario nao informado)" para
# 18/08, o dia que a frase nega, com o nome tirado da saudacao.
AVISO_TROCA_DE_DIA = (
    "Prezados/as,\n\nConforme comentei anteriormente, nesta semana 5, nossa "
    "live ocorrerá na quinta-feira (20/08) e não na terça-feira (18/08).\n\n"
    "Na semana que vem, a de nº 6, voltamos pra terça-feira (25/08).\n\n"
    "Portanto, a live desta semana será na quinta-feira (20/08), às 20h.\n\n"
    "Tragam as dúvidas de vocês."
)
pz_troca = C.extrair_prazos(
    AVISO_TROCA_DE_DIA, datetime(2026, 8, 18, 8, 30, tzinfo=BR)
)
dias_troca = {p["quando"][:10] for p in pz_troca}
checa("2026-08-18" not in dias_troca,
      "data negada por 'e nao na terca-feira (18/08)' nao vira compromisso")
checa("2026-08-20" in dias_troca,
      "a data afirmada na mesma frase continua valendo")
checa("2026-08-25" in dias_troca,
      "a live da semana seguinte, em outra frase, nao some junto")
checa(all(sem_acento(p.get("titulo_evento") or "") != "prezados/as"
          for p in pz_troca),
      "saudacao 'Prezados/as' nao vira nome de live")
checa(any(p["quando"] == "2026-08-20T20:00:00-03:00" for p in pz_troca),
      "a unica frase que traz a hora ('as 20h') e lida com a hora certa")

checa(eh_saudacao("Prezados/as") and eh_saudacao("Prezados(as)")
      and eh_saudacao("prezadas,"),
      "as tres formas de escrever a mesma saudacao sao reconhecidas")
checa(not eh_saudacao("Olavo e Cassia"),
      "nome proprio que comeca parecido com saudacao nao e descartado")

# ---------------------------------------------------------------------------
print("\n== As seis lives da Quinzena 3 (pagina 228101, lida ao vivo) ==")

# Tres das seis dividem dia com outra, e a deducao por dia da fonte de
# instrucoes ficava com metade delas: o guia mostrava tres opcoes onde o AVA
# oferece seis. Participar ao vivo de uma live e um dos dez pontos da quinzena.
LEMBRETE_Q3 = (
    "LEMBRETE DE DATAS E DA LIVE\nGuarde estas datas\n\n"
    "23 de agosto, domingo, às 23h59. É a data em que os Módulos 1, 2, 3 e 4 "
    "precisam estar concluídos.\n\n"
    "De 24 a 29 de agosto, até sábado, às 23h59. É a janela de envio no "
    "Laboratório de Revisão.\n\n"
    "A quinzena oferece 7 lives, em dias e horários diferentes.\n\n"
    "LIVES\nGabrieli e Uebert\n18/08/2026 · 18h\nEntrar na live\n"
    "Lyon e Victor\n19/08/2026 · 18h\nEntrar na live\n"
    "Vittoria e Nicolle\n19/08/2026 · 16h\nEntrar na live\n"
    "Cauê e participante\n19/08/2026 · 19h\nEntrar na live\n"
    "Lívia e Cássia\n20/08/2026 · 10h\nEntrar na live\n"
    "Carlos e Siguara\n20/08/2026 · 17h\nEntrar na live"
)
pz_q3 = C.extrair_prazos(LEMBRETE_Q3, datetime(2026, 8, 18, 8, 30, tzinfo=BR))
lives_q3 = [p for p in pz_q3 if p["tipo"] == "compromisso"]
checa(len(lives_q3) == 6, "as seis lives publicadas na pagina sao lidas")
sobreviventes = set()
for prazo in lives_q3:
    chave = chave_do_prazo(prazo)
    checa(chave not in sobreviventes,
          f"a live de {prazo['quando'][5:16]} sobrevive a deducao da fonte")
    sobreviventes.add(chave)
checa(chave_do_prazo({"quando": "2026-08-23T23:59:00-03:00", "tipo": "fim"})
      == chave_do_prazo({"quando": "2026-08-23T23:59:00-03:00", "tipo": "fim",
                         "rotulo": "outra frase, mesmo dia"}),
      "data de prazo repetida em varios paragrafos continua saindo uma vez")

# ---------------------------------------------------------------------------
print("\n== A pagina diz a hora, e o guia dizia nao saber (18/08/2026) ==")

# Texto real das duas paginas da Quinzena 3 (ids 228099 e 228101), lidas ao
# vivo em 18/08. A tabela-calendario da so o numero do dia, entao o cartao
# saia "vence 23/08 (horario nao informado)" com a hora escrita por extenso
# dois paragrafos abaixo, e ainda uma regra geral para a disciplina inteira.
TEXTO_Q3 = (
    "A Quinzena 3 comeca no dia 16 de agosto e termina no dia 30, quando a "
    "Quinzena 4 se inicia. Dentro desse periodo existem dois prazos: 23 de "
    "agosto para concluir os quatro primeiros modulos e 29 de agosto para "
    "enviar os trabalhos.\n"
    "23 de agosto, domingo, as 23h59. E a data em que os Modulos 1, 2, 3 e 4 "
    "precisam estar concluidos.\n"
    "Uma regra que vale para toda a disciplina: os prazos terminam sempre as "
    "23h59 do dia indicado.\n"
    "Quem conclui os quatro primeiros modulos depois de domingo, 23 de "
    "agosto, as 23h59, recebe na segunda-feira a etapa pratica individual: "
    "le a situacao e escreve o trabalho individual, dentro da mesma janela "
    "de entrega. Esse trabalho vale por inteiro. O trabalho em grupo fica "
    "com quem concluiu os modulos ate domingo, e a sua proxima oportunidade "
    "de participar dele chega na quinzena seguinte."
)

checa(hora_declarada(TEXTO_Q3, 23, 8) == (23, 59),
      "a hora escrita ao lado da data e lida")
checa(hora_declarada(TEXTO_Q3, 29, 8) == (23, 59),
      "e a regra geral da disciplina responde pelas datas sem hora propria")
checa(hora_declarada("nenhuma hora aqui, so o dia 5 de setembro", 5, 9)
      is None,
      "pagina que nao escreve hora nenhuma continua sem hora")

prazo_23 = _completar_pelo_texto(
    {"quando": "2026-08-23T23:59:00-03:00", "hora_certa": False}, TEXTO_Q3
)
checa(prazo_23["hora_certa"] is True,
      "o prazo da tabela para de dizer 'horario nao informado'")
checa(prazo_23["quando"] == "2026-08-23T23:59:00-03:00",
      "e a hora continua sendo a que a pagina declarou")
checa("declara o horario" in sem_acento(prazo_23.get("hora_fonte") or ""),
      "com a origem da hora registrada")

sem_hora = _completar_pelo_texto(
    {"quando": "2026-09-05T23:59:00-03:00", "hora_certa": False},
    "Uma pagina qualquer, sem hora nenhuma escrita.",
)
checa(sem_hora["hora_certa"] is False,
      "sem declaracao na pagina, o guia segue dizendo que nao sabe a hora")

# ---------------------------------------------------------------------------
print("\n== O que se perde ao passar do prazo (18/08/2026) ==")

perda = consequencia_do_prazo(TEXTO_Q3, 23)
checa(perda is not None, "a pagina diz o que acontece com quem passa do dia 23")
checa(perda and "trabalho em grupo fica com quem" in perda,
      "e a frase que importa entra, mesmo estando duas sentencas adiante")
checa(perda and perda.startswith("Quem conclui"),
      "o trecho comeca na frase do gatilho, nao no meio dela")
checa(consequencia_do_prazo(TEXTO_Q3, 29) is None,
      "prazo sem consequencia escrita nao ganha explicacao inventada")
checa(consequencia_do_prazo("Entregue ate o dia 23 de agosto.", 23) is None,
      "frase que so repete a data nao vira aviso de perda")

# ---------------------------------------------------------------------------
print("\n== Data sem gatilho nenhum não vira prazo firme (19/08/2026) ==")

# Texto real do aviso do LET110 de 17/08/2026, publicado em dois fóruns. A
# frase do dia 25 fala da live da semana seguinte, e o guia publicou
# "Conclua: Semana 5 · conclusão, vence 25/08" com etiqueta de aviso oficial,
# contra os itens da mesma semana que o cronograma oficial dá para 26/08.
AVISO_LIVE_LET110 = (
    "Prezados/as,\n"
    "Conforme comentei anteriormente, nesta semana 5, nossa live ocorrerá na "
    "quinta-feira (20/08) e não na terça-feira (18/08).\n"
    "Na semana que vem, a de nº 6, voltamos pra terça-feira (25/08).\n"
    "Portanto, a live desta semana será na quinta-feira (20/08), às 20h.\n"
    "Tragam as dúvidas de vocês."
)
pz_let = C.extrair_prazos(
    AVISO_LIVE_LET110, datetime(2026, 8, 17, 20, tzinfo=BR)
)
dia_25 = [p for p in pz_let if p["quando"][:10] == "2026-08-25"]
checa(bool(dia_25) and all(p["confianca"] == "baixa" for p in dia_25),
      "data sem gatilho de prazo nem de abertura nasce duvidosa, nao firme")
checa(C.casar_prazos("Semana 5", pz_let) == [],
      "e por isso nao vira conclusao da Semana 5 na fila")
checa(any(p["quando"] == "2026-08-20T20:00:00-03:00"
          and p["tipo"] == "compromisso" for p in pz_let),
      "a live com hora escrita continua sendo lida")
checa(all(p["quando"][:10] != "2026-08-18" for p in pz_let),
      "e a data que o aviso desmarca continua fora")

# A correcao nao pode calar prazo que a frase declara: a confianca alta pede
# escopo forte E palpite seguro, e quem tem gatilho na frase segue seguro.
pz_firme = C.extrair_prazos("Semana 5: a entrega vai até 30/07.", REF)
checa(bool(pz_firme) and pz_firme[0]["confianca"] == "alta",
      "frase com escopo e 'ate' segue publicando prazo firme")
checa([p["quando"][:10] for p in C.casar_prazos("Semana 5", pz_firme)]
      == ["2026-07-30"], "e continua casando com a secao da semana")

# ---------------------------------------------------------------------------
print("\n== A pagina promete mais lives do que publica (19/08/2026) ==")

# Texto real da "Q3 - Lembrete de datas e live": a pagina escreve 7 e lista
# seis, todas em 18, 19 e 20/08. Participar ao vivo de uma delas e um dos dez
# pontos da quinzena, entao mostrar seis como se fossem todas transforma
# leitura parcial em oferta completa.
checa(lives_anunciadas(
    "A quinzena oferece 7 lives, em dias e horários diferentes.") == 7,
    "o numero escrito em algarismo e lido")
checa(lives_anunciadas(
    "A quinzena oferece sete lives, em dias diferentes.") == 7,
    "e o numero escrito por extenso tambem")
checa(lives_anunciadas("Participe da live da quinzena.") is None,
      "pagina que nao promete numero nenhum nao gera alerta")

_pz_live = {"quando": "2026-08-19T18:00:00-03:00", "tipo": "compromisso"}
_item = {"label": "Q3 - Lembrete de datas e live", "url": "https://ava/p=1"}
com_falta = como_aviso(_item, [_pz_live] * 6, "A quinzena oferece 7 lives.")
checa(com_falta.get("lives_anunciadas") == 7
      and com_falta.get("lives_lidas") == 6,
      "sete anunciadas e seis lidas viram alerta no cartao")
completo = como_aviso(_item, [_pz_live] * 7, "A quinzena oferece 7 lives.")
checa("lives_anunciadas" not in completo,
      "quando o guia acha todas, nao ha o que avisar")
sobrando = como_aviso(_item, [_pz_live] * 8, "A quinzena oferece 7 lives.")
checa("lives_anunciadas" not in sobrando,
      "achar mais que o anunciado nao e falta e nao vira alerta")

print("\n" + "=" * 62)
if falhas:
    print(f"{len(falhas)} FALHA(S):")
    for f in falhas:
        print("  - " + f)
    sys.exit(1)
print("Todos os testes passaram.")
