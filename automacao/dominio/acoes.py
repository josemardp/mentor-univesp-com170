# -*- coding: utf-8 -*-
"""Montagem, ordenação e deduplicação da fila de ações."""
import re
from datetime import datetime, timedelta

from configuracao import NOVO_ATE_DIAS
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


def itens_por_secao(curso, filtro=None):
    """Itens de cada seção, incluindo os das seções filhas.

    O aviso do facilitador fala da quinzena inteira ("prazos da avaliação por
    pares da Quinzena 1"), mas os laboratórios moram nos módulos, que são
    sub-seções. Olhando só os itens da própria seção, a Quinzena 1 parece não
    ter laboratório nenhum, e a cobrança sobrevive à entrega: em 04/08/2026 o
    guia continuou pedindo "avalie hoje" depois da avaliação salva.
    """
    secoes = curso.get("sections") or []
    filhos = {}
    for secao in secoes:
        filhos.setdefault(secao.get("parent"), []).append(secao)

    def coletar(secao, nivel=0):
        itens = [
            item
            for item in secao.get("items") or []
            if filtro is None or filtro(item)
        ]
        if nivel < 6:
            for filha in filhos.get(secao.get("id"), []):
                itens.extend(coletar(filha, nivel + 1))
        return itens

    return {secao.get("id"): coletar(secao) for secao in secoes}


def laboratorios_por_secao(curso):
    """Só os Laboratórios de Avaliação, para as fases de entrega e avaliação."""
    return itens_por_secao(
        curso, lambda item: item.get("type") == "workshop"
    )


def _workshop_ja_enviado(labs):
    """Algum Laboratório desta seção (ou das filhas) já foi enviado.

    Selo "Concluído" do Moodle só fecha quando as 5 fases terminam pra ele,
    inclusive avaliar o trabalho de outro grupo — não serve pra saber se a
    entrega em si já foi feita. A fonte da verdade é ``item["enviado"]``,
    lido direto da página "Meu envio" (ver ``fontes/itens.estado_workshop``).
    """
    return any(item.get("enviado") is True for item in labs)


def _workshop_avaliacao_feita(labs):
    """Nenhum Laboratório em jogo tem avaliação por pares pendente."""
    if not labs:
        return False
    return all(item.get("avaliacao_pendente") is False for item in labs)


TIPOS_QUE_VALEM_NOTA = ("quiz", "scorm", "assign", "workshop")


def entrega_provada(item):
    """A atividade foi mesmo entregue? ``True``/``False``/``None``.

    O selo "Concluído" do Moodle não responde isso: em 04/08/2026 a S2 -
    Atividade Avaliativa do COM100 estava concluída, sem nenhuma tentativa e
    sem nota, com prazo em aberto — aquele item fecha só por ter sido aberto.
    Prova é nota lançada (mesmo zero), envio confirmado ou tentativa
    finalizada. ``None`` quer dizer "não sei", e não sei nunca vira acusação.
    """
    if item.get("tem_nota"):
        return True
    # Devolutiva escrita é prova tão boa quanto nota: alguém leu o trabalho.
    # A S2 - Ferramenta para Envio da COM170 é assim, com elogio do
    # facilitador e sem nota numérica.
    if item.get("feedback"):
        return True
    if item.get("type") == "workshop":
        return True if item.get("enviado") is True else None
    return item.get("entrega_confirmada")


def _item_resolvido(item):
    """O item já está feito? Mesmas regras que tiram o item da fila.

    Mantido em uma função só porque o laço de itens e a supressão da cobrança
    de seção precisam concordar: se divergirem, o guia tira o item da fila e
    continua cobrando a seção que só tinha aquele item — que é exatamente o
    defeito de 09/08/2026.
    """
    sem_entrega = (
        item.get("type") in TIPOS_QUE_VALEM_NOTA
        and entrega_provada(item) is False
    )
    if item.get("status") == "Concluído" and not sem_entrega:
        return True
    return (
        item.get("type") == "workshop"
        and item.get("enviado") is True
        and item.get("avaliacao_pendente") is not True
    )


def _item_rastreado(item):
    """Item que o Moodle acompanha, ou que vale nota.

    Fórum sem marcação de conclusão nunca fica "feito" e travaria a supressão
    para sempre; o laço de itens já o ignora pelo mesmo critério.
    """
    return item.get("status") is not None or bool(item.get("conta_nota"))


def _secao_cumprida(itens):
    """Todo item rastreado da seção (e das filhas) já está resolvido.

    Sem evidência nenhuma — seção vazia ou só com itens que o Moodle não
    acompanha — devolve ``False``: silenciar cobrança exige prova, e a falta
    de prova nunca pode virar "está tudo feito".
    """
    rastreados = [item for item in itens if _item_rastreado(item)]
    if not rastreados:
        return False
    return all(_item_resolvido(item) for item in rastreados)


def _verbo_workshop(item):
    """Entregou mas ainda falta avaliar: o pedido muda de fase."""
    if item.get("enviado") is True and item.get("avaliacao_pendente") is True:
        return "Avalie", "o trabalho do colega"
    return verbo_de(item)


QUINZENA_RE = re.compile(r"^quinzena\s+(\d+)$")

# Coisa que se entrega ou se responde. Nunca é "sobra": a revisão entre pares
# da Quinzena 2 vai até 18/08, dois dias depois da Quinzena 3 abrir, e some
# do guia justamente na hora de fazer se a virada de quinzena a apagar.
TIPOS_DE_ENTREGA = ("workshop", "assign", "quiz", "scorm", "feedback")


def _sobra_de_quinzena(item):
    """Só página e fórum que o Moodle nem marca como pendente."""
    if item.get("type") in TIPOS_DE_ENTREGA:
        return False
    if item.get("status") == "Pendente":
        return False
    return item.get("avaliacao_pendente") is not True


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


# O Moodle declara o papel do evento no campo ``tipo``. Abertura marca quando a
# atividade passa a aceitar trabalho — é o oposto de prazo, e confundir os dois
# foi o que fez o guia de 09/08/2026 anunciar "vence amanhã, 10/08 às 00:00"
# para uma entrega que só fechava em 15/08.
TIPOS_DE_ABERTURA = ("open", "opensubmission", "openassessment")

TIPOS_DE_FIM = (
    "close",
    "closeassessment",
    # O Moodle emite "closesubmission"; a lista só tinha o nome invertido, e o
    # prazo de envio do Laboratório vinha sendo salvo pelo nome do evento
    # ("prazo limite de envios"), não pelo tipo. Um evento com nome genérico
    # teria passado batido.
    "closesubmission",
    "due",
    "gradingdue",
    "submissionclose",
    "expectcompletionon",
)
NOMES_DE_FIM = (
    "termino",
    "prazo limite",
    "encerra",
    "encerramento",
    "vencimento",
    "fechamento",
)


def _eh_fim_de_prazo(evento):
    # O tipo declarado pelo Moodle manda. Abertura nunca vira prazo, mesmo que
    # o nome do evento fale em encerramento: 10/08 00:00 é quando a entrega do
    # Laboratório ABRE, e virou "vence amanhã" no guia de 09/08/2026.
    if evento.get("tipo") in TIPOS_DE_ABERTURA:
        return False
    if evento.get("tipo") in TIPOS_DE_FIM:
        return True
    nome = sem_acento(evento.get("nome") or "")
    return bool(nome) and any(palavra in nome for palavra in NOMES_DE_FIM)


def _verbo_do_evento(nome):
    alvo = sem_acento(nome or "")
    if "avaliacao" in alvo or "avaliar" in alvo or "revisao" in alvo:
        return "Avalie", "o trabalho do colega"
    if "envio" in alvo or "entrega" in alvo or "submissao" in alvo:
        return "Entregue", "o trabalho"
    return "Conclua", ""


def tarefas_do_calendario(dados, hoje, ja_na_fila):
    """Rede de segurança: prazo do calendário que não virou tarefa vira tarefa.

    Todo erro grave desta sessão teve a mesma forma — uma atividade com data
    marcada no AVA não chegou à fila, seja porque a seção foi descartada, seja
    porque o item foi lido como encerrado. O calendário sabia do prazo o tempo
    todo. Aqui ele deixa de ser só um enfeite do item e passa a ser fonte por
    conta própria: se o prazo existe, não está vencido e a atividade não está
    concluída, ele aparece — mesmo que o resto da leitura tenha falhado.
    """
    por_curso = {
        str(curso.get("id") or ""): curso.get("code")
        for curso in dados.get("courses", [])
    }
    status_por_cmid = {
        str(item.get("cmid")): item.get("status")
        for curso in dados.get("courses", [])
        for secao in curso.get("sections") or []
        for item in secao.get("items") or []
        if item.get("cmid")
    }
    novos, vistos = [], set()
    for evento in dados.get("eventos") or []:
        cmid = str(evento.get("cmid") or "")
        if not cmid or cmid in ja_na_fila or cmid in vistos:
            continue
        if not _eh_fim_de_prazo(evento) or _eh_encontro(evento):
            continue
        if status_por_cmid.get(cmid) == "Concluído":
            continue
        urgencia, texto = urgencia_de(evento.get("quando"), hoje)
        if urgencia in ("vencido", "sem_prazo"):
            continue
        vistos.add(cmid)
        verbo, coisa = _verbo_do_evento(evento.get("nome"))
        novos.append(
            {
                "curso": por_curso.get(str(evento.get("curso_id") or ""))
                or evento.get("curso")
                or "",
                "secao": "Calendário do AVA",
                "fase": "regular",
                "verbo": verbo,
                "coisa": coisa,
                "o_que": evento.get("atividade")
                or evento.get("nome")
                or "atividade com prazo",
                "tipo": "calendario",
                "url": evento.get("url"),
                "conta_nota": True,
                "prazo": evento.get("quando"),
                "prazo_txt": texto,
                "prazo_fonte": "calendário do AVA",
                "fonte_url": None,
                "autoridade": "institucional",
                "carencia": None,
                "hora_certa": True,
                "urgencia": urgencia,
                "resgatado": True,
            }
        )
    return novos


def montar_acoes(dados, hoje, agora=None):
    """``agora`` só é exigido para tirar da fila encontro que já começou."""
    acoes, encerrados, confirmar, higiene = [], [], [], []
    # Atividades que saíram da fila por já estarem feitas. A rede de segurança
    # do calendário não pode ressuscitá-las — senão o M6, entregue e avaliado,
    # volta pelo evento "prazo limite para avaliação". Item que saiu por
    # leitura duvidosa (o AVA "disse" que fechou) fica de fora desta lista de
    # propósito: é justamente esse caso que a rede precisa pegar.
    resolvidos = set()
    for curso in dados["courses"]:
        quinzenas_antigas = quinzenas_encerradas(curso)
        labs_por_secao = laboratorios_por_secao(curso)
        itens_de_secao = itens_por_secao(curso)
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
                labs = labs_por_secao.get(secao.get("id")) or []
                if verbo == "Entregue" and _workshop_ja_enviado(labs):
                    continue
                if verbo == "Avalie" and _workshop_avaliacao_feita(labs):
                    continue
                # "Conclua o Módulo 4 até hoje" não tem fase própria para
                # conferir, e por isso sobrevivia à conclusão: em 09/08/2026 o
                # guia cobrou três seções 100% concluídas (COM100 Semana 2,
                # COM170 Módulo 4 e Q2 Módulo 4), todas com o quiz já
                # pontuado. Cobrança de seção morre quando a seção acaba.
                if verbo == "Conclua" and _secao_cumprida(
                    itens_de_secao.get(secao.get("id")) or []
                ):
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
                cmid_item = (
                    str(item["cmid"]) if item.get("cmid") else None
                )
                sem_entrega = (
                    item.get("type") in TIPOS_QUE_VALEM_NOTA
                    and entrega_provada(item) is False
                )
                if item.get("status") == "Concluído" and not sem_entrega:
                    resolvidos.add(cmid_item)
                    continue
                # Laboratório de Avaliação são duas obrigações em sequência:
                # entregar e avaliar o trabalho de outra pessoa. Só sai da
                # fila quando as duas terminam. Sumia na primeira.
                if (
                    item.get("type") == "workshop"
                    and item.get("enviado") is True
                    and item.get("avaliacao_pendente") is not True
                ):
                    resolvidos.add(cmid_item)
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
                if sem_entrega:
                    base["entrega_nao_confirmada"] = True
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
                if (
                    not prazo
                    and secao.get("id") in quinzenas_antigas
                    and _sobra_de_quinzena(item)
                ):
                    resolvidos.add(cmid_item)
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
        for lista in (acoes, higiene)
        for acao in lista
        for cmid in [_cmid_da_url(acao.get("url"))]
        if cmid
    }
    acoes.extend(
        compromissos_do_calendario(dados, hoje, agora, ja_na_fila)
    )
    # Depois dos compromissos: o que já entrou como live não volta como prazo.
    ja_na_fila |= {
        cmid
        for acao in acoes
        for cmid in [_cmid_da_url(acao.get("url"))]
        if cmid
    }
    acoes.extend(
        tarefas_do_calendario(
            dados, hoje, ja_na_fila | {c for c in resolvidos if c}
        )
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
    """Atividade que apareceu no AVA desde o retrato anterior.

    Calculava também item concluído e post de aviso, e nada lia o resultado:
    ficava gravando três tipos de mudança no ``data.json`` que nunca chegaram
    a uma tela. Item concluído é ação dele, não notícia; aviso de fórum já
    entra por conta própria na aba. Sobrou o que é novidade de verdade: a
    atividade que não existia na leitura anterior, que é como a abertura de
    uma semana nova aparece.
    """
    antes = set()
    for curso in (anterior or {}).get("courses", []):
        for secao in curso.get("sections", []):
            for item in secao.get("items", []):
                antes.add(identidade_item(curso, secao, item))
    if not antes:
        # Sem retrato anterior o AVA inteiro pareceria novidade.
        return []
    mudancas = []
    for curso in dados["courses"]:
        for secao in curso["sections"]:
            for item in secao["items"]:
                if item.get("status") is None:
                    continue
                if identidade_item(curso, secao, item) in antes:
                    continue
                mudancas.append(
                    {
                        "curso": curso["code"],
                        "secao": secao.get("title"),
                        "label": item["label"],
                        "url": item.get("url"),
                        "cmid": (
                            str(item["cmid"])
                            if item.get("cmid") is not None
                            else None
                        ),
                    }
                )
    return mudancas


# Só boletim que o robô abriu de fato serve de termo de comparação. Leitura
# que falhou devolve as notas do cache, e comparar contra o cache faria o guia
# anunciar como nova uma nota que já estava lá desde sempre.
BOLETIM_LIDO = ("live", "vazio_confirmado")


def _notas_lidas(pacote):
    """``({(curso, cmid): nota}, {cursos cujo boletim foi lido})``."""
    notas, lidos = {}, set()
    for curso in (pacote or {}).get("courses") or []:
        if (curso.get("boletim") or {}).get("status") not in BOLETIM_LIDO:
            continue
        codigo = curso.get("code")
        lidos.add(codigo)
        for secao in curso.get("sections") or []:
            for item in secao.get("items") or []:
                # "-" é o AVA dizendo que não há nota. Só valor lançado conta,
                # inclusive 0,00, que é nota e é notícia.
                if not item.get("tem_nota") or item.get("cmid") is None:
                    continue
                notas[f"{codigo}:{item['cmid']}"] = item.get("nota_txt")
    return notas, lidos


def notas_novas(anterior, dados, estado, agora, janela_dias=NOVO_ATE_DIAS):
    """Nota que saiu ou mudou, e que continua à vista por alguns dias.

    Motivo, achado em 10/08/2026: o guia lia o boletim das quatro disciplinas
    e mostrava as notas na aba "Como estou", mas não avisava quando uma nota
    aparecia. Ele só descobriria comparando de memória com o que viu ontem.
    Isso ficou visível pelo SOC100, cujo boletim está vazio: do jeito antigo,
    o dia em que a primeira nota fosse lançada seria um dia igual aos outros.

    O que sustenta a comparação é o retrato anterior, não o cache: disciplina
    cujo boletim não foi lido na rodada passada fica de fora até haver duas
    leituras boas seguidas. Assim o guia nunca chama de nova uma nota que só
    reapareceu depois de uma falha de leitura.

    A janela em dias existe porque o robô roda cinco vezes ao dia. Anunciar
    só na rodada seguinte faria a notícia passar enquanto ele dormia.
    """
    registro = estado.setdefault("_notas_vistas", {}) if estado is not None else {}
    antes, confiaveis = _notas_lidas(anterior)
    depois, _ = _notas_lidas(dados)

    for chave, nota in depois.items():
        if chave.split(":", 1)[0] not in confiaveis:
            continue  # sem leitura anterior boa, não dá para saber se é nova
        anotado = registro.get(chave)
        if anotado and anotado.get("nota") == nota:
            continue  # já anunciada, e o valor não mudou
        if antes.get(chave) == nota:
            continue  # já estava no retrato anterior: não é notícia
        registro[chave] = {
            "nota": nota,
            "de": (anotado or {}).get("nota") or antes.get(chave),
            "em": agora,
        }

    corte = (datetime.fromisoformat(agora) - timedelta(days=janela_dias))
    itens = {}
    for curso in dados.get("courses") or []:
        for secao in curso.get("sections") or []:
            for item in secao.get("items") or []:
                if item.get("cmid") is not None:
                    itens[f"{curso.get('code')}:{item['cmid']}"] = (curso, item)

    saida = []
    for chave in list(registro):
        anotado = registro[chave]
        try:
            # Fora da janela o retrato anterior já cobre o caso. Registro de
            # formato estranho (cache antigo) é descartado em vez de derrubar
            # a rodada inteira por causa de uma linha.
            velha = datetime.fromisoformat(anotado.get("em")) < corte
        except (AttributeError, TypeError, ValueError):
            velha = True
        if velha:
            del registro[chave]
            continue
        achado = itens.get(chave)
        if not achado:
            continue  # atividade sumiu do AVA; não invento linha para ela
        curso, item = achado
        saida.append({
            "curso": curso.get("code"),
            "label": item.get("label"),
            "url": item.get("url"),
            "cmid": chave.split(":", 1)[1],
            "nota": anotado.get("nota"),
            "de": anotado.get("de"),
            "feedback": item.get("feedback") or None,
            "em": anotado.get("em"),
        })
    saida.sort(key=lambda linha: (linha["em"], linha["curso"]), reverse=True)
    return saida


def _prazos_por_item(pacote):
    """``{(curso, cmid): prazo}`` de tudo que já tinha prazo no retrato."""
    prazos, vistos = {}, set()
    for curso in (pacote or {}).get("courses") or []:
        codigo = curso.get("code")
        for secao in curso.get("sections") or []:
            for item in secao.get("items") or []:
                if item.get("cmid") is None:
                    continue
                chave = f"{codigo}:{item['cmid']}"
                vistos.add(chave)
                if item.get("prazo"):
                    prazos[chave] = item["prazo"]
    return prazos, vistos


def prazos_novos(anterior, dados, estado, agora, janela_dias=7):
    """Prazo que apareceu ou mudou desde o retrato anterior.

    O robô relê o AVA cinco vezes ao dia, mas o e-mail é um só, de manhã. Um
    prazo publicado às 14h só chegava nele às 8h do dia seguinte, e quando o
    prazo é para hoje isso é tarde. Esta lista é o que autoriza o guia a
    mandar um segundo e-mail: não "o que está urgente" (isso repete todo dia),
    e sim "o que o AVA passou a dizer agora".

    O registro em ``estado`` existe contra oscilação de fonte: prazo que some
    e volta entre duas leituras avisaria de novo a cada ida e volta. Mesmo
    prazo, mesma atividade, uma vez por semana no máximo.
    """
    registro = (
        estado.setdefault("_prazos_avisados", {}) if estado is not None else {}
    )
    antes, conhecidos = _prazos_por_item(anterior)
    if not conhecidos:
        return []  # sem retrato anterior, todo prazo pareceria novidade

    corte = datetime.fromisoformat(agora) - timedelta(days=janela_dias)
    for chave in list(registro):
        try:
            velho = datetime.fromisoformat(registro[chave].get("em")) < corte
        except (AttributeError, TypeError, ValueError):
            velho = True
        if velho:
            del registro[chave]

    saida = []
    for curso in dados.get("courses") or []:
        codigo = curso.get("code")
        for secao in curso.get("sections") or []:
            for item in secao.get("items") or []:
                if item.get("cmid") is None or not item.get("prazo"):
                    continue
                chave = f"{codigo}:{item['cmid']}"
                prazo = item["prazo"]
                if antes.get(chave) == prazo:
                    continue  # o guia já dizia isso na leitura anterior
                if (registro.get(chave) or {}).get("prazo") == prazo:
                    continue  # já avisei este mesmo prazo faz pouco tempo
                registro[chave] = {"prazo": prazo, "em": agora}
                saida.append({
                    "curso": codigo,
                    "label": item.get("label"),
                    "url": item.get("url"),
                    "cmid": str(item["cmid"]),
                    "prazo": prazo,
                    "de": antes.get(chave),
                    "fonte": item.get("prazo_fonte"),
                    "conta_nota": bool(item.get("conta_nota")),
                    "atividade_nova": chave not in conhecidos,
                })
    saida.sort(key=lambda linha: linha["prazo"])
    return saida
