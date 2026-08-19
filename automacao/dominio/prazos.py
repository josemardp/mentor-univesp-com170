# -*- coding: utf-8 -*-
"""Extração e casamento de prazos vindos de texto livre."""
import re

from dominio.datas import achar_datas, sem_acento


def _posicoes(alvo, termos):
    return [
        encontrado.start()
        for termo in termos
        for encontrado in re.finditer(
            r"\b" + re.escape(termo.strip()) + r"\b", alvo
        )
    ]


def _tem(alvo, termos):
    posicoes = _posicoes(alvo, termos)
    return min(posicoes) if posicoes else -1


GATILHOS_PRAZO = [
    "prazo",
    "ate",
    "vencimento",
    "vence",
    "entrega",
    "entregar",
    "entregue",
    "fechamento",
    "encerramento",
    "encerra",
    "submissao",
    "submissoes",
    "avaliacao por pares",
    "avaliacoes por pares",
    "abertura",
    "limite",
    "data",
    "horario",
    "acontece",
    "sera realizada",
    "abre",
    "abrem",
    "fecha",
    "fecham",
]
# Live não é prazo, é compromisso: tem hora de começar e, se passou, passou.
# O aviso que anunciou a live de 30/07 dizia "está marcada para", e nenhuma
# palavra dessa frase estava nos gatilhos de prazo, então a data nem chegava
# a ser lida. Estes termos entram em GATILHOS_PRAZO logo abaixo.
GATILHOS_EVENTO = [
    "live",
    "lives",
    "encontro",
    "encontros",
    "webinar",
    "plantao",
    "plantoes",
    "transmissao",
    "aula ao vivo",
    "agenda",
    "cronograma de lives",
    "marcada",
    "marcado",
    "agendada",
    "agendado",
    "remarcada",
    "remarcado",
    "acontecera",
    "ocorre",
    "ocorrera",
    "sera realizado",
    "havera",
    "supervisao",
]
GATILHOS_PRAZO += GATILHOS_EVENTO
GATILHOS_INICIO = [
    "abertura",
    "abre",
    "abrem",
    "inicia",
    "iniciam",
    "comeca",
    "comecam",
    "disponivel a partir",
    "libera",
    "liberacao",
]
GATILHOS_FIM = [
    "fechamento",
    "ate",
    "vencimento",
    "vence",
    "encerra",
    "encerramento",
    "limite",
    "entregue",
    "entregar",
    "entrega",
    "prazo",
    "fecha",
]


def _tipo_prazo(
    fragmento, contexto, pos_data=None, modo_evento=False, hora_certa=False
):
    alvo = sem_acento(fragmento)
    if modo_evento and _tem(alvo, GATILHOS_FIM) < 0:
        # Só vira compromisso se a própria frase não falar de entrega. Um
        # aviso pode misturar "a live é 04/08" com "entregue até 06/08".
        # A hora no relógio é o que separa live de data solta: "a live é
        # 05/08 às 11h" tem hora, "a quinzena inicia (3/8)" não tem.
        if _tem(alvo, GATILHOS_INICIO) < 0 and (
            hora_certa or _tem(alvo, GATILHOS_EVENTO) >= 0
        ):
            return "compromisso", True
    inicio = _posicoes(alvo, GATILHOS_INICIO)
    fim = _posicoes(alvo, GATILHOS_FIM)
    if pos_data is not None and (inicio or fim):
        antes_inicio = [pos for pos in inicio if pos <= pos_data]
        antes_fim = [pos for pos in fim if pos <= pos_data]
        depois_inicio = [pos for pos in inicio if pos > pos_data]
        depois_fim = [pos for pos in fim if pos > pos_data]

        por_antes = por_depois = None
        if antes_inicio or antes_fim:
            por_antes = (
                "inicio"
                if max(antes_inicio or [-1]) > max(antes_fim or [-1])
                else "fim"
            )
        if depois_inicio or depois_fim:
            por_depois = (
                "inicio"
                if min(depois_inicio or [10**9]) < min(depois_fim or [10**9])
                else "fim"
            )
        escolhido = por_antes or por_depois or "fim"
        seguro = (
            por_antes is None
            or por_depois is None
            or por_antes == por_depois
        )
        return escolhido, seguro

    for texto in (alvo, sem_acento(contexto)):
        pos_inicio = _tem(texto, GATILHOS_INICIO)
        pos_fim = _tem(texto, GATILHOS_FIM)
        if pos_inicio < 0 and pos_fim < 0:
            continue
        if pos_inicio >= 0 and (pos_fim < 0 or pos_inicio < pos_fim):
            return "inicio", True
        return "fim", True
    # Nenhuma palavra da frase nem do contexto diz o que essa data é. Tratar
    # como prazo é o palpite mais provável, mas *seguro* ele não é, e é o
    # `seguro` que decide se a data sai como cobrança com etiqueta oficial ou
    # como "confirme se é prazo". Em 19/08/2026 o LET110 escreveu "Na semana
    # que vem, a de nº 6, voltamos pra terça-feira (25/08)" — uma frase sobre
    # a live da semana seguinte — e o guia publicou "Conclua: Semana 5 ·
    # conclusão, vence 25/08", contra os itens da mesma semana que o
    # cronograma oficial dá para 26/08. O escopo ainda dizia "semana 5" (a
    # frase troca de unidade com "a de nº 6", que não casa com nenhum padrão
    # de escopo), e escopo forte + palpite seguro virava confiança alta.
    return "fim", False


ESCOPO_RE = re.compile(
    r"\b(m[óo]dulos?|semanas?|quinzenas?)\b([\s\d,ee]{0,20})",
    re.IGNORECASE,
)
PALAVRAS_FASE = (
    "abertura",
    "fechamento",
    "encerramento",
    "inicio",
    "fim",
    "prazo",
    "entrega",
    "submissao",
    "submissoes",
    "avaliacao",
    "avaliacoes",
    "revisao",
    "data",
    "horario",
    "limite",
    "vencimento",
    "atencao",
    "obs",
)
ROTULO_RE = re.compile(r"^([^:]{2,60}):")
NEGACAO_RE = re.compile(
    r"\b(nao\s+(?:hav|have|tera|tem|ha|sera|have?ra)\w*|sem\s+"
    r"(?:entrega|prazo|atividade|submissao)|fica\s+sem|"
    r"nao\s+e\s+necessario)\b"
)
CAIXA_ALTA_RE = re.compile(
    r"^[A-ZÀ-Ý][A-ZÀ-Ý]+(\s+[A-ZÀ-Ý0-9]{2,}){1,}"
)
FAMILIA_RE = re.compile(r"(\D+?)\s*(\d+)\s*$")
ABREV_MES = r"\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\."


def _escopo_de(fragmento):
    encontrado = ESCOPO_RE.search(fragmento or "")
    if not encontrado:
        return None
    numeros = [int(numero) for numero in re.findall(r"\d+", encontrado.group(2))]
    if not numeros:
        return None
    familia = sem_acento(encontrado.group(1)).rstrip("s")
    return {"familia": familia, "numeros": numeros, "txt": fragmento[:120]}


def tem_negacao(texto):
    return bool(NEGACAO_RE.search(sem_acento(texto or "")))


# "e não na terça-feira (18/08)". Aqui a negação não derruba o fragmento
# inteiro: ela derruba uma data e confirma outra, na mesma frase. Em
# 17/08/2026 o facilitador do LET110 escreveu "nossa live ocorrerá na
# quinta-feira (20/08) e não na terça-feira (18/08)", e o guia publicou um
# encontro para o dia que o aviso nega. Afirmar um compromisso que o próprio
# aviso desmarca é pior do que não ter lido o aviso.
NEGA_A_DATA_RE = re.compile(
    r"\bnao\s+(?:e\s+|sera\s+|vai\s+ser\s+)?"
    r"(?:na|no|em|as|no\s+dia|nesta|neste|nessa|nesse|dia)\b"
)
# Distância entre o "não" e a data que ele nega. Uma frase típica é
# "e não na terça-feira (18/08)": 20 caracteres. Trinta cobre "não no
# próximo sábado, 23/08" sem alcançar a data da oração seguinte.
ALCANCE_DA_NEGACAO = 30


def datas_negadas(fragmento, achados):
    """Posições das datas que a própria frase desmarca.

    ``achados`` são as tuplas de ``achar_datas``, cuja quarta posição é onde
    a data começa no fragmento. Só cai a data que vem logo depois do "não",
    nunca a frase toda: quem escreve "é X e não Y" está afirmando X.
    """
    alvo = sem_acento(fragmento or "")
    negadas = set()
    for negacao in NEGA_A_DATA_RE.finditer(alvo):
        candidatas = [
            posicao
            for *_, posicao in achados
            if negacao.end() <= posicao <= negacao.end() + ALCANCE_DA_NEGACAO
        ]
        if candidatas:
            negadas.add(min(candidatas))
    return negadas


def eh_fase(fragmento):
    encontrado = ROTULO_RE.match((fragmento or "").strip())
    if not encontrado:
        return False
    return any(
        palavra in sem_acento(encontrado.group(1))
        for palavra in PALAVRAS_FASE
    )


def muda_assunto(fragmento):
    trecho = (fragmento or "").strip()
    if CAIXA_ALTA_RE.match(trecho):
        return True
    encontrado = ROTULO_RE.match(trecho)
    return bool(encontrado) and not eh_fase(trecho)


def encerra_escopo(fragmento):
    encontrado = ROTULO_RE.match((fragmento or "").strip())
    if not encontrado:
        return False
    rotulo = sem_acento(encontrado.group(1))
    if _escopo_de(fragmento):
        return False
    return not any(palavra in rotulo for palavra in PALAVRAS_FASE)


# A partir da Quinzena 2 o AVA prefixa a seção com a quinzena: o Módulo 4 se
# chama "Q2 Módulo 4". Sem tirar o prefixo, o padrão de família nem casa,
# porque ele exige que o título comece por não-dígito.
PREFIXO_QUINZENA_RE = re.compile(r"^q(\d+)\s+", re.IGNORECASE)


def escopo_cobre(escopo, titulo_secao):
    """O prazo é desta seção?

    "Módulo 4" existe em toda quinzena. Um prazo que veio do calendário da
    Quinzena 2 carrega ``quinzena: 2`` e só cobre seções daquela quinzena,
    senão a data de 09/08 grudaria no Módulo 4 da Quinzena 1, que encerrou.
    Escopo de aviso, que não diz a quinzena, continua casando pelos dois
    formatos de título.
    """
    if not escopo:
        return False
    titulo = (titulo_secao or "").strip()
    prefixo = PREFIXO_QUINZENA_RE.match(titulo)
    quinzena_do_titulo = int(prefixo.group(1)) if prefixo else None
    if prefixo:
        titulo = titulo[prefixo.end():]
    exigida = escopo.get("quinzena")
    if exigida is not None:
        # Prazo que sabe de qual quinzena é só cobre seções daquela quinzena.
        if quinzena_do_titulo != exigida:
            return False
    elif quinzena_do_titulo is not None:
        # E prazo que não sabe não invade a quinzena nova: o aviso sobre
        # "Módulo 6 e 7" da Quinzena 1 chegou a cobrar o Q2 Módulo 6, que
        # sequer abriu.
        return False
    encontrado = FAMILIA_RE.match(titulo)
    if not encontrado:
        return False
    familia = sem_acento(encontrado.group(1)).strip().rstrip("s")
    return (
        familia == escopo["familia"]
        and int(encontrado.group(2)) in escopo["numeros"]
    )


SAUDACOES = {
    "prezados",
    "prezadas",
    "prezados(as)",
    "ola",
    "olá",
    "bom dia",
    "boa tarde",
    "boa noite",
    "pessoal",
    "atenciosamente",
    "cordialmente",
    "caros",
    "caras",
}
# Lista de saudação não sobrevive a variação de escrita: em 17/08/2026 o
# aviso do LET110 abriu com "Prezados/as," e o guia batizou a live de
# "Assista ao vivo: Prezados/as". O conjunto tinha "prezados(as)" e não
# "prezados/as". Em vez de caçar cada forma, a comparação passa a ignorar o
# que separa as variantes — barra, parênteses, ponto — e a raiz responde
# pelas duas.
SEPARADOR_DE_FLEXAO_RE = re.compile(r"[\s/()\\.\-]+")


def eh_saudacao(trecho):
    alvo = sem_acento(trecho or "").strip(" ,:;!")
    if alvo in SAUDACOES:
        return True
    # "prezados/as" e "prezados(as)" são a mesma palavra com a flexão
    # colada. A raiz antes do separador responde pelas duas, e comparar por
    # igualdade evita transformar "Olavo" em saudação por causa de "olá".
    raiz = SEPARADOR_DE_FLEXAO_RE.split(alvo, maxsplit=1)[0]
    return bool(raiz) and raiz in SAUDACOES


def _nome_do_evento(trechos, indice):
    """Numa agenda, quem apresenta vem na linha logo antes da data.

    Sem isso as seis lives da quinzena virariam seis linhas com o mesmo
    título, e ele não saberia qual é a do supervisor da turma dele.
    """
    for passo in (1, 2):
        if indice - passo < 0:
            break
        anterior = (trechos[indice - passo] or "").strip(" -–—•:,")
        if not 3 <= len(anterior) <= 60:
            continue
        if "http" in anterior.lower() or any(
            caractere.isdigit() for caractere in anterior
        ):
            continue
        if eh_saudacao(anterior):
            continue
        return anterior
    return None


def extrair_prazos(texto, referencia):
    protegido = re.sub(
        ABREV_MES, r"\1§", texto or "", flags=re.IGNORECASE
    )
    trechos = [
        trecho.strip().replace("§", ".")
        for trecho in re.split(r"[\n;]|\.\s+", protegido)
        if trecho.strip()
    ]
    prazos, vistos = [], set()
    escopo, escopo_forte = None, False
    modo_evento = False
    for indice, fragmento in enumerate(trechos):
        achado = _escopo_de(fragmento)
        if achado:
            escopo, escopo_forte = achado, True
        elif escopo is not None and muda_assunto(fragmento):
            escopo_forte = False
        # Numa agenda de lives o nome do evento aparece uma vez no topo e
        # depois vêm só as linhas de data. Sem manter o modo ligado, só a
        # primeira live seria reconhecida e as outras cinco sumiriam.
        if _tem(sem_acento(fragmento), GATILHOS_EVENTO) >= 0:
            modo_evento = True
        elif (
            modo_evento
            and "http" not in fragmento.lower()
            and encerra_escopo(fragmento)
        ):
            # O link de cada live fica entre as datas, e "https:" passava por
            # troca de assunto: desligava o modo e comia as lives seguintes.
            modo_evento = False
        if not 4 <= len(fragmento) <= 300:
            continue
        contexto = " ".join(trechos[max(0, indice - 2) : indice + 1])
        if not modo_evento and _tem(sem_acento(contexto), GATILHOS_PRAZO) < 0:
            continue
        if tem_negacao(fragmento):
            continue
        achados = list(achar_datas(fragmento, referencia))
        negadas = datas_negadas(fragmento, achados)
        for quando, trecho, hora_certa, posicao in achados:
            if posicao in negadas:
                continue
            rotulo = (
                fragmento.split(":")[0].strip()
                if ":" in fragmento[:70]
                else contexto
            )
            rotulo = rotulo[:87] + "..." if len(rotulo) > 90 else rotulo
            chave = (quando.isoformat(), rotulo[:40])
            if chave in vistos:
                continue
            vistos.add(chave)
            tipo, tipo_seguro = _tipo_prazo(
                fragmento, contexto, posicao, modo_evento, hora_certa
            )
            registro = {
                    "rotulo": rotulo,
                    "quando": quando.isoformat(),
                    "trecho": trecho,
                    "tipo": tipo,
                    "hora_certa": hora_certa,
                    "escopo": escopo,
                    "confianca": (
                        "alta"
                        if tipo == "compromisso"
                        or (escopo_forte and tipo_seguro)
                        else "baixa"
                    ),
                    "frase": (
                        contexto
                        if len(contexto) <= 220
                        else contexto[:217] + "..."
                    ),
                }
            if tipo == "compromisso":
                registro["titulo_evento"] = _nome_do_evento(trechos, indice)
            prazos.append(registro)
    return prazos


def casar_prazos(titulo_secao, prazos_aviso, so_confiaveis=True):
    chave = sem_acento(titulo_secao)
    if not chave:
        return []
    saida = []
    for prazo in prazos_aviso:
        # Compromisso tem trilha própria em montar_acoes, no nível do curso:
        # live não pertence a um módulo, e casar por seção nunca acharia.
        if prazo.get("tipo") in ("inicio", "compromisso"):
            continue
        escopo = prazo.get("escopo") or {}
        cobre = escopo_cobre(escopo, titulo_secao)
        # A reserva por rótulo ("Módulo 4" aparece no texto do prazo) não pode
        # atropelar um escopo que já disse a quinzena: senão o prazo de
        # 09/08 da Quinzena 2 voltava a cair no Módulo 4 da Quinzena 1.
        if not cobre and escopo.get("quinzena") is not None:
            continue
        if cobre or chave in sem_acento(prazo.get("rotulo") or ""):
            saida.append(prazo)
    saida.sort(key=lambda item: item["quando"])
    if not so_confiaveis:
        return saida
    return [
        item
        for item in saida
        if item.get("confianca", "alta") == "alta"
    ]


def fase_de(prazo):
    def classificar(alvo):
        if any(
            palavra in alvo
            for palavra in (
                "avaliacao por pares",
                "avaliacoes por pares",
                "revisao entre pares",
                "avaliar",
            )
        ):
            return "Avalie", "o trabalho do outro grupo"
        if any(
            palavra in alvo
            for palavra in ("submissao", "submissoes", "entrega", "entregue")
        ):
            return "Entregue", "o trabalho"
        return None

    return (
        classificar(sem_acento(prazo.get("rotulo") or ""))
        or classificar(sem_acento(prazo.get("frase") or ""))
        or ("Conclua", "")
    )


def rotulo_fase(prazo):
    rotulo = (prazo.get("rotulo") or "").strip()
    # Rótulo longo mas inteiro vira um resumo que preserva o começo e o fim.
    # "…do módulo individual" e "…do módulo em grupo" são obrigações
    # diferentes, e cortar os dois no meio fazia as duas virarem a mesma
    # linha "entrega" (rodada 3). Rótulo truncado na origem (termina em
    # "...") não serve como nome e continua caindo no nome da fase.
    if len(rotulo) > 55 and not rotulo.endswith("..."):
        return rotulo[:32].rstrip() + "… " + rotulo[-20:].lstrip()
    if 3 < len(rotulo) <= 55 and not rotulo.endswith("..."):
        return rotulo
    verbo, _ = fase_de(prazo)
    return {
        "Avalie": "avaliação por pares",
        "Entregue": "entrega",
    }.get(verbo, "conclusão")
