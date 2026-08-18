# -*- coding: utf-8 -*-
"""Estado aberto, fechado ou indefinido de uma atividade."""
import re

from playwright.sync_api import Error as PlaywrightError

from dominio.datas import sem_acento

SINAIS_FECHADO = [
    "nao esta aberta",
    "nao esta aberto",
    "nao esta disponivel",
    "nao esta mais disponivel",
    "esta atividade encerrou",
    "o prazo para envio expirou",
    "nao e mais possivel",
    "periodo encerrado",
    "fora do prazo",
    "esta pesquisa nao esta",
    "submissoes fechadas",
    "avaliacoes fechadas",
    "o prazo de envio terminou",
    "prazo encerrado",
    "envio encerrado",
    "atividade encerrada",
]
SINAIS_INDEFINIDO = [
    "precisa fazer login",
    "voce precisa se identificar",
    "acesso negado",
    "nao tem permissao",
    "sem permissao para",
    "erro de permissao",
]
SINAIS_NAO_ENVIADO = [
    "voce nao enviou seu trabalho ainda",
    "voce ainda nao enviou",
    "nenhum envio",
]
SINAIS_ENVIADO = [
    # A página `view.php` (a que o robô visita) não mostra os botões "Editar
    # envio"/"Excluir envio" - esses só existem na tela de edição
    # (`submission.php`). Em `view.php`, depois de enviar, a linha do tempo
    # troca "Tarefas a fazer" por "Tarefa realizada" e aparece o carimbo
    # "enviado em <data>" junto do título do envio.
    "tarefa realizada",
    "enviado em",
    "editar envio",
    "excluir envio",
]


def item_aberto(page, url):
    if not url:
        return None
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(500)
        corpo = sem_acento(page.locator("body").inner_text()[:4000])
    except PlaywrightError:
        return None
    if any(sinal in corpo for sinal in SINAIS_INDEFINIDO):
        return None
    if any(sinal in corpo for sinal in SINAIS_FECHADO):
        return False
    return True


# "Avaliar colegas — total: 1 pendente: 1" é o contador que o Moodle mostra na
# fase de avaliação. É a única leitura confiável de "ainda falta avaliar
# alguém": o selo de conclusão do curso não distingue as fases.
CONTADOR_AVALIACAO_RE = re.compile(
    r"avaliar colegas.{0,200}?total:\s*(\d+)\s*pendente:\s*(\d+)",
    re.DOTALL,
)

# Sem contador, a fase de avaliação tem duas caras diferentes, e até
# 17/08/2026 as duas viravam "não sei". A frase abaixo é o Moodle afirmando
# que nada foi sorteado para esta conta: no Q2 M7, laboratório de grupo, quem
# recebe o trabalho da outra equipe é o representante, e a fila cobrava dele
# "Avalie o trabalho do colega" com prazo para o dia seguinte. É o mesmo caso
# da entrega de grupo resolvido em 15/08, agora do lado da avaliação.
SEM_ENVIO_ATRIBUIDO = "voce nao recebeu nenhum envio para avaliar"


def _texto_da_atividade(page, url):
    """Corpo da página em minúsculas, sem acento e com espaço normalizado.

    O Moodle separa rótulo e valor com tabulação ("Situação\\tFinalizada"), e
    sem normalizar isso as frases procuradas nunca casam.
    """
    if not url:
        return None
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(500)
        bruto = page.locator("body").inner_text()[:6000]
    except PlaywrightError:
        return None
    return " ".join(sem_acento(bruto).split())


# Nome antigo, mantido porque os testes de regressão do laboratório o usam.
_texto_do_workshop = _texto_da_atividade


def _enviado_no_texto(corpo):
    if any(sinal in corpo for sinal in SINAIS_INDEFINIDO):
        return None
    if any(sinal in corpo for sinal in SINAIS_NAO_ENVIADO):
        return False
    if any(sinal in corpo for sinal in SINAIS_ENVIADO):
        return True
    return None


def estado_workshop(page, url):
    """Envio e avaliação por pares de um Laboratório de Avaliação.

    Aberto/fechado (``item_aberto``) só enxerga a janela de datas, e o selo
    "Concluído" do Moodle só fecha quando as 5 fases terminam. São duas
    obrigações distintas com prazos distintos: entregar o trabalho e avaliar
    o de outra pessoa. Tratar as duas como uma só faz o guia sumir com a
    avaliação assim que a entrega é feita — foi o que aconteceu com o M7 em
    04/08/2026, cuja avaliação vencia naquele mesmo dia.
    """
    corpo = _texto_da_atividade(page, url)
    if corpo is None:
        # "aberto" faltava neste retorno, e quem chama lê a chave direto. Uma
        # página de Laboratório que não carregasse derrubaria a rodada com
        # KeyError — a falha de uma leitura levando junto as outras sete
        # fontes, que é exatamente o que `FONTES_QUE_NAO_BLOQUEIAM` existe
        # para impedir. Leitura que falha responde "não sei" em todos os
        # campos, nunca some com um deles.
        return {
            "enviado": None,
            "aberto": None,
            "avaliacoes_total": None,
            "avaliacoes_pendentes": None,
            "avaliacao_pendente": None,
            "sem_envio_atribuido": None,
        }
    enviado = _enviado_no_texto(corpo)
    total = pendentes = None
    sem_atribuicao = SEM_ENVIO_ATRIBUIDO in corpo
    encontrado = CONTADOR_AVALIACAO_RE.search(corpo)
    if encontrado:
        total = int(encontrado.group(1))
        pendentes = int(encontrado.group(2))
    elif sem_atribuicao:
        total, pendentes = 0, 0
    elif "ja foi avaliada" in corpo and "avaliar" not in corpo:
        total, pendentes = 1, 0
    # `item_aberto` não serve aqui. A página do Laboratório em fase de
    # avaliação diz, nas instruções, "o prazo de envio terminou" — frase da
    # lista de encerramento. Em 04/08/2026 isso mandou o M7 para "já
    # encerrou" no mesmo dia em que a avaliação vencia. Quem sabe se ainda
    # há o que fazer é a linha do tempo das 5 fases, não uma frase solta.
    if pendentes is not None and pendentes > 0:
        aberto = True
    elif enviado is True:
        aberto = True
    elif enviado is False and any(
        sinal in corpo for sinal in SINAIS_FECHADO
    ):
        aberto = False
    else:
        aberto = None
    return {
        "enviado": enviado,
        "aberto": aberto,
        "avaliacoes_total": total,
        "avaliacoes_pendentes": pendentes,
        "avaliacao_pendente": None if pendentes is None else pendentes > 0,
        "sem_envio_atribuido": sem_atribuicao,
    }


def envio_workshop(page, url):
    """Compatibilidade: só o "já enviei?" de ``estado_workshop``."""
    return estado_workshop(page, url)["enviado"]


# A página do questionário diz, sem ambiguidade, se existe tentativa: depois de
# responder aparece o bloco "Suas tentativas" com "Situação: Finalizada". Antes,
# só o botão "Tentativa do questionário". É a prova direta que o selo de
# conclusão do Moodle não dá — o selo pode fechar só por ter aberto a página.
SINAIS_TENTOU = ("suas tentativas", "situacao finalizada", "resumo da tentativa")
SINAIS_NAO_TENTOU = (
    "tentativa do questionario",
    "nenhuma tentativa",
    "ainda nao fez nenhuma tentativa",
)
# Tarefa (assign): o quadro de status diz se houve envio.
SINAIS_ENVIOU_TAREFA = ("enviado para avaliacao", "enviado(a) para avaliacao")
SINAIS_NAO_ENVIOU_TAREFA = (
    "nenhuma tentativa",
    "nenhum envio",
    "nao entregue",
)


def entrega_feita(page, url, tipo):
    """``True``/``False``/``None`` para "esta atividade foi mesmo entregue?".

    ``None`` é a resposta honesta quando a página não afirma nem nega. Nunca
    devolver ``False`` por falta de sinal: acusar entrega faltando quando ela
    existe é pior que ficar calado.
    """
    if tipo not in ("quiz", "assign"):
        return None
    corpo = _texto_da_atividade(page, url)
    if corpo is None or any(
        sinal in corpo for sinal in SINAIS_INDEFINIDO
    ):
        return None
    if tipo == "quiz":
        if any(sinal in corpo for sinal in SINAIS_TENTOU):
            return True
        if any(sinal in corpo for sinal in SINAIS_NAO_TENTOU):
            return False
        return None
    if any(sinal in corpo for sinal in SINAIS_ENVIOU_TAREFA):
        return True
    if any(sinal in corpo for sinal in SINAIS_NAO_ENVIOU_TAREFA):
        return False
    return None
