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


def cronograma_padrao(hoje=None):
    """Reserva usada só quando a disciplina não publica o link do cronograma.

    Estava fixa em ``cronograma_regular_3.html``, o 3º bimestre de 2026. Na
    virada do bimestre a reserva continuaria aplicando datas vencidas em
    silêncio, que é o pior jeito de errar num guia de prazos. O bimestre passa
    a sair da data corrente: são quatro por ano, de dois meses cada.
    """
    from datetime import datetime

    hoje = hoje or datetime.now(BR_TZ).date()
    # Os quatro bimestres letivos se espalham pelo ano inteiro, então o mês
    # dividido em quatro acerta melhor que blocos de dois meses: agosto é o
    # 3º bimestre, não o 4º. Mesmo assim é palpite, e por isso quem lê o
    # cronograma confere se as semanas contêm a data de hoje antes de aceitar.
    bimestre = min(4, (hoje.month - 1) // 3 + 1)
    return (
        f"https://assets.univesp.br/cronograma/{hoje.year}"
        f"/cronograma_regular_{bimestre}.html"
    )


# Compatibilidade com quem importava a constante.
CRONOGRAMA_PADRAO = cronograma_padrao()

# Limites para não estourar o tempo da GitHub Action.
MAX_DISCUSSOES_POR_RUN = 60
MAX_ITENS_CONFERIDOS = 45
# Conferência de entrega abre uma página por atividade suspeita. Suspeita é
# rara por definição (vale nota, marcada como concluída e sem nota lançada),
# então um teto baixo por disciplina já cobre e não estoura o tempo da Action.
MAX_ENTREGAS_CONFERIDAS = 12
MAX_POSTS_POR_DISCUSSAO = 10
TRECHO_AVISO = 400
JANELA_AVISOS_DIAS = 45
NOVO_ATE_DIAS = 3
# Autor visto num fórum "Avisos" vale como fonte oficial por este tempo. Sem
# validade o registro só crescia, e um colega que postasse uma vez ali viraria
# fonte de prazo confiável para sempre. Um bimestre tem sete semanas.
VALIDADE_AUTOR_DIAS = 90

# Incrementar quando o formato persistido de fórum mudar.
# 3: prazos passaram a distinguir compromisso (live) de entrega. O cache
# guarda o texto já cortado em 400, então sem reler do AVA a agenda das
# lives ficava fora do alcance do parser novo.
VERSAO_CACHE = 3
