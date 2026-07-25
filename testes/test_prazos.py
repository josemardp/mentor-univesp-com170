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
    ok = any(d.strftime("%d/%m") == dia for d, _, _ in achados)
    checa(ok, f"lê data em {texto!r}")
    if ok:
        certa = [h for d, _, h in achados if d.strftime("%d/%m") == dia][0]
        checa(certa == tem_hora,
              f"hora_certa={tem_hora} em {texto!r} (não inventa horário)")

# virada de ano: aviso de dezembro falando em janeiro
ref_dez = datetime(2026, 12, 20, 10, 0, tzinfo=BR)
achados = C.achar_datas("entregar até 10 de janeiro", ref_dez)
checa(any(d.year == 2027 for d, _, _ in achados),
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
acoes, encerrados = C.montar_acoes(dados, HOJE)

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
print("\n== Falhar fechado ==")

ok, probs = C.validar_cobertura({"courses": []}, {"courses": [{"code": "X"}]})
checa(not ok, "coleta sem nenhuma disciplina é recusada")
checa(any("disciplina" in p for p in probs), "e explica o motivo")

anterior = {"courses": [{"code": "A"}, {"code": "B"}, {"code": "C"}, {"code": "D"}]}
ok, _ = C.validar_cobertura({"courses": [{"code": "A", "sections": [
    {"items": [{"label": "x"}]}]}]}, anterior)
checa(not ok, "queda de 4 para 1 disciplina é recusada")

bom = {"courses": [{"code": "A", "sections": [{"items": [{"label": "x"}]}]},
                   {"code": "B", "sections": [{"items": [{"label": "y"}]}]}]}
ok, probs = C.validar_cobertura(bom, {"courses": [{"code": "A"}, {"code": "B"}]})
checa(ok, "coleta saudável passa")

ok, probs = C.validar_cobertura(
    {"courses": [{"code": "A", "sections": []}]}, None)
checa(not ok, "disciplina sem seção nenhuma é recusada")

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
print("\n" + "=" * 62)
if falhas:
    print(f"{len(falhas)} FALHA(S):")
    for f in falhas:
        print("  - " + f)
    sys.exit(1)
print("Todos os testes passaram.")
