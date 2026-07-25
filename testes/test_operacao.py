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
        "foruns": {"status": "parcial", "last_live_at": agora},
    },
})
checa("não consegui reler agora: fóruns" in fontes_html and "degraded" in fontes_html,
      "fonte parcial fica visível no site")

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
