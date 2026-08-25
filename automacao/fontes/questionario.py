# -*- coding: utf-8 -*-
"""Nota e tentativas lidas na própria página do questionário.

Motivo de existir, medido no AVA em 25/08/2026: o boletim do SOC100 está
vazio de verdade. A tabela do relatório do usuário abre com o cabeçalho
"Item de nota | Nota" e nenhuma linha, embora as quatro Atividades
Avaliativas já encerradas tenham 10,00. O guia então mostrava a disciplina
inteira sem nota nenhuma, sem conseguir dizer se era ausência de entrega ou
ausência de leitura.

A página do questionário responde o que o boletim não responde, e responde
mais: quantas tentativas foram usadas das permitidas, e por qual método a
nota é escolhida. "Três tentativas, vale a nota mais alta, você ainda não
usou nenhuma" é a informação que muda o que ele faz no dia, e ela nunca
esteve em lugar nenhum do guia.

Fonte secundária, nunca substituta: onde o boletim tem nota, é o boletim que
manda. Ele é a nota lançada pelo facilitador; esta aqui é a nota que o
questionário calculou.
"""
import re

# O texto chega de ``itens._texto_da_atividade``: minúsculo, sem acento e com
# espaço normalizado. "A sua nota final neste questionário é 10,00/10,00."
# vira "a sua nota final neste questionario e 10,00/10,00.".
NOTA_FINAL_RE = re.compile(
    r"sua nota final neste questionario e\s*"
    r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)"
)
# Fallback: o resumo da tentativa escreve a mesma nota de outro jeito, e
# aparece mesmo quando a nota final ainda não foi consolidada.
NOTA_DA_TENTATIVA_RE = re.compile(
    r"nota\s+(\d+(?:[.,]\d+)?)\s+de um maximo de\s+(\d+(?:[.,]\d+)?)"
)
PERMITIDAS_RE = re.compile(r"tentativas permitidas:\s*(\d+)")
# O método é uma de poucas frases fixas do Moodle, e logo depois dela vem
# texto qualquer ("...nota mais alta pagina anterior s5 - aprofundando..."),
# então casar "o resto da linha" pegaria meia página. Lista fechada.
METODOS = (
    "nota mais alta",
    "media das notas",
    "primeira tentativa",
    "ultima tentativa",
)
METODO_RE = re.compile(
    r"metodo de avaliacao:\s*(" + "|".join(METODOS) + r")"
)
# Cada tentativa registrada abre um bloco "Resumo da tentativa N".
RESUMO_DE_TENTATIVA_RE = re.compile(r"resumo da tentativa\s+(\d+)")

# "Tentativa do questionário" é o cabeçalho do botão de começar, e ele só
# existe enquanto não há nenhuma tentativa: assim que existe uma, o bloco vira
# "Suas tentativas". É o mesmo sinal que ``itens.SINAIS_NAO_TENTOU`` usa para
# afirmar que não houve entrega, e conferido nas duas páginas em 25/08/2026.
SEM_TENTATIVA = (
    "tentativa do questionario",
    "nenhuma tentativa",
    "ainda nao fez nenhuma tentativa",
)


def _numero(bruto):
    try:
        return float(str(bruto).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _formatar(valor):
    """Devolve a nota no formato do AVA, com vírgula e duas casas."""
    if valor is None:
        return None
    return f"{valor:.2f}".replace(".", ",")


def resumo_do_texto(corpo):
    """Lê o corpo já normalizado da página e devolve o que ela afirma.

    Devolve ``None`` quando o texto não é de uma página de questionário. Cada
    campo é ``None`` quando a página não afirma nada sobre ele: questionário
    sem tentativa nenhuma tem nota desconhecida, não nota zero.
    """
    if not corpo:
        return None
    permitidas = PERMITIDAS_RE.search(corpo)
    achou_nota = NOTA_FINAL_RE.search(corpo)
    tentativas = RESUMO_DE_TENTATIVA_RE.findall(corpo)
    if not (permitidas or achou_nota or tentativas):
        return None

    nota = maximo = None
    if achou_nota:
        nota = _numero(achou_nota.group(1))
        maximo = _numero(achou_nota.group(2))
    else:
        # Sem a linha de nota final, a maior nota entre as tentativas é a
        # melhor resposta disponível — e é a que o método padrão do AVA
        # ("nota mais alta") usaria de qualquer jeito.
        notas = [
            (_numero(a), _numero(b))
            for a, b in NOTA_DA_TENTATIVA_RE.findall(corpo)
        ]
        notas = [(n, m) for n, m in notas if n is not None]
        if notas:
            nota, maximo = max(notas, key=lambda par: par[0])

    if tentativas:
        feitas = max(int(n) for n in tentativas)
    elif any(sinal in corpo for sinal in SEM_TENTATIVA):
        feitas = 0
    else:
        # Página que não listou tentativa nenhuma e também não mostrou o
        # botão de começar não autoriza afirmar "zero tentativas". Silêncio
        # vira "não sei", nunca "não fez".
        feitas = None

    metodo = METODO_RE.search(corpo)
    return {
        "nota": nota,
        "nota_txt": _formatar(nota),
        "maximo": maximo,
        "tentativas_feitas": feitas,
        "tentativas_permitidas": (
            int(permitidas.group(1)) if permitidas else None
        ),
        "metodo": metodo.group(1).strip() if metodo else None,
    }
