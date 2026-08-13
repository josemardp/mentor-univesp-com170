# -*- coding: utf-8 -*-
"""Como a nota da disciplina é composta, e o que o robô não acompanha.

A nota de uma disciplina regular é 40% de participação no AVA e 60% de prova
presencial no polo. O guia acompanhava com detalhe os 40% e não dizia uma
palavra sobre os 60%, o que é pior do que parece: quem lê "está tudo em dia"
pode concluir que está tudo em dia na disciplina, quando o guia só olha a
menor metade.

A regra não é chutada aqui. Ela é lida de aviso institucional já coletado, e
só aparece quando um aviso oficial diz os dois percentuais. Sem aviso, o guia
fica calado sobre a composição, como sempre fez com prazo sem fonte.

A data da prova continua fora do alcance: ela sai no Sistema de Provas
(`acesso.univesp.br`), que tem autenticação própria, separada do AVA. Enquanto
não houver coletor para lá, o guia declara essa ausência em vez de omiti-la.
"""
import re
from datetime import date

from dominio.datas import sem_acento

SISTEMA_DE_PROVAS = "https://acesso.univesp.br"

# "40% - nota pela participação na fase de estudos (AVA)" e
# "60% - nota pelo desempenho nas provas presenciais (nos Polos)", ou
# "40% atividades avaliativas do AVA mais 60% da prova final".
#
# O que descreve cada percentual é o texto ATÉ o próximo percentual. Uma
# captura só, por padrão único, engolia os dois e não classificava nenhum.
PERCENTUAL_RE = re.compile(r"(\d{1,3})\s*%")
LIMITE_DESCRICAO = 90


FIM_DE_FRASE = ("\n", ". ", ".\t", ";", " · ")


def _ate_o_fim_da_frase(trecho):
    """Corta na primeira quebra de frase.

    O último percentual do aviso não tem outro percentual depois dele para
    servir de parada, e a janela fixa invadia o parágrafo seguinte. No texto
    real do COM100 isso fazia a descrição de "60%" carregar junto a palavra
    "Participação" da frase seguinte, ficar ambígua entre prova e AVA, e a
    regra inteira ser descartada.
    """
    corte = len(trecho)
    for marca in FIM_DE_FRASE:
        posicao = trecho.find(marca)
        if 0 <= posicao < corte:
            corte = posicao
    if trecho[corte:corte + 1] == ".":
        corte += 1
    return trecho[:corte]


def _percentuais(texto):
    achados = list(PERCENTUAL_RE.finditer(texto or ""))
    for indice, achado in enumerate(achados):
        fim = (
            achados[indice + 1].start()
            if indice + 1 < len(achados)
            else len(texto)
        )
        trecho = texto[achado.end():fim][:LIMITE_DESCRICAO]
        yield int(achado.group(1)), _ate_o_fim_da_frase(trecho)
TERMOS_AVA = ("ava", "participacao", "fase de estudos", "atividades avaliativas")
TERMOS_PROVA = ("prova", "presencia", "polo")


def _classificar(trecho):
    alvo = sem_acento(trecho)
    tem_prova = any(termo in alvo for termo in TERMOS_PROVA)
    tem_ava = any(termo in alvo for termo in TERMOS_AVA)
    if tem_prova and not tem_ava:
        return "prova"
    if tem_ava and not tem_prova:
        return "ava"
    return None


def composicao_da_nota(curso):
    """Devolve os dois pesos quando um aviso oficial declara os dois.

    Exigir os dois no mesmo aviso é o que impede transformar um "60%" solto
    numa afirmação sobre a nota inteira.
    """
    for aviso in curso.get("avisos") or []:
        if aviso.get("autoridade") != "institucional":
            continue
        texto = aviso.get("texto") or ""
        achados = {}
        for valor, trecho in _percentuais(texto):
            if not 1 <= valor <= 100:
                continue
            papel = _classificar(trecho)
            if papel and papel not in achados:
                achados[papel] = valor
        if len(achados) == 2 and sum(achados.values()) == 100:
            return {
                "ava": achados["ava"],
                "prova": achados["prova"],
                "autor": aviso.get("autor"),
                "url": aviso.get("url"),
            }
    return None


# A data da prova mora no Sistema de Provas, que autentica por conta
# Microsoft e não é alcançável por aqui. Mas ela costuma circular antes disso,
# em aviso de facilitador — foi assim com todo prazo que o guia aprendeu a
# ler. Então em vez de só declarar a lacuna, ele procura: quando um aviso
# institucional disser a data, o guia passa a mostrá-la, com a fonte à vista.
FALA_DE_PROVA = re.compile(
    r"prova(?!\s+de\s+conceito)|avalia[cç][ãa]o presencial", re.IGNORECASE
)
FALA_DE_PRESENCIAL = re.compile(r"presencia|polo", re.IGNORECASE)


def data_da_prova(curso, hoje=None):
    """Data da prova presencial, se algum aviso oficial já a disse.

    Exige as duas marcas na mesma frase (prova **e** presencial/polo) porque
    "prova" sozinho aparece em frase sobre atividade avaliativa do AVA, e uma
    data errada aqui é pior que data nenhuma — foi o erro original do guia.
    """
    from dominio.datas import achar_datas

    for aviso in curso.get("avisos") or []:
        if aviso.get("autoridade") != "institucional":
            continue
        texto = aviso.get("texto") or ""
        for frase in re.split(r"(?<=[.!?])\s+|\n", texto):
            if not (FALA_DE_PROVA.search(frase)
                    and FALA_DE_PRESENCIAL.search(frase)):
                continue
            datas = achar_datas(frase, hoje or date.today())
            if not datas:
                continue
            quando, trecho, hora_certa = datas[0][0], datas[0][1], datas[0][2]
            return {
                "quando": quando.isoformat(),
                "trecho": trecho,
                "hora_certa": hora_certa,
                "frase": " ".join(frase.split())[:220],
                "autor": aviso.get("autor"),
                "url": aviso.get("url"),
            }
    return None


def lacuna_da_prova(curso, hoje=None):
    """O que o guia sabe e o que ele não acompanha sobre a prova presencial."""
    composicao = composicao_da_nota(curso)
    if not composicao:
        return None
    try:
        achada = data_da_prova(curso, hoje)
    except Exception:
        # Procurar a data nunca pode derrubar o bloco que declara a lacuna:
        # a declaração é o mínimo garantido, a data é o bônus.
        achada = None
    return {
        **composicao,
        "acompanhado": False,
        "onde": SISTEMA_DE_PROVAS,
        "data_achada": achada,
    }


# ---------------------------------------------------------------------------
# Os pontos contáveis da quinzena (COM170)
#
# O aviso CRITÉRIOS DE AVALIAÇÃO de 21/07/2026 lista dez itens de mesmo peso
# por quinzena: os quatro módulos, a entrega individual, a entrega de grupo,
# os dois feedbacks (ao colega e ao outro grupo), participação em uma live e
# a qualidade da participação.
#
# O painel "Meu Progresso de Participação" só mostra cinco deles (módulos e
# qualidade). Os outros cinco o guia já lia sem saber que eram ponto: o
# estado dos dois Laboratórios responde por quatro, e a live é a única que
# ele não tem como provar. Sem juntar isso num lugar, o painel dizia
# "progresso avançado" com quatro de cinco e sobrava a impressão de que
# faltava pouco, quando faltavam quatro pontos de dez.
# ---------------------------------------------------------------------------

MARCA_DE_GRUPO = "grupo"
# A qualidade da participação fecha a lista: é o único critério do painel que
# não é módulo, e sai no fim para os quatro módulos ficarem juntos.
MARCA_DE_QUALIDADE = "qualidade"


def _laboratorios_vivos(curso, encerradas):
    """Os dois Laboratórios da quinzena que ainda está em curso."""
    achados = []
    for secao in curso.get("sections") or []:
        if secao.get("id") in encerradas or secao.get("locked"):
            continue
        for item in secao.get("items") or []:
            if item.get("type") == "workshop":
                achados.append(item)
    return achados


def _ponto(nome, estado, detalhe=None):
    return {"nome": nome, "atendido": estado, "detalhe": detalhe}


def pontos_da_quinzena(curso, encerradas=()):
    """Placar dos dez pontos contáveis, ou ``None`` fora da COM170.

    ``atendido`` é ``True``, ``False`` ou ``None``. ``None`` é a resposta
    honesta para o que o guia não consegue provar — hoje, só a live — e nunca
    deve virar ``False``: cobrar presença numa live que ele pode ter assistido
    é o mesmo erro de acusar entrega que existe.
    """
    if (curso.get("code") or "").upper() != "COM170":
        return None
    participacao = curso.get("participacao") or {}
    criterios = participacao.get("criterios") or []
    if not criterios:
        return None

    pontos = [
        _ponto(criterio.get("nome"), criterio.get("atendido"))
        for criterio in criterios
        if MARCA_DE_QUALIDADE not in sem_acento(criterio.get("nome") or "")
    ]

    labs = _laboratorios_vivos(curso, encerradas)
    individual = next(
        (
            lab
            for lab in labs
            if MARCA_DE_GRUPO not in sem_acento(lab.get("label") or "")
        ),
        None,
    )
    grupo = next(
        (
            lab
            for lab in labs
            if MARCA_DE_GRUPO in sem_acento(lab.get("label") or "")
        ),
        None,
    )
    for lab, rotulo, feedback in (
        (individual, "Entrega individual do portfólio",
         "Feedback ao colega"),
        (grupo, "Entrega de grupo", "Feedback ao outro grupo"),
    ):
        if lab is None:
            pontos.append(_ponto(rotulo, None, "não achei a atividade"))
            pontos.append(_ponto(feedback, None, "não achei a atividade"))
            continue
        pontos.append(_ponto(rotulo, lab.get("enviado")))
        pendente = lab.get("avaliacao_pendente")
        pontos.append(
            _ponto(feedback, None, "só dá para saber quando a fase de "
                                   "avaliação abrir")
            if pendente is None
            else _ponto(feedback, not pendente)
        )

    pontos.append(
        _ponto(
            "Participação em uma live",
            None,
            "o guia não consegue conferir presença em live",
        )
    )
    for criterio in criterios:
        if MARCA_DE_QUALIDADE in sem_acento(criterio.get("nome") or ""):
            pontos.append(
                _ponto(criterio.get("nome"), criterio.get("atendido"))
            )
    return {
        "pontos": pontos,
        "atendidos": sum(1 for p in pontos if p["atendido"] is True),
        "pendentes": sum(1 for p in pontos if p["atendido"] is False),
        "desconhecidos": sum(1 for p in pontos if p["atendido"] is None),
        "total": len(pontos),
    }
