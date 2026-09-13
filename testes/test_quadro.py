# -*- coding: utf-8 -*-
"""
Quadro das matérias e a leitura da página do questionário, pedidos por
Josemar em 25/08/2026.

O que este teste protege, em ordem de importância:

1. **Célula sem informação nunca vira acusação.** O quadro tem cara de
   tabela, e tabela é lida como verdade. "não sei" precisa continuar
   aparecendo onde o guia não leu, em vez de virar "você não fez".
2. **A nota do SOC100 existe.** O boletim daquela disciplina abre sem nenhuma
   linha no AVA (conferido em 25/08/2026), e a nota só está na página do
   questionário. Sem esta leitura, a disciplina inteira fica vazia no quadro.
3. **O boletim continua mandando onde ele responde.** A nota da página é
   fonte secundária, nunca substituta.
4. **Semana e quinzena não se misturam.** A COM170 tem "Semana 1" a
   "Semana 4" dentro da ambientação encerrada, e elas não podem entrar no
   quadro junto com as quinzenas.

Rodar:  python testes/test_quadro.py
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

from dominio import quadro as Q  # noqa: E402
from dominio.datas import sem_acento  # noqa: E402
from fontes import itens as I  # noqa: E402
from fontes import questionario  # noqa: E402

falhas = []


def checa(cond, msg):
    print(("  ok    " if cond else "  FALHA") + " | " + msg)
    if not cond:
        falhas.append(msg)


BR = timezone(timedelta(hours=-3))
AGORA = datetime(2026, 8, 25, 11, 0, tzinfo=BR)
ONTEM = "2026-08-24T23:59:00-03:00"
DEPOIS = "2026-08-30T23:59:00-03:00"


def normalizar(bruto):
    """Mesma normalização que ``itens._texto_da_atividade`` faz na página."""
    return " ".join(sem_acento(bruto).split())


# ---------------------------------------------------------------------------
print("\n== página do questionário: texto real do AVA em 25/08/2026 ==")

# S4 do SOC100, respondida. Copiado da página, não inventado.
FEITO = normalizar(
    "Tentativas permitidas: 3 Método de avaliação: Nota mais alta "
    "A sua nota final neste questionário é 10,00/10,00. Suas tentativas "
    "Tentativa 1 Resumo da tentativa 1 Situação Finalizada Iniciado "
    "sexta-feira, 14 ago. 2026, 18:45 Nota 10,00 de um máximo de 10,00(100%)"
)
# S5 do SOC100, ainda não respondida.
INTOCADO = normalizar(
    "caso a atividade já tenha sido iniciada, mas não seja enviada dentro do "
    "prazo, o AVA realizará o envio automaticamente após o vencimento. "
    "Tentativa do questionário Tentativas permitidas: 3 "
    "Método de avaliação: Nota mais alta"
)

lido = questionario.resumo_do_texto(FEITO)
checa(lido["nota_txt"] == "10,00", "le a nota final do questionario")
checa(lido["tentativas_feitas"] == 1, "conta 1 tentativa usada")
checa(lido["tentativas_permitidas"] == 3, "le as 3 tentativas permitidas")
checa(lido["metodo"] == "nota mais alta", "le o metodo de avaliacao")

zerado = questionario.resumo_do_texto(INTOCADO)
checa(zerado["tentativas_feitas"] == 0, "sem tentativa nenhuma responde 0")
checa(zerado["nota"] is None,
      "e a nota fica None, nunca zero: nao tentou nao e tirou zero")
checa(questionario.resumo_do_texto("pagina de aviso qualquer") is None,
      "pagina que nao e questionario responde None")
checa(questionario.resumo_do_texto("") is None, "texto vazio responde None")

# O enunciado do questionário contém a frase "você verá um resumo da sua
# tentativa", que quase virou "tem 1 tentativa feita".
checa(
    questionario.resumo_do_texto(
        normalizar(
            "clique em finalizar tentativa; você verá um resumo da sua "
            "tentativa com o status de cada questão. Tentativa do "
            "questionário Tentativas permitidas: 3"
        )
    )["tentativas_feitas"] == 0,
    "o enunciado falando em 'resumo da sua tentativa' nao conta como "
    "tentativa feita",
)


# ---------------------------------------------------------------------------
print("\n== uma leitura só responde aberto, entrega e nota ==")


class Pagina:
    def __init__(self, texto):
        self.texto = texto

    def goto(self, *a, **k):
        pass

    def wait_for_timeout(self, *a):
        pass

    def locator(self, _):
        pagina = self

        class Alvo:
            def inner_text(self):
                return pagina.texto

        return Alvo()


class PaginaMorta(Pagina):
    def goto(self, *a, **k):
        from playwright.sync_api import Error as PlaywrightError

        raise PlaywrightError("net::ERR_CONNECTION_RESET")


estado = I.estado_quiz(Pagina(FEITO), "https://ava/q")
checa(estado["entrega_confirmada"] is True, "estado_quiz confirma a entrega")
checa(estado["quiz"]["nota"] == 10.0, "e traz a nota junto, sem visita extra")

morto = I.estado_quiz(PaginaMorta(""), "https://ava/q")
checa(
    morto == {"aberto": None, "entrega_confirmada": None, "quiz": None},
    "leitura que falhou responde 'nao sei' em tudo, sem sumir com campo",
)


# ---------------------------------------------------------------------------
print("\n== quadro regular: semana, prazo e nota ==")


def curso_regular(**ajustes):
    avaliativa = {
        "cmid": "1", "type": "quiz", "label": "S1 - Atividade Avaliativa",
        "url": "https://ava/q", "conta_nota": True,
        "prazo": "2026-08-19T23:59:00-03:00", "carencia": ONTEM,
    }
    avaliativa.update(ajustes)
    return {
        "code": "SOC100", "id": "18880", "modelo": "regular",
        "boletim": {"status": "vazio_confirmado"},
        "sections": [
            {
                "id": "s1", "parent": None, "title": "Semana 1",
                "items": [
                    avaliativa,
                    {"cmid": "2", "type": "forum",
                     "label": "S1 - Fórum temático: ética", "postei": True},
                    {"cmid": "3", "type": "forum",
                     "label": "S1 - Fórum de dúvidas gerais", "postei": False},
                ],
            },
            {"id": "s2", "parent": None, "title": "Semana 2", "items": []},
        ],
    }


def celulas(curso, agora=AGORA):
    pronto = Q.quadro_do_curso({"eventos": []}, curso, agora)
    return pronto, {c["chave"]: c for c in pronto["linhas"][0]["celulas"]}

pronto, cel = celulas(curso_regular(tem_nota=True, nota_txt="10,00", nota=10.0))
checa(pronto["colunas"][0] == "Semana", "disciplina regular abre por Semana")
checa(cel["avaliativa"]["estado"] == "ok"
      and cel["avaliativa"]["texto"] == "10,00",
      "nota lancada aparece na celula da avaliativa")
checa(cel["forum"]["texto"] == "postou",
      "o forum tematico e quem responde pela coluna Forum")
checa(pronto["linhas"][0]["prazos"][0]["quando"] == ONTEM,
      "a data do quadro e a carencia, que e quando o AVA fecha")
checa(pronto["linhas"][0]["prazos"][0]["alvo"] == "2026-08-19T23:59:00-03:00",
      "e o vencimento do cronograma fica junto como alvo")
checa(pronto["linhas"][1]["situacao"] == "nao_aberta",
      "semana sem nenhum item e 'ainda nao aberta'")
checa(pronto["linhas"][0]["situacao"] == "fechada",
      "semana com prazo vencido e 'fechada'")

# O caso que motivou tudo: prazo vencido, sem nota, e o guia não sabe se ela
# foi entregue. Não pode virar "não fez".
_, cel = celulas(curso_regular())
checa(cel["avaliativa"]["estado"] == "nao_sei",
      "prazo vencido sem nota e sem prova de entrega vira 'nao sei'")

# Com a página do questionário dizendo que ele não tentou, aí sim é perda.
_, cel = celulas(curso_regular(
    quiz={"tentativas_feitas": 0, "tentativas_permitidas": 3},
    entrega_confirmada=False,
))
checa(cel["avaliativa"]["estado"] == "perdeu",
      "com a pagina afirmando zero tentativas, o vencido vira 'nao fez'")
checa(cel["avaliativa"]["detalhe"] is None,
      "em semana ja encerrada as tentativas somem: nao decidem mais nada e "
      "dobravam a altura do quadro no celular")

# Prazo em aberto: é tarefa, não perda, e aí as tentativas importam.
_, cel = celulas(curso_regular(
    carencia=DEPOIS, prazo=DEPOIS,
    quiz={"tentativas_feitas": 0, "tentativas_permitidas": 3},
))
checa(cel["avaliativa"]["estado"] == "falta",
      "com prazo em aberto a avaliativa por fazer e 'falta', nunca 'perdeu'")
checa(cel["avaliativa"]["detalhe"] == "0 de 3 tentativas",
      "e com o prazo correndo o quadro mostra quantas tentativas sobraram")

# Fórum sem leitura confiável dos posts dele.
_, cel = celulas(curso_regular(tem_nota=True, nota_txt="10,00"))
checa(cel["forum"]["estado"] == "ok", "forum postado fica verde")
curso = curso_regular(tem_nota=True)
curso["sections"][0]["items"][1]["postei"] = None
_, cel = celulas(curso)
checa(cel["forum"]["estado"] == "nao_sei",
      "sem leitura das mensagens dele, o forum vira 'nao sei', nao 'sem post'")


# ---------------------------------------------------------------------------
print("\n== a nota da pagina do questionario nao atropela o boletim ==")

pronto, cel = celulas(curso_regular(
    tem_nota=True, nota_txt="7,50", nota=7.5, nota_fonte="boletim",
    quiz={"nota": 10.0, "nota_txt": "10,00", "tentativas_permitidas": 3,
          "tentativas_feitas": 1},
))
checa(cel["avaliativa"]["texto"] == "7,50",
      "onde o boletim respondeu, e o boletim que aparece")

pronto, cel = celulas(curso_regular(
    tem_nota=True, nota_txt="10,00", nota=10.0,
    nota_fonte="página do questionário",
    quiz={"tentativas_permitidas": 3, "tentativas_feitas": 1},
))
checa(pronto["notas_do_questionario"] is True,
      "o quadro avisa que a nota nao veio do boletim, e avisa uma vez no "
      "cabecalho em vez de sete vezes dentro da tabela")
pronto, _ = celulas(curso_regular(
    tem_nota=True, nota_txt="10,00", nota=10.0, nota_fonte="boletim",
))
checa(pronto["notas_do_questionario"] is False,
      "e nao avisa nada quando quem respondeu foi o boletim")


# ---------------------------------------------------------------------------
print("\n== quadro quinzenal: dois laboratorios, dois prazos ==")

COM170 = {
    "code": "COM170", "id": "18922", "modelo": "quinzenal",
    "boletim": {"media": {"rotulo": "Média AVA", "nota": "0,51"}},
    "sections": [
        {"id": "q3", "parent": None, "title": "Quinzena 3", "items": []},
        {"id": "m6", "parent": "q3", "title": "Q3 Módulo 6", "items": [
            {"cmid": "228139", "type": "workshop",
             "label": "Q3 M6 - Revisão entre pares (Portfólio Individual)",
             "conta_nota": True, "enviado": False, "prazo": DEPOIS},
        ]},
        {"id": "m7", "parent": "q3", "title": "Q3 Módulo 7", "items": [
            {"cmid": "228142", "type": "workshop",
             "label": "Q3 M7 - Revisão entre pares (Trabalho em grupo)",
             "conta_nota": True, "enviado": False, "prazo": DEPOIS},
            {"cmid": "9", "type": "scorm", "label": "Q3 M4 - Mini-quiz",
             "tem_nota": True, "nota": 0.0, "nota_txt": "0,00"},
        ]},
        # A ambientação encerrada tem "Semana 1", e ela não pode virar linha.
        {"id": "aia", "parent": None, "fase": "AIA",
         "title": "AIA - Ambientação", "items": []},
        {"id": "aia1", "parent": "aia", "fase": "AIA", "title": "Semana 1",
         "items": [{"cmid": "8", "type": "quiz", "label": "S1"}]},
    ],
}
EVENTOS = {"eventos": [
    {"curso_id": "18922", "cmid": "228139", "tipo": "closesubmission",
     "quando": DEPOIS},
    {"curso_id": "18922", "cmid": "228139", "tipo": "closeassessment",
     "quando": "2026-09-01T23:59:00-03:00"},
]}

pronto = Q.quadro_do_curso(EVENTOS, COM170, AGORA)
linha = pronto["linhas"][0]
checa(pronto["colunas"][0] == "Quinzena", "disciplina quinzenal abre por Quinzena")
checa(len(pronto["linhas"]) == 1,
      "as Semanas da ambientacao encerrada nao viram linha do quadro")
checa(linha["rotulo"] == "Q3", "e a quinzena mantem o proprio numero")
checa([p["quando"] for p in linha["prazos"]]
      == [DEPOIS, "2026-09-01T23:59:00-03:00"],
      "entrega e avaliacao aparecem como dois prazos distintos")

por_chave = {c["chave"]: c for c in linha["celulas"]}
checa(por_chave["individual"]["estado"] == "falta",
      "portfolio individual sem envio, com prazo aberto, e 'falta'")
checa(por_chave["grupo"]["detalhe"] == "envia o representante",
      "a celula de grupo lembra que quem envia e o representante")
checa(pronto["zeros_interativos"] == 1,
      "conta as atividades interativas lancadas com zero, que puxam a media")

# Prazo do grupo vencido sem envio: não dá para acusar, o representante pode
# ter entregue pela equipe.
vencido = {**COM170, "sections": [dict(s) for s in COM170["sections"]]}
vencido["sections"][2] = {**vencido["sections"][2], "items": [
    {**COM170["sections"][2]["items"][0], "prazo": ONTEM},
]}
por_chave = {
    c["chave"]: c
    for c in Q.quadro_do_curso({"eventos": []}, vencido, AGORA)["linhas"][0][
        "celulas"
    ]
}
checa(por_chave["grupo"]["estado"] == "nao_sei",
      "grupo vencido sem envio nesta conta nao vira acusacao de perda")

# Zero em Laboratório é sempre um zero a contestar, nunca um verde.
zerado = {**COM170, "sections": [dict(s) for s in COM170["sections"]]}
zerado["sections"][1] = {**zerado["sections"][1], "items": [
    {**COM170["sections"][1]["items"][0],
     "enviado": True, "tem_nota": True, "nota": 0.0, "nota_txt": "0,00"},
]}
por_chave = {
    c["chave"]: c
    for c in Q.quadro_do_curso({"eventos": []}, zerado, AGORA)["linhas"][0][
        "celulas"
    ]
}
checa(por_chave["individual"]["estado"] == "atencao",
      "laboratorio entregue e zerado fica em atencao, nem verde nem vermelho")


# ---------------------------------------------------------------------------
print("\n== o quadro nao inventa disciplina ==")

checa(Q.quadro_do_curso({}, {"code": "X", "sections": []}) is None,
      "curso sem semana nem quinzena lida nao gera quadro")
checa(Q.montar({"courses": []}) == [], "sem disciplina, sem quadro")
checa(Q.montar({}) == [], "data.json sem 'courses' nao quebra")


print("\n" + "=" * 66)
if falhas:
    print(f"{len(falhas)} teste(s) falharam.")
    raise SystemExit(1)
print("Todos os testes do quadro passaram.")
