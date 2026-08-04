# -*- coding: utf-8 -*-
"""Contratos operacionais: silêncio, frescor, publicação e escrita."""
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

import coletar as C  # noqa: E402
import enviar_email as E  # noqa: E402
import render as R  # noqa: E402

falhas = 0


def checa(condicao, nome):
    global falhas
    if condicao:
        print(f"  ok     | {nome}")
    else:
        falhas += 1
        print(f"  FALHOU | {nome}")


def curso(avisos=0, cronograma=False, prazo=False):
    return {
        "id": 1, "code": "COM170", "modelo": "quinzenal",
        "avisos": [{"titulo": "x"}] * avisos,
        "cronograma": {"semanas": []} if cronograma else None,
        "sections": [{
            "id": "s1", "title": "Módulo 1", "fase": "regular", "locked": None,
            "items": [{
                "cmid": "1", "label": "Item", "type": "page",
                "status": "Pendente", "conta_nota": True, "aberto": True,
                "url": "#", "prazo": "2026-08-01T23:59:00-03:00" if prazo else None,
                "prazo_fonte": "teste" if prazo else None, "carencia": None,
            }],
        }],
    }


print("\n== Fontes: falha persistente não envenena a referência ==")
anterior = {
    "status": "ok", "checked_at": "2026-07-25T12:00:00+00:00",
    "snapshot_at": "2026-07-25T12:00:00+00:00",
    "publication_id": "bom", "courses": [curso(12, True, True)],
    "fontes": {
        "avisos": 12, "eventos_calendario": 3,
        "cronograma": 1, "itens_com_prazo": 1,
    },
}
zerado = {
    "courses": [curso()], "eventos": [], "notificacoes": [],
    "fontes_status": {},
}

with tempfile.TemporaryDirectory() as tmp:
    data_antigo, estado_antigo, coletar_antigo = C.DATA_PATH, C.ESTADO_PATH, C.coletar
    try:
        C.DATA_PATH = Path(tmp) / "data.json"
        C.ESTADO_PATH = Path(tmp) / "estado.json"
        C.gravar_json(C.DATA_PATH, anterior)
        C.gravar_json(C.ESTADO_PATH, {})
        C.coletar = lambda estado: (copy.deepcopy(zerado), "ok")
        with contextlib.redirect_stdout(io.StringIO()):
            rc1 = C.main()
            rc2 = C.main()
        final = json.loads(C.DATA_PATH.read_text(encoding="utf-8"))
        checa(rc1 == 2 and rc2 == 2, "duas perdas consecutivas falham fechado")
        checa(final["status"] == "coleta_incompleta", "a segunda pane não volta para ok")
        checa(final["fontes"]["avisos"] == 12, "baseline continua sendo a última leitura válida")
        checa(final["fontes_tentativa"]["avisos"] == 0, "tentativa falha tem telemetria separada")
        checa(final["snapshot_at"] == anterior["snapshot_at"], "pane não rejuvenesce o snapshot")
        checa(final["attempted_at"] != anterior["snapshot_at"], "hora da tentativa fica registrada")
    finally:
        C.DATA_PATH, C.ESTADO_PATH, C.coletar = data_antigo, estado_antigo, coletar_antigo


print("\n== Fontes: cache e queda parcial ==")


class ForumOffline:
    def goto(self, *args, **kwargs):
        raise TimeoutError("fórum fora")

    def wait_for_timeout(self, *args, **kwargs):
        pass


url = "https://ava.invalid/forum"
post = {
    "data": "2026-07-25T10:00:00-03:00", "texto": "Entrega até 26/07",
    "titulo": "Aviso", "url": url, "prazos": [],
}
diag = {}
avisos, _ = C.varrer_foruns(
    ForumOffline(), [{"url": url, "label": "Avisos"}],
    {url: {"ultimo": post["data"], "posts": [post]}},
    60, date(2026, 7, 25), diag)
com_cache = {
    "courses": [curso(1, True, True)], "eventos": [1],
    "fontes_status": {"foruns": diag},
}
base_cache = {"courses": [curso(1, True, True)], "fontes": C.resumo_fontes(com_cache)}
ok_cache, _ = C.validar_cobertura(com_cache, base_cache)
checa(len(avisos) == 1, "cache preserva o aviso conhecido")
checa(diag["status"] == "falhou", "telemetria distingue cache de leitura ao vivo")
checa(not ok_cache, "fórum offline com cache não passa como saudável")

parcial = {"courses": [curso(1, True, True)], "eventos": [1], "fontes_status": {}}
base_grande = {
    "courses": [curso(60, True, True)],
    "fontes": {
        "avisos": 60, "eventos_calendario": 3,
        "cronograma": 3, "itens_com_prazo": 15,
    },
}
ok_parcial, probs_parcial = C.validar_cobertura(parcial, base_grande)
checa(not ok_parcial, "queda 60→1 não passa só porque ficou acima de zero")
checa(any("menos da metade" in p for p in probs_parcial), "queda parcial explica o limiar")


print("\n== SMTP obrigatório em CI ==")
chaves = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "EMAIL_PARA", "EMAIL_OPCIONAL")
ambiente = {k: os.environ.get(k) for k in chaves}
smtp_antigo, data_email_antigo = E.smtplib.SMTP, E.DATA_PATH
try:
    for k in chaves:
        os.environ.pop(k, None)
    with contextlib.redirect_stdout(io.StringIO()):
        rc_sem_config = E.main()
    checa(rc_sem_config == 2, "Secret ausente é falha, não sucesso")

    os.environ["EMAIL_OPCIONAL"] = "1"
    with contextlib.redirect_stdout(io.StringIO()):
        rc_opcional = E.main()
    checa(rc_opcional == 0, "execução local pode dispensar e-mail explicitamente")

    with tempfile.TemporaryDirectory() as tmp:
        E.DATA_PATH = Path(tmp) / "data.json"
        os.environ.update({
            "SMTP_HOST": "smtp.invalid", "SMTP_PORT": "587",
            "SMTP_USER": "x", "SMTP_PASS": "x", "EMAIL_PARA": "x@example.invalid",
        })
        os.environ.pop("EMAIL_OPCIONAL", None)
        with contextlib.redirect_stdout(io.StringIO()):
            rc_sem_dados = E.main()
        checa(rc_sem_dados == 2, "data.json ausente também é falha no CI")

        E.DATA_PATH.write_text(
            json.dumps({"acoes": [], "status": "ok"}), encoding="utf-8")

        class SmtpFora:
            def __init__(self, *args, **kwargs):
                raise OSError("smtp fora")

        E.smtplib.SMTP = SmtpFora
        with contextlib.redirect_stdout(io.StringIO()):
            rc_smtp = E.main()
        checa(rc_smtp == 1, "pane de transporte continua derrubando o passo")
finally:
    E.smtplib.SMTP, E.DATA_PATH = smtp_antigo, data_email_antigo
    for chave, valor in ambiente.items():
        if valor is None:
            os.environ.pop(chave, None)
        else:
            os.environ[chave] = valor


print("\n== Frescor e recado condicionado ==")
velho = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
agora = datetime.now(timezone.utc).isoformat()
_, banner = R.frescor({"snapshot_at": velho, "attempted_at": agora})
checa(bool(banner), "frescor usa o snapshot, não a tentativa mais recente")
checa("Date.now()" in R.TEMPLATE and "setInterval" in R.TEMPLATE,
      "idade é recalculada enquanto a página está aberta")
fontes_html = R.render_fontes_status({
    "status": "ok", "fontes_status": {
        "disciplinas": {
            "status": "live", "last_live_at": agora, "quantidade_atual": 4,
        },
        "foruns": {
            "status": "live", "last_live_at": agora, "quantidade_atual": 60,
            "foruns": 14, "truncado": True,
        },
    },
})
checa("Li as fontes do AVA agora" in fontes_html and "Li tudo" not in fontes_html,
      "mensagem saudável não promete ter guardado tudo")
checa("60 publicações selecionadas em 14 fóruns" in fontes_html,
      "quantidade dos fóruns explica o que foi contado")

parcial_html = R.render_fontes_status({
    "status": "ok", "fontes_status": {
        "itens": {
            "status": "parcial", "last_live_at": agora,
            "quantidade_atual": 16,
        },
    },
})
checa("Leitura parcial" in parcial_html and "li agora" in parcial_html
      and "houve falha" not in parcial_html,
      "leitura parcial não é apresentada como falha ou cache")

falha_html = R.render_fontes_status({
    "status": "coleta_degradada", "fontes_status": {
        "foruns": {
            "status": "falhou", "last_live_at": agora,
            "quantidade_atual": 60, "foruns": 14, "from_cache": True,
        },
    },
})
checa("houve falha ao atualizar: fóruns" in falha_html
      and "Mantive o dado anterior" in falha_html,
      "falha com cache informa que preservou a última leitura boa")

recado_antigo = R.RECADO_PATH
with tempfile.TemporaryDirectory() as tmp:
    try:
        R.RECADO_PATH = Path(tmp) / "revisao.json"
        R.RECADO_PATH.write_text(json.dumps({
            "text": "Faça o item antigo.", "written_at": agora,
            "requires_pending_cmids": ["10"],
        }), encoding="utf-8")
        dados = {
            "courses": [{"sections": [{"items": [
                {"cmid": "10", "status": "Concluído"},
            ]}]}],
        }
        html = R.render_recado(dados)
        checa("arquivado automaticamente" in html, "recado superado é recolhido")
        checa("Faça o item antigo" not in html, "orientação vencida não continua em destaque")
    finally:
        R.RECADO_PATH = recado_antigo


print("\n== Abas (render_tabs) ==")
dados_min = {"acoes": [], "courses": [], "eventos": [], "notificacoes": [], "mensagens": []}
tabs_html = R.render_tabs(dados_min)
checa('data-tab="agora"' in tabs_html, "aba 'O que fazer agora' sempre existe")
checa('data-tab="novidades"' in tabs_html, "aba 'Chegou novo' sempre existe")
checa('data-tab="mapa"' in tabs_html, "aba 'Mapa das disciplinas' sempre existe")
checa('data-tab="confirmar"' not in tabs_html, "aba 'Confirme' some quando não há nada a confirmar")
checa('data-tab="higiene"' not in tabs_html, "aba 'Higiene' some quando vazia")
checa('data-tab="encerrados"' not in tabs_html, "aba 'Já encerrou' some quando vazia")
checa('id="panel-agora"' in tabs_html and "hidden" in tabs_html,
      "painéis nascem escondidos; o JS decide qual mostrar")

dados_cheio = dict(dados_min)
dados_cheio["higiene"] = [{"o_que": "X", "curso": "COM170"}] * 3
tabs_cheio = R.render_tabs(dados_cheio)
checa('data-tab="higiene"' in tabs_cheio, "aba 'Higiene' aparece quando há itens")
checa('<span class="tab-badge">3</span>' in tabs_cheio,
      "contagem na aba bate com o número de itens")


print("\n== Escrita e identidade ==")
with tempfile.TemporaryDirectory() as tmp:
    alvo = Path(tmp) / "data.json"
    alvo.write_text('{"old": 1}', encoding="utf-8")
    replace_antigo = C.os.replace

    def interromper(*args, **kwargs):
        raise RuntimeError("queda antes do replace")

    C.os.replace = interromper
    try:
        try:
            C.gravar_json(alvo, {"new": 2})
        except RuntimeError:
            pass
    finally:
        C.os.replace = replace_antigo
    checa(json.loads(alvo.read_text(encoding="utf-8")) == {"old": 1},
          "interrupção preserva o JSON anterior")
    checa(not list(Path(tmp).glob("*.tmp")), "temporário é removido após falha")

    html = Path(tmp) / "index.html"
    R.gravar_texto_atomico(html, "<p>ok</p>")
    checa(html.read_text(encoding="utf-8") == "<p>ok</p>", "HTML também usa substituição atômica")

with tempfile.TemporaryDirectory() as tmp:
    data_antigo, estado_antigo = C.DATA_PATH, C.ESTADO_PATH
    replace_antigo = C.os.replace
    try:
        C.DATA_PATH, C.ESTADO_PATH = Path(tmp) / "data.json", Path(tmp) / "estado.json"
        C.DATA_PATH.write_text('{"versao": "antiga"}', encoding="utf-8")
        C.ESTADO_PATH.write_text('{"versao": "antiga"}', encoding="utf-8")
        chamadas = 0

        def cair_antes_do_commit(origem, destino):
            global chamadas
            chamadas += 1
            if chamadas == 2:
                raise RuntimeError("queda antes de publicar data.json")
            return replace_antigo(origem, destino)

        C.os.replace = cair_antes_do_commit
        try:
            C.gravar_snapshot({"versao": "nova"}, {"versao": "nova"})
        except RuntimeError:
            pass
        checa(json.loads(C.DATA_PATH.read_text(encoding="utf-8"))["versao"] == "antiga",
              "data.json é o marcador final e fica antigo se o snapshot não terminou")
        checa(not list(Path(tmp).glob("*.tmp")), "falha do snapshot limpa os dois temporários")
    finally:
        C.os.replace = replace_antigo
        C.DATA_PATH, C.ESTADO_PATH = data_antigo, estado_antigo

corrompido = None
with tempfile.TemporaryDirectory() as tmp:
    corrompido = Path(tmp) / "data.json"
    corrompido.write_text("{", encoding="utf-8")
    try:
        C.carregar(corrompido, None, critico=True)
        levantou = False
    except RuntimeError:
        levantou = True
checa(levantou, "data.json corrompido falha explicitamente")

ant = {"courses": [{"code": "X", "sections": [
    {"id": "a", "items": [{"label": "Mesmo", "cmid": None, "status": "Pendente"}]},
    {"id": "b", "items": [{"label": "Mesmo", "cmid": None, "status": "Concluído"}]},
]}]}
novo = {"courses": [{"code": "X", "sections": [
    {"id": "a", "items": [{"label": "Mesmo", "cmid": None, "status": "Concluído"}]},
    {"id": "b", "items": [{"label": "Mesmo", "cmid": None, "status": "Concluído"}]},
]}]}
checa(len(C.novidades(ant, novo)) == 1, "seção distingue itens sem cmid")
ant_tipo = {"courses": [{"code": "X", "sections": [
    {"id": "a", "items": [{"label": "Mesmo", "cmid": 1, "status": "Pendente"}]},
]}]}
novo_tipo = {"courses": [{"code": "X", "sections": [
    {"id": "a", "items": [{"label": "Mesmo", "cmid": "1", "status": "Concluído"}]},
]}]}
nov_tipo = C.novidades(ant_tipo, novo_tipo)
checa(len(nov_tipo) == 1 and nov_tipo[0]["kind"] == "concluido",
      "cmid numérico e textual têm a mesma identidade")


print("\n== Leitura do AVA: o que sumia do retrato (04/08/2026) ==")

# 1) Sub-seção colapsada tem o nome só num <a> em linha própria: o innerText
#    começa com "\n" e o título vinha vazio. Seção sem título era descartada,
#    e com ela os Módulos 6 e 7 — inclusive o Laboratório ainda pendente.
from fontes.disciplinas import JS_CURSO  # noqa: E402

checa("data-sectionname" in JS_CURSO,
      "título da seção vem do atributo do Moodle, não só do texto visível")
checa("filter(Boolean)" in JS_CURSO,
      "título com quebra de linha na frente não vira string vazia")

# 2) A API do Moodle só devolve atividade com pendência. Live marcada pelo
#    facilitador é evento de curso e nunca voltava por ali.
from fontes.calendario import unir  # noqa: E402

api = [{"nome": "Término de S3", "quando": "2026-08-16T23:59:00-03:00",
        "cmid": "1", "curso": "COM100-T001"}]
dom = [{"nome": "Término de S3", "quando": "2026-08-16T23:59:00-03:00",
        "cmid": "1", "curso": None},
       {"nome": "LIVE DE DÚVIDAS", "quando": "2026-08-10T20:00:00-03:00",
        "cmid": "9", "tipo": "course"}]
unidos = unir(api, dom)
checa(len(unidos) == 2, "evento repetido nas duas leituras não vira dois")
checa(any(e["nome"] == "LIVE DE DÚVIDAS" for e in unidos),
      "evento que só o DOM enxerga entra no retrato")
checa(next(e for e in unidos if e["cmid"] == "1")["curso"] == "COM100-T001",
      "o campo que só a API traz é preservado na união")

print("\n== Encontros: hora que passou, e um horário por encontro ==")

AGORA = datetime(2026, 8, 4, 17, 30, tzinfo=timezone(timedelta(hours=-3)))
HOJE_EV = AGORA.date()

urg, txt = C.urgencia_de("2026-08-04T14:00:00-03:00", HOJE_EV, True,
                         evento=True, agora=AGORA)
checa(urg == "vencido", "live das 14h não é cobrada às 17h30 do mesmo dia")
urg2, _ = C.urgencia_de("2026-08-04T20:00:00-03:00", HOJE_EV, True,
                        evento=True, agora=AGORA)
checa(urg2 == "hoje", "live das 20h continua na fila às 17h30")

def _live(quando, nome):
    return {"rotulo": nome, "quando": quando, "tipo": "compromisso",
            "hora_certa": True, "confianca": "alta", "frase": nome,
            "titulo_evento": nome, "escopo": None}

curso_lives = {
    "code": "COM170", "modelo": "quinzenal", "id": 18922,
    "avisos": [{"autor": "formador", "url": "https://ava/d=1",
                "autoridade": "institucional", "titulo": "Cronograma de Lives",
                "prazos": [_live("2026-08-05T11:00:00-03:00", "Cauê e participante"),
                           _live("2026-08-05T16:00:00-03:00", "Vittoria"),
                           _live("2026-08-06T10:00:00-03:00", "Lívia")]}],
    "sections": [],
}
acoes_lv, *_ = C.montar_acoes({"courses": [curso_lives]}, HOJE_EV, agora=AGORA)
compromissos = [a for a in acoes_lv if a["tipo"] == "compromisso"]
checa(len(compromissos) == 1,
      "seis horários do mesmo aviso viram um compromisso, não seis")
checa(len(compromissos[0].get("opcoes") or []) == 3,
      "os horários alternativos continuam visíveis no mesmo cartão")
checa(compromissos[0]["prazo"].startswith("2026-08-05T11:00"),
      "o horário que abre o cartão é o próximo a acontecer")

print("\n== Quinzena que já passou ==")

curso_q = {
    "code": "COM170", "modelo": "quinzenal", "id": 18922, "avisos": [],
    "sections": [
        {"id": "s1", "title": "Quinzena 1", "parent": None, "fase": "regular",
         "locked": None, "items": []},
        {"id": "s1a", "title": "Módulo 7", "parent": "s1", "fase": "regular",
         "locked": None, "items": [
             {"cmid": "1", "label": "M7 - Grupo: Ponto de encontro",
              "type": "forum", "status": None, "conta_nota": True,
              "aberto": True, "url": "#a", "prazo": None},
             {"cmid": "2", "label": "M7 - Revisão entre pares",
              "type": "workshop", "status": "Pendente", "conta_nota": True,
              "aberto": True, "enviado": True, "avaliacao_pendente": True,
              "url": "#b", "prazo": "2026-08-04T23:59:00-03:00",
              "prazo_fonte": "calendário do AVA"},
         ]},
        {"id": "s2", "title": "Quinzena 2", "parent": None, "fase": "regular",
         "locked": None, "items": [
             {"cmid": "3", "label": "Q2 M1 - Atividade", "type": "scorm",
              "status": "Pendente", "conta_nota": True, "aberto": True,
              "url": "#c", "prazo": None},
         ]},
    ],
}
ac_q, enc_q, hig_q, _ = C.montar_acoes({"courses": [curso_q]}, HOJE_EV,
                                       agora=AGORA)
na_fila = {a["o_que"] for a in ac_q} | {h["o_que"] for h in hig_q}
checa("M7 - Grupo: Ponto de encontro" not in na_fila,
      "sobra sem prazo da quinzena anterior sai da fila")
checa(any("Quinzena 1 encerrou" in e["motivo"] for e in enc_q),
      "e vai para 'já encerrou' dizendo o motivo")
checa("M7 - Revisão entre pares" in na_fila,
      "mas obrigação com data da quinzena anterior continua cobrada")
checa("Q2 M1 - Atividade" in na_fila,
      "a quinzena atual não é afetada")

print("\n== Rede de segurança: prazo do calendário sempre vira tarefa ==")

# Reproduz a falha de 04/08/2026 na forma mais crua: a seção inteira sumiu da
# leitura (título vazio, seção descartada), então a atividade com prazo pra
# hoje não existe em courses[]. O calendário sabia. Tem que aparecer assim
# mesmo — é o que separa "o robô errou" de "o Josemar perdeu o prazo".
sem_secao_alguma = {
    "courses": [{"code": "COM170", "modelo": "quinzenal", "id": 18922,
                 "avisos": [], "sections": []}],
    "eventos": [{
        "nome": "M7 - Revisão entre pares (Portfólio em grupo) - prazo limite "
                "para avaliação",
        "atividade": "M7 - Revisão entre pares (Portfólio em grupo)",
        "quando": "2026-08-04T23:59:00-03:00", "curso_id": "18922",
        "cmid": "173857", "tipo": "closeassessment",
        "url": "https://ava.univesp.br/mod/workshop/view.php?id=173857",
    }],
}
ac_r, *_ = C.montar_acoes(sem_secao_alguma, HOJE_EV, agora=AGORA)
resgatadas = [a for a in ac_r if a.get("resgatado")]
checa(len(resgatadas) == 1 and resgatadas[0]["urgencia"] == "hoje",
      "atividade que sumiu do retrato volta pelo prazo do calendário")
checa(resgatadas and resgatadas[0]["verbo"] == "Avalie"
      and resgatadas[0]["url"].endswith("173857"),
      "e volta com o verbo certo e o link da atividade")

# Não pode virar eco: se o item foi lido normalmente, uma linha só.
com_item = json.loads(json.dumps(sem_secao_alguma))
com_item["courses"][0]["sections"] = [{
    "id": "s7", "title": "Módulo 7", "parent": None, "fase": "regular",
    "locked": None, "items": [{
        "cmid": "173857", "label": "M7 - Revisão entre pares (Portfólio em grupo)",
        "type": "workshop", "status": "Pendente", "conta_nota": True,
        "aberto": True, "enviado": True, "avaliacao_pendente": True,
        "url": "https://ava.univesp.br/mod/workshop/view.php?id=173857",
        "prazo": "2026-08-04T23:59:00-03:00",
        "prazo_fonte": "calendário do AVA"}],
}]
ac_i, *_ = C.montar_acoes(com_item, HOJE_EV, agora=AGORA)
checa(len([a for a in ac_i if "173857" in (a.get("url") or "")]) == 1,
      "com o item lido normalmente, continua sendo uma linha só")

# Atividade concluída não é ressuscitada pelo evento de encerramento.
feito = json.loads(json.dumps(sem_secao_alguma))
feito["courses"][0]["sections"] = [{
    "id": "s7", "title": "Módulo 7", "parent": None, "fase": "regular",
    "locked": None, "items": [{
        "cmid": "173857", "label": "M7", "type": "workshop",
        "status": "Concluído", "conta_nota": True, "url": "#", "prazo": None}],
}]
ac_f, *_ = C.montar_acoes(feito, HOJE_EV, agora=AGORA)
checa(not [a for a in ac_f if a.get("resgatado")],
      "o que já está concluído não volta pela rede de segurança")

# O M6 real: entregue e avaliado, sem selo "Concluído" do Moodle (o selo só
# fecha nas 5 fases). Sai da fila pelo estado do laboratório — e o evento
# "prazo limite para avaliação" não pode trazê-lo de volta.
lab_pronto = json.loads(json.dumps(sem_secao_alguma))
lab_pronto["eventos"][0]["cmid"] = "173854"
lab_pronto["courses"][0]["sections"] = [{
    "id": "s6", "title": "Módulo 6", "parent": None, "fase": "regular",
    "locked": None, "items": [{
        "cmid": "173854", "label": "M6", "type": "workshop",
        "status": "Pendente", "conta_nota": True, "aberto": True,
        "enviado": True, "avaliacao_pendente": False, "url": "#",
        "prazo": None}],
}]
ac_p, *_ = C.montar_acoes(lab_pronto, HOJE_EV, agora=AGORA)
checa(not [a for a in ac_p if a.get("resgatado")],
      "laboratório entregue e avaliado não é ressuscitado pelo calendário")

# Já o item que saiu por leitura duvidosa ("o AVA diz que não está aberta")
# precisa voltar: foi assim que o M7 sumiu no dia do prazo.
lido_fechado = json.loads(json.dumps(sem_secao_alguma))
lido_fechado["courses"][0]["sections"] = [{
    "id": "s7", "title": "Módulo 7", "parent": None, "fase": "regular",
    "locked": None, "items": [{
        "cmid": "173857", "label": "M7", "type": "workshop",
        "status": "Pendente", "conta_nota": True, "aberto": False,
        "motivo_fechado": "o AVA diz que não está aberta", "url": "#",
        "prazo": None}],
}]
ac_lf, *_ = C.montar_acoes(lido_fechado, HOJE_EV, agora=AGORA)
checa(len([a for a in ac_lf if a.get("resgatado")]) == 1,
      "item lido como fechado volta quando o calendário mostra prazo aberto")

print("\n== Selo 'Concluído' não é prova de entrega (COM100 S2, 04/08/2026) ==")

from fontes import boletim as B  # noqa: E402
from fontes import itens as I  # noqa: E402


class PaginaComTexto:
    def __init__(self, texto):
        self._t = texto

    def goto(self, *a, **k):
        pass

    def wait_for_timeout(self, *a, **k):
        pass

    def locator(self, _):
        return self

    def inner_text(self):
        return self._t


# A página do questionário é a prova direta. Texto real lido do AVA.
sem_tentativa = ("S2 - Atividade Avaliativa\nTentativa do questionário\n"
                 "Tentativas permitidas: 3\nMétodo de avaliação: Nota mais alta")
com_tentativa = ("S1 - Atividade Avaliativa\nTentativas permitidas: 3\n"
                 "Suas tentativas\nTentativa 1\nSituação\tFinalizada\n"
                 "Iniciado\tterça-feira, 28 jul. 2026, 20:58\nVoltar ao curso")
checa(I.entrega_feita(PaginaComTexto(sem_tentativa), "#", "quiz") is False,
      "questionário sem 'Suas tentativas' é entrega não feita")
checa(I.entrega_feita(PaginaComTexto(com_tentativa), "#", "quiz") is True,
      "'Situação Finalizada' separada por tabulação é reconhecida como entrega")
checa(I.entrega_feita(PaginaComTexto("Você precisa fazer login"), "#", "quiz")
      is None,
      "página de login não afirma nem nega a entrega")
checa(I.entrega_feita(PaginaComTexto(com_tentativa), "#", "page") is None,
      "tipo que não tem entrega não é interrogado")

checa(C.entrega_provada({"type": "quiz", "tem_nota": True}) is True,
      "nota lançada é prova de entrega")
checa(C.entrega_provada({"type": "scorm", "tem_nota": True, "nota": 0.0})
      is True,
      "nota zero também é prova: houve entrega, o desempenho é outra conversa")
checa(C.entrega_provada({"type": "quiz", "tem_nota": False}) is None,
      "sem nota e sem conferência, a resposta é 'não sei'")
checa(C.entrega_provada(
        {"type": "assign", "tem_nota": False, "feedback": "Parabéns pela entrega!"})
      is True,
      "devolutiva escrita do facilitador também prova que houve entrega")
checa(C.entrega_provada(
        {"type": "quiz", "tem_nota": False, "entrega_confirmada": False})
      is False,
      "conferência negativa é a única coisa que afirma que não entregou")

# Boletim: rótulo vem com o tipo na frente e a célula traz o menu "Ações".
checa(B._limpar_nota("10,00 Ações") == "10,00", "menu da célula sai da nota")
checa(B._numero("7,50") == 7.5 and B._numero("-") is None,
      "vírgula decimal vira número e traço vira ausência de nota")
checa(B._rotulo_limpo("QUESTIONÁRIO S2 - Atividade Avaliativa")
      == "S2 - Atividade Avaliativa",
      "tipo sai do rótulo do boletim")

def curso_com_quiz(**item):
    base = {"cmid": "160791", "label": "S2 - Atividade Avaliativa",
            "type": "quiz", "status": "Concluído", "conta_nota": True,
            "aberto": True, "url": "#s2",
            "prazo": "2026-08-09T23:59:00-03:00",
            "prazo_fonte": "calendário do AVA"}
    base.update(item)
    return {"courses": [{"code": "COM100", "modelo": "regular", "id": 18870,
            "avisos": [], "sections": [{"id": "s2", "title": "Semana 2",
            "fase": "regular", "locked": None, "items": [base]}]}],
            "eventos": []}


concluido_sem_entrega = C.montar_acoes(
    curso_com_quiz(tem_nota=False, entrega_confirmada=False),
    HOJE_EV, agora=AGORA)[0]
checa(len(concluido_sem_entrega) == 1
      and concluido_sem_entrega[0].get("entrega_nao_confirmada"),
      "'Concluído' sem entrega registrada continua na fila, marcado")
checa(concluido_sem_entrega and concluido_sem_entrega[0]["urgencia"] == "semana",
      "e mantém o prazo real do calendário")

concluido_com_nota = C.montar_acoes(
    curso_com_quiz(tem_nota=True, nota=10.0), HOJE_EV, agora=AGORA)[0]
checa(not concluido_com_nota, "com nota lançada, sai da fila como antes")

# O caso do SOC100: boletim da disciplina veio sem nenhuma linha. Isso é
# ausência de informação, não prova de que nada foi entregue.
concluido_sem_boletim = C.montar_acoes(
    curso_com_quiz(tem_nota=False), HOJE_EV, agora=AGORA)[0]
checa(not concluido_sem_boletim,
      "boletim indisponível não vira acusação de entrega faltando")

# O boletim não pode congelar o site. Em 04/08/2026 o relatório de uma
# disciplina não renderizou e a rodada inteira virou "coleta_incompleta",
# segurando um retrato bom por causa de uma fonte que só acrescenta prova.
import saude as SA  # noqa: E402

base_ok = {
    "courses": [{"id": 1, "code": "COM100",
                 "sections": [{"items": [{"cmid": "1", "label": "x",
                                          "prazo": "2026-08-09T23:59:00-03:00"}]}],
                 "avisos": [{"titulo": "a"}], "cronograma": {"semanas": []}}],
    "eventos": [{"nome": "e"}],
}
com_boletim_ruim = copy.deepcopy(base_ok)
com_boletim_ruim["fontes_status"] = {
    "disciplinas": {"status": "live"},
    "boletim": {"status": "degradado", "falhas": 1},
}
ok_b, probs_b = SA.validar_cobertura(com_boletim_ruim, None)
checa(ok_b, "boletim degradado não derruba a coleta")

com_calendario_ruim = copy.deepcopy(base_ok)
com_calendario_ruim["fontes_status"] = {"calendario": {"status": "degradado"}}
ok_c, _ = SA.validar_cobertura(com_calendario_ruim, None)
checa(not ok_c, "fonte de prazo degradada continua derrubando")

print("\n== Workflow de publicação ==")
workflow = (ROOT / ".github" / "workflows" / "guia-diario.yml").read_text(encoding="utf-8")
checa('- cron: "0 11 * * *"' in workflow, "agenda matinal tem gatilho próprio")
checa("github.event.schedule" in workflow and "date -u +%H" not in workflow,
      "atraso do runner não muda a decisão de enviar")
pos_publicar = workflow.index("- name: Publicar mudanças")
pos_confirmar = workflow.index("Pages confirmou o artefato")
pos_email = workflow.index("- name: Enviar resumo por e-mail")
checa(pos_publicar < pos_confirmar < pos_email,
      "e-mail só vem depois da confirmação pública do artefato")
checa("publication_id" in workflow, "deploy é conferido pelo ID do artefato servido")


print("\n" + "=" * 66)
if falhas:
    print(f"{falhas} teste(s) operacional(is) falharam.")
    raise SystemExit(1)
print("Todos os testes operacionais passaram.")
