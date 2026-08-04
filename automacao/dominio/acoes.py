# -*- coding: utf-8 -*-
"""Montagem, ordenação e deduplicação da fila de ações."""
import re
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


def urgencia_de(prazo_iso, hoje, hora_certa=True, evento=False, agora=None):
    if not prazo_iso:
        return "sem_prazo", ""
    prazo = datetime.fromisoformat(prazo_iso)
    dias = (prazo.date() - hoje).days
    hora = (
        f" às {prazo:%H:%M}"
        if hora_certa
        else " (horário não informado)"
    )
    if evento:
        # Live não vence, acontece. Dizer "vence hoje às 14h" para um
        # encontro que começa às 14h faz ele achar que tem o dia todo.
        # E encontro com hora marcada sai da fila quando a hora passa: às
        # 17h30 o guia ainda pedia pra assistir a live das 14h do mesmo dia.
        if agora is not None and hora_certa and dias == 0 and prazo <= agora:
            return "vencido", f"aconteceu hoje às {prazo:%H:%M}"
        if dias < 0:
            return "vencido", f"aconteceu em {prazo:%d/%m}"
        if dias == 0:
            return "hoje", f"acontece hoje{hora}"
        if dias == 1:
            return "amanha", f"acontece amanhã, {prazo:%d/%m}{hora}"
        if dias <= 7:
            return "semana", f"acontece {prazo:%d/%m}{hora}"
        return "depois", f"acontece {prazo:%d/%m}"
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
    lido direto da página "Meu envio" (ver ``fontes/itens.estado_workshop``).
    """
    return any(
        item.get("type") == "workshop" and item.get("enviado") is True
        for item in secao.get("items", [])
    )


def _workshop_avaliacao_feita(secao):
    """Nenhum Laboratório desta seção tem avaliação por pares pendente.

    Sem isto, o guia cobrava "avalie o trabalho do outro grupo" de quem já
    tinha avaliado — e continuava cobrando até o prazo virar.
    """
    labs = [
        item
        for item in secao.get("items", [])
        if item.get("type") == "workshop"
    ]
    if not labs:
        return False
    return all(item.get("avaliacao_pendente") is False for item in labs)


def _verbo_workshop(item):
    """Entregou mas ainda falta avaliar: o pedido muda de fase."""
    if item.get("enviado") is True and item.get("avaliacao_pendente") is True:
        return "Avalie", "o trabalho do colega"
    return verbo_de(item)


QUINZENA_RE = re.compile(r"^quinzena\s+(\d+)$")


def quinzenas_encerradas(curso):
    """Seções da quinzena que já passou, com o rótulo dela.

    A quinzena anterior deixa para trás páginas e fóruns de grupo que nunca
    ganham data e ficariam para sempre em "sem prazo definido" — o mesmo tipo
    de ruído que o AIA encerrado já não produz. Só vale para item sem prazo:
    obrigação com data (a avaliação por pares, que atravessa a virada) segue
    intacta.
    """
    secoes = curso.get("sections") or []
    por_id = {secao.get("id"): secao for secao in secoes}
    numeros = {}
    for secao in secoes:
        achado = QUINZENA_RE.match(
            sem_acento(secao.get("title") or "").strip()
        )
        if achado and not secao.get("parent") and not secao.get("locked"):
            numeros[secao.get("id")] = int(achado.group(1))
    if len(numeros) < 2:
        return {}
    atual = max(numeros.values())
    antigas = {
        sid: numero for sid, numero in numeros.items() if numero < atual
    }
    encerradas = {}
    for secao in secoes:
        no, nivel = secao, 0
        while no is not None and nivel < 6:
            if no.get("id") in antigas:
                encerradas[secao.get("id")] = antigas[no["id"]]
                break
            no = por_id.get(no.get("parent"))
            nivel += 1
    return encerradas


def _cmid_da_url(url):
    encontrado = re.search(r"[?&]id=(\d+)", url or "")
    return encontrado.group(1) if encontrado else None


def _obrigacao_chave(acao):
    return (
        acao.get("curso"),
        (acao.get("verbo") or "").split()[0] if acao.get("verbo") else "",
        (acao.get("prazo") or "")[:10],
    )


def _suprimir_avisos_redundantes(acoes):
    """Uma obrigação, uma linha — a que leva direto à atividade.

    O mesmo dever chega por dois caminhos: o aviso do facilitador (que sabe a
    data mas não tem link) e o item do AVA (que tem link, hora exata e nome
    real). Quando os dois falam do mesmo dia, do mesmo curso e do mesmo verbo,
    fica o item, herdando o link do aviso como fonte. Se o item não foi
    coletado, o aviso continua sendo a única rede de proteção e permanece.
    """
    por_item = {}
    for acao in acoes:
        if (
            acao.get("tipo") not in ("obrigacao", "compromisso")
            and acao.get("url")
            and acao.get("prazo")
        ):
            por_item.setdefault(_obrigacao_chave(acao), acao)
    saida = []
    for acao in acoes:
        alvo = por_item.get(_obrigacao_chave(acao))
        if acao.get("tipo") == "obrigacao" and alvo is not None:
            if not alvo.get("fonte_url"):
                alvo["fonte_url"] = acao.get("fonte_url")
                alvo["aviso_txt"] = acao.get("o_que")
            continue
        saida.append(acao)
    return saida


def _agrupar_compromissos(acoes):
    """Seis horários da mesma live viravam seis compromissos na fila.

    O aviso de 31/07/2026 dizia o contrário do que o guia mostrava:
    "participem da live que melhor se adequar à sua disponibilidade". São
    opções do mesmo encontro, anunciadas no mesmo post. Fica um cartão só,
    com o próximo horário na frente e os demais listados como alternativa.
    """
    saida, por_aviso = [], {}
    for acao in acoes:
        chave = (acao.get("curso"), acao.get("fonte_url"))
        if acao.get("tipo") != "compromisso" or not acao.get("fonte_url"):
            saida.append(acao)
            continue
        if chave not in por_aviso:
            por_aviso[chave] = acao
            acao["opcoes"] = []
            saida.append(acao)
        principal = por_aviso[chave]
        principal["opcoes"].append(
            {
                "quando": acao.get("prazo"),
                "prazo_txt": acao.get("prazo_txt"),
                "o_que": acao.get("o_que"),
            }
        )
    for acao in saida:
        if len(acao.get("opcoes") or []) < 2:
            acao.pop("opcoes", None)
    return saida


GATILHOS_ENCONTRO = (
    "live",
    "encontro",
    "plantao",
    "webinar",
    "transmissao",
    "aula ao vivo",
    "tira-duvidas",
    "tira duvidas",
)


def _eh_encontro(evento):
    """Evento de agenda (tem hora marcada), não fechamento de atividade."""
    nome = sem_acento(evento.get("nome") or "")
    if any(palavra in nome for palavra in GATILHOS_ENCONTRO):
        return True
    hora = (evento.get("quando") or "")[11:16]
    return evento.get("tipo") == "course" and hora not in ("", "23:59")


def compromissos_do_calendario(dados, hoje, agora, ja_na_fila):
    """Live marcada no calendário do AVA também é compromisso.

    A API de "ações pendentes" do Moodle só devolve atividade com pendência,
    então a live de tira-dúvidas do facilitador — que é evento de curso, não
    atividade — nunca chegava ao guia. Ele avisou que não pode perder live.
    """
    por_curso = {
        str(curso.get("id") or ""): curso.get("code")
        for curso in dados.get("courses", [])
    }
    novos, vistos = [], set()
    for evento in dados.get("eventos") or []:
        if not _eh_encontro(evento):
            continue
        cmid = str(evento.get("cmid") or "")
        if cmid and cmid in ja_na_fila:
            continue
        quando = evento.get("quando")
        hora_certa = (quando or "")[11:16] != "23:59"
        urgencia, texto = urgencia_de(
            quando, hoje, hora_certa, evento=True, agora=agora
        )
        if urgencia == "vencido":
            continue
        # A mesma live se repete toda semana. Só o próximo encontro entra;
        # os seguintes viram contagem, não seis linhas iguais na fila.
        chave = (evento.get("curso_id"), sem_acento(evento.get("nome") or ""))
        if chave in vistos:
            for anterior in novos:
                if anterior.get("_chave") == chave:
                    anterior["repete"] = anterior.get("repete", 1) + 1
            continue
        vistos.add(chave)
        novos.append(
            {
                "_chave": chave,
                "curso": por_curso.get(str(evento.get("curso_id") or ""))
                or evento.get("curso")
                or "",
                "secao": "Calendário do AVA",
                "fase": "regular",
                "verbo": "Assista",
                "coisa": "ao vivo",
                "o_que": evento.get("nome") or "encontro da disciplina",
                "tipo": "compromisso",
                "url": evento.get("url"),
                "conta_nota": True,
                "prazo": quando,
                "prazo_txt": texto,
                "prazo_fonte": "calendário do AVA",
                "fonte_url": None,
                "autoridade": "institucional",
                "carencia": None,
                "hora_certa": hora_certa,
                "urgencia": urgencia,
            }
        )
    for acao in novos:
        acao.pop("_chave", None)
    return novos


def montar_acoes(dados, hoje, agora=None):
    """``agora`` só é exigido para tirar da fila encontro que já começou."""
    acoes, encerrados, confirmar, higiene = [], [], [], []
    for curso in dados["courses"]:
        quinzenas_antigas = quinzenas_encerradas(curso)
        prazos_aviso = [
            {**prazo, "aviso": aviso}
            for aviso in curso.get("avisos", [])
            for prazo in aviso.get("prazos", [])
        ] + [
            # Data lida da página de instruções da quinzena. Nasce sempre com
            # confiança baixa, então só aparece no "confirme se é prazo".
            {**prazo, "aviso": pagina}
            for pagina in curso.get("paginas_instrucao", [])
            for prazo in pagina.get("prazos", [])
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
        # Compromisso vive no nível do curso, não dentro de um módulo: a
        # live é anunciada em aviso e não tem item próprio com data no AVA.
        vistos_compromisso = set()
        for prazo in prazos_aviso:
            if prazo.get("tipo") != "compromisso":
                continue
            urgencia, texto = urgencia_de(
                prazo["quando"],
                hoje,
                prazo.get("hora_certa", True),
                evento=True,
                agora=agora,
            )
            if urgencia == "vencido":
                continue
            # Dedup por data e nome do encontro: o mesmo cronograma de lives
            # postado duas vezes (original e "Re:") tem rótulos diferentes e
            # passava como se fossem encontros distintos.
            chave = (
                prazo["quando"],
                sem_acento(
                    prazo.get("titulo_evento") or prazo.get("rotulo") or ""
                ),
            )
            if chave in vistos_compromisso:
                continue
            vistos_compromisso.add(chave)
            aviso = prazo["aviso"]
            nome = prazo.get("titulo_evento") or aviso.get("titulo")
            acoes.append(
                {
                    "curso": curso["code"],
                    "secao": aviso.get("titulo") or "",
                    "fase": "regular",
                    "verbo": "Assista",
                    "coisa": "ao vivo",
                    "o_que": nome or "live da disciplina",
                    "tipo": "compromisso",
                    "url": aviso.get("url"),
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
                if verbo == "Avalie" and _workshop_avaliacao_feita(secao):
                    continue
                # Dedup pelo que o Josemar vê. O facilitador postou o mesmo
                # lembrete de 04/08 em dois fóruns no mesmo minuto, e a fila
                # exibia duas linhas idênticas. Obrigações de verdade
                # distintas continuam separadas porque ``rotulo_fase``
                # preserva o que difere no rótulo (rodada 3).
                chave_fase = (
                    prazo["quando"],
                    verbo,
                    sem_acento(rotulo_fase(prazo)),
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
                # Laboratório de Avaliação são duas obrigações em sequência:
                # entregar e avaliar o trabalho de outra pessoa. Só sai da
                # fila quando as duas terminam. Sumia na primeira.
                if (
                    item.get("type") == "workshop"
                    and item.get("enviado") is True
                    and item.get("avaliacao_pendente") is not True
                ):
                    continue
                if item.get("status") is None and not item.get("conta_nota"):
                    continue
                verbo, coisa = _verbo_workshop(item)
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
                if not prazo and secao.get("id") in quinzenas_antigas:
                    encerrados.append(
                        {
                            **base,
                            "motivo": (
                                f"a Quinzena {quinzenas_antigas[secao['id']]}"
                                " encerrou"
                            ),
                        }
                    )
                    continue
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

    # Só o que já está na fila conta como "já coberto". Comparar com todos os
    # itens do curso escondia a live: o link fixo "Live com facilitador" existe
    # em toda disciplina, nunca vira tarefa, e mesmo assim cancelava o evento
    # com data marcada que veio do calendário.
    ja_na_fila = {
        cmid
        for acao in acoes
        for cmid in [_cmid_da_url(acao.get("url"))]
        if cmid
    }
    acoes.extend(
        compromissos_do_calendario(dados, hoje, agora, ja_na_fila)
    )
    acoes = _agrupar_compromissos(acoes)
    acoes = _suprimir_avisos_redundantes(acoes)

    propagar_urgencia(acoes, dados, hoje)

    # O link fixo "Live com facilitador" não tem data e ficava eternamente em
    # "sem prazo". Quando já existem lives com hora marcada, ele só repete.
    cursos_com_live = {
        acao["curso"] for acao in acoes if acao["tipo"] == "compromisso"
    }
    acoes = [
        acao
        for acao in acoes
        if not (
            acao["tipo"] == "lti"
            and acao["urgencia"] == "sem_prazo"
            and "live" in sem_acento(acao.get("o_que") or "")
            and acao["curso"] in cursos_com_live
        )
    ]

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
