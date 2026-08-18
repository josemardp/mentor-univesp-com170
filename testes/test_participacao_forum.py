# -*- coding: utf-8 -*-
"""
Nas disciplinas regulares a participação nos fóruns temáticos compõe a nota,
mas até 14/08/2026 o guia só sabia se o fórum estava marcado como concluído.
A marcação é manual, então mente nos dois sentidos: quatro fóruns ficaram
parados desde a Semana 2 sem aparecer em lugar nenhum, e duas avaliativas
apareceram "Concluído" sem uma única tentativa.

A prova passou a vir da lista de mensagens do próprio aluno na disciplina
(``fontes/meus_posts.py``). O campo ``postei`` tem três estados, e o terceiro
é o que importa: ``None`` quer dizer que a leitura não funcionou, e leitura
que falhou nunca vira cobrança.

Rodar:  python testes/test_participacao_forum.py
"""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automacao"))

from dominio.acoes import montar_acoes  # noqa: E402
from fontes.meus_posts import (  # noqa: E402
    MAX_PAGINAS,
    chave_forum,
    ler,
    nome_do_forum,
    resultado,
)

falhas = []


def checa(cond, msg):
    print(("  ok    " if cond else "  FALHA") + " | " + msg)
    if not cond:
        falhas.append(msg)


HOJE = date(2026, 8, 14)
AGORA = datetime(2026, 8, 14, 20, 0, tzinfo=timezone(timedelta(hours=-3)))


def montar(postei, status=None, modelo="regular", label="S3 - Fórum temático"):
    dados = {
        "courses": [
            {
                "id": "18870",
                "code": "COM100",
                "modelo": modelo,
                "avisos": [],
                "sections": [
                    {
                        "id": "1",
                        "title": "Semana 3",
                        "items": [
                            {
                                "cmid": "160798",
                                "label": label,
                                "type": "forum",
                                "url": "https://ava.univesp.br/mod/forum/view.php?id=160798",
                                "status": status,
                                "conta_nota": False,
                                "postei": postei,
                                "prazo": None,
                            }
                        ],
                    }
                ],
            }
        ],
        "eventos": [],
    }
    acoes, encerrados, higiene, confirmar = montar_acoes(
        dados, HOJE, agora=AGORA
    )
    return acoes, higiene


print("\n== não postou: vira cobrança de verdade, não higiene ==")

acoes, higiene = montar(postei=False)
checa(len(acoes) == 1, f"o fórum entra na fila de ações (veio {len(acoes)})")
checa(not higiene, "e não fica no balde de higiene")
if acoes:
    a = acoes[0]
    checa(a.get("conta_nota") is True, "sai marcado como algo que vale nota")
    checa(a.get("prazo") is None, "sem prazo inventado: o AVA não publica um")
    checa("participação" in (a.get("explicacao") or ""),
          "o cartão explica por que está ali")
    checa(a.get("verbo") == "Participe", "o verbo é participar")


print("\n== postou: some da fila, mesmo sem o Moodle marcar ==")

acoes, higiene = montar(postei=True)
checa(not acoes, "quem já escreveu não é cobrado")
checa(not higiene, "e nem sobra como pendência de higiene")


print("\n== marcado como concluído mas sem post: continua cobrando ==")

acoes, _ = montar(postei=False, status="Concluído")
checa(len(acoes) == 1,
      "o selo manual do Moodle não encerra o que a nota ainda cobra")


print("\n== postou e o Moodle marcou: silêncio ==")

acoes, higiene = montar(postei=True, status="Concluído")
checa(not acoes and not higiene, "nada a dizer quando as duas provas batem")


print("\n== leitura falhou (None): não acusa ninguém ==")

acoes, higiene = montar(postei=None)
checa(not acoes, "sem prova, não vira cobrança")
checa(not higiene,
      "e nem inventa pendência: sem status no Moodle e sem leitura, cala")

acoes, higiene = montar(postei=None, status="Marcar como feito")
checa(not acoes, "com o Moodle pedindo marcação, ainda assim não cobra nota")
checa(len(higiene) == 1,
      "volta ao comportamento antigo, como pendência de higiene")


print("\n== fórum de dúvidas não é cobrado ==")

acoes, _ = montar(postei=False, label="S3 - Fórum de dúvidas gerais")
checa(not acoes, "ninguém é cobrado por não ter dúvida")


print("\n== disciplina de quinzena (COM170) segue outra regra ==")

acoes, _ = montar(postei=False, modelo="quinzena")
checa(not acoes,
      "a regra de participação por fórum temático é das disciplinas regulares")


print("\n== casamento de nome de fórum ==")

checa(chave_forum("S3 - Fórum temático") == chave_forum("S3 - Forum tematico "),
      "acento, caixa e espaço sobrando não separam o mesmo fórum")
checa(chave_forum("S3 - Fórum  temático") == chave_forum("S3 - Fórum temático"),
      "espaço duplicado no meio também não")
checa(chave_forum("S3 - Fórum temático") != chave_forum("S4 - Fórum temático"),
      "semanas diferentes continuam diferentes")


print("\n== cabeçalho do post: fórum, e não título do tópico ==")

# Textos copiados da página de mensagens dele em 15/08/2026, com as quebras de
# linha como o Moodle manda. Quem abre a discussão tem duas linhas; quem
# responde tem quatro, e era aí que a leitura antiga se perdia.
ABRIU = (
    "                    COM170-BIA-DRP12-2026S2-T001 ->\n"
    "                Q2 - Fórum geral\n"
)
RESPONDEU = (
    "                    COM170-BIA-DRP12-2026S2-T001 ->\n"
    "                Q2 M7 - Grupo: Ponto de encontro\n"
    "                    Informar participantes na atividade em grupo\n"
    "                        -> Re: Informar participantes na atividade em grupo\n"
)
LONGO = (
    "                    SOC100-BIA-2026S2B1-T001 ->\n"
    "                S1 - Fórum Temático - Autonomia e liberdade: até que "
    "ponto as pessoas são livres?\n"
)

checa(nome_do_forum(ABRIU) == "Q2 - Fórum geral",
      "post que abre a discussão devolve o nome do fórum")
checa(nome_do_forum(RESPONDEU) == "Q2 M7 - Grupo: Ponto de encontro",
      "resposta devolve o fórum, não o 'Re: ' do tópico")
checa(nome_do_forum(LONGO).endswith("as pessoas são livres?"),
      "nome longo com traço e dois-pontos chega inteiro")
checa(nome_do_forum("sem seta nenhuma") == "",
      "cabeçalho fora do formato não vira nome de fórum")
checa(nome_do_forum("CURSO ->\n    -> Re: Missão da Semana 3") == "",
      "cabeçalho sem o nome do fórum não devolve o 'Re: ' no lugar dele")


print("\n== paginação: parar no fim da lista, não no primeiro repetido ==")


class PaginaFalsa:
    """Devolve páginas de 5 posts, como o Moodle faz de verdade.

    A terceira página repete fóruns já vistos e a quarta traz um fórum novo.
    É o caso real do COM170 em 15/08, e era exatamente onde a leitura parava.
    """

    def __init__(self, paginas):
        self.paginas = paginas
        self.atual = 0
        self.visitadas = []

    def goto(self, url, **kwargs):
        self.atual = int(url.split("page=")[1])
        self.visitadas.append(self.atual)

    def wait_for_timeout(self, *a):
        pass

    def evaluate(self, js):
        if self.atual >= len(self.paginas):
            return []
        return [{"titulo": f"CURSO ->\n{nome}\n", "quando": "2026-08-01"}
                for nome in self.paginas[self.atual]]


PAGINAS = [
    ["S4 - Fórum temático"] * 5,
    ["S3 - Fórum temático"] * 5,
    ["S3 - Fórum temático"] * 5,          # página inteira sem nome novo
    ["S1 - Fórum de apresentação"] * 5,   # o que sumia
]

pagina = PaginaFalsa(PAGINAS)
mapa, ok, truncado = ler(pagina, "134270", "18922")
checa("s1 - forum de apresentacao" in mapa,
      "fórum da quarta página é lido, mesmo com a terceira só repetindo")
checa(ok and not truncado,
      "lista que terminou não é leitura truncada")
checa(pagina.visitadas[:5] == [0, 1, 2, 3, 4],
      "a varredura só para quando a página vem vazia")

cheia = PaginaFalsa([[f"Fórum {i}"] * 5 for i in range(MAX_PAGINAS + 2)])
_, ok_cheia, truncado_cheio = ler(cheia, "134270", "18922")
checa(ok_cheia and truncado_cheio,
      "bater no teto de páginas é leitura incompleta, e sai marcada como tal")

resultado_cheio = resultado(cheia, "134270", "18922", "2026-08-15T00:00:00")
checa(resultado_cheio.truncado and resultado_cheio.problemas,
      "e o corte chega ao site com o motivo, como manda a regra dos tetos")


print("\n" + ("FALHOU: " + str(len(falhas)) if falhas else "TUDO OK"))
# `sys.exit` no corpo do módulo derrubava a coleta do pytest inteira: quem
# rodasse `pytest testes` levava um INTERNALERROR e nenhum dos dez arquivos
# rodava. O CI chama cada teste como script, então ninguém via. Sob o pytest
# o módulo só é importado, e importar não pode terminar o processo.
if __name__ == "__main__":
    sys.exit(1 if falhas else 0)
