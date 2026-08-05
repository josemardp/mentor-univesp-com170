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


def _percentuais(texto):
    achados = list(PERCENTUAL_RE.finditer(texto or ""))
    for indice, achado in enumerate(achados):
        fim = (
            achados[indice + 1].start()
            if indice + 1 < len(achados)
            else len(texto)
        )
        trecho = texto[achado.end():fim][:LIMITE_DESCRICAO]
        yield int(achado.group(1)), trecho
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


def lacuna_da_prova(curso):
    """O que o guia sabe e o que ele não acompanha sobre a prova presencial."""
    composicao = composicao_da_nota(curso)
    if not composicao:
        return None
    return {
        **composicao,
        "acompanhado": False,
        "onde": SISTEMA_DE_PROVAS,
    }
