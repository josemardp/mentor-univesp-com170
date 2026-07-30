# -*- coding: utf-8 -*-
"""Montagem, ordenação e deduplicação da fila de ações."""
from datetime import datetime

from dominio.datas import sem_acento
from dominio.dependencias import propagar_urgencia
from dominio.prazos import casar_prazos, fase_de, rotulo_fase

ORDEM = {
    "hoje": 0,
    "amanha": 1,
    "semana": 2,
    "depois": 3,
    "sem_prazo": 4,
    "vencido": 5,
}


def conta_nota(modelo, item, secao):
    rotulo = sem_acento(item.get("label", ""))
    tipo = item.get("type")
    if tipo in ("quiz", "scorm", "assign", "workshop"):
        return True
    if modelo == "regular":
        return any(
            palavra in rotulo
            for palavra in (
                "videoaula",
                "video-base",
                "video base",
                "texto-base",
                "material-base",
                "material base",
            )
        )
    if sem_acento(secao).startswith("modulo") or "live" in rotulo:
        return True
    return tipo == "feedback"


def verbo_de(item):
    rotulo = sem_acento(item.get("label", ""))
    tipo = item.get("type")
    if tipo == "quiz":
        return "Responda", "questionário"
    if tipo == "scorm":
        return "Faça", "quiz interativo"
    if tipo == "feedback":
        return "Responda", "formulário"
    if tipo == "assign":
        return "Entregue", "tarefa"
    if tipo == "workshop":
        return "Entregue e avalie", "revisão por pares"
    if tipo == "lti":
        return (
            ("Assista", "live")
            if "live" in rotulo
            else ("Acesse", "ferramenta")
        )
    if tipo == "forum":
        return "Participe", "do fórum"
    if any(
        palavra in rotulo
        for palavra in ("videoaula", "video-base", "video base")
    ):
        return "Assista", "videoaula"
    if any(
        palavra in rotulo
        for palavra in (
            "texto-base",
            "material-base",
            "material",
            "leia",
        )
    ):
        return "Leia", "material-base"
    if tipo == "url":
        return "Acesse", "link"
    return "Abra e conclua", "página"


def urgencia_de(prazo_iso, hoje, hora_certa=True):
    if not prazo_iso:
        return "sem_prazo", ""
    prazo = datetime.fromisoformat(prazo_iso)
    dias = (prazo.date() - hoje).days
    hora = (
        f" às {prazo:%H:%M}"
        if hora_certa
        else " (horário não informado)"
    )
    if dias < 0:
        return "vencido", f"venceu em {prazo:%d/%m}"
    if dias == 0:
        return "hoje", f"vence hoje{hora}"
    if dias == 1:
        return "amanha", f"vence amanhã, {prazo:%d/%m}{hora}"
    if dias <= 7:
        return "semana", f"vence {prazo:%d/%m}{hora}"
    return "depois", f"vence {prazo:%d/%m}"


def _workshop_ja_enviado(secao):
    """Existe um Laboratório de Avaliação nesta seção que o aluno já enviou.

    Selo "Concluído" do Moodle só fecha quando as 5 fases terminam pra ele,
    inclusive avaliar o trabalho de outro grupo — não serve pra saber se a
    entrega em si já foi feita. A fonte da verdade é ``item["enviado"]``,
    lido direto da página "Meu envio" (ver ``fontes/itens.envio_workshop``).
    """
    return any(
        item.get("type") == "workshop" and item.get("enviado") is True
        for item in secao.get("items", [])
    )


def montar_acoes(dados, hoje):
    acoes, encerrados, confirmar, higiene = [], [], [], []
    for curso in dados["courses"]:
        prazos_aviso = [
            {**prazo, "aviso": aviso}
            for aviso in curso.get("avisos", [])
            for prazo in aviso.get("prazos", [])
        ]
        vistos_confirmar = set()
        for prazo in prazos_aviso:
            if prazo.get("confianca", "alta") == "alta":
                continue
            urgencia, texto = urgencia_de(
                prazo["quando"], hoje, prazo.get("hora_certa", True)
            )
            if urgencia == "vencido":
                continue
            chave = (
                prazo["quando"],
                sem_acento(prazo.get("rotulo") or ""),
            )
            if chave in vistos_confirmar:
                continue
            vistos_confirmar.add(chave)
            confirmar.append(
                {
                    "curso": curso["code"],
                    "quando": prazo["quando"],
                    "quando_txt": texto,
                    "tipo_lido": prazo.get("tipo"),
                    "rotulo": prazo.get("rotulo"),
                    "frase": prazo.get("frase"),
                    "autor": (prazo.get("aviso") or {}).get("autor"),
                    "autoridade": (prazo.get("aviso") or {}).get(
                        "autoridade", "colega"
                    ),
                    "url": (prazo.get("aviso") or {}).get("url"),
                }
            )
        for secao in curso["sections"]:
            vistos_fase = set()
            for prazo in casar_prazos(secao["title"], prazos_aviso):
                urgencia, texto = urgencia_de(
                    prazo["quando"], hoje, prazo.get("hora_certa", True)
                )
                if urgencia == "vencido":
                    continue
                verbo, coisa = fase_de(prazo)
                if verbo == "Entregue" and _workshop_ja_enviado(secao):
                    continue
                chave_fase = (
                    prazo["quando"],
                    sem_acento(prazo.get("rotulo") or ""),
                )
                if chave_fase in vistos_fase:
                    continue
                vistos_fase.add(chave_fase)
                aviso = prazo["aviso"]
                acoes.append(
                    {
                        "curso": curso["code"],
                        "secao": secao["title"],
                        "fase": secao.get("fase", "regular"),
                        "verbo": verbo,
                        "coisa": coisa,
                        "o_que": f"{secao['title']} · {rotulo_fase(prazo)}",
                        "tipo": "obrigacao",
                        "url": None,
                        "conta_nota": True,
                        "prazo": prazo["quando"],
                        "prazo_txt": texto,
                        "prazo_fonte": (
                            f"aviso de {aviso.get('autor') or 'facilitador'}"
                        ),
                        "fonte_url": aviso.get("url"),
                        "autoridade": aviso.get("autoridade", "colega"),
                        "carencia": None,
                        "hora_certa": prazo.get("hora_certa", True),
                        "urgencia": urgencia,
                        "bloqueio": secao.get("locked"),
                    }
                )
            if secao.get("locked"):
                continue
            for item in secao["items"]:
                if item.get("status") == "Concluído":
                    continue
                if item.get("type") == "workshop" and item.get("enviado") is True:
                    continue
                if item.get("status") is None and not item.get("conta_nota"):
                    continue
                verbo, coisa = verbo_de(item)
                base = {
                    "curso": curso["code"],
                    "secao": secao["title"],
                    "fase": secao.get("fase", "regular"),
                    "verbo": verbo,
                    "coisa": coisa,
                    "o_que": item["label"],
                    "tipo": item["type"],
                    "url": item.get("url"),
                    "conta_nota": item.get("conta_nota", False),
                }
                if item.get("aberto") is False:
                    encerrados.append(
                        {
                            **base,
                            "motivo": item.get(
                                "motivo_fechado", "encerrado"
                            ),
                        }
                    )
                    continue
                prazo = item.get("prazo")
                fonte = item.get("prazo_fonte")
                urgencia, texto = urgencia_de(prazo, hoje)
                if urgencia == "vencido":
                    encerrados.append({**base, "motivo": texto})
                    continue
                registro = {
                    **base,
                    "prazo": prazo,
                    "prazo_txt": texto,
                    "prazo_fonte": fonte,
                    "fonte_url": None,
                    "carencia": item.get("carencia"),
                    "hora_certa": True,
                    "urgencia": urgencia,
                }
                if (
                    item.get("aberto") is None
                    and item.get("status") == "Pendente"
                ):
                    registro["verificacao"] = "indefinida"
                if not prazo and not item.get("conta_nota"):
                    higiene.append(registro)
                    continue
                acoes.append(registro)

    propagar_urgencia(acoes, dados, hoje)

    def ordenar(lista):
        return sorted(
            lista,
            key=lambda acao: (
                ORDEM.get(acao["urgencia"], 9),
                acao.get("prazo")
                or acao.get("prioridade_ate")
                or "9999",
                0 if acao["conta_nota"] else 1,
                acao["curso"],
            ),
        )

    confirmar.sort(key=lambda item: item["quando"])
    return ordenar(acoes), encerrados, ordenar(higiene), confirmar


def identidade_item(curso, secao, item):
    """Identidade estável: ID Moodle, URL e só então seção+rótulo."""
    cmid = item.get("cmid")
    if cmid is not None and str(cmid).strip():
        return curso.get("code"), "cmid", str(cmid).strip()
    url = (item.get("url") or "").strip()
    if url:
        return curso.get("code"), "url", url
    secao_id = secao.get("id") or secao.get("title") or ""
    return (
        curso.get("code"),
        "fallback",
        str(secao_id),
        sem_acento(item.get("label") or ""),
    )


def novidades(anterior, dados):
    mudancas = []
    antes = {}
    for curso in (anterior or {}).get("courses", []):
        for secao in curso.get("sections", []):
            for item in secao.get("items", []):
                antes[identidade_item(curso, secao, item)] = item.get("status")
    for curso in dados["courses"]:
        for secao in curso["sections"]:
            for item in secao["items"]:
                chave = identidade_item(curso, secao, item)
                cmid = (
                    str(item["cmid"])
                    if item.get("cmid") is not None
                    else None
                )
                if chave not in antes and item.get("status") is not None:
                    mudancas.append(
                        {
                            "curso": curso["code"],
                            "label": item["label"],
                            "kind": "novo",
                            "cmid": cmid,
                        }
                    )
                elif (
                    antes.get(chave) != item.get("status")
                    and item.get("status") == "Concluído"
                ):
                    mudancas.append(
                        {
                            "curso": curso["code"],
                            "label": item["label"],
                            "kind": "concluido",
                            "cmid": cmid,
                        }
                    )
        for aviso in curso.get("avisos", []):
            if aviso.get("novo"):
                mudancas.append(
                    {
                        "curso": curso["code"],
                        "label": aviso.get("titulo") or "novo post",
                        "kind": "aviso",
                        "autoridade": aviso.get("autoridade", "colega"),
                    }
                )
    return mudancas
