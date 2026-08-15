# -*- coding: utf-8 -*-
"""Cobertura, idade das fontes e política de falhar fechado."""
from datetime import datetime


def resumo_fontes(dados):
    cursos = dados.get("courses") or []
    return {
        "disciplinas": len(cursos),
        "secoes": sum(len(curso.get("sections") or []) for curso in cursos),
        "itens": sum(
            len(secao.get("items") or [])
            for curso in cursos
            for secao in curso.get("sections") or []
        ),
        "avisos": sum(len(curso.get("avisos") or []) for curso in cursos),
        "eventos_calendario": len(dados.get("eventos") or []),
        # Evento sem nome não vira ação nem prazo. Contar só os úteis evita
        # que uma limpeza de ruído pareça perda de fonte para a saúde.
        "eventos_uteis": sum(
            1
            for evento in dados.get("eventos") or []
            if not isinstance(evento, dict)
            or (evento.get("nome") or "").strip()
        ),
        "notificacoes": len(dados.get("notificacoes") or []),
        "cronograma": sum(
            1 for curso in cursos if curso.get("cronograma")
        ),
        "itens_com_prazo": sum(
            1
            for curso in cursos
            for secao in curso.get("sections") or []
            for item in secao.get("items") or []
            if item.get("prazo")
        ),
    }


# Fonte que só acrescenta prova de entrega não pode congelar o site. Sem o
# boletim o guia fica mais cauteloso (mantém a atividade na fila por falta de
# prova), nunca menos — o oposto de uma fonte de prazo, cuja ausência esconde
# obrigação. Em 04/08/2026 o boletim de uma disciplina não renderizou e a
# rodada inteira virou "coleta_incompleta", segurando um retrato bom.
FONTES_QUE_NAO_BLOQUEIAM = ("boletim", "participacao", "meus_posts")


def validar_cobertura(dados, anterior):
    problemas = []
    cursos = dados.get("courses") or []
    if not cursos:
        problemas.append("não encontrei nenhuma disciplina em Meus cursos")

    def chave(curso):
        return str(curso.get("id") or curso.get("code") or "")

    virada = False
    antes = {
        chave(curso): curso.get("code")
        for curso in (anterior or {}).get("courses", [])
        if chave(curso)
    }
    agora = {chave(curso) for curso in cursos if chave(curso)}
    if antes:
        sumiram = set(antes) - agora
        novas = agora - set(antes)
        virada = sumiram == set(antes) and bool(novas)
        if sumiram and not virada:
            perdidas = [antes[item] for item in sumiram if antes.get(item)]
            problemas.append(
                "disciplina que existia ontem sumiu hoje: "
                + ", ".join(perdidas or sorted(sumiram))
            )

    sem_secao = [
        curso["code"] for curso in cursos if not curso.get("sections")
    ]
    if sem_secao:
        problemas.append(
            "disciplina sem nenhuma seção: " + ", ".join(sem_secao)
        )

    sem_item = [
        curso["code"]
        for curso in cursos
        if not any(
            secao.get("items") for secao in curso.get("sections", [])
        )
    ]
    if sem_item:
        problemas.append(
            "disciplina sem nenhuma atividade: " + ", ".join(sem_item)
        )

    fontes_atuais = resumo_fontes(dados)
    fontes_anteriores = (anterior or {}).get("fontes") or {}
    for nome, mensagem in (
        ("itens_com_prazo", "nenhum item ficou com prazo"),
        ("avisos", "não li nenhum aviso de fórum"),
        ("eventos_uteis", "o calendário voltou sem nenhum evento com nome"),
        ("cronograma", "não li o cronograma de nenhuma disciplina"),
    ):
        antes_n = int(fontes_anteriores.get(nome, 0) or 0)
        agora_n = int(fontes_atuais.get(nome, 0) or 0)
        if virada or antes_n <= 0:
            continue
        if agora_n == 0:
            problemas.append(
                f"{mensagem} (na última leitura válida eram {antes_n})"
            )
        elif agora_n < antes_n * 0.5:
            problemas.append(
                f"{nome} caiu de {antes_n} para {agora_n} "
                "(menos da metade da última leitura válida)"
            )

    for fonte, info in (dados.get("fontes_status") or {}).items():
        if fonte in FONTES_QUE_NAO_BLOQUEIAM:
            continue
        status = (info or {}).get("status")
        if status in ("falhou", "degradado"):
            falhas = (info or {}).get("falhas")
            detalhe = f", {falhas} falha(s)" if falhas else ""
            problemas.append(
                f"fonte {fonte} não foi conferida por inteiro "
                f"({status}{detalhe})"
            )
    return not problemas, problemas


def completar_idade_fontes(status_atual, status_anterior, agora_iso):
    """Calcula a idade a partir do último sucesso real de cada fonte."""
    agora = datetime.fromisoformat(agora_iso)
    saida = {}
    for nome, atual in (status_atual or {}).items():
        info = dict(atual or {})
        anterior = (status_anterior or {}).get(nome) or {}
        ultimo = info.get("last_live_at")
        if not ultimo and info.get("status") not in ("live", "vazio_confirmado"):
            ultimo = anterior.get("last_live_at")
        if not ultimo and info.get("status") in ("live", "vazio_confirmado"):
            ultimo = agora_iso
        info["last_live_at"] = ultimo
        if ultimo:
            try:
                info["idade_segundos"] = max(
                    0, int((agora - datetime.fromisoformat(ultimo)).total_seconds())
                )
            except (TypeError, ValueError):
                info["idade_segundos"] = None
        else:
            info["idade_segundos"] = None
        info.setdefault("checked_at", agora_iso)
        info.setdefault("quantidade_atual", 0)
        info.setdefault("from_cache", False)
        info.setdefault("truncado", False)
        info.setdefault("problemas", [])
        saida[nome] = info
    return saida
