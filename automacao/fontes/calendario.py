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
# Eventos que o aluno já cumpriu (ou que não são atividade, como uma live de
# tira-dúvidas marcada pelo facilitador) não voltam pela API de "ações
# pendentes". Só aparecem no DOM. Por isso as duas fontes são somadas, e não
# uma usada como reserva da outra.
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
                "tipo": evento.get("eventtype"),
                "via": "api",
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
                "tipo": evento.get("tipo"),
                "via": "dom",
            }
        )
    return eventos, leituras_ok > 0


def _chave(evento):
    return (
        str(evento.get("cmid") or "").strip()
        or (evento.get("nome") or "").strip().lower(),
        (evento.get("quando") or "")[:16],
    )


def unir(da_api, do_dom):
    """Soma as duas leituras sem duplicar o mesmo evento.

    A API vence em caso de empate porque traz o nome curto do curso; o DOM
    entra com tudo que a API não devolve (evento de curso, atividade já
    concluída).
    """
    unidos = {}
    for evento in list(da_api) + list(do_dom):
        chave = _chave(evento)
        if chave in unidos:
            for campo, valor in evento.items():
                if valor and not unidos[chave].get(campo):
                    unidos[chave][campo] = valor
            continue
        unidos[chave] = dict(evento)
    return sorted(unidos.values(), key=lambda e: e.get("quando") or "")


def ler(page, hoje, diagnostico=None):
    da_api, api_ok = ler_api(page)
    do_dom, dom_ok = ler_dom(page, hoje)
    eventos = unir(da_api, do_dom)
    print(
        f"  calendario: {len(da_api)} pela API + {len(do_dom)} pela pagina "
        f"= {len(eventos)} evento(s)"
    )
    if diagnostico is not None:
        via = "api+dom" if (api_ok and dom_ok) else "api" if api_ok else "dom"
        diagnostico.update(
            {
                "status": (
                    "live"
                    if eventos
                    else "vazio_confirmado"
                    if api_ok or dom_ok
                    else "falhou"
                ),
                "via": via if (api_ok or dom_ok) else "nenhuma",
                "eventos": len(eventos),
                "api": len(da_api),
                "dom": len(do_dom),
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
