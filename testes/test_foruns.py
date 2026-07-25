# -*- coding: utf-8 -*-
"""Contratos de prioridade, autoridade e corte dos fóruns."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

from fontes import foruns as F  # noqa: E402


def post(numero, autor, prazos=False, texto=None):
    return {
        "id": str(numero),
        "autor": autor,
        "data": f"2026-07-25T10:{numero % 60:02d}:00-03:00",
        "texto": texto or f"Post {numero}",
        "prazos": (
            [{"quando": "2026-08-01T23:59:00-03:00", "confianca": "alta"}]
            if prazos
            else []
        ),
    }


institucionais = {"Docente A", "Facilitadora B", "Equipe C"}
misturados = [
    post(numero, f"Colega {numero}", prazos=(numero == 4))
    for numero in range(1, 41)
] + [
    post(101, "Docente A"),
    post(102, "Facilitadora B"),
    post(103, "Equipe C"),
]
guardados, truncado, todos = F.priorizar_posts(misturados, institucionais, 10)
assert truncado
assert len(todos) == 43
assert {item["autor"] for item in guardados} >= institucionais
print("ok | três institucionais sobrevivem ao teto de dez")

aviso = {"label": "Avisos da disciplina", "url": "aviso"}
autores = F.autores_institucionais_do_forum(
    aviso, [post(201, "Docente A"), post(202, "Facilitadora B")]
)
outro_forum = [post(203, "Docente A"), post(204, "Colega X")]
classificados, _, _ = F.priorizar_posts(outro_forum, autores, 10)
por_autor = {item["autor"]: item["autoridade"] for item in classificados}
assert por_autor["Docente A"] == "institucional"
assert por_autor["Colega X"] == "colega"
print("ok | autores de Avisos são institucionais nos outros fóruns do curso")

colega_com_data = post(301, "Colega X", prazos=True)
classificados, _, _ = F.priorizar_posts([colega_com_data], autores, 10)
assert classificados[0]["prazos"]
assert classificados[0]["prazos"][0]["confianca"] == "baixa"
print("ok | prazo de colega é preservado com confiança baixa")

duplicado_colega = post(401, "Colega X")
duplicado_oficial = {**post(401, "Docente A"), "texto": "Versão completa"}
entrada = [duplicado_colega, post(402, "Colega Y", prazos=True), duplicado_oficial]
classificados, _, todos = F.priorizar_posts(entrada, autores, 10)
assert len(todos) == 2
assert classificados[0]["id"] == "401"
assert classificados[0]["autoridade"] == "institucional"
print("ok | desduplicação antecede a ordenação por autoridade")

ordem = [
    forum["label"]
    for _, forum in F.ordenar_foruns(
        [
            {"label": "Dúvidas", "url": "d"},
            {"label": "Grupo G4", "url": "g"},
            {"label": "Avisos", "url": "a"},
            {"label": "Temático", "url": "t"},
        ]
    )
]
assert ordem == ["Avisos", "Grupo G4", "Dúvidas", "Temático"]
print("ok | orçamento visita Avisos e grupo antes dos demais")
