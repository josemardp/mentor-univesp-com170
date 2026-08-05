# -*- coding: utf-8 -*-
"""Contratos de prioridade, autoridade e corte dos fóruns."""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

from fontes import foruns as F  # noqa: E402
import enviar_email as E  # noqa: E402
import render as R  # noqa: E402


def post(numero, autor, prazos=False, texto=None):
    return {
        "id": str(numero),
        "autor": autor,
        "data": f"2026-07-25T10:{numero % 60:02d}:00-03:00",
        "texto": texto or f"Post {numero}",
        "prazos": (
            [
                {
                    "quando": "2026-08-01T23:59:00-03:00",
                    "confianca": "alta",
                    "tipo": "fim",
                    "rotulo": "Entrega sanitizada",
                }
            ]
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

HOJE_AUT = date(2026, 8, 4)
estado_autores = {}
F.acumular_autores_institucionais(
    estado_autores, "18922", aviso, [post(211, "Docente A")], HOJE_AUT
)
F.acumular_autores_institucionais(
    estado_autores, "18922", aviso, [post(212, "Facilitadora B")], HOJE_AUT
)
registro = estado_autores["_autores_institucionais"]["18922"]
assert sorted(registro) == ["Docente A", "Facilitadora B"]
assert registro["Docente A"] == HOJE_AUT.isoformat()
print("ok | autores institucionais acumulam entre leituras do curso")

# O registro só crescia: quem postasse uma vez em Avisos virava fonte oficial
# para sempre, e as datas dessa pessoa valiam como confiança alta.
antigo = {"_autores_institucionais": {"18922": {
    "Docente A": "2026-08-01", "Visitante": "2026-01-05"}}}
F.acumular_autores_institucionais(
    antigo, "18922", aviso, [post(213, "Docente A")], HOJE_AUT
)
assert sorted(antigo["_autores_institucionais"]["18922"]) == ["Docente A"]
print("ok | autor sem aparição recente em Avisos deixa de ser fonte oficial")

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

aviso_oficial = {
    **post(501, "Docente A", prazos=True),
    "autoridade": "institucional",
    "titulo": "Orientação oficial",
    "forum": "Avisos",
    "url": "https://ava.univesp.br/mod/forum/discuss.php?d=501",
}
aviso_colega = {
    **post(502, "Colega X", prazos=True),
    "autoridade": "colega",
    "titulo": "Conversa",
    "forum": "Dúvidas",
    "url": "https://ava.univesp.br/mod/forum/discuss.php?d=502",
}
html_oficial = R.render_aviso("COM170", aviso_oficial)
html_colega = R.render_aviso("COM170", aviso_colega)
assert 'class="aviso oficial"' in html_oficial
assert "aviso oficial" in html_oficial
assert 'class="aviso colega"' in html_colega
assert "post de colega" in html_colega
texto_email = E.montar_texto(
    {
        "status": "ok",
        "acoes": [],
        "higiene": [],
        "courses": [
            {
                "code": "COM170",
                "avisos": [aviso_colega, aviso_oficial],
            }
        ],
        "mensagens": [],
        "notificacoes": [],
    }
)
assert texto_email.index("[OFICIAL]") < texto_email.index("[colega]")
assert "prazo oficial" in texto_email
assert "data para conferir" in texto_email
print("ok | site e e-mail distinguem aviso oficial de conversa")
