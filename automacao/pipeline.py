# -*- coding: utf-8 -*-
"""Orquestra fontes sem converter bug de programação em ausência normal."""
from dataclasses import dataclass
from typing import Callable

from fontes.moodle import FalhaFonte
from modelos import SourceResult


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
