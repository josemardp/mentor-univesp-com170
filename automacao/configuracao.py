# -*- coding: utf-8 -*-
"""Configuração central da automação, sem acesso ao AVA."""
from datetime import timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DATA_PATH = DOCS / "data.json"
ESTADO_PATH = DOCS / "estado.json"

BR_TZ = timezone(timedelta(hours=-3))
AVA = "https://ava.univesp.br"
CRONOGRAMA_PADRAO = (
    "https://assets.univesp.br/cronograma/2026/cronograma_regular_3.html"
)

# Limites para não estourar o tempo da GitHub Action.
MAX_DISCUSSOES_POR_RUN = 60
MAX_ITENS_CONFERIDOS = 45
MAX_POSTS_POR_DISCUSSAO = 10
TRECHO_AVISO = 400
JANELA_AVISOS_DIAS = 45
NOVO_ATE_DIAS = 3

# Incrementar quando o formato persistido de fórum mudar.
VERSAO_CACHE = 2
