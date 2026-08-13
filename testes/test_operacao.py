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
ultimo_envio_antigo = E.ULTIMO_ENVIO_PATH
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
        # Sem isolar este arquivo também, um envio real de hoje (o robô já
        # escreve a data aqui após mandar o e-mail da manhã) faz o main()
        # devolver 0 antes de chegar no SMTP mockado: o teste passava só
        # em dias sem envio prévio, e falhava em qualquer segunda rodada.
        E.ULTIMO_ENVIO_PATH = Path(tmp) / ".ultimo_email_enviado"
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
    E.ULTIMO_ENVIO_PATH = ultimo_envio_antigo
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

# Identidade do item, provada pelo que o guia anuncia: rótulo igual em seção
# diferente é outra atividade; cmid igual escrito como número ou texto é a
# mesma. Errar aqui faz o guia anunciar como nova uma atividade de sempre.
ant = {"courses": [{"code": "X", "sections": [
    {"id": "a", "items": [{"label": "Mesmo", "cmid": None, "status": "Pendente"}]},
]}]}
novo = {"courses": [{"code": "X", "sections": [
    {"id": "a", "items": [{"label": "Mesmo", "cmid": None, "status": "Pendente"}]},
    {"id": "b", "items": [{"label": "Mesmo", "cmid": None, "status": "Pendente"}]},
]}]}
checa(len(C.novidades(ant, novo)) == 1, "seção distingue itens sem cmid")
ant_tipo = {"courses": [{"code": "X", "sections": [
    {"id": "a", "items": [{"label": "Mesmo", "cmid": 1, "status": "Pendente"}]},
]}]}
novo_tipo = {"courses": [{"code": "X", "sections": [
    {"id": "a", "items": [{"label": "Mesmo", "cmid": "1", "status": "Concluído"}]},
]}]}
checa(C.novidades(ant_tipo, novo_tipo) == [],
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
                 "name": "Disciplina", "sections": [
        {"title": "Semana 1", "fase": "regular", "locked": None, "items": [{"cmid": "1", "label": "x",
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

print("\n== Aba 'Como estou' ==")

dados_notas = {"courses": [
    {"code": "COM100", "boletim": {"media": {"rotulo": "Média AVA", "nota": "0,80"}},
     "name": "Disciplina", "sections": [
        {"title": "Semana 1", "fase": "regular", "locked": None, "items": [
        {"label": "S1 - Atividade Avaliativa", "type": "quiz", "conta_nota": True,
         "nota_txt": "10,00", "tem_nota": True, "url": "#1"},
        {"label": "S2 - Atividade Avaliativa", "type": "quiz", "conta_nota": True,
         "nota_txt": "-", "tem_nota": False, "url": "#2"},
     ]}]},
    {"code": "COM170", "boletim": {"media": {"rotulo": "Média AVA", "nota": "Erro"}},
     "name": "Disciplina", "sections": [
        {"title": "Semana 1", "fase": "regular", "locked": None, "items": [
        {"label": "S2 - Ferramenta para Envio", "type": "assign", "conta_nota": True,
         "nota_txt": "", "tem_nota": False, "feedback": "Parabéns pela entrega!",
         "url": "#3"},
     ]}]},
    {"code": "LET110", "name": "Leitura", "boletim": {}, "sections": [
        {"title": "Semana 3", "fase": "regular", "locked": None, "items": [
            {"label": "S3 - Início", "type": "page", "conta_nota": False},
        ]}]},
]}
html_notas = R.render_notas(dados_notas)
checa("10,00" in html_notas and "Média AVA" in html_notas,
      "mostra a nota da atividade e a média da disciplina")
checa("sem nota lançada" in html_notas,
      "atividade que vale nota e está em branco fica explícita")
html_sem_entrega = R.render_notas({"courses": [dict(
    dados_notas["courses"][0],
    sections=[{"title": "Semana 2", "fase": "regular", "locked": None, "items": [
        {"label": "S2 - Atividade Avaliativa", "type": "quiz", "conta_nota": True,
         "nota_txt": "-", "tem_nota": False, "entrega_confirmada": False,
         "url": "#2"}]}])]})
checa("não registrou nenhuma entrega" in html_sem_entrega,
      "quando a conferência provou que não houve entrega, a aba diz isso")
checa("Parabéns pela entrega!" in html_notas,
      "devolutiva escrita do facilitador aparece")
checa("não consegue calcular" in html_notas,
      "média com 'Erro' é apresentada como problema do AVA, não como nota")
checa("S3 - Início" not in html_notas,
      "item sem nota e sem devolutiva não polui a aba")
checa(R.render_notas({"courses": []}) == "",
      "sem boletim nenhum, a aba não existe")
checa('data-tab="notas"' in R.render_tabs(dados_notas),
      "a aba entra na barra quando há o que mostrar")
checa('data-tab="notas"' not in R.render_tabs({"courses": [], "acoes": []}),
      "e não entra quando não há")

print("\n== Composição da nota e a lacuna da prova (Etapa 6) ==")

from dominio.avaliacao import composicao_da_nota, lacuna_da_prova  # noqa: E402

# Texto REAL como o robô guarda, cortado em 400 caracteres e com o parágrafo
# seguinte colado. A primeira versão deste teste usava frases curtas e passava
# enquanto o dado de verdade falhava: a descrição do último percentual invadia
# a frase seguinte e ficava ambígua entre prova e AVA.
aviso_com100 = {"autor": "facilitador", "autoridade": "institucional",
    "url": "#c", "texto": "CRITÉRIOS DE AVALIAÇÃO \n\nEixos de COMPUTAÇÂO e de "
    "NEGÓCIOS E PRODUÇÃO \n\n40% - nota pela participação na fase de estudos "
    "(AVA) \xa0\n\n60% - nota pelo desempenho nas provas presenciais (nos "
    "Polos)\xa0\n\nParticipação na fase de estudos (AVA): a nota será "
    "atribuída com base na participação dos estudantes ao longo da disciplina"}
aviso_let110 = {"autor": "Paulo Otavio", "autoridade": "institucional",
    "url": "#l", "texto": "Olá, aluno (a)! Tudo bem?\n\nComo você já deve "
    "saber, sua nota de uma disciplina regular é composta por 40% atividades "
    "avaliativas do AVA mais 60% da prova final.\n\nTeremos atividades "
    "avaliativas nas semanas 1 a 7, para que você acompanhe melhor seu "
    "aprendizado ao longo de toda a disciplina."}

comp = composicao_da_nota({"avisos": [aviso_com100]})
checa(comp and comp["ava"] == 40 and comp["prova"] == 60,
      "lê 40/60 do aviso de critérios do COM100")
comp2 = composicao_da_nota({"avisos": [aviso_let110]})
checa(comp2 and comp2["ava"] == 40 and comp2["prova"] == 60,
      "lê a mesma regra escrita de outro jeito, no LET110")
checa(composicao_da_nota({"avisos": [
        {"autoridade": "institucional", "texto": "a prova vale 60% da nota"}]})
      is None,
      "um percentual solto não vira afirmação sobre a nota inteira")
checa(composicao_da_nota({"avisos": [
        {**aviso_com100, "autoridade": "colega"}]}) is None,
      "post de colega não define a regra de avaliação")
checa(composicao_da_nota({"avisos": [
        {"autoridade": "institucional",
         "texto": "30% do AVA e 60% da prova presencial"}]}) is None,
      "pesos que não fecham 100 são descartados em vez de exibidos")

html_c = R.render_composicao({"courses": [
    {"code": "COM100", "avisos": [aviso_com100]}]})
checa("60% prova presencial" in html_c and "login separado" in html_c,
      "o site diz o que não acompanha, em vez de omitir")
checa(R.render_composicao({"courses": [{"code": "X", "avisos": []}]}) == "",
      "sem aviso oficial, o guia fica calado sobre a composição")

print("\n== Fontes endurecidas (Etapa 5) ==")

from configuracao import cronograma_padrao  # noqa: E402
from fontes import foruns as FO  # noqa: E402

checa(cronograma_padrao(date(2026, 8, 4)).endswith("2026/cronograma_regular_3.html"),
      "agosto cai no 3º bimestre")
checa(cronograma_padrao(date(2026, 10, 1)).endswith("2026/cronograma_regular_4.html"),
      "outubro cai no 4º, em vez de repetir o bimestre passado para sempre")

from fontes.cronograma import _cobre_hoje  # noqa: E402

semanas_agosto = [
    {"n": 1, "inicio": "2026-07-20", "vencimento": "2026-07-29T23:59:00-03:00",
     "carencia": "2026-08-02T23:59:00-03:00"},
    {"n": 7, "inicio": "2026-08-31", "vencimento": "2026-09-09T23:59:00-03:00",
     "carencia": "2026-09-11T23:59:00-03:00"},
]
checa(_cobre_hoje(semanas_agosto, date(2026, 8, 4)) is True,
      "cronograma do bimestre corrente é aceito")
checa(_cobre_hoje(semanas_agosto, date(2026, 12, 1)) is False,
      "cronograma de outro bimestre é descartado em vez de virar prazo vencido")
checa(_cobre_hoje([{"n": 1}], date(2026, 8, 4)) is True,
      "sem datas para conferir, não inventa motivo para descartar")
checa(cronograma_padrao(date(2027, 2, 9)).endswith("2027/cronograma_regular_1.html"),
      "virada de ano acompanha o ano na URL")
checa(cronograma_padrao(date(2026, 12, 20)).endswith("cronograma_regular_4.html"),
      "dezembro não estoura para um 5º bimestre")

registro = FO.normalizar_registro_autores(["formador", "formador"], date(2026, 8, 4))
checa(registro == {"formador": "2026-08-04", "formador": "2026-08-04"},
      "registro antigo em lista vira registro com data")
antigo = {"formador": "2026-08-01", "Colega": "2026-01-10"}
sobrou = FO.esquecer_autores_antigos(antigo, date(2026, 8, 4))
checa(set(sobrou) == {"formador"},
      "autor que não aparece em Avisos há um bimestre deixa de ser fonte oficial")

sem_nome = [{"nome": "", "quando": "2026-08-01T23:59:00-03:00"},
            {"nome": "Término de S3", "quando": "2026-08-16T23:59:00-03:00"}]
checa(SA.resumo_fontes({"eventos": sem_nome, "courses": []})["eventos_uteis"] == 1,
      "a saúde conta só os eventos que têm nome")

print("\n== Cobrança de avaliação some quando o laboratório está na sub-seção ==")

def curso_quinzena(avaliacao_pendente):
    return {"code": "COM170", "modelo": "quinzenal", "id": 18922,
            "avisos": [{"autor": "formador", "url": "#a",
                        "autoridade": "institucional",
                        "prazos": [{"rotulo": "avaliação por pares da Quinzena 1",
                                    "quando": "2026-08-04T23:59:00-03:00",
                                    "tipo": "fim", "hora_certa": True,
                                    "confianca": "alta",
                                    "frase": "prazos da avaliação por pares",
                                    "escopo": {"familia": "quinzena",
                                               "numeros": [1], "txt": ""}}]}],
            "sections": [
                {"id": "s1", "title": "Quinzena 1", "parent": None,
                 "fase": "regular", "locked": None, "items": []},
                {"id": "s7", "title": "Módulo 7", "parent": "s1",
                 "fase": "regular", "locked": None, "items": [
                    {"cmid": "173857", "label": "M7 - Revisão entre pares",
                     "type": "workshop", "status": "Pendente",
                     "conta_nota": True, "aberto": True, "enviado": True,
                     "avaliacao_pendente": avaliacao_pendente, "url": "#w",
                     "prazo": "2026-08-04T23:59:00-03:00",
                     "prazo_fonte": "calendário do AVA"}]},
            ]}

ainda_falta = C.montar_acoes({"courses": [curso_quinzena(True)]},
                             HOJE_EV, agora=AGORA)[0]
checa(any("Avalie" in a["verbo"] for a in ainda_falta),
      "com a avaliação pendente, a cobrança aparece")

ja_avaliou = C.montar_acoes({"courses": [curso_quinzena(False)]},
                            HOJE_EV, agora=AGORA)[0]
checa(not [a for a in ja_avaliou if a["verbo"].startswith("Avalie")],
      "depois de avaliar, o aviso da quinzena para de cobrar mesmo com o "
      "laboratório numa sub-seção")

print("\n== Boletim vazio não faz a disciplina sumir (SOC100, 10/08/2026) ==")


def curso_boletim(estado, media=None, entrega=None):
    item = {"cmid": "1", "label": "S1 - Atividade Avaliativa", "type": "quiz",
            "status": "Concluído", "conta_nota": True, "url": "#q"}
    if entrega is not None:
        item["entrega_confirmada"] = entrega
    return {"code": "SOC100", "modelo": "regular",
            "boletim": {"status": estado, "media": media, "itens": 0},
            "sections": [{"id": "s1", "title": "Semana 1", "fase": "regular",
                          "locked": None, "items": [item]}]}


vazio = R.render_notas({"courses": [curso_boletim("vazio_confirmado")]})
checa("SOC100" in vazio,
      "disciplina com boletim vazio continua aparecendo na aba")
checa("ainda não publicou nenhuma nota" in vazio,
      "e diz que o boletim é que está vazio, em vez de sumir calada")
checa("deixou de entregar" in vazio,
      "sem nota não é apresentado como entrega faltando")

com_prova = R.render_notas(
    {"courses": [curso_boletim("vazio_confirmado", entrega=True)]}
)
checa("a entrega está registrada" in com_prova,
      "entrega conferida na página da atividade é dita, mesmo sem boletim")

falhou = R.render_notas({"courses": [curso_boletim("falhou")]})
checa("Não consegui ler o boletim" in falhou and "Confira no AVA" in falhou,
      "boletim que não abriu pede conferência, em vez de virar 'sem nota'")
checa("ainda não publicou nenhuma nota" not in falhou,
      "'não li' nunca é apresentado como 'está vazio'")

sem_boletim = R.render_notas(
    {"courses": [{"code": "X", "modelo": "regular", "sections": []}]}
)
checa(sem_boletim == "",
      "disciplina sem boletim nenhum continua fora, sem inventar bloco")

print("\n== Regra do curso não pode ser cortada pelo teto de avisos ==")

from fontes.foruns import post_estruturante, priorizar_posts  # noqa: E402

# Achado em 13/08/2026: o bloco "Como a nota é composta" não aparecia em
# NENHUMA das quatro disciplinas. A funcionalidade estava pronta e testada; o
# que faltava era o aviso chegar. O teto de 15 posts por disciplina é por
# recência, e os CRITÉRIOS DE AVALIAÇÃO são publicados uma vez, no começo do
# semestre — sempre os primeiros a cair.
checa(post_estruturante(
        {"autoridade": "institucional", "titulo": "CRITÉRIOS DE AVALIAÇÃO",
         "texto": ""}),
      "post de critérios de avaliação é regra do curso")
checa(post_estruturante(
        {"autoridade": "institucional", "titulo": "Pesos das Atividades",
         "texto": ""}),
      "post de pesos das atividades também")
checa(post_estruturante(
        {"autoridade": "institucional", "titulo": "Informações",
         "texto": "sua nota é composta por 40% do AVA mais 60% da prova"}),
      "e o que declara a composição no corpo, sem dizer no título")
checa(not post_estruturante(
        {"autoridade": "colega", "titulo": "CRITÉRIOS DE AVALIAÇÃO",
         "texto": ""}),
      "colega falando de critérios não vira regra do curso")
checa(not post_estruturante(
        {"autoridade": "institucional", "titulo": "LIVE COM FACILITADORES",
         "texto": "quinta-feira às 18:30, para tirar dúvidas"}),
      "aviso de live não é regra do curso")

lotados = [
    # Textos e ids distintos: posts iguais são deduplicados antes do teto, e
    # aí o teste não estaria medindo o corte.
    {"autor": "F", "id": str(1000 + i), "titulo": f"Aviso {i}",
     "texto": f"lembrete numero {i}",
     "data": f"2026-08-{10 + i % 3:02d}", "prazos": [{"quando": "x"}]}
    for i in range(20)
]
antigo = {"autor": "F", "titulo": "Pesos das Atividades",
          "texto": "sua nota é composta por 40% do AVA mais 60% da prova",
          "data": "2026-07-21"}
guardados, cortou, _ = priorizar_posts(lotados + [antigo], ["F"], 15)
checa(any("Pesos" in (p.get("titulo") or "") for p in guardados),
      "com 20 avisos recentes na frente, a regra do curso sobrevive ao teto")
checa(cortou, "e o corte continua sendo sinalizado")

print("\n== Data da prova presencial: procurar em vez de só declarar ==")

from dominio.avaliacao import data_da_prova, lacuna_da_prova  # noqa: E402

_HOJE = date(2026, 8, 13)
PESOS = ("Sua nota é composta por 40% atividades avaliativas do AVA mais "
         "60% da prova final.")


def _curso_com(texto_extra):
    return {"code": "LET110", "avisos": [
        {"autoridade": "institucional", "autor": "colega", "url": "#a",
         "texto": PESOS},
        {"autoridade": "institucional", "autor": "colega", "url": "#b",
         "texto": texto_extra}]}


achou = data_da_prova(
    _curso_com("A prova presencial será no dia 20/09/2026, no seu polo."),
    _HOJE)
checa(achou and achou["quando"].startswith("2026-09-20"),
      "data de prova dita em aviso oficial é encontrada")
checa(achou and "polo" in achou["frase"],
      "e vem com a frase original, para ele conferir a fonte")

# "prova" sozinho aparece em frase sobre atividade do AVA. Uma data errada
# aqui é pior que data nenhuma, que foi o erro original do guia.
checa(data_da_prova(
        _curso_com("A prova de conhecimentos do AVA vence em 19/08/2026."),
        _HOJE) is None,
      "'prova' sem marca de presencial não vira data de prova presencial")
checa(data_da_prova(
        _curso_com("A prova presencial acontece no polo, aguardem a data."),
        _HOJE) is None,
      "frase sobre prova presencial sem data nenhuma não inventa data")
checa(data_da_prova({"code": "LET110", "avisos": [
        {"autoridade": "colega", "autor": "X", "texto":
         "ouvi dizer que a prova presencial é 20/09/2026 no polo"}]},
        _HOJE) is None,
      "boato de colega não vira data de prova")

lac = lacuna_da_prova(_curso_com("Prova presencial: 20/09/2026, no polo."),
                      _HOJE)
checa(lac["ava"] == 40 and lac["prova"] == 60,
      "a composição continua saindo do aviso, como antes")
checa(lac["data_achada"] is not None,
      "e agora a lacuna carrega a data quando ela existe")
html_prova = R.render_composicao({"courses": [
    _curso_com("Prova presencial: 20/09/2026, no polo.")]})
checa("20/09" in html_prova and "Sistema de Provas" in html_prova,
      "o site mostra a data achada e ainda manda confirmar na fonte oficial")
sem_data = R.render_composicao({"courses": [_curso_com("Bons estudos.")]})
checa("se um facilitador disser a data, ela aparece aqui" in sem_data,
      "sem data, o guia diz que está procurando, não só que não sabe")

print("\n== Recado da mentora: escrita e envelhecimento ==")

import recado as REC  # noqa: E402

_BR = timezone(timedelta(hours=-3))
_ESCRITA = datetime(2026, 8, 13, 18, 0, tzinfo=_BR)

r_novo = REC.escrever("Foco de hoje é o portfólio.", agora=_ESCRITA)
checa(r_novo["valid_until"].startswith("2026-08-20"),
      "recado sem validade explícita vale uma semana, não para sempre")
checa(r_novo["written_at"].startswith("2026-08-13T18:00"),
      "guarda quando foi escrito, no fuso de Brasília")
checa(REC.escrever("x", ate="2026-08-15", agora=_ESCRITA)["valid_until"]
      == "2026-08-15T23:59:00-03:00",
      "--ate sem hora vira fim do dia, que é como os prazos do AVA funcionam")
checa(REC.escrever("x", enquanto_pendente=[215609], agora=_ESCRITA)
      ["requires_pending_cmids"] == ["215609"],
      "o gatilho de pendência é gravado como texto, igual ao resto do guia")

# O recado de 25/07 ficou 18 dias no ar como uma aba que só anunciava o
# próprio vencimento. Passada a carência, ele some junto com a aba.
_agora_13 = datetime(2026, 8, 13, 18, 0, tzinfo=_BR)
checa(R._recado_vencido_ha_muito(
        {"valid_until": "2026-07-26T23:59:00-03:00"}, _agora_13),
      "recado vencido há 18 dias é velho demais até para dizer que venceu")
checa(not R._recado_vencido_ha_muito(
        {"valid_until": "2026-08-12T23:59:00-03:00"}, _agora_13),
      "recado que venceu ontem ainda vale como aviso de que venceu")
checa(not R._recado_vencido_ha_muito({}, _agora_13),
      "recado sem data nenhuma continua à vista: sem idade, não se descarta")

print("\n== Vigia: rodada que nunca dispara ==")

import re as _re  # noqa: E402

import vigia as V  # noqa: E402

_AGORA = datetime(2026, 8, 13, 21, 0, tzinfo=timezone.utc)


def _com_publicado(retorno):
    original = V.ler_publicado
    V.ler_publicado = lambda **k: retorno
    try:
        return V.diagnostico(agora=_AGORA)
    finally:
        V.ler_publicado = original


recente = datetime(2026, 8, 13, 18, 0, tzinfo=timezone.utc)
congelado, texto = _com_publicado((3.0, recente, None))
checa(congelado is False, "retrato de 3h atrás não acorda o vigia")

velho = datetime(2026, 8, 11, 21, 0, tzinfo=timezone.utc)
congelado, texto = _com_publicado((48.0, velho, None))
checa(congelado is True and "48h" in texto,
      "retrato de dois dias é o caso que o vigia existe para pegar")

# Site fora do ar conta como congelado. É a mesma regra do resto do robô ao
# contrário: aqui o silêncio é do próprio guia, e silêncio do guia é falha.
congelado, texto = _com_publicado((None, None, "o site não respondeu (URLError)"))
checa(congelado is True and "não respondeu" in texto,
      "site que não responde acorda o vigia, não o deixa dormir")
congelado, texto = _com_publicado(
    (None, None, "o data.json publicado não diz quando foi lido"))
checa(congelado is True, "data.json sem carimbo também é motivo de aviso")

_limite_antigo = os.environ.get("LIMITE_HORAS")
os.environ["LIMITE_HORAS"] = "16"
congelado, _ = _com_publicado((15.0, velho, None))
checa(congelado is False, "15h com limite de 16h ainda é sono normal")
congelado, _ = _com_publicado((17.0, velho, None))
checa(congelado is True, "17h com limite de 16h desperta")
if _limite_antigo is None:
    os.environ.pop("LIMITE_HORAS", None)
else:
    os.environ["LIMITE_HORAS"] = _limite_antigo

vigia_yml = (ROOT / ".github" / "workflows" / "vigia.yml").read_text(
    encoding="utf-8")
principal = (ROOT / ".github" / "workflows" / "guia-diario.yml").read_text(
    encoding="utf-8")
crons_vigia = _re.findall(r'- cron: "([^"]+)"', vigia_yml)
crons_robo = _re.findall(r'- cron: "([^"]+)"', principal)
checa(crons_vigia and not set(crons_vigia) & set(crons_robo),
      "o vigia tem horário próprio, separado do robô")
checa("EMAIL_PARA" in vigia_yml and "--avisar" in vigia_yml,
      "o vigia sabe mandar e-mail quando acha o guia parado")
checa("AVA_USUARIO" not in vigia_yml and "AVA_SENHA" not in vigia_yml,
      "o vigia não recebe credencial do AVA: ele só olha o site público")

# O Secret da sessão salva saiu: o log de 13/08 mostrou a sessão sendo
# restaurada, vencendo e o robô logando por credencial do mesmo jeito.
# O alvo é o consumo do Secret, não a palavra: o comentário que explica por
# que ele saiu tem que poder continuar ali.
checa("secrets.AVA_STORAGE_STATE" not in principal,
      "o workflow não carrega mais a sessão salva")
checa("AVA_USUARIO" in principal and "AVA_SENHA" in principal,
      "e continua logando com as credenciais, que é o caminho que funciona")

print("\n== Os dez pontos contáveis da quinzena (COM170) ==")

from dominio.avaliacao import pontos_da_quinzena  # noqa: E402

# O aviso CRITÉRIOS DE AVALIAÇÃO (21/07/2026) lista dez itens de mesmo peso.
# O painel oficial mostra cinco. Ver "4 de 5" sem os outros cinco dá a
# impressão de que falta pouco quando falta quase metade.
CRITERIOS_PAINEL = [
    {"nome": "Módulo 1", "situacao": "Critério ainda não identificado",
     "atendido": False},
    {"nome": "Módulo 2", "situacao": "Critério atendido", "atendido": True},
    {"nome": "Módulo 3", "situacao": "Critério atendido", "atendido": True},
    {"nome": "Módulo 4", "situacao": "Critério atendido", "atendido": True},
    {"nome": "Qualidade da participação", "situacao": "Critério atendido",
     "atendido": True},
]
CURSO_Q2 = {
    "code": "COM170",
    "participacao": {"criterios": CRITERIOS_PAINEL},
    "sections": [{"id": "s-q2m6", "title": "Q2 Módulo 6", "items": [
        {"type": "workshop", "label": "Q2 M6 - Revisão entre pares "
         "(colega)", "enviado": False,
         "avaliacao_pendente": None}]},
        {"id": "s-q2m7", "title": "Q2 Módulo 7", "items": [
            {"type": "workshop", "label": "Q2 M7 - Revisão entre pares "
             "(Portfólio em grupo)", "enviado": False,
             "avaliacao_pendente": None}]}],
}

placar = pontos_da_quinzena(CURSO_Q2)
checa(placar["total"] == 10, "o placar tem os dez pontos, não os cinco do painel")
checa([p["nome"] for p in placar["pontos"]][:4]
      == ["Módulo 1", "Módulo 2", "Módulo 3", "Módulo 4"],
      "os quatro módulos vêm do painel oficial, em ordem")
checa(placar["pontos"][-1]["nome"] == "Qualidade da participação",
      "a qualidade da participação fecha a lista")
checa(placar["atendidos"] == 4 and placar["pendentes"] == 3,
      "estado real de 13/08: 4 contaram, 3 faltam")
por_nome = {p["nome"]: p for p in placar["pontos"]}
checa(por_nome["Entrega individual do portfólio"]["atendido"] is False
      and por_nome["Entrega de grupo"]["atendido"] is False,
      "as duas entregas viram ponto próprio, lidas do Laboratório")
checa(por_nome["Participação em uma live"]["atendido"] is None,
      "presença em live é None, nunca False: o guia não consegue conferir")
checa("não consegue conferir" in por_nome["Participação em uma live"]["detalhe"],
      "e o site diz por que não sabe")
checa(por_nome["Feedback ao colega"]["atendido"] is None,
      "feedback antes da fase de avaliação abrir é 'não sei', não 'falta'")

entregue = json.loads(json.dumps(CURSO_Q2))
entregue["sections"][0]["items"][0].update(
    {"enviado": True, "avaliacao_pendente": False})
depois = pontos_da_quinzena(entregue)
checa({p["nome"]: p["atendido"] for p in depois["pontos"]}[
          "Entrega individual do portfólio"] is True
      and {p["nome"]: p["atendido"] for p in depois["pontos"]}[
          "Feedback ao colega"] is True,
      "entrega feita e feedback dado passam a contar")

checa(pontos_da_quinzena({"code": "COM100", "participacao":
                          {"criterios": CRITERIOS_PAINEL}}) is None,
      "disciplina regular não tem placar de quinzena")
checa(pontos_da_quinzena({"code": "COM170", "participacao": {}}) is None,
      "sem os critérios do painel, o guia não inventa o placar")
checa(pontos_da_quinzena(
        {**CURSO_Q2, "sections": []})["pontos"][4]["detalhe"]
      == "não achei a atividade",
      "Laboratório ausente vira 'não achei', não 'não entregou'")

html_pontos = R.render_pontos_da_quinzena({"courses": [CURSO_Q2]})
checa("4 de 10 já contaram" in html_pontos,
      "o site mostra a escala real, não só o 4 de 5 do painel")
checa("não sei" in html_pontos and "falta" in html_pontos,
      "o site separa o que falta do que ele não consegue conferir")
checa(R.render_pontos_da_quinzena({"courses": [{"code": "COM100"}]}) == "",
      "sem placar não sai bloco")

print("\n== Entregou e o boletim lançou zero (M6 Q1, 13/08/2026) ==")

# Estado real: entrega em 29/07, avaliação do colega no nível máximo, boletim
# com 0,00 no envio. Sem isto à vista, "entreguei e zerei" tem a mesma cara
# de "não fiz".
M6_ZERADO = {"label": "M6 - Revisão entre pares (colega)",
             "type": "workshop", "conta_nota": True, "enviado": True,
             "nota_txt": "0,00", "nota": 0.0, "tem_nota": True,
             "url": "https://ava.univesp.br/mod/workshop/view.php?id=173854"}
SCORM_ZERADO = {"label": "Q2 M1 - Atividade: tokenizador interativo",
                "type": "scorm", "conta_nota": True, "nota_txt": "0,00",
                "nota": 0.0, "tem_nota": True}

checa(R._entregou_e_zerou(M6_ZERADO),
      "entrega confirmada com nota zero é sinalizada")
checa(not R._entregou_e_zerou(SCORM_ZERADO),
      "zero sem prova de envio não vira alerta (SCORM do COM170 é 0,00 normal)")
checa(not R._entregou_e_zerou({**M6_ZERADO, "nota": 1.0}),
      "entrega com nota não vira alerta")
checa(not R._entregou_e_zerou({**M6_ZERADO, "enviado": None}),
      "sem leitura de envio, o guia não acusa nada")

html_zero = R.render_notas({"courses": [{"code": "COM170",
    "boletim": {"status": "live", "media": {"rotulo": "Média AVA",
                                            "nota": "0,29"}},
    "sections": [{"title": "Módulo 6", "items": [M6_ZERADO, SCORM_ZERADO]}]}]})
checa("lançou <b>zero</b>" in html_zero,
      "a aba 'Como estou' avisa que a entrega existiu e a nota veio zero")
checa(html_zero.count("lançou <b>zero</b>") == 1,
      "e avisa só no item entregue, não em todo zero do boletim")

print("\n== Espaço do grupo parado (G4, 13/08/2026) ==")

import dominio.acoes as D_ACOES  # noqa: E402
from dominio.acoes import avisos_de_grupo_parado, montar_acoes  # noqa: E402

# Cenário real: a dois dias da entrega, o "Q2 M7 - Grupo: Ponto de encontro"
# do G4 não tinha um único tópico. Fórum vazio não gera post, então nada disso
# chegava ao guia.
ENTREGA_G4 = {
    "curso": "COM170", "secao": "Q2 Módulo 7", "tipo": "workshop",
    "o_que": "Q2 M7 - Revisão entre pares (Portfólio em grupo)",
    "url": "https://ava.univesp.br/mod/workshop/view.php?id=215612",
    "prazo": "2026-08-15T23:59:00-03:00", "prazo_txt": "vence 15/08 às 23:59",
    "prazo_fonte": "calendário do AVA", "urgencia": "semana",
    "conta_nota": True, "hora_certa": True,
}
ESPACO_VAZIO = {"label": "Q2 M7 - Grupo: Ponto de encontro",
                "url": "https://ava.univesp.br/mod/forum/view.php?id=215611",
                "cmid": "215611", "tem_topico": False}

def _com_grupo(espacos, acoes):
    return avisos_de_grupo_parado(
        {"courses": [{"code": "COM170", "espacos_de_grupo": espacos}]}, acoes
    )

avisos_grupo = _com_grupo([ESPACO_VAZIO], [ENTREGA_G4])
checa(len(avisos_grupo) == 1, "grupo sem tópico com entrega em aberto vira aviso")
checa(avisos_grupo[0]["prazo"] == ENTREGA_G4["prazo"]
      and avisos_grupo[0]["urgencia"] == "semana",
      "o aviso herda o prazo e a urgência da entrega em grupo")
checa(avisos_grupo[0]["url"] == ESPACO_VAZIO["url"],
      "o link leva ao espaço do grupo, que é onde a ação acontece")
checa(_com_grupo([{**ESPACO_VAZIO, "tem_topico": True}], [ENTREGA_G4]) == [],
      "grupo que já tem conversa não gera aviso")
checa(_com_grupo([ESPACO_VAZIO], []) == [],
      "sem entrega em grupo em aberto, espaço vazio não é problema")
# "Não consegui ler" nunca pode virar "está vazio": é a mesma regra que o
# boletim do SOC100 forçou em 10/08.
checa(_com_grupo([{**ESPACO_VAZIO, "tem_topico": None}], [ENTREGA_G4]) == [],
      "fórum não lido nesta rodada não é tratado como fórum vazio")
checa(_com_grupo([], [ENTREGA_G4]) == [],
      "disciplina sem espaço de grupo lido não gera aviso")

# Rodada real de 13/08: o COM170 tem cinco fóruns de grupo, três deles da
# ambientação já encerrada. Todos vazios, todos herdaram o prazo do Q2 M7 e
# viraram cobranças que não existem. O espaço tem que casar com a entrega da
# mesma unidade.
ANTIGOS = [{"label": f"S{n} - Fórum do Grupo",
            "url": f"https://ava.univesp.br/mod/forum/view.php?id=15{n}",
            "cmid": None, "tem_topico": False} for n in (2, 3, 4)]
checa(_com_grupo(ANTIGOS, [ENTREGA_G4]) == [],
      "fórum de grupo de outra unidade não herda o prazo da entrega atual")
checa(len(_com_grupo(ANTIGOS + [ESPACO_VAZIO], [ENTREGA_G4])) == 1,
      "no meio dos antigos, só o espaço da unidade da entrega vira aviso")
checa(D_ACOES.unidade_do_rotulo("Q2 M7 - Grupo: Ponto de encontro")
      == D_ACOES.unidade_do_rotulo(
          "Q2 M7 - Revisão entre pares (Portfólio em grupo)") == "q2 m7",
      "espaço e entrega da mesma unidade têm o mesmo prefixo")
checa(D_ACOES.unidade_do_rotulo("Fórum do Grupo") is None,
      "rótulo sem prefixo de unidade não casa com nada")

html_grupo = R.render_acao(avisos_grupo[0])
checa("Ponto de encontro" in html_grupo and "vence 15/08" in html_grupo,
      "o cartão mostra o espaço do grupo com o prazo da entrega")
checa("começar sozinho já vale" in html_grupo,
      "e diz o que fazer quando ninguém do grupo apareceu")

print("\n== Nota que sai é notícia (10/08/2026) ==")

from dominio.acoes import notas_novas  # noqa: E402


def pacote(estado_boletim="live", nota=None, feedback=None, code="SOC100"):
    """Um retrato mínimo com uma atividade avaliada (ou não)."""
    item = {"cmid": "1", "label": "S1 - Atividade Avaliativa", "type": "quiz",
            "conta_nota": True, "url": "#q"}
    if nota is not None:
        item.update({"nota_txt": nota, "tem_nota": True, "feedback": feedback})
    return {"courses": [{
        "code": code, "modelo": "regular",
        "boletim": {"status": estado_boletim, "media": None, "itens": 0},
        "sections": [{"id": "s1", "title": "Semana 1", "fase": "regular",
                      "locked": None, "items": [item]}]}]}


T0 = "2026-08-10T09:00:00+00:00"
T1 = "2026-08-10T15:00:00+00:00"   # mesma janela, rodada seguinte
T5 = "2026-08-15T09:00:00+00:00"   # cinco dias depois, fora da janela

# O caso que puxou este fio: SOC100 com boletim vazio até a nota sair.
estado_novo = {}
saiu = notas_novas(pacote("vazio_confirmado"), pacote(nota="8,00"),
                   estado_novo, T0)
checa(len(saiu) == 1 and saiu[0]["nota"] == "8,00",
      "nota que aparece num boletim antes vazio vira notícia")
checa(saiu[0]["de"] is None,
      "nota que nunca existiu é anunciada como nova, não como mudança")

# A notícia precisa sobreviver às rodadas do mesmo dia: ele lê o guia uma vez.
ainda = notas_novas(pacote(nota="8,00"), pacote(nota="8,00"), estado_novo, T1)
checa(len(ainda) == 1,
      "a nota continua anunciada nas rodadas seguintes, dentro da janela")
depois = notas_novas(pacote(nota="8,00"), pacote(nota="8,00"), estado_novo, T5)
checa(depois == [] and estado_novo["_notas_vistas"] == {},
      "passada a janela, a notícia sai e não fica entulhando o estado")

# Nota que já estava no retrato anterior nunca é anunciada de novo.
checa(notas_novas(pacote(nota="8,00"), pacote(nota="8,00"), {}, T0) == [],
      "nota que já estava no retrato anterior não vira notícia")

# Correção de nota é notícia, e diz de onde veio.
mudou = notas_novas(pacote(nota="7,50"), pacote(nota="9,00"), {}, T0)
checa(len(mudou) == 1 and mudou[0]["de"] == "7,50" and mudou[0]["nota"] == "9,00",
      "nota corrigida é anunciada com o valor anterior")

# O alarme falso que este desenho existe para evitar.
checa(notas_novas(pacote("falhou", nota="8,00"), pacote(nota="8,00"), {}, T0) == [],
      "boletim que falhou na rodada anterior não gera 'nota nova' falsa")
checa(notas_novas(None, pacote(nota="8,00"), {}, T0) == [],
      "primeira rodada, sem retrato anterior, não anuncia nota nenhuma")
checa(notas_novas({"courses": []}, pacote(nota="8,00"), {}, T0) == [],
      "disciplina que ainda não tinha sido lida entra sem alarde")

# Zero é nota, e é exatamente a que ele precisa ver.
zero = notas_novas(pacote("vazio_confirmado"), pacote(nota="0,00"), {}, T0)
checa(len(zero) == 1, "0,00 é nota lançada e é anunciada como qualquer outra")
tracinho = notas_novas(pacote("vazio_confirmado"), pacote("live"), {}, T0)
checa(tracinho == [], "atividade sem nota lançada não vira notícia de nota")

# A notícia chega no site...
com_nota = R.render_novidades(
    {"notas_novas": [{"curso": "SOC100", "label": "S1 - Atividade Avaliativa",
                      "url": "#q", "nota": "8,00", "de": None,
                      "feedback": "bom trabalho", "em": T0}]}
)
checa("8,00" in com_nota and "SOC100" in com_nota,
      "a aba 'Chegou novo' mostra a nota que saiu")
checa("saiu a nota" in com_nota and "bom trabalho" in com_nota,
      "e mostra a devolutiva do facilitador junto")
vazia = R.render_novidades({})
checa("Nenhum prazo, nota, atividade" in vazia,
      "sem novidade nenhuma, a aba diz isso nomeando tudo que ela cobre")

checa(R.contar_novidades(
        {"notas_novas": [{"curso": "SOC100", "nota": "8,00"}]}) == 1,
      "o contador da aba soma a nota nova")
checa(R.contar_novidades(
        {"notas_novas": [{"curso": "SOC100", "nota": "8,00"}],
         "mensagens": [{"nao_lidas": 2}],
         "notificacoes": [{"lida": False}]}) == 4,
      "e continua somando fórum, mensagem e notificação junto")

# ...e no e-mail, que é o que ele lê antes de abrir o site.
corpo = E.montar_texto({
    "acoes": [], "notas_novas": [{"curso": "SOC100", "label": "S1 - Atividade",
    "nota": "8,00", "de": None, "feedback": "bom trabalho", "em": T0}]})
checa("SAIU NOTA" in corpo and "SOC100: S1 - Atividade = 8,00" in corpo,
      "o e-mail traz a nota que saiu, com a disciplina e o valor")
checa("devolutiva: bom trabalho" in corpo,
      "e traz a devolutiva junto, que é o que explica a nota")
checa("saiu nota em SOC100" in E.assunto({
        "acoes": [], "notas_novas": [{"curso": "SOC100", "nota": "8,00"}]}),
      "sem nada urgente, o assunto anuncia a nota em vez de 'tudo em dia'")
checa("tudo em dia" in E.assunto({"acoes": [], "notas_novas": []}),
      "sem nota nova, o assunto de dia calmo continua o mesmo")

print("\n== A média do curso não é o total de uma quinzena (10/08/2026) ==")

from fontes import boletim as B  # noqa: E402


class BoletimFake:
    """Devolve as linhas cruas, como o ``page.evaluate`` do boletim."""

    def __init__(self, linhas):
        self.linhas = linhas

    def goto(self, url, **kwargs):
        pass

    def wait_for_selector(self, seletor, timeout=None):
        pass

    def wait_for_timeout(self, ms):
        pass

    def evaluate(self, script):
        return self.linhas


def linha(rotulo, nota, url=None):
    return {"rotulo": rotulo, "nota": nota, "feedback": "", "url": url}


CABECALHO = linha("Item de nota", "Nota")
# Rótulos copiados do relatório do COM170 (id 18922) em 10/08/2026, com o
# prefixo de tipo que o Moodle escreve na frente do nome.
COM170_REAL = [
    CABECALHO,
    linha("QUESTIONÁRIO M1 - Quiz: Identifique o paradigma", "0,00",
          "https://ava.univesp.br/mod/quiz/view.php?id=173832"),
    linha("FORMA DE AGREGAÇÃO DAS NOTAS Quinzena 1 total", "2,00"),
    linha("FORMA DE AGREGAÇÃO DAS NOTAS Quinzena 2 total", "-"),
    linha("FORMA DE AGREGAÇÃO DAS NOTAS Quinzena 3 total", "-"),
    linha("FORMA DE AGREGAÇÃO DAS NOTAS Quiz total", "-"),
    linha("NOTA CALCULADA Média AVA", "0,29"),
]

_, resumo = B.ler(BoletimFake(COM170_REAL), 18922)
checa(resumo["media"] == {"rotulo": "Média AVA", "nota": "0,29",
                          "tipo": "nota calculada"},
      "a média do curso é a linha que o Moodle declara como nota calculada")
checa(resumo["media"]["nota"] != "2,00",
      "o total da Quinzena 1 não é mais estampado como se fosse a média")
checa([t["rotulo"] for t in resumo["totais"]] == ["Quinzena 1 total"],
      "totais de unidade viram detalhe, e só os que têm nota lançada")

# COM100 e LET110: uma linha calculada só, e continua funcionando.
_, simples = B.ler(BoletimFake([CABECALHO, linha("NOTA CALCULADA Média AVA", "2,00")]), 18870)
checa(simples["media"]["nota"] == "2,00" and simples["totais"] == [],
      "disciplina com uma linha calculada só segue lendo a média igual")

# Sem linha do curso inteiro, o guia não promove total de unidade a média.
_, sem_media = B.ler(
    BoletimFake([CABECALHO,
                 linha("FORMA DE AGREGAÇÃO DAS NOTAS Quinzena 1 total", "2,00")]),
    99)
checa(sem_media["media"] is None and len(sem_media["totais"]) == 1,
      "sem nota calculada do curso, a média fica vazia em vez de inventada")

cabec = R.render_notas({"courses": [{
    "code": "COM170", "modelo": "regular",
    "boletim": {"status": "live",
                "media": {"rotulo": "Média AVA", "nota": "0,29"},
                "totais": [{"rotulo": "Quinzena 1 total", "nota": "2,00"}],
                "itens": 1},
    "sections": [{"id": "s1", "title": "Quinzena 1", "fase": "regular",
                  "locked": None, "items": [
                      {"cmid": "1", "label": "M1 - Quiz", "type": "quiz",
                       "conta_nota": True, "nota_txt": "0,00",
                       "tem_nota": True, "url": "#q"}]}]}]})
checa("Média AVA: " in cabec and "0,29" in cabec,
      "a aba mostra a média do curso como número principal")
checa("Quinzena 1 total: 2,00" in cabec,
      "e o total da quinzena continua à vista, como detalhe")

print("\n== As oito fontes aparecem na linha de saúde ==")

saude_ok = R.render_fontes_status({"status": "ok", "fontes_status": {
    "disciplinas": {"status": "live", "quantidade_atual": 4,
                    "last_live_at": T0},
    "boletim": {"status": "live", "quantidade_atual": 25, "last_live_at": T0},
    "participacao": {"status": "live", "quantidade_atual": 7,
                     "last_live_at": T0}}})
checa("25 notas no boletim" in saude_ok
      and "7 quinzenas de participação" in saude_ok,
      "boletim e participação entram no 'o que eu li'")

saude_ruim = R.render_fontes_status({"status": "ok", "fontes_status": {
    "disciplinas": {"status": "live", "quantidade_atual": 4,
                    "last_live_at": T0},
    "boletim": {"status": "falhou", "from_cache": True,
                "quantidade_atual": 25, "last_live_at": T0}}})
checa("Atenção" in saude_ruim and "boletins" in saude_ruim,
      "boletim que falhou passa a ser dito, em vez de sumir da linha de saúde")

saude_na = R.render_fontes_status({"status": "ok", "fontes_status": {
    "disciplinas": {"status": "live", "quantidade_atual": 4,
                    "last_live_at": T0},
    "participacao": {"status": "nao_aplicavel", "quantidade_atual": 0}}})
checa("participação" not in saude_na and "Atenção" not in saude_na,
      "fonte que nenhuma disciplina tem não vira 0 nem alarme")

print("\n== Atividade nova deixou de ser cálculo sem tela ==")

from dominio.acoes import novidades  # noqa: E402


def com_itens(rotulos):
    return {"courses": [{
        "code": "COM100", "modelo": "regular",
        "sections": [{"id": "s4", "title": "Semana 4", "fase": "regular",
                      "locked": None, "items": [
                          {"cmid": str(900 + i), "label": r,
                           "status": "Pendente", "url": f"#i{i}"}
                          for i, r in enumerate(rotulos)]}]}]}


novos = novidades(com_itens(["S4 - Início"]),
                  com_itens(["S4 - Início", "S4 - Avaliação", "S4 - Live"]))
checa(len(novos) == 2 and novos[0]["secao"] == "Semana 4",
      "atividade que não existia na leitura anterior vira novidade, com a seção")
checa(novidades(None, com_itens(["S4 - Início"])) == [],
      "sem retrato anterior o AVA inteiro não é anunciado como novidade")
checa(novidades(com_itens(["S4 - Início"]), com_itens(["S4 - Início"])) == [],
      "sem item novo, nada é anunciado")

muitos = {"novidades": [
    {"curso": "COM100", "secao": "Semana 4", "label": f"S4 - item {i}"}
    for i in range(20)]}
html_novos = R.render_novidades(muitos)
checa("COM100" in html_novos and "Semana 4" in html_novos
      and "e mais 17" in html_novos,
      "vinte itens de uma semana viram uma linha só, com a conta do resto")
checa(R.contar_novidades(muitos) == 1,
      "e contam como uma novidade no rótulo da aba, não vinte")

# Formato antigo do data.json, que sobrevive até a próxima leitura do robô.
legado = {"novidades": [
    {"curso": "COM100", "label": "Re: Fórum de dúvidas", "kind": "aviso"},
    {"curso": "COM100", "label": "S3 - Videoaula", "kind": "concluido"},
    {"curso": "COM100", "label": "S4 - Início", "kind": "novo"}]}
checa(R.contar_novidades(legado) == 1
      and "Re: Fórum de dúvidas" not in R.render_novidades(legado),
      "post e item concluído do formato antigo não viram atividade nova")

print("\n== Prazo que aparece à tarde não espera até amanhã (10/08/2026) ==")

from dominio.acoes import prazos_novos  # noqa: E402

AGORA_UTC = "2026-08-10T17:00:00+00:00"   # 14h de Brasília


def com_prazo(prazo, cmid="1", rotulo="S3 - Atividade Avaliativa",
              conta_nota=True):
    item = {"cmid": cmid, "label": rotulo, "type": "quiz", "url": "#q",
            "status": "Pendente", "conta_nota": conta_nota,
            "prazo_fonte": "calendário do AVA"}
    if prazo:
        item["prazo"] = prazo
    return {"courses": [{
        "code": "COM100", "modelo": "regular",
        "sections": [{"id": "s3", "title": "Semana 3", "fase": "regular",
                      "locked": None, "items": [item]}]}]}


HOJE_23H = "2026-08-10T23:59:00-03:00"
DAQUI_5_DIAS = "2026-08-15T23:59:00-03:00"

estado_p = {}
apareceu = prazos_novos(com_prazo(None), com_prazo(HOJE_23H), estado_p, AGORA_UTC)
checa(len(apareceu) == 1 and apareceu[0]["prazo"] == HOJE_23H,
      "prazo que o AVA passou a mostrar vira aviso")
checa(apareceu[0]["de"] is None and apareceu[0]["atividade_nova"] is False,
      "atividade que já existia e ganhou prazo é dita como prazo novo, não como item novo")

repetido = prazos_novos(com_prazo(HOJE_23H), com_prazo(HOJE_23H), estado_p,
                        AGORA_UTC)
checa(repetido == [], "prazo que já estava no retrato anterior não vira aviso")

# Oscilação de fonte: prazo some numa leitura e volta na seguinte.
sumiu = prazos_novos(com_prazo(HOJE_23H), com_prazo(None), estado_p, AGORA_UTC)
voltou = prazos_novos(com_prazo(None), com_prazo(HOJE_23H), estado_p, AGORA_UTC)
checa(sumiu == [] and voltou == [],
      "prazo que some e volta não avisa de novo a cada ida e volta")

mudou_p = prazos_novos(com_prazo(HOJE_23H), com_prazo(DAQUI_5_DIAS), {},
                       AGORA_UTC)
checa(len(mudou_p) == 1 and mudou_p[0]["de"] == HOJE_23H,
      "prazo adiado ou antecipado é avisado com a data anterior")
checa(prazos_novos(None, com_prazo(HOJE_23H), {}, AGORA_UTC) == [],
      "primeira rodada, sem retrato anterior, não avisa prazo nenhum")

# O filtro do e-mail: perto o bastante para interromper o dia.
UMA_HORA_ANTES = datetime(2026, 8, 10, 14, 0, tzinfo=E.BR_TZ)
perto = E.prazos_para_alertar({"prazos_novos": [
    {"curso": "COM100", "label": "S3", "prazo": HOJE_23H}]}, UMA_HORA_ANTES)
checa(len(perto) == 1, "prazo para hoje à noite entra no alerta")
longe = E.prazos_para_alertar({"prazos_novos": [
    {"curso": "COM100", "label": "S3", "prazo": "2026-08-20T23:59:00-03:00"}]},
    UMA_HORA_ANTES)
checa(longe == [], "prazo de daqui a dez dias cabe no e-mail da manhã")
vencido = E.prazos_para_alertar({"prazos_novos": [
    {"curso": "COM100", "label": "S3", "prazo": "2026-08-09T23:59:00-03:00"}]},
    UMA_HORA_ANTES)
checa(vencido == [], "prazo que já venceu não vira alerta de interrupção")

alerta = E.montar_alerta({}, perto)
checa("10/08 às 23:59" in alerta and "COM100" in alerta,
      "o alerta diz a data, a hora e a disciplina")
checa("e-mail da manhã" in alerta,
      "e deixa claro que não substitui o resumo do dia")
checa("prazo novo" in E.assunto_alerta(perto),
      "o assunto do alerta diz que é prazo novo, não repete 'tudo em dia'")

diario = E.montar_texto({"acoes": [], "prazos_novos": [
    {"curso": "COM100", "label": "S3 - Atividade", "prazo": HOJE_23H,
     "conta_nota": True}]})
checa("PRAZO NOVO DESDE A ÚLTIMA LEITURA" in diario and "vale nota" in diario,
      "o resumo da manhã também separa o que é prazo novo")

site_prazo = R.render_novidades({"prazos_novos": [
    {"curso": "COM100", "label": "S3 - Atividade Avaliativa", "url": "#q",
     "prazo": HOJE_23H, "de": None, "conta_nota": True,
     "fonte": "calendário do AVA", "atividade_nova": False}]})
checa("10/08 às 23:59" in site_prazo and "vale nota" in site_prazo,
      "a aba 'Chegou novo' também mostra o prazo que apareceu")
checa("passou a mostrar prazo" in site_prazo,
      "e diz por que aquilo está ali")
checa(R.contar_novidades({"prazos_novos": [{"curso": "X", "prazo": HOJE_23H}]}) == 1,
      "prazo novo entra no contador da aba")

print("\n== Corte por teto de rodada deixou de ser segredo do log ==")

corte = R.render_fontes_status({"status": "ok", "fontes_status": {
    "itens": {"status": "live", "quantidade_atual": 45, "truncado": True,
              "nao_conferidos": 7, "last_live_at": T0}}})
checa("7 atividade(s) ficaram sem conferência" in corte,
      "o site diz quantas atividades ficaram sem conferência")
checa("continuam na lista" in corte,
      "e explica que elas não sumiram, só não foram confirmadas")

corte_forum = R.render_fontes_status({"status": "ok", "fontes_status": {
    "foruns": {"status": "live", "quantidade_atual": 60, "truncado": True,
               "last_live_at": T0}}})
checa("mais posts do que eu guardo" in corte_forum,
      "o corte dos fóruns continua com a explicação dele, que é outra")

print("\n== Curso que volta sem seção é 'não li', não 'curso vazio' ==")

from fontes import disciplinas as D  # noqa: E402
from fontes.moodle import FalhaFonte as FalhaDeFonte  # noqa: E402

SECOES_BOAS = {"secoes": [{"id": "s1", "title": "Semana 1", "locked": None,
                           "items": [{"cmid": "1", "label": "S1 - Videoaula",
                                      "status": "Pendente"}]}],
               "links": {}}


class CursoFake:
    """A página do curso monta só depois de ``vazias`` leituras."""

    def __init__(self, vazias):
        self.vazias, self.leituras, self.esperas = vazias, 0, 0
        self.url = "https://ava.univesp.br/course/view.php?id=1"

    def goto(self, url, **kwargs):
        self.url = url

    def wait_for_timeout(self, ms):
        self.esperas += 1

    def evaluate(self, script):
        self.leituras += 1
        if self.leituras <= self.vazias:
            return {"secoes": [], "links": {}}
        return copy.deepcopy(SECOES_BOAS)


pagina_lenta = CursoFake(vazias=1)
with contextlib.redirect_stdout(io.StringIO()):
    secoes_lidas, _ = D.ler_curso(pagina_lenta, {"id": 1, "nome": "SOC100"})
checa(len(secoes_lidas) == 1 and pagina_lenta.leituras == 2,
      "página que ainda não montou é relida, e a segunda leitura salva o curso")

pagina_vazia = CursoFake(vazias=9)
saida_curso = io.StringIO()
try:
    with contextlib.redirect_stdout(saida_curso):
        D.ler_curso(pagina_vazia, {"id": 1, "nome": "SOC100"})
except FalhaDeFonte as erro:
    recusou = "sem nenhuma seção" in str(erro)
else:
    recusou = False
checa(recusou and pagina_vazia.leituras == 3,
      "curso que insiste em voltar vazio vira falha declarada, não curso sem atividade")
checa("SOC100" in saida_curso.getvalue(),
      "e o log diz qual disciplina não montou, para achar no dia seguinte")

print("\n== A página inteira, renderizada de verdade ==")

with tempfile.TemporaryDirectory() as tmp:
    docs_antigo = R.DOCS
    try:
        R.DOCS = Path(tmp)
        R.render_html({
            "status": "ok", "checked_at": T0, "snapshot_at": T0,
            "courses": [], "acoes": [],
            "prazos_novos": [{"curso": "COM100", "label": "S3", "url": "#q",
                              "prazo": HOJE_23H, "conta_nota": True}],
            "notas_novas": [{"curso": "SOC100", "label": "S1", "nota": "8,00",
                             "em": T0}],
        })
        pagina = (Path(tmp) / "index.html").read_text(encoding="utf-8")
    finally:
        R.DOCS = docs_antigo

checa("overflow-wrap:break-word" in pagina,
      "link de 90 caracteres não empurra a página para o lado no celular")
checa(pagina.index("Prazo novo") < pagina.index("Saiu nota nova"),
      "na aba, prazo vem antes de nota: é o único que pode vencer hoje")
checa('<span class="tab-badge">2</span>' in pagina,
      "o rótulo da aba soma prazo e nota da mesma leitura")

print("\n== Silêncio do robô deixou de parecer dia calmo ==")

falha_txt = E.montar_falha("atualizar (rodada 42)",
                           "https://github.com/x/y/actions/runs/1",
                           "10/08 às 06:49, cerca de 12h atrás")
checa("não conseguiu terminar" in falha_txt.lower()
      and "atualizar (rodada 42)" in falha_txt,
      "o aviso de falha diz que o robô parou e onde parou")
checa("actions/runs/1" in falha_txt,
      "e leva direto para o log daquela rodada")
checa("salvar_credenciais.bat" in falha_txt,
      "com o passo a passo do caso mais comum, a sessão vencida")
checa("cerca de 12h atrás" in falha_txt,
      "e diz de quando é o retrato que ficou publicado")

print("\n== Abertura não é prazo, e o calendário resolve o indefinido ==")

from pipeline import _prazo_por_cmid, janela_declarada  # noqa: E402

# Os três eventos que o AVA publica para um Laboratório, com os tipos reais
# lidos em 09/08/2026 (opensubmission / closesubmission / closeassessment).
LAB = [
    {"cmid": "215612", "tipo": "opensubmission",
     "nome": "Q2 M7 - início de envios", "quando": "2026-08-10T00:00:00-03:00"},
    {"cmid": "215612", "tipo": "closesubmission",
     "nome": "Q2 M7 - prazo limite de envios",
     "quando": "2026-08-15T23:59:00-03:00"},
    {"cmid": "215612", "tipo": "closeassessment",
     "nome": "Q2 M7 - prazo limite para avaliação",
     "quando": "2026-08-18T23:59:00-03:00"},
]
NOITE = "2026-08-09T23:30:00-03:00"

escolhido = _prazo_por_cmid(LAB, NOITE)["215612"]
checa(escolhido["quando"] == "2026-08-15T23:59:00-03:00",
      "o prazo é o fechamento do envio, não a abertura de amanhã")
checa(escolhido["tipo"] not in ("opensubmission",),
      "abertura nunca é escolhida como prazo, mesmo sendo o próximo evento")

checa(janela_declarada(LAB, NOITE)["215612"] is True,
      "com fechamento no futuro, o calendário responde 'ainda aberto'")
checa(janela_declarada(LAB, "2026-08-19T08:00:00-03:00")["215612"] is False,
      "passados todos os fechamentos, o calendário responde 'encerrado'")
# Sem prova nenhuma a resposta continua sendo "não sei": a meta é ler melhor,
# nunca preencher silêncio com suposição.
checa(janela_declarada(
        [{"cmid": "9", "tipo": "opensubmission",
          "quando": "2026-08-10T00:00:00-03:00"}], NOITE)["9"] is None,
      "só com abertura, sem nenhum fechamento, a resposta segue indefinida")
checa(janela_declarada([], NOITE) == {},
      "atividade sem evento no calendário não ganha resposta inventada")

print("\n== Soneca de rede não custa a página inteira (09/08/2026) ==")

from playwright.sync_api import Error as PWError  # noqa: E402

from fontes.moodle import (  # noqa: E402
    FalhaFonte, SessaoExpirada, navegar_insistindo,
)


class PaginaFake:
    """Falha ``quedas`` vezes e só então responde, como um tropeço de rede."""

    def __init__(self, quedas=0, login=False):
        self.quedas, self.login = quedas, login
        self.idas = self.esperas = 0
        self.url = "https://ava.univesp.br/mod/forum/view.php?id=1"

    def goto(self, url, **kwargs):
        self.idas += 1
        if self.idas <= self.quedas:
            raise PWError("net::ERR_TIMED_OUT")
        self.url = (
            "https://ava.univesp.br/custom/univesp_login.php"
            if self.login
            else url
        )

    def wait_for_timeout(self, ms):
        self.esperas += 1


pagina_ok = PaginaFake(quedas=1)
with contextlib.redirect_stdout(io.StringIO()):
    navegar_insistindo(pagina_ok, "http://x", tentativas=3, rotulo="Avisos")
checa(pagina_ok.idas == 2,
      "falha transitória é repetida e a segunda tentativa salva a leitura")

pagina_morta = PaginaFake(quedas=9)
saida = io.StringIO()
try:
    with contextlib.redirect_stdout(saida):
        navegar_insistindo(pagina_morta, "http://x", tentativas=3,
                           rotulo="Avisos")
except FalhaFonte:
    caiu = True
else:
    caiu = False
checa(caiu and pagina_morta.idas == 3,
      "falha persistente ainda falha, depois de esgotar as tentativas")
checa("Avisos" in saida.getvalue(),
      "o log diz qual página caiu, em vez de falhar em silêncio")

pagina_login = PaginaFake(quedas=0, login=True)
try:
    navegar_insistindo(pagina_login, "http://x", tentativas=3)
except SessaoExpirada:
    parou = True
except FalhaFonte:
    parou = False
checa(parou and pagina_login.idas == 1,
      "sessão expirada não é repetida: insistir não loga de novo")

print("\n== 'Conclua o Módulo X' morre quando o módulo acaba (09/08/2026) ==")


def curso_modulo(itens):
    """Aviso 'finalizar o Módulo 4 até hoje' + o módulo que ele cobra."""
    return {"code": "COM170", "modelo": "quinzenal", "id": 18922,
            "avisos": [{"autor": "formador", "url": "#a",
                        "autoridade": "institucional",
                        "prazos": [{"rotulo": "conclusão",
                                    "quando": "2026-08-04T23:59:00-03:00",
                                    "tipo": "fim", "hora_certa": True,
                                    "confianca": "alta",
                                    "frase": "finalizar o Módulo 4",
                                    "escopo": {"familia": "modulo",
                                               "numeros": [4], "txt": ""}}]}],
            "sections": [{"id": "m4", "title": "Módulo 4", "parent": None,
                          "fase": "regular", "locked": None, "items": itens}]}


def pagina(status):
    return {"cmid": "1", "label": "M4 - Videoaula", "type": "page",
            "status": status, "conta_nota": True, "aberto": True, "url": "#p"}


def quiz(status, tem_nota):
    return {"cmid": "2", "label": "M4 - Quiz", "type": "scorm",
            "status": status, "conta_nota": True, "aberto": True, "url": "#q",
            "tem_nota": tem_nota}


def cobra(itens):
    acoes = C.montar_acoes({"courses": [curso_modulo(itens)]},
                           HOJE_EV, agora=AGORA)[0]
    return [a for a in acoes if a["tipo"] == "obrigacao"]


checa(bool(cobra([pagina("Pendente"), quiz("Concluído", True)])),
      "com item pendente, a cobrança do módulo aparece")
checa(not cobra([pagina("Concluído"), quiz("Concluído", True)]),
      "módulo inteiro concluído para de ser cobrado")
# O selo do Moodle fecha por visualização: quiz "Concluído" sem nota e sem
# tentativa não é entrega, e silenciar por causa dele esconderia o dever.
checa(bool(cobra([pagina("Concluído"),
                  {**quiz("Concluído", None), "entrega_confirmada": False}])),
      "selo 'Concluído' sem prova de entrega não silencia a cobrança")
# Sem nada rastreado não há prova de conclusão, e falta de prova nunca pode
# virar "está tudo feito".
checa(bool(cobra([{"cmid": "3", "label": "M4 - Fórum", "type": "forum",
                   "status": None, "conta_nota": False, "aberto": True,
                   "url": "#f"}])),
      "seção sem item rastreado continua cobrada, por falta de evidência")

print("\n== Prazo da quinzena e cadeia de desbloqueio (Etapa 4) ==")

from dominio.prazos import casar_prazos, escopo_cobre  # noqa: E402
from dominio.dependencias import secao_do_predecessor  # noqa: E402

esc_q2 = {"familia": "modulo", "numeros": [4], "quinzena": 2, "txt": ""}
esc_sem = {"familia": "modulo", "numeros": [6, 7], "txt": ""}
checa(escopo_cobre(esc_q2, "Q2 Módulo 4") is True,
      "prazo da Quinzena 2 cobre a seção prefixada daquela quinzena")
checa(escopo_cobre(esc_q2, "Módulo 4") is False,
      "e não cobre o Módulo 4 da quinzena anterior, que já encerrou")
checa(escopo_cobre(esc_sem, "Módulo 6") is True,
      "escopo de aviso antigo continua casando com o título sem prefixo")
checa(escopo_cobre(esc_sem, "Q2 Módulo 6") is False,
      "e não invade a quinzena nova, que sequer abriu")

prazo_q2 = {"rotulo": "Prazo módulo 4", "quando": "2026-08-09T23:59:00-03:00",
            "tipo": "fim", "confianca": "alta", "escopo": esc_q2, "frase": ""}
checa([p["rotulo"] for p in casar_prazos("Q2 Módulo 4", [prazo_q2])]
      == ["Prazo módulo 4"],
      "o casamento entrega o prazo à seção certa")
checa(casar_prazos("Módulo 4", [prazo_q2]) == [],
      "a reserva por rótulo não atropela o escopo que já disse a quinzena")

titulos = ["Quinzena 1", "Módulo 3", "Quinzena 2", "Q2 Módulo 2", "Q2 Módulo 3"]
checa(secao_do_predecessor("Q2 M3 - Alucinação: o teste", titulos)
      == "Q2 Módulo 3",
      "o módulo vem do último marcador, não do prefixo da quinzena")
checa(secao_do_predecessor("M3 - Alucinação", titulos) == "Módulo 3",
      "rótulo sem prefixo continua achando a seção sem prefixo")

print("\n== Participação da COM170 (ativa.univesp.br) ==")

from fontes import participacao as PA  # noqa: E402

# Texto real da ferramenta, lido em 04/08/2026.
VISAO_REAL = ["Visão geral", "Meu progresso de participação",
 "Última atualização: 04/08/2026 às 18:07", "Quinzena atual",
 "Q1 - Resultado final", "Progresso muito avançado",
 "Todos os critérios previstos para esta quinzena foram identificados.",
 "Ver detalhes da Quinzena 1", "Panorama das sete quinzenas",
 "Q1", "Final", "Q2", "Ainda não iniciada", "Q3", "Ainda não iniciada"]
DETALHE_REAL = ["Q1", "Final", "Perfil temporal", "No prazo",
 "Cobertura de conteúdos", "atendido", "Regularidade de acesso", "atendido"]

v = PA._visao_geral(VISAO_REAL)
checa(v.get("atualizado_em") == "04/08/2026 às 18:07",
      "lê quando a própria ferramenta atualizou")
checa(v["quinzena_atual"]["progresso"] == "Progresso muito avançado",
      "lê o resultado da quinzena corrente")
checa([q["quinzena"] for q in v["quinzenas"]] == ["Q1", "Q2", "Q3"]
      and v["quinzenas"][1]["estado"] == "Ainda não iniciada",
      "lê o panorama das quinzenas sem confundir rótulo com estado")

d = PA._visao_geral(DETALHE_REAL)
checa(d["perfil_temporal"] == "No prazo",
      "lê o perfil temporal, que é o critério de distribuição")
checa([c["nome"] for c in d["criterios"]]
      == ["Cobertura de conteúdos", "Regularidade de acesso"],
      "lê os critérios com a situação de cada um")

checa(PA.item_de_participacao([{"items": [
        {"type": "lti", "label": "Meu Progresso de Participação",
         "url": "#p"}]}])["url"] == "#p",
      "acha o item de participação pelo rótulo")
checa(PA.item_de_participacao([{"items": [
        {"type": "lti", "label": "Live com facilitador", "url": "#l"}]}])
      is None,
      "não confunde com outro item de ferramenta externa")

html_p = R.render_participacao({"courses": [{"code": "COM170",
    "participacao": {**v, **d}}]})
checa("Progresso muito avançado" in html_p and "No prazo" in html_p,
      "o site mostra o resultado e o perfil temporal")
checa("Cobertura de conteúdos" in html_p,
      "e mostra os critérios um a um")
checa(R.render_participacao({"courses": [{"code": "X"}]}) == "",
      "disciplina sem a ferramenta não gera bloco")

# Texto real da ferramenta em 13/08/2026, copiado da página. Ela mudou duas
# coisas desde 04/08: desenha DOIS cartões "Quinzena atual" para a mesma
# quinzena (um com o resultado, outro vazio) e escreve "Critério atendido" no
# lugar de "atendido". As duas mudanças passaram pela suíte antiga e
# publicaram estado errado no site por dias.
VISAO_13_08 = ["Ir para o conteúdo principal", "Visão geral",
 "Meu progresso de participação",
 "Olá, Aluno. Acompanhe sua participação ao longo da disciplina.",
 "Última atualização: 12/08/2026 às 23:25",
 "Quinzena atual", "Q2 - Indicador provisório", "Progresso avançado",
 "Parte dos critérios previstos para esta quinzena foi identificada.",
 "Ver detalhes da Quinzena 2",
 "Quinzena atual", "Q2 - Ainda não iniciada",
 "Progresso ainda não identificado",
 "Esta quinzena ainda não foi iniciada.", "Ver detalhes da Quinzena 2",
 "Panorama das sete quinzenas",
 "Q2", "Provisório", "Q2", "Ainda não iniciada", "Q3", "Ainda não iniciada",
 "Q4", "Ainda não iniciada", "Q5", "Ainda não iniciada",
 "Q6", "Ainda não iniciada", "Q7", "Ainda não iniciada",
 "Resumo da trajetória", "0", "quinzenas concluídas",
 "1", "quinzena em andamento"]
CRITERIOS_13_08 = ["Resumo", "Critérios", "Perfil de participação",
 "Critérios detalhados",
 "Módulo 1", "Critério ainda não identificado",
 "Este critério ainda não foi identificado para esta quinzena.",
 "Módulo 2", "Critério atendido",
 "Foram identificadas interações acadêmicas relacionadas aos conteúdos e "
 "atividades do Módulo 2 durante a quinzena.",
 "Módulo 3", "Critério atendido",
 "Foram identificadas interações acadêmicas relacionadas aos conteúdos e "
 "atividades do Módulo 3 durante a quinzena.",
 "Módulo 4", "Critério atendido",
 "Foram identificadas interações acadêmicas relacionadas aos conteúdos e "
 "atividades do Módulo 4 durante a quinzena.",
 "Qualidade da participação", "Critério atendido",
 "Foram identificadas interações com os conteúdos previstos e uma "
 "distribuição das interações ao longo da quinzena."]

novo = PA._visao_geral(VISAO_13_08)
checa(novo["quinzena_atual"]["progresso"] == "Progresso avançado",
      "entre dois cartões 'Quinzena atual', fica com o que afirma algo")
checa("Ainda não iniciada" not in novo["quinzena_atual"]["rotulo"],
      "não publica 'ainda não iniciada' na quinzena que já está em curso")
checa([q["quinzena"] for q in novo["quinzenas"]]
      == ["Q2", "Q3", "Q4", "Q5", "Q6", "Q7"]
      and novo["quinzenas"][0]["estado"] == "Provisório",
      "o panorama não repete a quinzena nem perde o estado informativo")

crit = PA._visao_geral(CRITERIOS_13_08)
checa([c["nome"] for c in crit["criterios"]]
      == ["Módulo 1", "Módulo 2", "Módulo 3", "Módulo 4",
          "Qualidade da participação"],
      "lê os cinco critérios no formato 'Critério <estado>'")
checa([c["atendido"] for c in crit["criterios"]]
      == [False, True, True, True, True],
      "distingue critério atendido de critério ainda não identificado")
checa(PA._atendido("atendido") is True
      and PA._atendido("Critério atendido") is True,
      "o formato antigo continua sendo lido")
checa(PA._atendido("Critério parcialmente atendido") is None,
      "parcial não é atendido nem pendente")

pendentes = [c["nome"] for c in crit["criterios"] if c["atendido"] is False]
html_novo = R.render_participacao({"courses": [{"code": "COM170",
    "participacao": {**novo, **crit, "criterios_pendentes": pendentes}}]})
checa("Progresso avançado" in html_novo,
      "o site publica o progresso real, não o cartão vazio")
checa("Critério atendido" in html_novo and 'class="status ok"' in html_novo,
      "critério atendido sai marcado como atendido, não como pendente")
checa("Ainda não contaram" in html_novo and "Módulo 1" in html_novo,
      "o site nomeia o critério que ainda não contou")

print("\n== Vencimento não é carência ==")

import pipeline as P  # noqa: E402

semana2 = {"n": 2, "inicio": "2026-07-27",
           "vencimento": "2026-08-05T23:59:00-03:00",
           "carencia": "2026-08-09T23:59:00-03:00"}
crono = {"fonte": "x", "semanas": [semana2]}
checa(P._semana_do_cronograma(crono, 2) == semana2,
      "acha a semana do cronograma pelo número")
checa(P._semana_do_cronograma(crono, 5) is None,
      "semana que não existe no cronograma devolve nada")
checa(P._mesma_data("2026-08-09T23:59:00-03:00", semana2) is True,
      "data do calendário do AVA igual à carência é reconhecida")
checa(P._mesma_data("2026-08-05T23:59:00-03:00", semana2) is False,
      "data que bate com o vencimento não é confundida com carência")
checa(P._mesma_data("2026-08-09T23:59:00-03:00", None) is False,
      "sem cronograma não há o que reconciliar")

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
# A espera de 3 minutos falhou em 13/08 com um deploy de 187s, e ao desistir
# o passo seguinte empurrava outro commit, cancelando o deploy que estava
# quase pronto. A margem tem que ficar acima do pior caso já visto.
_espera = _re.search(r"for TENTATIVA in \$\(seq 1 (\d+)\)", workflow)
checa(_espera and int(_espera.group(1)) * 5 >= 420,
      "a espera do Pages cobre pelo menos 7 minutos")


print("\n" + "=" * 66)
if falhas:
    print(f"{falhas} teste(s) operacional(is) falharam.")
    raise SystemExit(1)
print("Todos os testes operacionais passaram.")
