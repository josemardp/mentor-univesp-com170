# -*- coding: utf-8 -*-
"""Ponto de entrada compatível do coletor modular."""
import os  # reexport de compatibilidade para injeção de falha nos testes
import sys
from datetime import date, datetime, timezone

import persistencia as _persistencia
from configuracao import BR_TZ, DATA_PATH, ESTADO_PATH, PROVAS_PATH
from dominio.acoes import (
    disciplinas_so_no_portal,
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

def _com_fuso(iso):
    """Data ISO com o fuso de Brasília garantido. Data ilegível vira ``None``.

    Devolver ``None`` em vez de deixar passar é o que impede uma linha
    digitada errada de virar "prova sem data" no meio da fila.
    """
    if not iso:
        return None
    try:
        quando = datetime.fromisoformat(str(iso))
    except ValueError:
        return None
    return (quando if quando.tzinfo else quando.replace(tzinfo=BR_TZ)).isoformat()


def provas_conferidas_a_mao():
    """Provas registradas à mão, quando ainda valem.

    O Sistema de Provas fica atrás de verificação anti-robô, e contornar isso
    está fora de escopo por decisão. Então a data vem de uma conferência
    humana, e vem com validade: registro velho não pode continuar afirmando o
    dia da prova depois que o bimestre virou.

    Sem arquivo, sem prova. Nunca inventa e nunca sobrescreve leitura viva.
    """
    registro = carregar(PROVAS_PATH, None) or {}
    provas = registro.get("provas") or []
    if not provas:
        return {}
    # Este arquivo é escrito à mão, e a mão esquece o fuso. Sem o ``-03:00`` a
    # data vira "ingênua" e qualquer comparação com o agora do robô levanta
    # TypeError: o site publicava a prova e o e-mail das 8h morria. Quem
    # completa é aqui, uma vez, na entrada.
    provas = [{**p, "inicio": _com_fuso(p.get("inicio")),
               "fim": _com_fuso(p.get("fim"))} for p in provas]
    provas = [p for p in provas if p.get("inicio")]
    if not provas:
        return {}
    vale_ate = registro.get("vale_ate")
    if vale_ate:
        try:
            if datetime.now(BR_TZ).date() > date.fromisoformat(vale_ate):
                return {}
        except ValueError:
            return {}
    return {
        "provas": provas,
        "provas_origem": "conferido à mão",
        "provas_conferido_em": registro.get("conferido_em"),
    }


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
    # O portal é completado antes de montar a fila, senão a prova conferida à
    # mão fica no site e não vira compromisso, que é justamente o que ela
    # precisa virar.
    portal = dict(dados.get("portal") or {})
    if portal:
        # O confronto entre as duas listas de matrícula precisa do AVA já
        # lido: portal sem AVA não é comparação, é metade dela.
        portal["_so_no_portal"] = disciplinas_so_no_portal(dados)
    # Prova conferida à mão entra quando o Sistema de Provas não pôde ser lido,
    # e é o caso normal: aquele sistema fica atrás de verificação anti-robô.
    # Nunca sobrescreve leitura ao vivo, e carrega a data da conferência para o
    # site poder dizer de quando ela é.
    if not portal.get("provas"):
        manual = provas_conferidas_a_mao()
        if manual:
            portal = {**portal, **manual}
    dados["portal"] = portal
    acoes, encerrados, higiene, confirmar = montar_acoes(
        dados, hoje, agora=momento
    )
    saida = {
        "portal": portal,
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
