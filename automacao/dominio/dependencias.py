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


MARCADOR_RE = re.compile(r"\b([A-Za-zÀ-ÿ])\s*0*(\d+)\b")
PREFIXO_RE = re.compile(r"^\s*([A-Za-zÀ-ÿ])\s*0*(\d+)\s+")


def secao_do_predecessor(predecessor, titulos):
    """De "Q2 M3 - Alucinação..." para a seção "Q2 Módulo 3".

    A partir da Quinzena 2 tudo ganhou prefixo, e o rótulo do item traz dois
    marcadores: a quinzena e o módulo. Lendo o primeiro, "Q2 M3" virava
    "quinzena 2" e a cadeia de desbloqueio parava no lugar errado. Quem
    identifica o módulo é o último marcador; o primeiro, quando existe, diz
    em qual quinzena procurar.
    """
    cabeca = (predecessor or "").split(" - ")[0]
    marcadores = MARCADOR_RE.findall(cabeca)
    if not marcadores:
        return None
    inicial = sem_acento(marcadores[-1][0])[:1]
    numero = int(marcadores[-1][1])
    prefixo = marcadores[0] if len(marcadores) > 1 else None
    for titulo in titulos:
        alvo = titulo or ""
        if prefixo:
            achado = PREFIXO_RE.match(alvo)
            if not achado:
                continue
            mesma_letra = (
                sem_acento(achado.group(1))[:1] == sem_acento(prefixo[0])[:1]
            )
            if not (mesma_letra and int(achado.group(2)) == int(prefixo[1])):
                continue
            alvo = alvo[achado.end():]
        elif PREFIXO_RE.match(alvo):
            # Predecessor sem prefixo não aponta para seção de outra quinzena.
            continue
        secao = FAMILIA_RE.match(alvo)
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
