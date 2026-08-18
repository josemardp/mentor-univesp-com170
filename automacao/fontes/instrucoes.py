# -*- coding: utf-8 -*-
"""Datas anunciadas na página de instruções da quinzena/semana.

A Univesp publica o calendário da quinzena numa página do próprio curso
("Q2 - Instruções da Quinzena 2"), e não no calendário do Moodle nem em
aviso de fórum. Em 04/08/2026 essa página dizia "9 de agosto para concluir
o Módulo 4" e "15 de agosto para enviar os trabalhos", enquanto o guia
mostrava as atividades da quinzena como "sem prazo definido".

Texto corrido é a camada onde este projeto mais errou (quatro rodadas de
auditoria). Por isso nada daqui entra na fila de tarefas: tudo nasce com
confiança baixa e cai no bloco "Confirme se isto é prazo mesmo", com a
frase original e o link da página. O robô mostra o que leu; quem decide é
o Josemar.
"""
import re
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError

from configuracao import BR_TZ
from dominio.datas import sem_acento
from dominio.prazos import extrair_prazos

# "Lembrete de datas e live" entrou em 17/08/2026. É outra página da mesma
# quinzena, e é onde moram as datas das lives: a Quinzena 3 oferece sete, uma
# delas conta ponto, e a primeira era no dia seguinte. Nada disso chegava ao
# guia, que mostrava "Assista: Live com facilitador" sem data nenhuma.
ROTULO_RE = re.compile(
    r"instrucoes da (quinzena|semana)|lembrete de datas", re.IGNORECASE
)
# Duas páginas por unidade, e duas unidades convivem na virada da quinzena.
MAX_PAGINAS = 6


def paginas_de_instrucao(secoes):
    achadas = []
    for secao in secoes:
        for item in secao.get("items") or []:
            if item.get("type") != "page" or not item.get("url"):
                continue
            if ROTULO_RE.search(sem_acento(item.get("label") or "")):
                achadas.append(item)
    return achadas[:MAX_PAGINAS]


# A legenda descreve um intervalo, e o intervalo pode atravessar dois meses:
# "de 3 a 18 de agosto de 2026" fica num mês só, "de 16 de agosto a 1º de
# setembro de 2026" não. Por isso as duas pontas são capturadas separadas.
CAPTION_RE = re.compile(
    r"calend[áa]rio da (quinzena|semana)\s*(\d+)"
    r".{0,40}?\bde\s+(\d{1,2})[ºo°]?\s*(?:de\s+(\w+))?"
    r"\s+a\s+(\d{1,2})[ºo°]?\s+de\s+(\w+)\s+de\s+(\d{4})",
    re.IGNORECASE,
)
CELULA_RE = re.compile(r"^(\d{1,2})\s+(.+)$")
ESCOPO_MODULO_RE = re.compile(r"m[óo]dulo\s+(\d+)", re.IGNORECASE)


def janela_da_legenda(caption):
    """As duas pontas do intervalo escrito na legenda, ou ``None``.

    O ano só aparece no fim ("a 1º de setembro de 2026"), então uma quinzena
    que vira o ano tem o começo no ano anterior.
    """
    from dominio.datas import mes as numero_do_mes

    achado = CAPTION_RE.search(caption or "")
    if not achado:
        return None
    mes_fim = numero_do_mes(achado.group(6))
    if not mes_fim:
        return None
    mes_ini = numero_do_mes(achado.group(4)) if achado.group(4) else mes_fim
    if not mes_ini:
        return None
    ano_fim = int(achado.group(7))
    return {
        "familia": sem_acento(achado.group(1)),
        "numero": int(achado.group(2)),
        "dia_ini": int(achado.group(3)),
        "mes_ini": mes_ini,
        "ano_ini": ano_fim - 1 if mes_ini > mes_fim else ano_fim,
        "dia_fim": int(achado.group(5)),
        "mes_fim": mes_fim,
        "ano_fim": ano_fim,
    }


def data_da_celula(dia, janela):
    """``(ano, mês)`` do dia solto da célula, ou ``None`` quando não dá para saber.

    A célula traz só o número ("23 PRAZO MÓDULOS 1 A 4"); o mês tem que vir da
    legenda. Até 17/08/2026 o código pegava o último mês escrito nela, e a
    legenda da Quinzena 3 ("de 16 de agosto a 1º de setembro de 2026") terminava
    em setembro: o dia 23 virou 23/09 no lugar de 23/08, e o mesmo com a entrega
    de 29/08. Um mês inteiro de folga em dois prazos que valem nota, publicados
    na fila e no e-mail como se fossem certos.

    Dia que não cabe no intervalo declarado não é adivinhado: a legenda e a
    tabela estão discordando, e aí o guia prefere não afirmar data nenhuma.
    """
    if (janela["mes_ini"], janela["ano_ini"]) == (
        janela["mes_fim"],
        janela["ano_fim"],
    ):
        if janela["dia_ini"] <= dia <= janela["dia_fim"]:
            return janela["ano_fim"], janela["mes_fim"]
        return None
    if dia >= janela["dia_ini"]:
        return janela["ano_ini"], janela["mes_ini"]
    if dia <= janela["dia_fim"]:
        return janela["ano_fim"], janela["mes_fim"]
    return None


def calendario_da_quinzena(page, url):
    """Prazos lidos da tabela-calendário, não do texto corrido.

    A página de instruções traz uma tabela com legenda ("Calendário da
    Quinzena 2, de 3 a 18 de agosto de 2026") e células marcadas por classe:
    ``prazo`` nas datas de fechamento, ``estudo``/``entrega``/``leitura`` nas
    etapas. Isso é dado estruturado: o dia vem do número da célula, o mês e o
    ano vêm da legenda, e o rótulo vem escrito ("PRAZO MÓDULO 4").

    Por ser estrutura e não prosa, estes prazos nascem com confiança alta,
    diferente do resto desta fonte. Foi a leitura de texto livre que causou
    quatro rodadas de auditoria; tabela com legenda não tem essa ambiguidade.
    """
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(1500)
    except PlaywrightError:
        return []
    for quadro in page.frames:
        try:
            tabela = quadro.evaluate(JS_CALENDARIO)
        except PlaywrightError:
            continue
        if not tabela:
            continue
        janela = janela_da_legenda(tabela.get("caption") or "")
        if not janela:
            continue
        familia = janela["familia"]
        prazos = []
        for celula in tabela.get("celulas") or []:
            if "prazo" not in (celula.get("classe") or ""):
                continue
            partes = CELULA_RE.match(celula.get("texto") or "")
            if not partes:
                continue
            dia = int(partes.group(1))
            rotulo = partes.group(2).strip()
            data = data_da_celula(dia, janela)
            if data is None:
                continue
            try:
                quando = datetime(
                    data[0], data[1], dia, 23, 59, tzinfo=BR_TZ
                )
            except ValueError:
                continue
            modulo = ESCOPO_MODULO_RE.search(rotulo)
            numero_quinzena = janela["numero"]
            escopo = (
                {
                    "familia": "modulo",
                    "numeros": [int(modulo.group(1))],
                    # Sem isto, "Módulo 4" da Quinzena 2 casaria também com o
                    # Módulo 4 da Quinzena 1, que já encerrou.
                    "quinzena": numero_quinzena,
                    "txt": rotulo,
                }
                if modulo
                else {
                    "familia": familia,
                    "numeros": [numero_quinzena],
                    "txt": rotulo,
                }
            )
            prazos.append(
                {
                    "rotulo": rotulo.capitalize(),
                    "quando": quando.isoformat(),
                    "trecho": celula.get("texto"),
                    "tipo": "fim",
                    "hora_certa": False,
                    "escopo": escopo,
                    "confianca": "alta",
                    "frase": (
                        f"{tabela.get('caption')}. Célula: "
                        f"{celula.get('texto')}"
                    ),
                }
            )
        if prazos:
            return prazos
    return []


JS_CALENDARIO = """
() => {
  const t = [...document.querySelectorAll('table')]
    .find(x => /calend[áa]rio da (quinzena|semana)/i.test(
      (x.querySelector('caption') || {}).innerText || ''));
  if (!t) return null;
  return {
    caption: (t.querySelector('caption').innerText || '').replace(/\\s+/g, ' ').trim(),
    celulas: [...t.querySelectorAll('td')].map(td => ({
      texto: (td.innerText || '').replace(/\\s+/g, ' ').trim(),
      classe: td.className || '',
    })).filter(c => c.texto),
  };
}
"""


def _texto_da_pagina(page, url):
    """O conteúdo fica dentro de um iframe, então lê a página e os quadros."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(800)
        partes = []
        for quadro in page.frames:
            try:
                partes.append(quadro.locator("body").inner_text()[:12000])
            except PlaywrightError:
                continue
        return "\n".join(partes)
    except PlaywrightError:
        return None


# "Uma regra que vale para toda a disciplina: os prazos terminam sempre às
# 23h59 do dia indicado." A tabela-calendário traz só o número do dia, então o
# cartão saía "vence 23/08 (horário não informado)" com a hora escrita na
# mesma página, dois parágrafos abaixo. Usar o que a página declara não é
# estimar: é ler a fonte inteira em vez de metade dela.
REGRA_DE_HORA_RE = re.compile(
    r"prazos?[^.]{0,90}?sempre[^.]{0,25}?(\d{1,2})\s*[h:]\s*(\d{2})"
)
# "23 de agosto, domingo, às 23h59." A hora da data específica ganha da regra
# geral, porque uma unidade pode ter uma exceção e quem diz isso é a frase
# mais próxima da data.
HORA_DA_DATA_RE = (
    r"\b{dia}\s+de\s+{mes}\b[^.]{{0,60}}?(\d{{1,2}})\s*[h:]\s*(\d{{2}})"
)
MESES_POR_NUMERO = {
    1: "janeiro", 2: "fevereiro", 3: "marco", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}
# "Quem conclui os quatro primeiros módulos depois de domingo, 23 de agosto,
# (...) O trabalho em grupo fica com quem concluiu os módulos até domingo."
# Perder este prazo não atrasa: tira ele do trabalho em grupo da quinzena. O
# cartão dizia só "Conclua: Prazo módulos 1 a 4".
GATILHO_CONSEQUENCIA_RE = re.compile(r"\bdepois\s+d[eo]\b", re.IGNORECASE)
# Quantas frases seguir procurando a perda depois do gatilho. Três cobrem o
# caso real da Quinzena 3 sem varrer parágrafo alheio.
FRASES_ADIANTE = 3
PERDA = ("grupo", "proxima oportunidade", "fica com quem", "nao participa")


def hora_declarada(texto, dia, mes):
    """A hora que a própria página dá para aquele prazo, ou ``None``.

    Devolve ``(hora, minuto)``. Procura primeiro a frase que fala da data e
    depois a regra geral da disciplina. Sem nenhuma das duas, cala: hora que
    a fonte não escreveu continua sendo hora que o guia não sabe.
    """
    alvo = sem_acento(texto or "")
    nome = MESES_POR_NUMERO.get(mes)
    if nome:
        especifica = re.search(
            HORA_DA_DATA_RE.format(dia=dia, mes=nome), alvo
        )
        if especifica:
            return int(especifica.group(1)), int(especifica.group(2))
    geral = REGRA_DE_HORA_RE.search(alvo)
    if geral:
        return int(geral.group(1)), int(geral.group(2))
    return None


def consequencia_do_prazo(texto, dia):
    """A frase em que a página diz o que se perde ao passar deste prazo.

    Sai literal, truncada, como o bloco "confirme se é prazo": o guia mostra
    o que leu e não resume por conta própria. Sem frase que ligue o dia à
    perda, devolve ``None`` — cartão sem explicação é melhor que explicação
    inventada.
    """
    # Quebra de linha separa frase tanto quanto ponto final: título de seção
    # não termina em ponto, e sem isso "Se você concluir os módulos depois do
    # dia 23" (o título) saía colado no parágrafo que vem embaixo dele,
    # repetindo a mesma informação duas vezes no cartão.
    frases = [
        " ".join(frase.split())
        for linha in (texto or "").splitlines()
        for frase in re.split(r"(?<=\.)\s+", linha)
        if len(frase.strip()) > 20
    ]
    for inicio, frase in enumerate(frases):
        if not GATILHO_CONSEQUENCIA_RE.search(frase):
            continue
        if not re.search(rf"\b{dia}\b", frase):
            continue
        # A perda quase nunca está na mesma frase do "depois de": a página
        # diz primeiro o que acontece com quem atrasa e só depois o que ele
        # deixa de fazer. Junta até achar, e para assim que achou.
        for fim in range(inicio, min(inicio + FRASES_ADIANTE, len(frases))):
            if any(
                palavra in sem_acento(frases[fim]) for palavra in PERDA
            ):
                return " ".join(frases[inicio:fim + 1])
    return None


def _chave_do_prazo(prazo):
    """Uma linha por data, menos quando o dia tem vários encontros.

    A dedução era só ``quando[:10]``, com um motivo bom: a mesma página
    repete "15 de agosto" em vários parágrafos e o bloco de conferência não
    precisa do eco. Só que a página "Lembrete de datas e live" da Quinzena 3
    publica seis lives, e três delas dividem dia com outra (19/08 às 16h, 18h
    e 19h; 20/08 às 10h e 17h). Com a chave por dia, as três segundas
    sumiam: o guia mostrava três opções de live onde o AVA oferece seis, e
    participar ao vivo de uma delas é um dos dez pontos da quinzena.

    Encontro com hora marcada casa por instante e nome; o resto continua
    casando por dia.
    """
    if prazo.get("tipo") == "compromisso" and prazo.get("hora_certa"):
        nome = prazo.get("titulo_evento") or prazo.get("rotulo") or ""
        return (prazo["quando"], sem_acento(nome))
    return prazo["quando"][:10]


def _completar_pelo_texto(prazo, texto):
    """Hora e consequência, quando a própria página as escreve."""
    quando = datetime.fromisoformat(prazo["quando"])
    hora = hora_declarada(texto, quando.day, quando.month)
    if hora and not prazo.get("hora_certa"):
        prazo["quando"] = quando.replace(
            hour=hora[0], minute=hora[1]
        ).isoformat()
        prazo["hora_certa"] = True
        prazo["hora_fonte"] = "a página da unidade declara o horário"
    consequencia = consequencia_do_prazo(texto, quando.day)
    if consequencia:
        prazo["consequencia"] = consequencia
    return prazo


def ler(page, secoes, referencia):
    saida = []
    for item in paginas_de_instrucao(secoes):
        # Tabela primeiro: é estrutura, e o que ela afirma dispensa o
        # tratamento defensivo que o texto corrido exige.
        prazos = [
            prazo
            for prazo in calendario_da_quinzena(page, item["url"])
            if prazo["quando"][:10] >= referencia.isoformat()
        ]
        texto = _texto_da_pagina(page, item["url"])
        if not texto:
            if prazos:
                saida.append(_como_aviso(item, prazos))
            continue
        # A tabela dá o dia; o texto da mesma página costuma dar a hora e
        # dizer o que se perde ao passar do prazo. Nada disso é inferência:
        # é a metade da página que a leitura estruturada não alcança.
        for prazo in prazos:
            _completar_pelo_texto(prazo, texto)
        vistos = {_chave_do_prazo(prazo) for prazo in prazos}
        for prazo in extrair_prazos(texto, referencia):
            if prazo["quando"][:10] < referencia.isoformat():
                continue
            chave = _chave_do_prazo(prazo)
            if chave in vistos:
                continue
            vistos.add(chave)
            prazos.append({**prazo, "confianca": "baixa"})
        if prazos:
            saida.append(_como_aviso(item, prazos))
    return saida


def _como_aviso(item, prazos):
    return {
        "autor": item["label"],
        "titulo": item["label"],
        "url": item["url"],
        "autoridade": "institucional",
        "prazos": prazos,
    }
