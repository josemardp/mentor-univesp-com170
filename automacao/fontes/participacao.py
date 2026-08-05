# -*- coding: utf-8 -*-
"""Progresso de participação da COM170, fora do Moodle.

A nota da disciplina tem dois componentes: participação na fase de estudos no
AVA e desempenho nas atividades presenciais. Quem calcula a participação não é
o Moodle, é uma ferramenta própria da Univesp em ``ativa.univesp.br``, aberta
pelo item "Meu Progresso de Participação". Ela usa cinco critérios de mesmo
peso por quinzena (conclusão dos Módulos 1 a 4 e qualidade da participação), e
a qualidade considera **a distribuição das interações ao longo da quinzena**.

Ou seja: existe um placar oficial dizendo se a participação está sendo
construída, e o guia não o lia. Um aluno pode entregar tudo no último dia e
perder ponto sem nunca ver o motivo.

A ferramenta abre numa aba nova (lançamento LTI), então a leitura precisa
capturar a página que nasce, não a que foi navegada.
"""
import re

from playwright.sync_api import Error as PlaywrightError

from dominio.datas import sem_acento
from modelos import SourceResult

ROTULO_ITEM = re.compile(r"progresso de participacao")
ESTADOS_CRITERIO = ("atendido", "nao atendido", "parcialmente atendido", "parcial")

RE_ATUALIZADO = re.compile(
    r"[Úu]ltima atualiza[çc][ãa]o:\s*([\d/]{8,10}\s*(?:às|as)\s*[\d:]{4,5})"
)
RE_PANORAMA = re.compile(r"^Q(\d)$")
RE_RESUMO = re.compile(r"^(\d+)$")


def item_de_participacao(secoes):
    for secao in secoes:
        for item in secao.get("items") or []:
            if item.get("type") != "lti" or not item.get("url"):
                continue
            if ROTULO_ITEM.search(sem_acento(item.get("label") or "")):
                return item
    return None


def _abrir(page, url):
    """Segue o lançamento LTI até a página externa que ele abre."""
    contexto = page.context
    try:
        with contexto.expect_page(timeout=30000) as espera:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
        nova = espera.value
    except PlaywrightError:
        # Algumas execuções reaproveitam uma aba já aberta em vez de criar
        # outra. Nesse caso a página existe, só não nasceu agora.
        nova = next(
            (p for p in contexto.pages if "ativa.univesp.br" in p.url), None
        )
        if nova is None:
            raise
    nova.wait_for_load_state("domcontentloaded", timeout=30000)
    nova.wait_for_timeout(2500)
    return nova


def _linhas(pagina):
    bruto = pagina.locator("body").inner_text()
    return [linha.strip() for linha in bruto.split("\n") if linha.strip()]


def _visao_geral(linhas):
    texto = "\n".join(linhas)
    dados = {"quinzenas": [], "criterios": []}
    achado = RE_ATUALIZADO.search(texto)
    if achado:
        dados["atualizado_em"] = achado.group(1)
    for indice, linha in enumerate(linhas):
        if linha == "Quinzena atual" and indice + 3 < len(linhas):
            dados["quinzena_atual"] = {
                "rotulo": linhas[indice + 1],
                "progresso": linhas[indice + 2],
                "detalhe": linhas[indice + 3],
            }
        # No panorama, o rótulo da quinzena vem numa linha e o estado na
        # seguinte: "Q1" / "Final", "Q2" / "Ainda não iniciada".
        if RE_PANORAMA.match(linha) and indice + 1 < len(linhas):
            estado = linhas[indice + 1]
            if not RE_PANORAMA.match(estado):
                dados["quinzenas"].append(
                    {"quinzena": linha, "estado": estado}
                )
        if linha == "Perfil temporal" and indice + 1 < len(linhas):
            dados["perfil_temporal"] = linhas[indice + 1]
        if sem_acento(linha) in ESTADOS_CRITERIO and indice > 0:
            nome = linhas[indice - 1]
            if 3 < len(nome) <= 60 and sem_acento(nome) not in ESTADOS_CRITERIO:
                dados["criterios"].append(
                    {"nome": nome, "situacao": linha}
                )
    return dados


def ler(page, secoes):
    item = item_de_participacao(secoes)
    if not item:
        return None
    pagina = _abrir(page, item["url"])
    try:
        dados = _visao_geral(_linhas(pagina))
        # A aba "Quinzenas" traz os critérios um a um. Se o clique falhar, a
        # visão geral já é útil sozinha, então a falha não derruba a leitura.
        try:
            pagina.get_by_text("Quinzenas", exact=True).first.click(
                timeout=8000
            )
            pagina.wait_for_timeout(2000)
            detalhe = _visao_geral(_linhas(pagina))
            if detalhe.get("criterios"):
                dados["criterios"] = detalhe["criterios"]
            dados.setdefault("perfil_temporal", detalhe.get("perfil_temporal"))
        except PlaywrightError:
            pass
        dados["fonte"] = pagina.url
        return dados
    finally:
        try:
            pagina.close()
        except PlaywrightError:
            pass


def resultado(page, secoes, checked_at, cache=None):
    try:
        dados = ler(page, secoes)
    except PlaywrightError as erro:
        return SourceResult(
            status="falhou",
            dados=cache,
            problemas=[
                f"progresso de participação não abriu ({type(erro).__name__})"
            ],
            checked_at=checked_at,
            from_cache=cache is not None,
            quantidade_atual=1 if cache else 0,
        )
    if dados is None:
        return SourceResult(
            status="nao_aplicavel",
            dados=None,
            checked_at=checked_at,
            quantidade_atual=0,
        )
    return SourceResult(
        status="live",
        dados=dados,
        checked_at=checked_at,
        last_live_at=checked_at,
        quantidade_atual=len(dados.get("quinzenas") or []) or 1,
    )
