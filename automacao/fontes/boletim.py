# -*- coding: utf-8 -*-
"""Boletim da disciplina: nota, devolutiva e prova de que a entrega existiu.

Motivo de existir, achado em 04/08/2026: o selo "Concluído" do Moodle não
prova entrega. A S2 - Atividade Avaliativa do COM100 estava marcada como
concluída, sem nenhuma tentativa e sem nota, com prazo em 09/08 — a conclusão
daquele item é por visualização. O guia confiava no selo e não cobrava.

O boletim é a fonte que resolve isso: cada linha aponta para o ``cmid`` da
atividade e traz a nota lançada e o retorno escrito do facilitador. Nota
lançada, inclusive zero, é prova de que a atividade foi entregue.

Limites conhecidos, tratados como "não sei" e nunca como "não entregou":
o relatório de uma disciplina pode vir sem nenhuma linha (é o caso do SOC100),
e a média pode vir com "Erro" de cálculo (é o caso da COM170).
"""
import re

from playwright.sync_api import Error as PlaywrightError

from configuracao import AVA
from dominio.datas import sem_acento
from modelos import SourceResult

JS_BOLETIM = """
() => {
  const linhas = [...document.querySelectorAll('tr')];
  const saida = [];
  for (const tr of linhas) {
    const nome = tr.querySelector('.column-itemname, .itemname');
    const nota = tr.querySelector('.column-grade, .grade');
    if (!nome || !nota) continue;
    const link = tr.querySelector('a[href*="/mod/"]');
    const retorno = tr.querySelector('.column-feedback, .feedbacktext');
    saida.push({
      rotulo: (nome.innerText || '').replace(/\\s+/g, ' ').trim(),
      nota: (nota.innerText || '').replace(/\\s+/g, ' ').trim(),
      feedback: retorno ? (retorno.innerText || '').replace(/\\s+/g, ' ').trim() : '',
      url: link ? link.href : null,
    });
  }
  return saida;
}
"""

# O menu de contexto da célula entra no innerText como "Ações"/"Editar".
LIXO_NA_NOTA = re.compile(r"\b(a[cç][oõ]es|editar|actions)\b", re.IGNORECASE)
CMID_RE = re.compile(r"[?&]id=(\d+)")
# Rótulo vem com o tipo na frente: "QUESTIONÁRIO S2 - Atividade Avaliativa".
TIPO_NO_ROTULO = re.compile(
    r"^(question[aá]rio|tarefa|pacote scorm|laborat[oó]rio de avalia[cç][aã]o|"
    r"pesquisa|f[oó]rum|nota calculada|forma de agrega[cç][aã]o das notas)\s+",
    re.IGNORECASE,
)


def _limpar_nota(bruto):
    """Tira o menu da célula sem tirar o traço, que é como o AVA diz 'sem nota'."""
    return LIXO_NA_NOTA.sub("", bruto or "").strip(" \t· ")


def _numero(texto):
    if not texto:
        return None
    achado = re.fullmatch(r"-?\d+(?:[.,]\d+)?", texto.strip())
    if not achado:
        return None
    try:
        return float(texto.strip().replace(",", "."))
    except ValueError:
        return None


def _rotulo_limpo(bruto):
    return TIPO_NO_ROTULO.sub("", (bruto or "").strip()).strip()


def ler(page, curso_id):
    """Devolve ``(por_cmid, resumo)`` ou levanta ``PlaywrightError``.

    A tabela de notas monta depois do carregamento da página. Esperar por
    tempo fixo faz a leitura oscilar entre "tem nota" e "não tem", e nota que
    aparece e some é pior que nota nenhuma. Espera-se pela primeira linha com
    link de atividade; o estouro dessa espera é informação legítima, porque
    existe disciplina com o relatório realmente vazio (SOC100 em 04/08/2026).
    """
    page.goto(
        f"{AVA}/grade/report/user/index.php?id={curso_id}",
        wait_until="domcontentloaded",
        timeout=45000,
    )
    try:
        page.wait_for_selector('tr a[href*="/mod/"]', timeout=10000)
    except PlaywrightError:
        page.wait_for_timeout(500)
    linhas = page.evaluate(JS_BOLETIM)
    por_cmid, media, itens = {}, None, 0
    for linha in linhas:
        rotulo = _rotulo_limpo(linha.get("rotulo"))
        nota_txt = _limpar_nota(linha.get("nota"))
        if sem_acento(rotulo).startswith("item de nota"):
            continue  # cabeçalho
        if not linha.get("url"):
            # Linha calculada (Média AVA, Total do curso): não é atividade.
            if "media" in sem_acento(rotulo) or "total" in sem_acento(rotulo):
                media = media or {"rotulo": rotulo, "nota": nota_txt}
            continue
        achado = CMID_RE.search(linha["url"])
        if not achado:
            continue
        cmid = achado.group(1)
        valor = _numero(nota_txt)
        registro = {
            "rotulo": rotulo,
            "nota_txt": nota_txt,
            "nota": valor,
            # Nota lançada, inclusive 0,00, é prova de que houve entrega.
            "tem_nota": valor is not None,
            "feedback": (linha.get("feedback") or "").strip() or None,
            "url": linha["url"],
        }
        # Laboratório de Avaliação aparece em duas linhas (envio e avaliação),
        # com o mesmo cmid. Vale a que tiver nota.
        anterior = por_cmid.get(cmid)
        if anterior and anterior["tem_nota"] and not registro["tem_nota"]:
            continue
        por_cmid[cmid] = registro
        itens += 1
    # `linhas` inclui o cabeçalho quando a tabela existe. Zero linhas significa
    # que nem a tabela apareceu, e isso é falha de leitura, não boletim vazio.
    return por_cmid, {
        "media": media,
        "itens": itens,
        "linhas_brutas": len(linhas),
    }


def resultado(page, curso_id, checked_at, cache=None):
    try:
        por_cmid, resumo = ler(page, curso_id)
    except PlaywrightError as erro:
        return SourceResult(
            status="falhou",
            dados=cache,
            problemas=[
                f"boletim de {curso_id} não abriu ({type(erro).__name__})"
            ],
            checked_at=checked_at,
            from_cache=cache is not None,
            quantidade_atual=len(cache or {}),
        )
    if not resumo.get("linhas_brutas"):
        return SourceResult(
            status="falhou",
            dados=cache,
            problemas=[f"boletim de {curso_id} não renderizou a tabela"],
            checked_at=checked_at,
            from_cache=cache is not None,
            quantidade_atual=len(cache or {}),
            detalhes=resumo,
        )
    if not por_cmid:
        # Disciplina sem nenhuma linha de atividade no relatório do usuário.
        # Acontece de verdade (SOC100 em 04/08/2026) e não pode ser lido como
        # "nada foi entregue": é ausência de informação, não de entrega.
        return SourceResult(
            status="vazio_confirmado",
            dados={},
            problemas=[f"boletim de {curso_id} veio sem linhas de atividade"],
            checked_at=checked_at,
            last_live_at=checked_at,
            quantidade_atual=0,
            detalhes=resumo,
        )
    return SourceResult(
        status="live",
        dados=por_cmid,
        checked_at=checked_at,
        last_live_at=checked_at,
        quantidade_atual=len(por_cmid),
        detalhes=resumo,
    )
