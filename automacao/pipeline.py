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
    CRONOGRAMA_PADRAO,
    MAX_DISCUSSOES_POR_RUN,
    MAX_ITENS_CONFERIDOS,
)
from dominio.acoes import conta_nota
from dominio.datas import sem_acento
from fontes import calendario, cronograma, disciplinas, foruns, itens, notificacoes
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
    if not ativos and nao_aplicavel:
        return SourceResult(
            status="nao_aplicavel",
            dados=[],
            checked_at=checked_at,
            quantidade_atual=0,
        )
    falhas = [resultado for resultado in ativos if resultado.status == "falhou"]
    vivos = [
        resultado
        for resultado in ativos
        if resultado.status in ("live", "vazio_confirmado")
    ]
    if falhas and not vivos:
        status = "falhou"
    elif falhas:
        status = "degradado"
    else:
        status = "live" if ativos else "nao_aplicavel"
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
        quantidade_atual=sum(resultado.quantidade_atual for resultado in ativos),
        last_live_at=checked_at if vivos else None,
        detalhes={
            "falhas": len(falhas),
            "esperados": len(ativos),
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
        diagnosticos_forum = []
        indefinidos = verificados = 0
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
                url_cronograma = CRONOGRAMA_PADRAO
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

            prazo_por_cmid = {
                evento["cmid"]: evento
                for evento in eventos_por_curso.get(
                    str(descoberto["id"]), []
                )
                if evento.get("cmid")
            }
            for secao in secoes:
                numero_semana = None
                encontrada = re.match(r"Semana (\d+)$", secao["title"])
                if encontrada and modelo == "regular":
                    numero_semana = int(encontrada.group(1))
                for item in secao["items"]:
                    item["conta_nota"] = conta_nota(
                        modelo, item, secao["title"]
                    )
                    item["prazo"] = None
                    item["prazo_fonte"] = None
                    item["carencia"] = None
                    evento = prazo_por_cmid.get(str(item.get("cmid")))
                    if evento:
                        item["prazo"] = evento["quando"]
                        item["prazo_fonte"] = "calendário do AVA"
                    elif (
                        numero_semana
                        and cronograma_curso
                        and item["conta_nota"]
                    ):
                        semana = next(
                            (
                                valor
                                for valor in cronograma_curso["semanas"]
                                if valor["n"] == numero_semana
                            ),
                            None,
                        )
                        if semana:
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
            avisos, orcamento = foruns.varrer_foruns(
                page,
                lista_foruns,
                estado,
                orcamento,
                hoje,
                diagnostico_forum,
                curso_id=descoberto["id"],
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
            for secao, item in pendentes[:MAX_ITENS_CONFERIDOS]:
                if secao.get("fase") == "AIA":
                    item["aberto"] = False
                    item["motivo_fechado"] = (
                        "a ambientação (AIA) encerrou"
                    )
                    continue
                item["aberto"] = itens.item_aberto(page, item.get("url"))
                verificados += 1
                if item["aberto"] is None:
                    indefinidos += 1
                elif item["aberto"] is False:
                    item["motivo_fechado"] = (
                        "o AVA diz que não está aberta"
                    )

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
                    "sections": secoes,
                }
            )

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
    resultado_itens = SourceResult(
        status="degradado" if indefinidos else "live",
        dados=None,
        problemas=(
            [f"{indefinidos} item(ns) com abertura indefinida"]
            if indefinidos
            else []
        ),
        checked_at=checked_at,
        quantidade_atual=verificados,
        last_live_at=checked_at,
        detalhes={"indefinidos": indefinidos},
    )

    resultados_finais = {
        "disciplinas": descoberta,
        "calendario": resultado_calendario,
        "cronograma": agregado_cronograma,
        "foruns": resultado_forum,
        "itens": resultado_itens,
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
    degradadas = [
        nome
        for nome, resultado in resultados_finais.items()
        if resultado.status in ("falhou", "degradado")
    ]
    return {
        "courses": cursos,
        "notificacoes": sinais.get("notificacoes", []),
        "mensagens": sinais.get("mensagens", []),
        "eventos": eventos,
        "fontes_status": status_fontes,
        "_fonte_obrigatoria_falhou": descoberta.status == "falhou",
        "_fontes_degradadas": degradadas,
    }, "ok"
