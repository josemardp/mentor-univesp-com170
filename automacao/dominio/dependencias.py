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
        por_id = {secao.get("id"): secao for secao in curso["sections"]}
        # Portões da unidade: quando o prazo é da seção-mãe e as travas ficam
        # nas filhas. Em 19/08/2026 o COM170 cobrava "Quinzena 3 · Prazo
        # módulos 1 a 4, vence 23/08" — com a página avisando que quem passa
        # da data fica fora do trabalho em grupo — enquanto os dois quizzes do
        # Módulo 1 apareciam em "sem prazo definido". O AVA escreve na tela
        # que o Módulo 2 só abre com "Q3 M1 - Atividade: Da manchete à
        # competência" concluída, e a caminhada só andava quando o item com
        # prazo estava *dentro* da cadeia travada, nunca acima dela.
        portoes_da_secao = {}
        for secao in curso["sections"]:
            predecessor = predecessor_de(secao.get("locked"))
            if not predecessor:
                continue
            trava_de[secao["title"]] = predecessor
            mae = por_id.get(secao.get("parent"))
            if mae:
                portoes_da_secao.setdefault(mae["title"], []).append(
                    (predecessor, secao["title"])
                )
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
            for predecessor, travada in portoes_da_secao.get(titulo_secao, []):
                # Só o portão que ainda está na fila sobe. Os módulos
                # seguintes estão trancados e nem foram coletados, então na
                # prática sobe um: o que está barrando agora.
                _promover(por_label.get(sem_acento(predecessor)), prazo,
                          travada, hoje, urgencia_de)
            # E quando o próprio prazo diz quais módulos ele cobra ("Prazo
            # módulos 1 a 4"), o que está pendente dentro deles sobe junto.
            # O portão resolve o primeiro; o irmão dele ficava embaixo, em
            # "sem prazo definido", com a mesma data em cima.
            for filha in _modulos_cobrados(
                alvo, por_id.get(_id_da_secao(curso, titulo_secao)), curso
            ):
                for acao in lista:
                    if acao.get("secao") == filha:
                        _promover(acao, prazo, None, hoje, urgencia_de,
                                  cobrado_por=alvo.get("o_que"))
            while (
                titulo_secao
                and titulo_secao in trava_de
                and titulo_secao not in visitados
            ):
                visitados.add(titulo_secao)
                predecessor = trava_de[titulo_secao]
                anterior = por_label.get(sem_acento(predecessor))
                if anterior:
                    _promover(anterior, prazo, alvo.get("secao"), hoje,
                              urgencia_de)
                    break
                titulo_secao = secao_do_predecessor(predecessor, titulos)
    return acoes


FAIXA_DE_MODULOS_RE = re.compile(
    r"m[óo]dulos?\s+(\d+)\s*(?:a|at[ée]|e)\s*(\d+)", re.IGNORECASE
)
MODULO_UNICO_RE = re.compile(r"m[óo]dulo\s+(\d+)", re.IGNORECASE)


def _id_da_secao(curso, titulo):
    for secao in curso.get("sections") or []:
        if secao.get("title") == titulo:
            return secao.get("id")
    return None


def _modulos_cobrados(alvo, mae, curso):
    """Seções-filhas que o próprio prazo nomeia.

    O rótulo vem da página: "Quinzena 3 · Prazo módulos 1 a 4" é a tradução
    de "23 de agosto, domingo, às 23h59. É a data em que os Módulos 1, 2, 3 e
    4 precisam estar concluídos". Sem faixa escrita não há nada a cobrar: os
    Módulos 5 e 6 da mesma quinzena respondem ao prazo de entrega, e herdar a
    data errada seria pior do que deixar o item sem prazo.
    """
    if not mae:
        return []
    rotulo = alvo.get("o_que") or ""
    faixa = FAIXA_DE_MODULOS_RE.search(rotulo)
    if faixa:
        primeiro, ultimo = int(faixa.group(1)), int(faixa.group(2))
    else:
        unico = MODULO_UNICO_RE.search(rotulo)
        if not unico:
            return []
        primeiro = ultimo = int(unico.group(1))
    if primeiro > ultimo:
        return []
    saida = []
    for secao in curso.get("sections") or []:
        if secao.get("parent") != mae.get("id"):
            continue
        titulo = secao.get("title") or ""
        achado = PREFIXO_RE.match(titulo)
        resto = titulo[achado.end():] if achado else titulo
        familia = FAMILIA_RE.match(resto)
        if not familia or sem_acento(familia.group(1)).strip()[:6] != "modulo":
            continue
        if primeiro <= int(familia.group(2)) <= ultimo:
            saida.append(titulo)
    return saida


def _promover(acao, prazo, destrava, hoje, urgencia_de, cobrado_por=None):
    """Sobe na fila quem responde por um prazo, sem inventar prazo próprio.

    ``prioridade_ate`` guarda a data emprestada e ``prazo_txt`` fica vazio: o
    cartão diz por que está no topo, e não que vence naquele dia. Item que já
    tem prazo, ou que já foi promovido por um prazo mais cedo, não muda.

    Dois motivos diferentes, e o cartão não pode trocá-los: ``destrava`` é o
    portão de uma seção trancada; ``cobrado_por`` é o item que o próprio
    prazo nomeia. Dizer "destrava Q3 Módulo 1" de uma atividade que mora
    dentro do Módulo 1 seria explicação errada com aparência de certa.
    """
    if not acao or acao.get("prazo") or acao.get("prioridade_ate"):
        return
    urgencia, _ = urgencia_de(prazo, hoje)
    acao["prioridade_ate"] = prazo
    acao["urgencia"] = urgencia
    acao["prazo_txt"] = ""
    if cobrado_por:
        acao["cobrado_por"] = cobrado_por
    else:
        acao["destrava"] = destrava
    acao["destrava_em"] = prazo
