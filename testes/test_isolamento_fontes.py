# -*- coding: utf-8 -*-
"""Isolamento: falha operacional degrada; bug de código derruba."""
import copy
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

from dominio.acoes import montar_acoes  # noqa: E402
from fontes.moodle import FalhaFonte  # noqa: E402
from modelos import SourceResult  # noqa: E402
from pipeline import Fonte, executar_fonte, executar_fontes, politica_publicacao  # noqa: E402
from saude import completar_idade_fontes, fontes_paradas  # noqa: E402

fixture = json.loads(
    (ROOT / "testes" / "fixtures" / "snapshot_dourado_sanitizado.json")
    .read_text(encoding="utf-8")
)
dados = copy.deepcopy(fixture["dados"])
dados["courses"][0]["sections"][0]["items"].append(
    {
        "cmid": "1003",
        "label": "Videoaula sanitizada",
        "type": "page",
        "url": "https://ava.univesp.br/mod/page/view.php?id=1003",
        "status": "Pendente",
        "conta_nota": True,
        "aberto": True,
        "prazo": "2026-07-29T23:59:00-03:00",
        "prazo_fonte": "cronograma oficial da Univesp",
        "carencia": "2026-08-02T23:59:00-03:00",
    }
)
agora = "2026-07-25T20:00:00-03:00"


def fora():
    raise FalhaFonte("fórum fora")


fontes = [
    Fonte("foruns", fora, cache=dados["courses"][1]["avisos"]),
    Fonte("calendario", lambda: dados["eventos"]),
    Fonte(
        "cronograma",
        lambda: dados["courses"][0]["cronograma"]["semanas"],
    ),
]
resultados = executar_fontes(fontes, agora)
acoes, _, _, _ = montar_acoes(dados, date.fromisoformat("2026-07-25"))
assert resultados["foruns"].status == "falhou"
assert resultados["foruns"].from_cache is True
assert resultados["calendario"].status == "live"
assert resultados["cronograma"].status == "live"
assert any(acao.get("prazo_fonte") == "calendário do AVA" for acao in acoes)
assert any(
    acao.get("prazo_fonte") == "cronograma oficial da Univesp"
    for acao in acoes
)
print("ok | fórum falha e as ações das demais fontes continuam")

anterior = {
    "status": "ok",
    "snapshot_at": "2026-07-25T12:00:00-03:00",
    "courses": [{"id": "anterior"}],
}
descoberta = Fonte("disciplinas", fora, cache=None, obrigatoria=True)
pares = {
    nome: (fonte, executar_fonte(fonte, agora))
    for nome, fonte in {"disciplinas": descoberta}.items()
}
preservado = politica_publicacao(pares, anterior, agora)
assert preservado["status"] == "coleta_incompleta"
assert preservado["courses"] == anterior["courses"]
assert preservado["snapshot_at"] == anterior["snapshot_at"]
print("ok | falha da descoberta preserva o retrato anterior")


def bug():
    raise TypeError("assinatura mudou")


try:
    executar_fonte(Fonte("foruns", bug, cache=[]), agora)
except TypeError:
    print("ok | exceção inesperada propaga e derruba a execução")
else:
    raise AssertionError("TypeError foi engolido como fonte vazia")

status = completar_idade_fontes(
    {
        "foruns": SourceResult(
            status="falhou",
            dados=[],
            checked_at=agora,
            from_cache=True,
            truncado=True,
            quantidade_atual=10,
        ).para_status()
    },
    {"foruns": {"last_live_at": "2026-07-25T19:00:00-03:00"}},
    agora,
)
assert status["foruns"]["status"] == "falhou"
assert status["foruns"]["idade_segundos"] == 3600
assert status["foruns"]["quantidade_atual"] == 10
assert status["foruns"]["from_cache"] is True
assert status["foruns"]["truncado"] is True
print("ok | status expõe estado, idade, quantidade, cache e truncamento")

# Regressão de 05/09/2026: o Outlook ficou cinco dias em "falhou" sem a Action
# ficar vermelha (é fonte que não bloqueia, e isso está certo) e sem uma linha
# no e-mail diário (isso estava errado). O idade_segundos já existia e ninguém
# lia.
paradas = fontes_paradas({
    "fontes_status": {
        "outlook": {
            "status": "falhou",
            "idade_segundos": 362870,
            "problemas": ["a lista de mensagens não montou"],
        },
        "calendario": {"status": "live", "idade_segundos": 0, "problemas": []},
        "portal": {
            "status": "parcial",
            "idade_segundos": 0,
            "problemas": ["o Sistema de Provas pediu verificação de robô"],
        },
        "boletim": {
            "status": "falhou",
            "idade_segundos": 600,
            "problemas": ["uma disciplina não renderizou"],
        },
        "email_novo": {"status": "falhou", "idade_segundos": None, "problemas": []},
    }
})
nomes = [p["fonte"] for p in paradas]
assert nomes == ["email_novo", "outlook"], nomes
assert paradas[1]["horas"] == 100
assert paradas[1]["problema"] == "a lista de mensagens não montou"
assert paradas[0]["horas"] is None
assert paradas[0]["problema"] == "sem motivo declarado"
print("ok | fonte parada há mais de um dia é reportada; falha recente e 'parcial' não viram ruído")
