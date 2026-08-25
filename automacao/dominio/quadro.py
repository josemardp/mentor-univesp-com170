# -*- coding: utf-8 -*-
"""O quadro de cada disciplina: uma linha por semana ou por quinzena.

Motivo de existir, pedido dele em 25/08/2026 depois de ver o levantamento
feito à mão: o guia sabia dizer o que fazer hoje e quanto ele tirou em cada
atividade, mas não tinha em lugar nenhum a visão de cima da disciplina — a
tabela onde cada semana é uma linha, com a data em que fecha e a nota ao
lado. Era a pergunta que ele fazia toda semana ("onde eu estou nessa
matéria?") e que exigia abrir quatro páginas do AVA.

Este módulo não lê nada: monta o quadro a partir do que as fontes já
colheram. É de propósito. Quadro é interpretação, e interpretação errada com
cara de tabela é pior que tabela nenhuma, então ele precisa ser testável sem
navegador.

Duas formas de disciplina, porque a Univesp tem duas:

- **regular** (COM100, SOC100, LET110): sete semanas, cada uma com uma
  Atividade Avaliativa e um fórum temático. Quem manda no prazo é o
  cronograma oficial, e a data que interessa é a do fim da carência, porque é
  nela que o AVA fecha de verdade.
- **quinzenal** (COM170): sete quinzenas, cada uma com dois Laboratórios de
  Avaliação (portfólio individual e trabalho em grupo). Cada um tem dois
  prazos distintos, entregar e avaliar o colega, e o segundo vale nota do
  mesmo jeito que o primeiro.

Célula sem informação vira "não sei", nunca "não fez". A regra vale para o
quadro inteiro: ele existe para ele confiar, e um verde errado custa mais que
um cinza honesto.
"""
import re
from datetime import datetime

from configuracao import BR_TZ

SEMANA_RE = re.compile(r"^semana\s+(\d+)$", re.IGNORECASE)
QUINZENA_RE = re.compile(r"^quinzena\s+(\d+)$", re.IGNORECASE)

# O rótulo do fórum que vale participação. "Fórum de dúvidas gerais" e
# "Fórum geral" não entram: não valem nota e não têm prazo.
FORUM_TEMATICO_RE = re.compile(r"f[oó]rum tem[aá]tico", re.IGNORECASE)

INDIVIDUAL_RE = re.compile(r"portf[oó]lio individual", re.IGNORECASE)
GRUPO_RE = re.compile(r"(portf[oó]lio em grupo|trabalho em grupo)", re.IGNORECASE)


def _quando(iso):
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None


def _passou(iso, agora):
    quando = _quando(iso)
    if quando is None or agora is None:
        return None
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=BR_TZ)
    return quando < agora


def _celula(chave, estado, texto, detalhe=None, url=None):
    return {
        "chave": chave,
        "estado": estado,
        "texto": texto,
        "detalhe": detalhe,
        "url": url,
    }


def _vazia(chave):
    return _celula(chave, "vazio", "—")


def _descendentes(curso, secao):
    """A seção e tudo o que pende dela.

    Na COM170 a Quinzena 3 é uma seção com cinco itens e sete sub-seções
    (Q3 Módulo 1 a 7); os Laboratórios moram nos módulos 6 e 7, não na
    quinzena. Ler só a seção-mãe devolvia quinzena sem nenhuma entrega.
    """
    secoes = curso.get("sections") or []
    familia, fronteira = [secao], {secao.get("id")}
    mudou = True
    while mudou:
        mudou = False
        for outra in secoes:
            if outra.get("id") in fronteira:
                continue
            if outra.get("parent") in fronteira:
                familia.append(outra)
                fronteira.add(outra.get("id"))
                mudou = True
    return familia


def _itens(curso, secao):
    return [
        item
        for parte in _descendentes(curso, secao)
        for item in parte.get("items") or []
    ]


def _prazos_do_calendario(dados, curso_id):
    """``{(cmid, tipo): quando}`` para os prazos que o AVA publicou.

    O item guarda um prazo só, e o Laboratório tem dois. O tipo do evento
    (``closesubmission`` / ``closeassessment``) é o próprio Moodle separando
    "entregar" de "avaliar o colega".
    """
    mapa = {}
    for evento in dados.get("eventos") or []:
        if str(evento.get("curso_id")) != str(curso_id):
            continue
        cmid, tipo = evento.get("cmid"), evento.get("tipo")
        if not cmid or not tipo:
            continue
        mapa.setdefault((str(cmid), tipo), evento.get("quando"))
    return mapa


def _nota_da_avaliativa(item, agora):
    """A célula de nota de um questionário."""
    resumo = item.get("quiz") or {}
    feitas = resumo.get("tentativas_feitas")
    permitidas = resumo.get("tentativas_permitidas")
    vencido = _passou(item.get("carencia") or item.get("prazo"), agora)

    detalhe = None
    # Quantas tentativas sobraram só decide alguma coisa enquanto o prazo
    # corre. Numa semana encerrada era informação morta repetida em toda
    # linha, e no celular ela dobrava a altura do quadro inteiro.
    if permitidas and not vencido:
        # Curto de propósito: "nenhuma das 3 tentativas usada" quebrava em
        # quatro linhas dentro da célula.
        usadas = "?" if feitas is None else feitas
        detalhe = f"{usadas} de {permitidas} tentativas"

    if item.get("tem_nota"):
        # De onde a nota veio não entra na célula: quando o boletim está
        # vazio, é a disciplina inteira que vem do questionário, e a frase
        # cabe uma vez no cabeçalho em vez de sete vezes na tabela.
        return _celula(
            "avaliativa", "ok", item.get("nota_txt") or "feita",
            detalhe, item.get("url"),
        )

    if item.get("entrega_confirmada") is False or feitas == 0:
        estado = "perdeu" if vencido else "falta"
        texto = "não fez" if vencido else "a fazer"
        return _celula("avaliativa", estado, texto, detalhe, item.get("url"))
    if vencido:
        # Prazo vencido, entrega não negada e sem nota: pode ser correção
        # atrasada do facilitador. Nem verde nem vermelho.
        return _celula(
            "avaliativa", "nao_sei", "sem nota", detalhe, item.get("url")
        )
    return _celula("avaliativa", "falta", "a fazer", detalhe, item.get("url"))


def _celula_forum(item):
    if item is None:
        return _vazia("forum")
    postei = item.get("postei")
    if postei is True:
        return _celula("forum", "ok", "postou", None, item.get("url"))
    if postei is False:
        return _celula("forum", "falta", "sem post", None, item.get("url"))
    return _celula("forum", "nao_sei", "não sei", None, item.get("url"))


def _celula_laboratorio(chave, item, agora):
    """Portfólio individual ou trabalho em grupo, com as duas obrigações.

    Entregar e avaliar são prazos diferentes. Até 25/08/2026 o quadro não
    existia, mas a fila já tratava os dois separados; aqui eles voltam a
    caber numa célula só, sem que a segunda suma quando a primeira fecha.
    """
    if item is None:
        return _vazia(chave)
    enviado = item.get("enviado")
    avaliacao_pendente = item.get("avaliacao_pendente")
    vencido = _passou(item.get("prazo"), agora)

    if item.get("tem_nota"):
        detalhe = "falta avaliar o colega" if avaliacao_pendente else None
        if item.get("nota") == 0:
            # Achado em 13/08/2026 e ainda de pé: laboratório entregue, o
            # colega marcou o nível máximo, e o boletim registra 0,00 porque
            # o facilitador não rodou a fase de encerramento. Verde aqui
            # diria "está resolvido" e vermelho diria "você não fez". Nem um
            # nem outro: é um zero que ele precisa contestar. Vale mesmo sem
            # prova de envio nesta leitura — zero em Laboratório nunca é
            # estado normal, ao contrário do zero das atividades SCORM.
            return _celula(
                chave, "atencao", item.get("nota_txt") or "0,00",
                detalhe or (
                    "entregue e zerado, confira"
                    if enviado is True else "zerado, confira"
                ),
                item.get("url"),
            )
        return _celula(
            chave, "ok", item.get("nota_txt") or "feito", detalhe,
            item.get("url"),
        )
    if enviado is True:
        if avaliacao_pendente:
            return _celula(
                chave, "falta", "enviado", "falta avaliar o colega",
                item.get("url"),
            )
        return _celula(chave, "ok", "enviado", None, item.get("url"))
    if enviado is False:
        if chave == "grupo":
            # Quem envia pelo grupo é o representante, então a ausência de
            # envio nesta conta não prova que o grupo não entregou. Enquanto
            # o prazo corre isso é cobrança legítima ("ninguém enviou até
            # agora"); depois de vencido vira acusação sem prova, e o guia
            # não acusa.
            return _celula(
                chave,
                "nao_sei" if vencido else "falta",
                "não consta" if vencido else "a enviar",
                "envia o representante",
                item.get("url"),
            )
        estado = "perdeu" if vencido else "falta"
        texto = "não enviou" if vencido else "a enviar"
        return _celula(chave, estado, texto, None, item.get("url"))
    return _celula(chave, "nao_sei", "não sei", None, item.get("url"))


def _primeiro(itens, teste):
    for item in itens:
        if teste(item):
            return item
    return None


def _linha_regular(curso, secao, numero, agora):
    itens = _itens(curso, secao)
    avaliativa = _primeiro(itens, lambda i: i.get("type") == "quiz")
    forum = _primeiro(
        itens,
        lambda i: i.get("type") == "forum"
        and FORUM_TEMATICO_RE.search(i.get("label") or ""),
    )
    fecha = alvo = None
    if avaliativa:
        fecha = avaliativa.get("carencia") or avaliativa.get("prazo")
        if avaliativa.get("carencia"):
            alvo = avaliativa.get("prazo")
    celulas = [
        _nota_da_avaliativa(avaliativa, agora) if avaliativa
        else _vazia("avaliativa"),
        _celula_forum(forum),
    ]
    return {
        "n": numero,
        "rotulo": f"S{numero}",
        "titulo": secao.get("title") or f"Semana {numero}",
        "tema": secao.get("theme"),
        "prazos": [{"rotulo": "Fecha", "quando": fecha, "alvo": alvo}],
        "celulas": celulas,
        "vazia": not itens,
    }


def _linha_quinzenal(curso, secao, numero, agora, prazos_calendario):
    itens = _itens(curso, secao)
    individual = _primeiro(
        itens,
        lambda i: i.get("type") == "workshop"
        and INDIVIDUAL_RE.search(i.get("label") or ""),
    )
    grupo = _primeiro(
        itens,
        lambda i: i.get("type") == "workshop"
        and GRUPO_RE.search(i.get("label") or ""),
    )

    def prazo(tipo):
        for lab in (individual, grupo):
            if not lab or not lab.get("cmid"):
                continue
            achado = prazos_calendario.get((str(lab["cmid"]), tipo))
            if achado:
                return achado
        return None

    entregar = prazo("closesubmission") or (
        individual.get("prazo") if individual else None
    ) or (grupo.get("prazo") if grupo else None)
    avaliar = prazo("closeassessment")
    return {
        "n": numero,
        "rotulo": f"Q{numero}",
        "titulo": secao.get("title") or f"Quinzena {numero}",
        "tema": secao.get("theme"),
        "prazos": [
            {"rotulo": "Entrega até", "quando": entregar, "alvo": None},
            {"rotulo": "Avaliar até", "quando": avaliar, "alvo": None},
        ],
        "celulas": [
            _celula_laboratorio("individual", individual, agora),
            _celula_laboratorio("grupo", grupo, agora),
        ],
        "vazia": not itens,
    }


def _situacao(linha, agora):
    if linha["vazia"]:
        return "nao_aberta"
    ultimo = [p["quando"] for p in linha["prazos"] if p.get("quando")]
    if ultimo and all(_passou(quando, agora) for quando in ultimo):
        return "fechada"
    return "aberta"


# Cabeçalho curto de propósito: são 4 ou 5 colunas em 375px de celular, e
# "Atividade avaliativa" por extenso empurrava a última coluna para fora da
# caixa. O texto de abertura da aba explica o que cada uma é.
COLUNAS = {
    "regular": ["Semana", "Fecha", "Avaliativa", "Fórum"],
    "quinzenal": [
        "Quinzena", "Entrega", "Avaliar", "Individual", "Grupo",
    ],
}


def quadro_do_curso(dados, curso, agora=None):
    """O quadro de uma disciplina, ou ``None`` se ela não tem unidades lidas."""
    agora = agora or datetime.now(BR_TZ)
    modelo = "quinzenal" if curso.get("modelo") == "quinzenal" else "regular"
    padrao = QUINZENA_RE if modelo == "quinzenal" else SEMANA_RE
    prazos_calendario = _prazos_do_calendario(dados, curso.get("id"))

    linhas = []
    for secao in curso.get("sections") or []:
        # A ambientação (AIA) da COM170 também tem "Semana 1" a "Semana 4", e
        # ela encerrou: entrar no quadro faria a disciplina parecer ter onze
        # unidades e duas contagens começando do 1.
        if secao.get("fase") == "AIA":
            continue
        achado = padrao.match((secao.get("title") or "").strip())
        if not achado:
            continue
        numero = int(achado.group(1))
        if modelo == "quinzenal":
            linha = _linha_quinzenal(
                curso, secao, numero, agora, prazos_calendario
            )
        else:
            linha = _linha_regular(curso, secao, numero, agora)
        linha["situacao"] = _situacao(linha, agora)
        linhas.append(linha)

    if not linhas:
        return None
    linhas.sort(key=lambda linha: linha["n"])

    # A unidade em curso é a primeira que já abriu e ainda não fechou. Sem
    # nenhuma aberta (fim do semestre, ou leitura incompleta), ninguém é
    # marcado: destacar a linha errada é pior que não destacar nenhuma.
    atual = next(
        (linha["n"] for linha in linhas if linha["situacao"] == "aberta"),
        None,
    )
    for linha in linhas:
        linha["atual"] = linha["n"] == atual

    boletim = curso.get("boletim") or {}
    # A "Média AVA" da COM170 é 0,51 e não mede nada: o boletim lança cada
    # atividade interativa (SCORM) com 0,00 mesmo concluída, e elas entram na
    # conta. Mostrar o número sozinho, sem dizer isso, é o jeito de um dado
    # certo assustar à toa. A contagem sai do próprio boletim, nunca de uma
    # regra escrita à mão sobre a disciplina.
    vistos, zeros, do_questionario = set(), 0, False
    for secao in curso.get("sections") or []:
        for item in secao.get("items") or []:
            if item.get("cmid") in vistos:
                continue
            vistos.add(item.get("cmid"))
            if item.get("type") == "scorm" and item.get("nota") == 0:
                zeros += 1
            if item.get("nota_fonte") not in (None, "boletim"):
                do_questionario = True
    return {
        "codigo": curso.get("code"),
        "nome": curso.get("name"),
        "id": curso.get("id"),
        "modelo": modelo,
        "colunas": COLUNAS[modelo],
        "linhas": linhas,
        "atual": atual,
        "media": boletim.get("media"),
        "boletim_status": boletim.get("status"),
        "zeros_interativos": zeros,
        "notas_do_questionario": do_questionario,
        "participacao": curso.get("participacao"),
    }


def montar(dados, agora=None):
    """Um quadro por disciplina, na ordem em que as disciplinas vieram."""
    quadros = []
    for curso in dados.get("courses") or []:
        quadro = quadro_do_curso(dados, curso, agora)
        if quadro:
            quadros.append(quadro)
    return quadros
