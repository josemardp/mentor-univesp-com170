# -*- coding: utf-8 -*-
"""Teste dourado do contrato público antes da modularização."""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

import coletar as C  # noqa: E402


def selecionar(acao):
    return {
        "curso": acao["curso"],
        "secao": acao["secao"],
        "o_que": acao["o_que"],
        "prazo": acao.get("prazo"),
        "prioridade_ate": acao.get("prioridade_ate"),
        "urgencia": acao["urgencia"],
    }


fixture = json.loads(
    (ROOT / "testes" / "fixtures" / "snapshot_dourado_sanitizado.json")
    .read_text(encoding="utf-8")
)
dados = fixture["dados"]
esperado = fixture["esperado"]
hoje = date.fromisoformat(fixture["hoje"])

acoes, _, higiene, confirmar = C.montar_acoes(dados, hoje)
fontes = C.resumo_fontes(dados)
estados = [
    {
        "curso": curso["code"],
        "secao": secao["title"],
        "cmid": str(item["cmid"]),
        "status": item.get("status"),
        "aberto": item.get("aberto"),
        "prazo": item.get("prazo"),
    }
    for curso in dados["courses"]
    for secao in curso["sections"]
    for item in secao["items"]
]
confirmar_resumo = [
    {
        "curso": item["curso"],
        "quando": item["quando"],
        "autor": item.get("autor"),
    }
    for item in confirmar
]

assert [selecionar(item) for item in acoes] == esperado["acoes"]
assert fontes == esperado["fontes"]
assert estados == esperado["estados"]
assert [item["o_que"] for item in higiene] == esperado["higiene"]
assert confirmar_resumo == esperado["confirmar"]

print("Teste dourado passou: ações, prazos, fontes e estados permanecem iguais.")
