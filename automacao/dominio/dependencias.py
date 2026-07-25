# -*- coding: utf-8 -*-
"""Cadeias de desbloqueio e propagação de prioridade, nunca de prazo."""
import re

from dominio.datas import sem_acento

FAMILIA_RE = re.compile(r"(\D+?)\s*(\d+)\s*$")
PREDECESSOR_RE = re.compile(
    r"atividade\s+(.+?)\s+(?:esteja|estiver|for|seja)\b", re.IGNORECASE
)


def predecessor_de(bloqueio):
    if not bloqueio:
        return None
    encontrado = PREDECESSOR_RE.search(bloqueio)
    return encontrado.group(1).strip(" .:-") if encontrado else None


def secao_do_predecessor(predecessor, titulos):
    encontrado = re.match(
        r"\s*([A-Za-zÀ-ÿ]{1,12})\s*0*(\d+)", predecessor or ""
    )
    if not encontrado:
        return None
    inicial = sem_acento(encontrado.group(1))[:1]
    numero = int(encontrado.group(2))
    for titulo in titulos:
        secao = FAMILIA_RE.match(titulo or "")
        if (
            secao
            and int(secao.group(2)) == numero
            and sem_acento(secao.group(1))[:1] == inicial
        ):
            return titulo
    return None


def propagar_urgencia(acoes, dados, hoje):
    from dominio.acoes import urgencia_de

    por_curso = {}
    for acao in acoes:
        por_curso.setdefault(acao["curso"], []).append(acao)

    for curso in dados["courses"]:
        lista = por_curso.get(curso["code"], [])
        if not lista:
            continue
        trava_de = {}
        for secao in curso["sections"]:
            predecessor = predecessor_de(secao.get("locked"))
            if predecessor:
                trava_de[secao["title"]] = predecessor
        if not trava_de:
            continue
        por_label = {sem_acento(acao["o_que"]): acao for acao in lista}
        titulos = [secao["title"] for secao in curso["sections"]]
        for alvo in sorted(
            [acao for acao in lista if acao.get("prazo")],
            key=lambda acao: acao["prazo"],
        ):
            titulo_secao = alvo.get("secao")
            visitados = set()
            prazo = alvo["prazo"]
            while (
                titulo_secao
                and titulo_secao in trava_de
                and titulo_secao not in visitados
            ):
                visitados.add(titulo_secao)
                predecessor = trava_de[titulo_secao]
                anterior = por_label.get(sem_acento(predecessor))
                if anterior:
                    if not anterior.get("prazo") and not anterior.get(
                        "prioridade_ate"
                    ):
                        urgencia, _ = urgencia_de(prazo, hoje)
                        anterior["prioridade_ate"] = prazo
                        anterior["urgencia"] = urgencia
                        anterior["prazo_txt"] = ""
                        anterior["destrava"] = alvo.get("secao")
                        anterior["destrava_em"] = prazo
                    break
                titulo_secao = secao_do_predecessor(predecessor, titulos)
    return acoes
