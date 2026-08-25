# -*- coding: utf-8 -*-
"""Orquestra fontes sem converter bug de programação em ausência normal."""
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from playwright.sync_api import sync_playwright

import sessao
from configuracao import (
    BR_TZ,
    cronograma_padrao,
    MAX_DISCUSSOES_POR_RUN,
    MAX_ENTREGAS_CONFERIDAS,
    MAX_ITENS_CONFERIDOS,
)
from dominio.acoes import TIPOS_DE_ABERTURA, conta_nota
from dominio.datas import sem_acento
from fontes import (
    boletim,
    calendario,
    cronograma,
    disciplinas,
    foruns,
    instrucoes,
    itens,
    meus_posts,
    notificacoes,
    participacao,
    portal,
)
from fontes.moodle import FalhaFonte
from fontes.moodle import user_id
from modelos import SourceResult
from saude import completar_idade_fontes


@dataclass
class Fonte:
    nome: str
    leitor: Callable
    cache: object = None
    obrigatoria: bool = False


def _quantidade(dados):
    if dados is None:
        return 0
    try:
        return len(dados)
    except TypeError:
        return 1


def executar_fonte(fonte, checked_at):
    """Captura apenas ``FalhaFonte``; qualquer exceção inesperada propaga."""
    try:
        resultado = fonte.leitor()
    except FalhaFonte as erro:
        return SourceResult(
            status="falhou",
            dados=fonte.cache,
            problemas=[str(erro)],
            checked_at=checked_at,
            from_cache=fonte.cache is not None,
            quantidade_atual=_quantidade(fonte.cache),
        )
    if isinstance(resultado, SourceResult):
        return resultado
    quantidade = _quantidade(resultado)
    return SourceResult(
        status="live" if quantidade else "vazio_confirmado",
        dados=resultado,
        checked_at=checked_at,
        last_live_at=checked_at,
        quantidade_atual=quantidade,
    )


def executar_fontes(fontes, checked_at):
    """Executa todas as fontes declaradas, mesmo após uma falha operacional."""
    return {
        fonte.nome: executar_fonte(fonte, checked_at) for fonte in fontes
    }


def politica_publicacao(resultados, anterior, attempted_at):
    """Preserva o retrato inteiro quando uma fonte obrigatória falha."""
    falhas = [
        nome
        for nome, (fonte, resultado) in resultados.items()
        if fonte.obrigatoria and resultado.status == "falhou"
    ]
    if not falhas:
        return None
    saida = dict(anterior or {"courses": []})
    saida["status"] = "coleta_incompleta"
    saida["snapshot_at"] = saida.get("snapshot_at") or saida.get("checked_at")
    saida["attempted_at"] = attempted_at
    saida["publication_id"] = attempted_at
    saida["problemas"] = [
        f"fonte obrigatória falhou: {nome}" for nome in falhas
    ]
    saida["fontes_status_tentativa"] = {
        nome: resultado.para_status()
        for nome, (_, resultado) in resultados.items()
    }
    return saida


def _eventos_por_cmid(eventos):
    """Todos os eventos de cada atividade, ordenados no tempo."""
    por_cmid = {}
    for evento in eventos:
        if not (evento.get("cmid") and evento.get("quando")):
            continue
        try:
            quando = datetime.fromisoformat(evento["quando"])
        except ValueError:
            continue
        por_cmid.setdefault(str(evento["cmid"]), []).append((quando, evento))
    for lista in por_cmid.values():
        lista.sort(key=lambda par: par[0])
    return por_cmid


def _prazo_por_cmid(eventos, agora_iso):
    """O próximo FECHAMENTO de cada atividade, nunca uma abertura.

    Uma mesma atividade tem vários eventos no calendário (abertura de envio,
    fechamento de envio, abertura da avaliação, fechamento da avaliação). Pegar
    "o próximo" resolveu a ordem aleatória, mas não o papel: a abertura também
    é um evento futuro, e virava prazo.
    """
    agora = datetime.fromisoformat(agora_iso)
    escolhidos = {}
    for cmid, lista in _eventos_por_cmid(eventos).items():
        fins = [
            (quando, evento)
            for quando, evento in lista
            if evento.get("tipo") not in TIPOS_DE_ABERTURA
        ]
        if not fins:
            continue
        futuros = [evento for quando, evento in fins if quando >= agora]
        escolhidos[cmid] = futuros[0] if futuros else fins[-1][1]
    return escolhidos


def janela_declarada(eventos, agora_iso):
    """Ainda há prazo por vir nesta atividade? ``True``/``False``/``None``.

    Resposta tirada do que o próprio Moodle declara no calendário, não de
    frases soltas na página. Os dois Laboratórios da Quinzena 2 ficaram com
    "abertura indefinida" em 09/08/2026 porque a página do Laboratório, antes
    do primeiro envio, não diz nem que está aberta nem que fechou — mas o
    calendário já dizia, com tipo e hora, que os envios fecham em 15/08 e as
    avaliações em 18/08.

    ``None`` continua sendo a resposta honesta quando não há evento com data
    para esta atividade: a meta é ler melhor, nunca afirmar sem base.
    """
    agora = datetime.fromisoformat(agora_iso)
    janela = {}
    for cmid, lista in _eventos_por_cmid(eventos).items():
        fins = [
            quando
            for quando, evento in lista
            if evento.get("tipo") not in TIPOS_DE_ABERTURA
        ]
        janela[cmid] = any(quando >= agora for quando in fins) if fins else None
    return janela


def _semana_do_cronograma(cronograma_curso, numero_semana):
    if not (cronograma_curso and numero_semana):
        return None
    return next(
        (
            valor
            for valor in cronograma_curso.get("semanas") or []
            if valor["n"] == numero_semana
        ),
        None,
    )


def _mesma_data(quando, semana):
    """A data do calendário do AVA é a carência daquela semana?"""
    if not (quando and semana and semana.get("carencia")):
        return False
    return quando[:10] == semana["carencia"][:10]


def _curso_anterior(anterior, curso_id, codigo):
    return next(
        (
            curso
            for curso in (anterior or {}).get("courses", [])
            if str(curso.get("id") or "") == str(curso_id)
            or curso.get("code") == codigo
        ),
        {},
    )


def _status_agregado(resultados, checked_at, nao_aplicavel=False):
    ativos = [resultado for resultado in resultados if resultado is not None]
    relevantes = [
        resultado
        for resultado in ativos
        if resultado.status != "nao_aplicavel"
    ]
    if (not ativos or not relevantes) and nao_aplicavel:
        return SourceResult(
            status="nao_aplicavel",
            dados=[],
            checked_at=checked_at,
            quantidade_atual=0,
        )
    falhas = [
        resultado
        for resultado in relevantes
        if resultado.status == "falhou"
    ]
    vivos = [
        resultado
        for resultado in relevantes
        if resultado.status in ("live", "vazio_confirmado")
    ]
    if falhas and not vivos:
        status = "falhou"
    elif falhas:
        status = "degradado"
    else:
        status = "live" if relevantes else "nao_aplicavel"
    return SourceResult(
        status=status,
        dados=[resultado.dados for resultado in ativos],
        problemas=[
            problema
            for resultado in ativos
            for problema in resultado.problemas
        ],
        checked_at=checked_at,
        from_cache=any(resultado.from_cache for resultado in ativos),
        truncado=any(resultado.truncado for resultado in ativos),
        quantidade_atual=sum(
            resultado.quantidade_atual for resultado in relevantes
        ),
        last_live_at=checked_at if vivos else None,
        detalhes={
            "falhas": len(falhas),
            "esperados": len(relevantes),
            "live": len(vivos),
        },
    )


def executar_coleta(estado, anterior=None):
    """Executa a coleta real usando fronteiras independentes por fonte."""
    hoje = datetime.now(BR_TZ).date()
    checked_at = datetime.now(timezone.utc).isoformat()
    cache_fontes = estado.setdefault("_fontes_cache", {})
    status_fontes = {}

    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(headless=True)
        contexto = sessao.novo_contexto(navegador)
        page = contexto.new_page()
        autenticado, como = sessao.garantir(page)
        if not autenticado:
            navegador.close()
            return None, "session_expired"
        if como == "login":
            sessao.salvar_sessao(contexto)
            print("  sessão renovada sozinha.")

        descoberta = executar_fonte(
            Fonte(
                "disciplinas",
                lambda: disciplinas.descobrir(page),
                obrigatoria=True,
            ),
            checked_at,
        )
        if descoberta.status == "falhou":
            status_fontes["disciplinas"] = descoberta.para_status()
            navegador.close()
            status_fontes = completar_idade_fontes(
                status_fontes,
                (anterior or {}).get("fontes_status") or {},
                checked_at,
            )
            return {
                "courses": [],
                "eventos": [],
                "notificacoes": [],
                "mensagens": [],
                "fontes_status": status_fontes,
                "_fonte_obrigatoria_falhou": True,
            }, "ok"

        descobertos = descoberta.dados or []
        print(f"Disciplinas encontradas: {len(descobertos)}")

        resultado_calendario = calendario.resultado(
            page,
            hoje,
            checked_at,
            cache=cache_fontes.get("calendario"),
        )
        if resultado_calendario.status in ("live", "vazio_confirmado"):
            cache_fontes["calendario"] = resultado_calendario.dados
        eventos = resultado_calendario.dados or []

        uid = user_id(page)
        cache_sinais = cache_fontes.get("notificacoes")
        if uid:
            resultado_sinais = executar_fonte(
                Fonte(
                    "notificacoes",
                    lambda: notificacoes.ler_sinais(page, uid),
                    cache=cache_sinais,
                ),
                checked_at,
            )
        else:
            resultado_sinais = SourceResult(
                status="falhou",
                dados=cache_sinais or {
                    "notificacoes": [],
                    "mensagens": [],
                },
                problemas=["não identifiquei o usuário do Moodle"],
                checked_at=checked_at,
                from_cache=cache_sinais is not None,
                quantidade_atual=(
                    len((cache_sinais or {}).get("notificacoes", []))
                    + len((cache_sinais or {}).get("mensagens", []))
                ),
            )
        if resultado_sinais.status in ("live", "vazio_confirmado"):
            cache_fontes["notificacoes"] = resultado_sinais.dados
        sinais = resultado_sinais.dados or {
            "notificacoes": [],
            "mensagens": [],
        }

        eventos_por_curso = {}
        for evento in eventos:
            eventos_por_curso.setdefault(
                str(evento.get("curso_id") or ""), []
            ).append(evento)

        cursos = []
        erros_estrutura = []
        resultados_cronograma = []
        resultados_boletim = []
        resultados_participacao = []
        resultados_meus_posts = []
        diagnosticos_forum = []
        indefinidos = verificados = nao_entregues = 0
        # O que o teto de conferência deixou de fora nesta leitura. Contar é o
        # que permite dizer isso no site: antes só saía no log da Action, que
        # ninguém lê, e o guia publicava a leitura como se fosse completa.
        nao_conferidos = 0
        orcamento = MAX_DISCUSSOES_POR_RUN
        cache_cronogramas = cache_fontes.setdefault("cronogramas", {})

        for descoberto in descobertos:
            codigo = disciplinas.codigo_de(descoberto)
            print(f"Lendo {codigo}...")
            try:
                secoes, links = disciplinas.ler_curso(page, descoberto)
            except FalhaFonte as erro:
                erros_estrutura.append(f"{codigo}: {erro}")
                continue
            modelo = disciplinas.modelo_de(secoes)
            disciplinas.marcar_fases(secoes)
            anterior_curso = _curso_anterior(
                anterior, descoberto["id"], codigo
            )

            url_cronograma = links.get("cronograma")
            if not url_cronograma and modelo == "regular":
                url_cronograma = cronograma_padrao(hoje)
            resultado_cronograma = cronograma.resultado(
                page,
                url_cronograma,
                checked_at,
                cache=cache_cronogramas.get(str(descoberto["id"]))
                or anterior_curso.get("cronograma"),
            )
            resultados_cronograma.append(resultado_cronograma)
            if resultado_cronograma.status == "live":
                cache_cronogramas[str(descoberto["id"])] = (
                    resultado_cronograma.dados
                )
            cronograma_curso = resultado_cronograma.dados

            eventos_do_curso = eventos_por_curso.get(
                str(descoberto["id"]), []
            )
            prazo_por_cmid = _prazo_por_cmid(eventos_do_curso, checked_at)
            janela_por_cmid = janela_declarada(eventos_do_curso, checked_at)

            cache_boletins = cache_fontes.setdefault("boletins", {})
            cache_medias = cache_fontes.setdefault("boletim_medias", {})
            cache_totais = cache_fontes.setdefault("boletim_totais", {})
            chave_curso = str(descoberto["id"])
            resultado_boletim = boletim.resultado(
                page,
                descoberto["id"],
                checked_at,
                cache=cache_boletins.get(chave_curso),
            )
            resultados_boletim.append(resultado_boletim)
            media_boletim = (resultado_boletim.detalhes or {}).get("media")
            totais_boletim = (resultado_boletim.detalhes or {}).get("totais")
            if resultado_boletim.status == "live":
                cache_boletins[chave_curso] = resultado_boletim.dados
                cache_medias[chave_curso] = media_boletim
                cache_totais[chave_curso] = totais_boletim or []
            elif media_boletim is None:
                # Leitura falhou e as notas vieram do cache. A média mora só
                # na telemetria, então sem guardá-la à parte a aba "Como
                # estou" perdia a linha da disciplina inteira.
                media_boletim = cache_medias.get(chave_curso)
                totais_boletim = cache_totais.get(chave_curso)
            notas_por_cmid = resultado_boletim.dados or {}

            # Em quais fóruns desta disciplina ele já escreveu. Fonte separada
            # porque a varredura de fóruns prioriza post institucional e corta
            # em 10 por discussão: num fórum de 800 respostas o post dele
            # simplesmente não sobrevive ao teto, então ela não serve para
            # responder "eu participei aqui?".
            cache_meus_posts = cache_fontes.setdefault("meus_posts", {})
            resultado_posts = meus_posts.resultado(
                page,
                uid,
                descoberto["id"],
                checked_at,
                cache=cache_meus_posts.get(chave_curso),
            )
            resultados_meus_posts.append(resultado_posts)
            if resultado_posts.status in ("live", "vazio_confirmado"):
                cache_meus_posts[chave_curso] = resultado_posts.dados
            foruns_com_post = resultado_posts.dados or {}
            sei_onde_postei = resultado_posts.status in (
                "live",
                "vazio_confirmado",
            )

            for secao in secoes:
                numero_semana = None
                encontrada = re.match(r"Semana (\d+)$", secao["title"])
                if encontrada and modelo == "regular":
                    numero_semana = int(encontrada.group(1))
                for item in secao["items"]:
                    item["conta_nota"] = conta_nota(
                        modelo, item, secao["title"]
                    )
                    # ``postei``: True, False ou None. O None é obrigatório e
                    # não é detalhe: sem leitura boa das mensagens dele, o
                    # guia não pode dizer nem que participou nem que faltou.
                    if item.get("type") == "forum":
                        item["postei"] = (
                            meus_posts.chave_forum(item.get("label"))
                            in foruns_com_post
                            if sei_onde_postei
                            else None
                        )
                    nota = notas_por_cmid.get(str(item.get("cmid")))
                    if nota:
                        item["nota"] = nota["nota"]
                        item["nota_txt"] = nota["nota_txt"]
                        item["tem_nota"] = nota["tem_nota"]
                        item["feedback"] = nota["feedback"]
                    item["prazo"] = None
                    item["prazo_fonte"] = None
                    item["carencia"] = None
                    semana = _semana_do_cronograma(
                        cronograma_curso, numero_semana
                    )
                    evento = prazo_por_cmid.get(str(item.get("cmid")))
                    if evento:
                        item["prazo"] = evento["quando"]
                        item["prazo_fonte"] = "calendário do AVA"
                        # O AVA fecha a atividade no fim da CARÊNCIA, não no
                        # vencimento. Mostrar a data do calendário como prazo
                        # dá quatro dias a mais do que o cronograma dá: a S2
                        # vencia em 05/08 e o guia dizia 09/08.
                        if _mesma_data(evento["quando"], semana):
                            item["prazo"] = semana["vencimento"]
                            item["carencia"] = semana["carencia"]
                            item["prazo_fonte"] = (
                                "cronograma oficial da Univesp"
                            )
                    elif semana and item["conta_nota"]:
                        item["prazo"] = semana["vencimento"]
                        item["carencia"] = semana["carencia"]
                        item["prazo_fonte"] = (
                            "cronograma oficial da Univesp"
                        )

            lista_foruns = [
                {"label": item["label"], "url": item["url"]}
                for secao in secoes
                for item in secao["items"]
                if item["type"] == "forum" and item.get("url")
            ]
            print(
                f"  {len(lista_foruns)} fórum(ns) a varrer "
                f"(orçamento {orcamento})"
            )
            diagnostico_forum = {}
            espacos_de_grupo = []
            avisos, orcamento = foruns.varrer_foruns(
                page,
                lista_foruns,
                estado,
                orcamento,
                hoje,
                diagnostico_forum,
                curso_id=descoberto["id"],
                espacos_de_grupo=espacos_de_grupo,
            )
            diagnosticos_forum.append(diagnostico_forum)
            autores = (
                estado.get("_autores_institucionais", {}).get(
                    str(descoberto["id"]), []
                )
            )
            avisos, _, _ = foruns.priorizar_posts(avisos, autores, 15)

            pendentes = [
                (secao, item)
                for secao in secoes
                if not secao.get("locked")
                for item in secao["items"]
                if item.get("status") != "Concluído"
                and (
                    item.get("status") == "Pendente"
                    or item.get("conta_nota")
                )
            ]
            if len(pendentes) > MAX_ITENS_CONFERIDOS:
                sobra = len(pendentes) - MAX_ITENS_CONFERIDOS
                nao_conferidos += sobra
                print(f"  aviso: {sobra} item(ns) de {codigo} ficaram sem "
                      "conferência de abertura nesta leitura")
            for secao, item in pendentes[:MAX_ITENS_CONFERIDOS]:
                if secao.get("fase") == "AIA":
                    item["aberto"] = False
                    item["motivo_fechado"] = (
                        "a ambientação (AIA) encerrou"
                    )
                    continue
                if item.get("type") == "workshop":
                    # Uma leitura só: a página do Laboratório responde as duas
                    # perguntas (ainda há o que fazer, e qual fase falta).
                    item.update(
                        itens.estado_workshop(page, item.get("url"))
                    )
                elif item.get("type") == "quiz":
                    # Mesma página que ``item_aberto`` abriria, lida inteira:
                    # traz também a nota e as tentativas usadas.
                    item.update(itens.estado_quiz(page, item.get("url")))
                else:
                    item["aberto"] = itens.item_aberto(page, item.get("url"))
                # Só onde a página não afirmou nada. O calendário responde por
                # último para nunca contradizer a atividade em si, e responde
                # com o que o Moodle declarou — não com suposição sobre o que
                # o silêncio da página quer dizer.
                if item["aberto"] is None and item.get("cmid"):
                    declarado = janela_por_cmid.get(str(item["cmid"]))
                    if declarado is not None:
                        item["aberto"] = declarado
                        item["aberto_fonte"] = "calendário do AVA"
                        if declarado is False:
                            item["motivo_fechado"] = (
                                "todos os prazos do calendário já passaram"
                            )
                verificados += 1
                if item["aberto"] is None:
                    indefinidos += 1
                elif item["aberto"] is False:
                    item["motivo_fechado"] = (
                        "o AVA diz que não está aberta"
                    )

            # Segunda prova de entrega, só onde o selo do Moodle é suspeito:
            # atividade que vale nota, marcada como concluída e sem nota
            # lançada. Foi assim que a S2 do COM100 passou batido — concluída
            # por visualização, sem nenhuma tentativa, com prazo em aberto.
            suspeitos = [
                item
                for secao in secoes
                if not secao.get("locked")
                for item in secao["items"]
                if item.get("status") == "Concluído"
                and item.get("type") in ("quiz", "assign")
                and not item.get("tem_nota")
            ]
            for item in suspeitos[:MAX_ENTREGAS_CONFERIDAS]:
                if item.get("type") == "quiz":
                    # A mesma visita responde "entregou?" e "quanto tirou?".
                    # É o que resolve o SOC100, cujo boletim vem vazio do AVA:
                    # sem isto, a disciplina inteira fica sem nota no guia.
                    item.update(itens.estado_quiz(page, item.get("url")))
                else:
                    item["entrega_confirmada"] = itens.entrega_feita(
                        page, item.get("url"), item.get("type")
                    )
                if item["entrega_confirmada"] is False:
                    nao_entregues += 1
                    print(
                        f"  ATENÇÃO: {codigo} · {item['label'][:50]} está "
                        "'Concluído' no AVA sem entrega registrada"
                    )
            if len(suspeitos) > MAX_ENTREGAS_CONFERIDAS:
                sobra = len(suspeitos) - MAX_ENTREGAS_CONFERIDAS
                nao_conferidos += sobra
                print(
                    f"  aviso: {sobra} entrega(s) suspeita(s) de {codigo} "
                    "ficaram sem conferência"
                )

            # A nota do questionário só entra onde o boletim não respondeu. O
            # boletim é a nota lançada pelo facilitador e continua mandando;
            # esta é a nota que o próprio questionário calculou, e existe para
            # o caso em que o relatório do usuário vem sem nenhuma linha
            # (SOC100, conferido no AVA em 25/08/2026).
            for secao in secoes:
                for item in secao["items"]:
                    resumo_quiz = item.get("quiz")
                    if not resumo_quiz:
                        continue
                    item["nota_fonte"] = "boletim" if item.get(
                        "tem_nota"
                    ) else None
                    if item.get("tem_nota") or resumo_quiz.get("nota") is None:
                        continue
                    item["nota"] = resumo_quiz["nota"]
                    item["nota_txt"] = resumo_quiz["nota_txt"]
                    item["tem_nota"] = True
                    item["nota_fonte"] = "página do questionário"

            cache_participacao = cache_fontes.setdefault("participacao", {})
            resultado_participacao = participacao.resultado(
                page,
                secoes,
                checked_at,
                cache=cache_participacao.get(chave_curso),
            )
            if resultado_participacao.status == "live":
                cache_participacao[chave_curso] = (
                    resultado_participacao.dados
                )
            if resultado_participacao.status != "nao_aplicavel":
                resultados_participacao.append(resultado_participacao)

            try:
                paginas_instrucao = instrucoes.ler(page, secoes, hoje)
            except FalhaFonte as erro:
                paginas_instrucao = []
                print(f"  aviso: instruções da quinzena não lidas ({erro})")

            cursos.append(
                {
                    "code": codigo,
                    "name": descoberto["nome"],
                    "id": descoberto["id"],
                    "modelo": modelo,
                    "progress_pct": descoberto.get("pct"),
                    "links": links,
                    "cronograma": cronograma_curso,
                    "avisos": avisos,
                    "espacos_de_grupo": espacos_de_grupo,
                    "paginas_instrucao": paginas_instrucao,
                    "boletim": {
                        "status": resultado_boletim.status,
                        "media": media_boletim,
                        "totais": totais_boletim or [],
                        "itens": len(notas_por_cmid),
                    },
                    "participacao": resultado_participacao.dados,
                    "sections": secoes,
                }
            )

        # O portal é o último passo de propósito: ele loga noutro sistema, e
        # se essa etapa quebrar o guia já tem o AVA inteiro lido na mão.
        resultado_portal = portal.resultado(
            contexto, checked_at, cache=cache_fontes.get("portal")
        )
        if resultado_portal.status in ("live", "parcial"):
            cache_fontes["portal"] = resultado_portal.dados
        dados_portal = resultado_portal.dados or {}

        navegador.close()

    if erros_estrutura:
        descoberta.status = "falhou"
        descoberta.problemas.extend(erros_estrutura)
        descoberta.dados = cursos
        descoberta.quantidade_atual = len(cursos)
    else:
        descoberta.quantidade_atual = len(cursos)

    agregado_cronograma = _status_agregado(
        resultados_cronograma, checked_at, nao_aplicavel=True
    )
    forum_falhas = sum(
        int(diag.get("falhas") or 0) for diag in diagnosticos_forum
    )
    forum_live = sum(
        int(diag.get("listas_live") or 0) for diag in diagnosticos_forum
    )
    forum_pulados = sum(
        int(diag.get("pulados_orcamento") or 0)
        for diag in diagnosticos_forum
    )
    if not diagnosticos_forum:
        status_forum = "nao_aplicavel"
    elif forum_falhas and not forum_live:
        status_forum = "falhou"
    elif forum_falhas:
        status_forum = "degradado"
    elif forum_pulados:
        status_forum = "parcial"
    else:
        status_forum = "live"
    resultado_forum = SourceResult(
        status=status_forum,
        dados=[curso.get("avisos", []) for curso in cursos],
        problemas=(
            [f"{forum_falhas} falha(s) ao ler fóruns"]
            if forum_falhas
            else []
        ),
        checked_at=checked_at,
        from_cache=any(
            diag.get("cache_usado_em_falha")
            for diag in diagnosticos_forum
        ),
        truncado=any(
            diag.get("truncado") for diag in diagnosticos_forum
        ),
        quantidade_atual=sum(
            len(curso.get("avisos", [])) for curso in cursos
        ),
        last_live_at=checked_at if forum_live else None,
        detalhes={
            "foruns": sum(
                int(diag.get("foruns") or 0)
                for diag in diagnosticos_forum
            ),
            "listas_live": forum_live,
            "falhas": forum_falhas,
            "pulados_orcamento": forum_pulados,
            "posts_institucionais_vistos": sum(
                int(diag.get("posts_institucionais_vistos") or 0)
                for diag in diagnosticos_forum
            ),
            "posts_institucionais_guardados": sum(
                int(diag.get("posts_institucionais_guardados") or 0)
                for diag in diagnosticos_forum
            ),
        },
    )
    problemas_itens = []
    if indefinidos:
        problemas_itens.append(f"{indefinidos} item(ns) com abertura indefinida")
    if nao_conferidos:
        problemas_itens.append(
            f"{nao_conferidos} item(ns) ficaram sem conferência pelo teto da "
            "rodada"
        )
    resultado_itens = SourceResult(
        status="parcial" if indefinidos else "live",
        dados=None,
        problemas=problemas_itens,
        checked_at=checked_at,
        from_cache=False,
        # Teto atingido é leitura incompleta, e o site tem que dizer isso com
        # a mesma clareza com que diz o corte dos fóruns.
        truncado=bool(nao_conferidos),
        quantidade_atual=verificados,
        last_live_at=checked_at,
        detalhes={
            "indefinidos": indefinidos,
            "entregas_nao_confirmadas": nao_entregues,
            "nao_conferidos": nao_conferidos,
        },
    )
    agregado_boletim = _status_agregado(
        resultados_boletim, checked_at, nao_aplicavel=True
    )
    agregado_participacao = _status_agregado(
        resultados_participacao, checked_at, nao_aplicavel=True
    )
    agregado_meus_posts = _status_agregado(
        resultados_meus_posts, checked_at, nao_aplicavel=True
    )

    resultados_finais = {
        "portal": resultado_portal,
        "disciplinas": descoberta,
        "calendario": resultado_calendario,
        "cronograma": agregado_cronograma,
        "foruns": resultado_forum,
        "itens": resultado_itens,
        "boletim": agregado_boletim,
        "participacao": agregado_participacao,
        "meus_posts": agregado_meus_posts,
        "notificacoes": resultado_sinais,
    }
    status_fontes = {
        nome: resultado.para_status()
        for nome, resultado in resultados_finais.items()
    }
    status_fontes = completar_idade_fontes(
        status_fontes,
        (anterior or {}).get("fontes_status") or {},
        checked_at,
    )
    # Boletim de fora da lista que deixa a Action vermelha: ele só acrescenta
    # prova de entrega. Sem ele o guia fica mais cauteloso (mantém o item na
    # fila), nunca menos — o oposto das fontes de prazo, cuja ausência esconde
    # obrigação. O estado dele continua visível em `fontes_status`.
    degradadas = [
        nome
        for nome, resultado in resultados_finais.items()
        if resultado.status in ("falhou", "degradado")
        and nome not in ("boletim", "participacao", "meus_posts", "portal")
    ]
    return {
        "courses": cursos,
        "notificacoes": sinais.get("notificacoes", []),
        "mensagens": sinais.get("mensagens", []),
        "eventos": eventos,
        "portal": dados_portal,
        "fontes_status": status_fontes,
        "_fonte_obrigatoria_falhou": descoberta.status == "falhou",
        "_fontes_degradadas": degradadas,
    }, "ok"
