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
# A ferramenta escreve a situação de duas formas. Em 04/08/2026 era só o
# estado ("atendido"); em 13/08/2026 passou a vir com o substantivo na frente
# ("Critério atendido", "Critério ainda não identificado"). Casar só a forma
# antiga fazia a lista de critérios sair vazia, e foi o que aconteceu: o site
# publicou o bloco de participação sem nenhum critério por vários dias.
ESTADOS_CRITERIO = (
    "atendido",
    "nao atendido",
    "parcialmente atendido",
    "parcial",
    "ainda nao identificado",
    "nao identificado",
)
# Estados que não afirmam nada. Servem para dois descartes: escolher entre
# blocos concorrentes de "Quinzena atual" e desempatar o panorama.
SEM_INFORMACAO = ("ainda nao iniciada", "nao identificado", "nao iniciada")

RE_ATUALIZADO = re.compile(
    r"[Úu]ltima atualiza[çc][ãa]o:\s*([\d/]{8,10}\s*(?:às|as)\s*[\d:]{4,5})"
)
RE_PANORAMA = re.compile(r"^Q(\d)$")
RE_RESUMO = re.compile(r"^(\d+)$")


def _situacao_de_criterio(linha):
    """Devolve o estado do critério, ou ``None`` se a linha não for um."""
    texto = sem_acento(linha or "").strip()
    nucleo = texto[9:].strip() if texto.startswith("criterio ") else texto
    return nucleo if nucleo in ESTADOS_CRITERIO else None


def _atendido(situacao):
    """``True``/``False``/``None`` a partir do texto da situação.

    ``None`` é para o parcial, que não é um nem outro. "Ainda não
    identificado" é ``False`` de propósito: do ponto de vista dele, critério
    que a ferramenta não enxergou é ponto que não está contando.
    """
    nucleo = _situacao_de_criterio(situacao)
    if nucleo is None:
        return None
    if nucleo == "atendido":
        return True
    if nucleo.startswith("parcial"):
        return None
    return False


def _sem_informacao(texto):
    junto = sem_acento(texto or "")
    return any(marca in junto for marca in SEM_INFORMACAO)


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


def _escolher_quinzena_atual(blocos):
    """Entre blocos concorrentes, o que afirma alguma coisa.

    Achado em 13/08/2026: a ferramenta desenha **dois** cartões "Quinzena
    atual" para a mesma quinzena, um com o resultado provisório de verdade
    ("Q2 - Indicador provisório · Progresso avançado") e outro sem nada
    ("Q2 - Ainda não iniciada"). Ficar com o último, que era o que o parser
    fazia, publicava "esta quinzena ainda não foi iniciada" no dia em que a
    própria ferramenta dizia progresso avançado, com quatro dos cinco
    critérios atendidos. Mesma família do defeito do boletim: o número certo
    estava na tela, e o guia escolheu a linha errada.
    """
    informativos = [
        bloco
        for bloco in blocos
        if not _sem_informacao(
            " ".join(
                filter(
                    None,
                    (
                        bloco.get("rotulo"),
                        bloco.get("progresso"),
                        bloco.get("detalhe"),
                    ),
                )
            )
        )
    ]
    escolhidos = informativos or blocos
    return escolhidos[0] if escolhidos else None


def _acrescentar_ao_panorama(panorama, quinzena, estado):
    """Uma linha por quinzena, ficando com o estado que diz alguma coisa."""
    for registro in panorama:
        if registro["quinzena"] != quinzena:
            continue
        if _sem_informacao(registro["estado"]) and not _sem_informacao(estado):
            registro["estado"] = estado
        return
    panorama.append({"quinzena": quinzena, "estado": estado})


def _visao_geral(linhas):
    texto = "\n".join(linhas)
    dados = {"quinzenas": [], "criterios": []}
    achado = RE_ATUALIZADO.search(texto)
    if achado:
        dados["atualizado_em"] = achado.group(1)
    blocos_atuais = []
    for indice, linha in enumerate(linhas):
        if linha == "Quinzena atual" and indice + 3 < len(linhas):
            blocos_atuais.append({
                "rotulo": linhas[indice + 1],
                "progresso": linhas[indice + 2],
                "detalhe": linhas[indice + 3],
            })
        # No panorama, o rótulo da quinzena vem numa linha e o estado na
        # seguinte: "Q1" / "Final", "Q2" / "Ainda não iniciada".
        if RE_PANORAMA.match(linha) and indice + 1 < len(linhas):
            estado = linhas[indice + 1]
            if not RE_PANORAMA.match(estado):
                _acrescentar_ao_panorama(dados["quinzenas"], linha, estado)
        if linha == "Perfil temporal" and indice + 1 < len(linhas):
            dados["perfil_temporal"] = linhas[indice + 1]
        situacao = _situacao_de_criterio(linha)
        if situacao is not None and indice > 0:
            nome = linhas[indice - 1]
            if 3 < len(nome) <= 60 and _situacao_de_criterio(nome) is None:
                dados["criterios"].append({
                    "nome": nome,
                    "situacao": linha,
                    "atendido": _atendido(linha),
                })
    atual = _escolher_quinzena_atual(blocos_atuais)
    if atual:
        dados["quinzena_atual"] = atual
    return dados


def _clicar(pagina, rotulo, espera_ms=1500):
    """Clique tolerante: devolve ``True`` se abriu, ``False`` se não achou."""
    try:
        pagina.get_by_text(rotulo, exact=True).first.click(timeout=8000)
    except PlaywrightError:
        return False
    pagina.wait_for_timeout(espera_ms)
    return True


def ler(page, secoes):
    item = item_de_participacao(secoes)
    if not item:
        return None
    pagina = _abrir(page, item["url"])
    try:
        dados = _visao_geral(_linhas(pagina))
        # São dois cliques, não um. "Quinzenas" abre a quinzena corrente, mas
        # os critérios um a um vivem na aba "Critérios" dentro dela — sem o
        # segundo clique a lista nunca aparece, que era o estado até 13/08.
        # Cada etapa é opcional: o que já foi lido continua valendo se o
        # clique seguinte falhar.
        if _clicar(pagina, "Quinzenas", espera_ms=2000):
            detalhe = _visao_geral(_linhas(pagina))
            dados.setdefault("perfil_temporal", detalhe.get("perfil_temporal"))
            if _clicar(pagina, "Critérios"):
                detalhe = _visao_geral(_linhas(pagina))
            if detalhe.get("criterios"):
                dados["criterios"] = detalhe["criterios"]
        dados["criterios_pendentes"] = [
            criterio["nome"]
            for criterio in dados.get("criterios") or []
            if criterio.get("atendido") is False
        ]
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
