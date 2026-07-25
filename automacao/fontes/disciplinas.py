# -*- coding: utf-8 -*-
"""Descoberta de disciplinas e leitura estrutural de cursos/seções."""
import re

from playwright.sync_api import Error as PlaywrightError

from configuracao import AVA
from dominio.datas import sem_acento
from fontes.moodle import FalhaFonte, deslogado, navegar

JS_MEUS_CURSOS = """
() => {
  const vistos = {};
  document.querySelectorAll('a[href*="/course/view.php?id="]').forEach(a => {
    const m = a.href.match(/id=(\\d+)/);
    if (!m) return;
    const nome = (a.innerText || '').trim();
    if (!nome || nome.length < 4) return;
    const card = a.closest('[data-region="course-content"], .card, li, .course-listitem') || a.parentElement;
    const prog = card ? card.querySelector('[role="progressbar"], .progress-bar') : null;
    const pct = prog ? (prog.getAttribute('aria-valuenow') || '').trim() : null;
    if (!vistos[m[1]] || (pct && !vistos[m[1]].pct)) {
      vistos[m[1]] = { id: m[1], nome: nome, pct: pct ? parseInt(pct, 10) : null };
    }
  });
  return Object.values(vistos);
}
"""

JS_CURSO = """
() => {
  const limpa = (t) => (t || '').replace(/^(Contrair|Expandir)\\s*/, '').split('\\n')[0].trim();
  const secoes = [...document.querySelectorAll('li.section, li.course-section')].map(s => {
    const own = [...s.querySelectorAll('li.activity')]
      .filter(a => a.closest('li.section, li.course-section') === s);
    const nameEl = s.querySelector('h3 .sectionname, .sectionname');
    const avail = s.querySelector('.availabilityinfo, .section_availability');
    const resumo = s.querySelector('.section_summary, .summarytext, .course-description-item');
    return {
      id: s.id,
      title: limpa(nameEl ? nameEl.innerText : ''),
      parent: (s.parentElement.closest('li.section, li.course-section') || {}).id || null,
      locked: avail ? avail.innerText.trim() : null,
      theme: resumo ? resumo.innerText.replace(/^Tema:\\s*/, '').trim().slice(0, 200) : null,
      items: own.map(a => {
        const m = a.className.match(/modtype_(\\w+)/);
        const link = a.querySelector('a.aalink, a.stretched-link, .activity-instance a');
        const compl = a.querySelector('.activity-completion');
        const nameNode = a.querySelector('[data-activityname]');
        const badge = a.querySelector('.badge, .unread');
        return {
          cmid: a.getAttribute('data-id'),
          label: nameNode ? nameNode.getAttribute('data-activityname') : null,
          type: m ? m[1] : null,
          url: link ? link.href : null,
          // O Moodle passou a colar o balão de ajuda dentro deste bloco, e o
          // texto virava "Concluído\\n...Você deve...Feito:...Ver M1 - ...".
          // Como o status era comparado por igualdade, TODO item concluído
          // voltava a aparecer como pendente. Ficamos só com a primeira linha.
          status: compl
            ? (compl.innerText.split('\\n').map(t => t.trim()).filter(Boolean)[0] || null)
            : null,
          nao_lidas: badge ? (badge.innerText.match(/\\d+/) || [null])[0] : null,
        };
      }).filter(x => x.label && x.type !== 'subsection'),
    };
  }).filter(s => s.title);
  const links = {};
  document.querySelectorAll('a[href*="planos-de-ensino"]').forEach(a => links.plano_ensino = a.href);
  document.querySelectorAll('a[href*="cronograma"]').forEach(a => links.cronograma = a.href);
  return { secoes, links };
}
"""


def limpar_bloqueio(texto):
    if not texto:
        return None
    limpo = re.sub(
        r"\b(Mostrar mais|Mostrar menos|Show more|Show less)\b", " ", texto
    )
    limpo = re.sub(r"\s+", " ", limpo).strip(" .…")
    return limpo or None


def descobrir(page):
    navegar(
        page,
        f"{AVA}/my/courses.php",
        timeout=60000,
        espera_ms=1500,
    )
    try:
        return page.evaluate(JS_MEUS_CURSOS)
    except PlaywrightError as erro:
        raise FalhaFonte(
            f"não consegui interpretar Meus cursos ({type(erro).__name__})"
        ) from erro


def ler_curso(page, curso):
    url = f"{AVA}/course/view.php?id={curso['id']}"
    navegar(page, url, timeout=60000, espera_ms=1500)
    if deslogado(page):
        raise FalhaFonte(f"sessão expirou ao abrir {curso.get('nome')}")
    try:
        bruto = page.evaluate(JS_CURSO)
    except PlaywrightError as erro:
        raise FalhaFonte(
            f"não consegui interpretar {curso.get('nome')} "
            f"({type(erro).__name__})"
        ) from erro
    secoes = bruto.get("secoes") or []
    for secao in secoes:
        secao["locked"] = limpar_bloqueio(secao.get("locked"))
    return secoes, bruto.get("links") or {}


def codigo_de(curso):
    encontrado = re.search(r"\b([A-Z]{3}\d{3})\b", curso["nome"])
    return encontrado.group(1) if encontrado else curso["nome"][:12]


def modelo_de(secoes):
    return (
        "quinzenal"
        if any(
            sem_acento(secao["title"]).startswith("quinzena")
            for secao in secoes
        )
        else "regular"
    )


def marcar_fases(secoes):
    por_id = {secao["id"]: secao for secao in secoes}

    def em_aia(secao):
        atual, nivel = secao, 0
        while atual and nivel < 6:
            if sem_acento(atual["title"]).startswith("aia"):
                return True
            atual = por_id.get(atual.get("parent"))
            nivel += 1
        return False

    for secao in secoes:
        secao["fase"] = "AIA" if em_aia(secao) else "regular"
    return secoes
