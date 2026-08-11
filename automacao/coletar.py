# -*- coding: utf-8 -*-
"""Ponto de entrada compatível do coletor modular."""
import os  # reexport de compatibilidade para injeção de falha nos testes
import sys
from datetime import datetime, timezone

import persistencia as _persistencia
from configuracao import BR_TZ, DATA_PATH, ESTADO_PATH
from dominio.acoes import (
    entrega_provada,
    identidade_item,
    montar_acoes,
    notas_novas,
    novidades,
    prazos_novos,
    urgencia_de,
)
from dominio.datas import achar_datas, sem_acento
from dominio.prazos import casar_prazos, extrair_prazos
from fontes.foruns import varrer_foruns
from fontes.itens import SINAIS_FECHADO, SINAIS_INDEFINIDO
from persistencia import carregar, gravar_json, normalizar_estado
from pipeline import executar_coleta
from saude import resumo_fontes, validar_cobertura

def gravar_snapshot(data, estado):
    return _persistencia.gravar_snapshot(data, estado, DATA_PATH, ESTADO_PATH)

def coletar(estado):
    anterior = carregar(DATA_PATH, None, critico=True)
    return executar_coleta(estado, anterior)

def _saida_preservada(anterior, status, agora, problemas, dados=None):
    saida = dict(anterior or {"courses": []})
    saida.update({
        "status": status, "attempted_at": agora, "publication_id": agora,
        "problemas": problemas,
    })
    saida["snapshot_at"] = saida.get("snapshot_at") or saida.get("checked_at")
    if dados:
        saida["fontes_tentativa"] = resumo_fontes(dados)
        saida["fontes_status_tentativa"] = dados.get("fontes_status") or {}
    return saida

def _degradacao_publicavel(dados):
    if dados.get("_fonte_obrigatoria_falhou"):
        return False
    status = dados.get("fontes_status") or {}
    for nome in dados.get("_fontes_degradadas") or []:
        if nome in ("calendario", "cronograma", "foruns"):
            if not (status.get(nome) or {}).get("from_cache"):
                return False
    return bool(dados.get("_fontes_degradadas"))

def main():
    anterior = carregar(DATA_PATH, None, critico=True)
    estado = normalizar_estado(carregar(ESTADO_PATH, {}))
    agora = datetime.now(timezone.utc).isoformat()
    dados, status = coletar(estado)

    if status == "session_expired":
        saida = _saida_preservada(
            anterior, "session_expired", agora,
            ["não consegui autenticar no AVA nesta tentativa"],
        )
        gravar_json(DATA_PATH, saida)
        print("SESSÃO EXPIRADA - mantive o último retrato e avisei no site.")
        return 0

    fontes = resumo_fontes(dados)
    confiavel, problemas = validar_cobertura(dados, anterior)
    degradada = not confiavel and _degradacao_publicavel(dados)
    if not confiavel and not degradada:
        saida = _saida_preservada(
            anterior, "coleta_incompleta", agora, problemas, dados
        )
        gravar_json(DATA_PATH, saida)
        print("COLETA INCOMPLETA, mantive o último retrato válido:")
        for problema in problemas:
            print(f"  - {problema}")
        return 2

    momento = datetime.now(BR_TZ)
    hoje = momento.date()
    acoes, encerrados, higiene, confirmar = montar_acoes(
        dados, hoje, agora=momento
    )
    saida = {
        "status": "coleta_degradada" if degradada else "ok",
        "checked_at": agora, "snapshot_at": agora, "attempted_at": agora,
        "publication_id": agora, "fontes": fontes,
        "problemas": problemas if degradada else [],
        "fontes_status": dados.get("fontes_status") or {},
        "courses": dados["courses"], "eventos": dados.get("eventos", []),
        "notificacoes": dados.get("notificacoes", []),
        "mensagens": dados.get("mensagens", []),
        "acoes": acoes, "encerrados": encerrados, "higiene": higiene,
        "confirmar": confirmar,
        "novidades": novidades(anterior, dados),
        "notas_novas": notas_novas(anterior, dados, estado, agora),
        "prazos_novos": prazos_novos(anterior, dados, estado, agora),
    }
    gravar_snapshot(saida, estado)
    print(
        f"{saida['status'].upper()}. {len(acoes)} ação(ões), "
        f"{len(higiene)} de higiene, {len(confirmar)} a confirmar, "
        f"{len(encerrados)} encerrada(s). Fontes: {fontes}")
    return 2 if degradada else 0

if __name__ == "__main__":
    sys.exit(main())
