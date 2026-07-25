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


def _tipo_prazo(fragmento, contexto, pos_data=None):
    alvo = sem_acento(fragmento)
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
    return "fim", True


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


def escopo_cobre(escopo, titulo_secao):
    if not escopo:
        return False
    encontrado = FAMILIA_RE.match(titulo_secao or "")
    if not encontrado:
        return False
    familia = sem_acento(encontrado.group(1)).strip().rstrip("s")
    return (
        familia == escopo["familia"]
        and int(encontrado.group(2)) in escopo["numeros"]
    )


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
    for indice, fragmento in enumerate(trechos):
        achado = _escopo_de(fragmento)
        if achado:
            escopo, escopo_forte = achado, True
        elif escopo is not None and muda_assunto(fragmento):
            escopo_forte = False
        if not 4 <= len(fragmento) <= 300:
            continue
        contexto = " ".join(trechos[max(0, indice - 2) : indice + 1])
        if _tem(sem_acento(contexto), GATILHOS_PRAZO) < 0:
            continue
        if tem_negacao(fragmento):
            continue
        for quando, trecho, hora_certa, posicao in achar_datas(
            fragmento, referencia
        ):
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
            tipo, tipo_seguro = _tipo_prazo(fragmento, contexto, posicao)
            prazos.append(
                {
                    "rotulo": rotulo,
                    "quando": quando.isoformat(),
                    "trecho": trecho,
                    "tipo": tipo,
                    "hora_certa": hora_certa,
                    "escopo": escopo,
                    "confianca": (
                        "alta" if escopo_forte and tipo_seguro else "baixa"
                    ),
                    "frase": (
                        contexto
                        if len(contexto) <= 220
                        else contexto[:217] + "..."
                    ),
                }
            )
    return prazos


def casar_prazos(titulo_secao, prazos_aviso, so_confiaveis=True):
    chave = sem_acento(titulo_secao)
    if not chave:
        return []
    saida = []
    for prazo in prazos_aviso:
        if prazo.get("tipo") == "inicio":
            continue
        if escopo_cobre(prazo.get("escopo"), titulo_secao) or chave in sem_acento(
            prazo.get("rotulo") or ""
        ):
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
    if 3 < len(rotulo) <= 55 and not rotulo.endswith("..."):
        return rotulo
    verbo, _ = fase_de(prazo)
    return {
        "Avalie": "avaliação por pares",
        "Entregue": "entrega",
    }.get(verbo, "conclusão")
