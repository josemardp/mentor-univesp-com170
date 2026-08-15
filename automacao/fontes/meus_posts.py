# -*- coding: utf-8 -*-
"""Em quais fóruns o próprio aluno já escreveu.

Por que existe: o guia sabia se um fórum estava marcado como concluído, e nada
mais. A marcação é manual, então ela mente nos dois sentidos. Em 14/08/2026 os
quatro fóruns temáticos parados desde a Semana 2 só apareceram porque alguém
conferiu na mão, e as avaliativas do SOC100 e do LET110 apareceram marcadas
como concluídas sem uma única tentativa. Nas disciplinas regulares a
participação nos fóruns compõe a nota, então "eu postei ali?" é pergunta de
nota, e não de higiene.

O caminho barato para responder é a página de mensagens do próprio usuário,
``/mod/forum/user.php?id=<usuario>&course=<curso>&mode=posts``. Ela lista os
posts dele naquela disciplina e traz, no cabeçalho de cada um, o nome do fórum
onde o post está.

O casamento é por nome de fórum, o que normalmente seria frágil. Aqui os dois
lados vêm do mesmo Moodle, para o mesmo objeto, então batem. E o modo de
falhar é o seguro: sem leitura boa, esta fonte devolve ``None`` e ninguém
afirma nada. "Não consegui ler" nunca vira "você não postou", que é a mesma
regra do boletim e do fórum de grupo.
"""
import re

from playwright.sync_api import Error as PlaywrightError

from configuracao import AVA
from dominio.datas import sem_acento
from modelos import SourceResult

# Cada post vem num article cujo h3 tem duas formas, e a diferença entre elas
# custou caro. Quando ele abriu a discussão, o cabeçalho é
#
#     COM100-BIA-2026S2B1-T001 ->
#     S3 - Fórum temático
#
# Quando ele respondeu a um tópico de outra pessoa, entram mais duas linhas:
#
#     COM170-BIA-DRP12-2026S2-T001 ->
#     Q2 M7 - Grupo: Ponto de encontro
#     Informar participantes na atividade em grupo
#         -> Re: Informar participantes na atividade em grupo
#
# Ler o trecho depois da *última* seta devolvia "Re: Informar participantes...",
# que não é nome de fórum nenhum, e o fórum sumia do mapa. Isto é, quem só
# responde aparecia como quem nunca escreveu. O JS devolve o texto cru, com as
# quebras de linha, e quem separa fórum de tópico é ``nome_do_forum``, aqui
# embaixo, onde dá para testar com o texto real da página.
JS_MEUS_POSTS = """
() => {
  const artigos = [...document.querySelectorAll('article.forum-post-container')];
  return artigos.map(a => {
    const titulo = a.querySelector('h3');
    const quando = a.querySelector('time');
    return {
      titulo: titulo ? titulo.textContent : '',
      quando: quando ? (quando.getAttribute('datetime') || quando.textContent.trim()) : null,
    };
  });
}
"""

# A página pagina de 10 em 10. Cinco páginas cobrem 50 posts numa disciplina,
# muito acima do que um bimestre gera, e o teto existe só para uma mudança de
# layout não virar laço infinito.
MAX_PAGINAS = 5


def chave_forum(rotulo):
    """Nome de fórum comparável: sem acento, sem caixa, sem espaço sobrando."""
    return re.sub(r"\s+", " ", sem_acento(rotulo or "")).strip()


def nome_do_forum(titulo):
    """Nome do fórum no cabeçalho de um post da página de mensagens.

    O cabeçalho começa pelo nome curto do curso e uma seta. O que vem logo
    depois, na própria linha, é o fórum; título de tópico e "Re: ..." vêm nas
    linhas seguintes e não interessam aqui.

    Cabeçalho fora do formato devolve string vazia, e vazio não entra no mapa:
    é melhor não saber onde ele postou do que registrar um fórum que não
    existe e depois cobrar (ou deixar de cobrar) pelo nome errado.
    """
    bruto = titulo or ""
    seta = bruto.find("->")
    if seta < 0:
        return ""
    depois = bruto[seta + 2:]
    for linha in depois.split("\n"):
        limpo = linha.strip()
        if limpo:
            # Linha que já começa na segunda seta quer dizer que o nome do
            # fórum não veio. "Re: alguma coisa" não é fórum, e registrar isso
            # como se fosse é o defeito que este parser existe para não ter.
            return "" if limpo.startswith("->") else limpo
    return ""


def ler(page, usuario_id, curso_id):
    """Fóruns da disciplina em que este usuário já escreveu.

    Devolve ``(mapa, ok)``. O mapa vai de nome normalizado do fórum para a
    data do post mais recente dele ali (ou string vazia quando a data não
    veio). ``ok`` falso quer dizer que a leitura não pode ser usada para
    concluir nada.
    """
    if not (usuario_id and curso_id):
        return {}, False
    encontrados = {}
    leu_alguma = False
    for pagina in range(MAX_PAGINAS):
        url = (
            f"{AVA}/mod/forum/user.php?id={usuario_id}"
            f"&course={curso_id}&mode=posts&page={pagina}"
        )
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(500)
            posts = page.evaluate(JS_MEUS_POSTS)
        except PlaywrightError:
            # Falha no meio da paginação não invalida o que já foi lido: os
            # fóruns achados continuam sendo prova de que ele postou. O que
            # não dá é concluir ausência, e é isso que ``ok`` carrega.
            return encontrados, False
        leu_alguma = True
        if not posts:
            break
        antes = len(encontrados)
        for post in posts:
            chave = chave_forum(nome_do_forum(post.get("titulo")))
            if not chave:
                continue
            quando = post.get("quando") or ""
            if quando > encontrados.get(chave, ""):
                encontrados[chave] = quando
        # Página repetida (o Moodle devolve a última quando o número passa do
        # fim) não acrescenta nome novo: parar aqui evita rodar o teto à toa.
        if len(encontrados) == antes and pagina:
            break
    return encontrados, leu_alguma


def resultado(page, usuario_id, curso_id, checked_at, cache=None):
    mapa, ok = ler(page, usuario_id, curso_id)
    if not ok:
        if cache:
            return SourceResult(
                status="falhou",
                dados=dict(cache),
                problemas=[
                    "não consegui ler suas mensagens de fórum nesta disciplina"
                ],
                checked_at=checked_at,
                from_cache=True,
                quantidade_atual=len(cache),
            )
        return SourceResult(
            status="falhou",
            dados={},
            problemas=[
                "não consegui ler suas mensagens de fórum nesta disciplina"
            ],
            checked_at=checked_at,
            quantidade_atual=0,
        )
    return SourceResult(
        status="live" if mapa else "vazio_confirmado",
        dados=mapa,
        checked_at=checked_at,
        quantidade_atual=len(mapa),
        last_live_at=checked_at,
    )
