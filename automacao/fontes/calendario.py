# -*- coding: utf-8 -*-
"""Calendário do Moodle por API e DOM."""
import re
from datetime import datetime, timedelta, timezone

from playwright.sync_api import Error as PlaywrightError

from configuracao import AVA, BR_TZ
from fontes.moodle import api_opcional
from modelos import SourceResult

JS_EVENTOS_LISTA = """
() => [...document.querySelectorAll('.event[data-event-id]')].map(e => {
  const link = e.querySelector('a[href*="/mod/"]');
  const hora = ((e.innerText || '').match(/\\d{1,2}:\\d{2}/) || [null])[0];
  return {
    id: e.getAttribute('data-event-id'),
    curso_id: e.getAttribute('data-course-id'),
    titulo: e.getAttribute('data-event-title'),
    tipo: e.getAttribute('data-event-eventtype'),
    url: link ? link.href : null,
    hora: hora,
  };
})
"""
JS_EVENTOS_MES = """
() => {
  const saida = [];
  document.querySelectorAll('td[data-day-timestamp]').forEach(td => {
    const ts = parseInt(td.getAttribute('data-day-timestamp'), 10);
    if (!ts) return;
    td.querySelectorAll('[data-event-id]').forEach(e => {
      saida.push({ id: e.getAttribute('data-event-id'), dia_ts: ts });
    });
  });
  return saida;
}
"""


def cmid_de(url):
    encontrado = re.search(r"id=(\d+)", url or "")
    return encontrado.group(1) if encontrado else ""


def ler_api(page):
    agora = int(datetime.now(timezone.utc).timestamp())
    dados = api_opcional(
        page,
        "core_calendar_get_action_events_by_timesort",
        {
            "timesortfrom": agora - 86400 * 60,
            "timesortto": agora + 86400 * 240,
            "limitnum": 50,
        },
    )
    if dados is None:
        return [], False
    eventos = []
    for evento in (dados or {}).get("events", []) or []:
        if not evento.get("timesort"):
            continue
        curso = evento.get("course") or {}
        eventos.append(
            {
                "nome": evento.get("name"),
                "quando": datetime.fromtimestamp(
                    evento["timesort"], BR_TZ
                ).isoformat(),
                "curso_id": str(curso.get("id") or ""),
                "curso": curso.get("shortname"),
                "atividade": evento.get("activityname"),
                "url": evento.get("url"),
                "acao": (evento.get("action") or {}).get("name"),
                "cmid": cmid_de(evento.get("url")),
            }
        )
    return eventos, True


def ler_dom(page, hoje):
    por_id = {}
    leituras_ok = 0
    try:
        page.goto(
            f"{AVA}/calendar/view.php?view=upcoming&lookahead=365",
            wait_until="domcontentloaded",
            timeout=45000,
        )
        page.wait_for_timeout(1500)
        for evento in page.evaluate(JS_EVENTOS_LISTA):
            if evento.get("id"):
                por_id[evento["id"]] = evento
        leituras_ok += 1
    except PlaywrightError as erro:
        print(
            f"  aviso: lista de eventos falhou ({type(erro).__name__})"
        )

    base = datetime(hoje.year, hoje.month, 15, 12, 0, tzinfo=BR_TZ)
    for salto in range(-1, 5):
        alvo = base + timedelta(days=31 * salto)
        try:
            page.goto(
                f"{AVA}/calendar/view.php?view=month&time={int(alvo.timestamp())}",
                wait_until="domcontentloaded",
                timeout=45000,
            )
            page.wait_for_timeout(900)
            for evento in page.evaluate(JS_EVENTOS_MES):
                destino = por_id.setdefault(
                    evento["id"], {"id": evento["id"]}
                )
                destino["dia"] = datetime.fromtimestamp(
                    evento["dia_ts"], BR_TZ
                ).date()
            leituras_ok += 1
        except PlaywrightError:
            continue

    eventos = []
    for evento in por_id.values():
        if not evento.get("dia"):
            continue
        hora, minuto = 23, 59
        if evento.get("hora"):
            try:
                hora, minuto = [
                    int(valor) for valor in evento["hora"].split(":")
                ]
            except ValueError:
                pass
        dia = evento["dia"]
        eventos.append(
            {
                "nome": evento.get("titulo"),
                "quando": datetime(
                    dia.year,
                    dia.month,
                    dia.day,
                    hora,
                    minuto,
                    tzinfo=BR_TZ,
                ).isoformat(),
                "curso_id": str(evento.get("curso_id") or ""),
                "curso": None,
                "atividade": evento.get("titulo"),
                "url": evento.get("url"),
                "acao": None,
                "cmid": cmid_de(evento.get("url")),
            }
        )
    return eventos, leituras_ok > 0


def ler(page, hoje, diagnostico=None):
    eventos, api_ok = ler_api(page)
    if eventos:
        print(f"  calendario pela API: {len(eventos)} evento(s)")
        if diagnostico is not None:
            diagnostico.update(
                {"status": "live", "via": "api", "eventos": len(eventos)}
            )
        return eventos
    eventos, dom_ok = ler_dom(page, hoje)
    print(f"  calendario pela pagina: {len(eventos)} evento(s)")
    if diagnostico is not None:
        diagnostico.update(
            {
                "status": (
                    "live"
                    if eventos
                    else "vazio_confirmado"
                    if api_ok or dom_ok
                    else "falhou"
                ),
                "via": "dom" if dom_ok else "nenhuma",
                "eventos": len(eventos),
            }
        )
    return eventos


def resultado(page, hoje, checked_at, cache=None):
    diagnostico = {}
    eventos = ler(page, hoje, diagnostico)
    status = diagnostico.get("status", "falhou")
    if status == "falhou" and cache:
        return SourceResult(
            status="falhou",
            dados=list(cache),
            problemas=["calendário indisponível; mantive o último resultado"],
            checked_at=checked_at,
            from_cache=True,
            quantidade_atual=len(cache),
            detalhes=diagnostico,
        )
    return SourceResult(
        status=status,
        dados=eventos,
        checked_at=checked_at,
        quantidade_atual=len(eventos),
        last_live_at=checked_at if status in ("live", "vazio_confirmado") else None,
        detalhes=diagnostico,
    )
