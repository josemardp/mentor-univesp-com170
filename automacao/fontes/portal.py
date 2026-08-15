# -*- coding: utf-8 -*-
"""Portal do aluno (SEI), que é outro sistema, com outro login.

Por que existe: até 15/08/2026 o guia só olhava o AVA, e o AVA não sabe de
tudo. Três coisas grandes moravam só aqui:

1. **A data da prova presencial.** O STATUS registrou por semanas que ela não
   tinha fonte alcançável. Tinha: o Sistema de Provas publica o dia e a hora
   de cada prova *daquele aluno*, e não é o mesmo dia para todo mundo, nem o
   mesmo do calendário geral.
2. **As disciplinas em que ele está matriculado.** O portal listava seis; o
   AVA, quatro. Disciplina que ainda não abriu turma no Moodle não existe para
   o guia, e mesmo assim conta carga horária e pode cair em prova.
3. **Recados da secretaria**, que trazem prazo próprio (matrícula em
   disciplina optativa, requerimento, ciclo de provas) e não passam por fórum
   nenhum.

Duas regras valem para esta fonte inteira:

**Ela nunca escreve.** Nem marca recado como lido, nem envia formulário. Em
15/08 medimos: abrir ``recadoAluno.xhtml`` marca sozinho o recado mais recente
como lido, e o contador caiu de 9 para 7. Por isso o robô não entra ali. O que
ele lê é o contador de não lidos na tela inicial, que é informação suficiente
para dizer "tem recado esperando" sem consumir o aviso no lugar dele.

**Ela nunca derruba o robô.** O portal é um JSF com sessão curta (44 minutos) e
login próprio. Se qualquer etapa falhar, a fonte devolve ``falhou`` e o guia
segue com o que o AVA deu, do mesmo jeito que já faz com boletim e
participação.

O caminho até o Sistema de Provas não é uma URL que se possa chamar direto:
o botão da tela inicial dispara um ``RichFaces.ajax`` que prepara um token na
sessão, e só depois ``/MestreGRSV`` devolve um formulário que se posta sozinho
para ``prova.univesp.br/ws/sso/``. Chamar ``/MestreGRSV`` sem o clique devolve
404. Por isso a leitura clica no botão e acompanha a aba que nasce.
"""
import os
import re
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError

from configuracao import BR_TZ
from modelos import SourceResult

PORTAL = "https://sei.univesp.br"
LOGIN_URL = f"{PORTAL}/index.xhtml"
TELA_INICIAL = f"{PORTAL}/visaoAluno/telaInicialVisaoAluno.xhtml"
NOTAS_URL = f"{PORTAL}/visaoAluno/minhasNotasAlunos.xhtml"
DISCIPLINAS_URL = f"{PORTAL}/visaoAluno/minhasDisciplinasAluno.xhtml"

# O formulário de acesso do SEI tem duas entradas: e-mail institucional (que
# leva ao SSO da Microsoft) e usuário/senha local. A segunda é a que aceita as
# mesmas credenciais do AVA, e é a única que dá para automatizar sem MFA.
CAMPO_USUARIO = "#form\\:usuario"
CAMPO_SENHA = "#form\\:senha"
# "Entrar" é um <a> que chama RichFaces.ajax, não um submit. Apertar Enter no
# campo da senha não envia nada, e foi assim que a primeira rodada na nuvem
# falhou: as credenciais estavam certas e o formulário nunca saiu.
BOTAO_ENTRAR = "#form\\:loginBtn\\:loginBtn"

ERROS_LOGIN = (
    "usuario ou senha",
    "usuário ou senha",
    "senha inválida",
    "senha invalida",
    "não cadastrado",
    "nao cadastrado",
    "inválidos",
    "invalidos",
)

RE_RA = re.compile(r"Registro Acad[êe]mico:\s*(\d+)")
RE_DISCIPLINA = re.compile(
    r"^([A-Z]{3}\d{3}|[A-Z]{3}\d{3}[A-Z]?|MMB\d{3})\s*-\s*(.+)$"
)
# "2026 - COM100 - PENSAMENTO COMPUTACIONAL - 3 BIMESTRE"
RE_TITULO_PROVA = re.compile(r"^(\d{4})\s*-\s*([A-Z]{3}\d{3})\s*-\s*(.+)$")
RE_ATIVIDADE = re.compile(
    r"(Presencial|Online)\s*\n\s*(.+?)\s*\n\s*"
    r"De:\s*(\d{2}/\d{2})\s+(\d{2}:\d{2})\s*\n\s*"
    r"At[ée]\s*(\d{2}/\d{2})\s+(\d{2}:\d{2})",
    re.IGNORECASE,
)


def _tem_credenciais():
    return bool(
        (os.environ.get("AVA_USUARIO") or os.environ.get("PORTAL_USUARIO"))
        and os.environ.get("AVA_SENHA")
    )


def _logado(page):
    try:
        return bool(RE_RA.search(page.locator("body").inner_text()[:3000]))
    except PlaywrightError:
        return False


def _identidades():
    """Quem tentar como usuário, na ordem.

    O AVA e o portal aceitam identificadores diferentes: o AVA loga com o que
    estiver em ``AVA_USUARIO`` e o campo "Usuário" do portal costuma querer o
    registro acadêmico. ``PORTAL_USUARIO`` existe para esse caso e é opcional;
    sem ele, tenta o mesmo do AVA, que é o cenário mais provável.
    """
    vistos, ordem = set(), []
    for chave in ("PORTAL_USUARIO", "AVA_USUARIO"):
        valor = (os.environ.get(chave) or "").strip()
        if valor and valor not in vistos:
            vistos.add(valor)
            ordem.append(valor)
    return ordem


def _erro_visivel(page):
    """A recusa que a tela mostra, para o log dizer o que houve.

    Sem isto, "não abriu a tela do aluno" cobre dois casos muito diferentes:
    credencial recusada e formulário que nem chegou a ser enviado. O texto sai
    truncado e nunca inclui o que foi digitado.
    """
    try:
        corpo = page.locator("body").inner_text()[:1500].lower()
    except PlaywrightError:
        return ""
    for marca in ERROS_LOGIN:
        if marca in corpo:
            return "o portal recusou usuário ou senha"
    return ""


def _tentar_login(page, usuario, senha):
    """Uma tentativa completa. Devolve (ok, motivo)."""
    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1000)
        campo = page.locator(CAMPO_USUARIO).first
        if not campo.count():
            return False, "a tela de login do portal mudou de formato"
        campo.fill(usuario)
        page.locator(CAMPO_SENHA).first.fill(senha)  # o valor não vai pra log
        botao = page.locator(BOTAO_ENTRAR).first
        if not botao.count():
            return False, 'não achei o botão "Entrar" na tela de login do portal'
        botao.click()
        page.wait_for_timeout(4000)
        page.wait_for_load_state("domcontentloaded", timeout=30000)
    except PlaywrightError as erro:
        return False, f"falhei ao entrar no portal ({type(erro).__name__})"
    if _logado(page):
        return True, "entrei no portal"
    return False, (
        _erro_visivel(page)
        or "o portal não abriu a tela do aluno depois do login"
    )


def _logar(page):
    """Entra no portal. Devolve (ok, motivo)."""
    senha = os.environ.get("AVA_SENHA")
    identidades = _identidades()
    if not (identidades and senha):
        return False, "sem credenciais para entrar no portal"
    motivo = ""
    for usuario in identidades:
        ok, motivo = _tentar_login(page, usuario, senha)
        if ok:
            return True, motivo
        # Só vale insistir com outra identidade quando a recusa foi de
        # credencial. Tela mudada ou erro de navegação se repetiria igual.
        if "recusou" not in motivo:
            break
    return False, motivo


def _texto(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(1200)
    return page.locator("body").inner_text()


def ler_tela_inicial(page):
    """Disciplinas matriculadas e quantos recados esperam por ele.

    O contador é lido aqui de propósito: ele responde "tem recado novo?" sem
    abrir a caixa, que marcaria como lido.
    """
    texto = _texto(page, TELA_INICIAL)
    linhas = [l.strip() for l in texto.split("\n")]
    disciplinas, vistas = [], set()
    for i, linha in enumerate(linhas):
        casou = RE_DISCIPLINA.match(linha)
        if not casou:
            continue
        codigo = casou.group(1)
        if codigo in vistas:
            continue
        situacao = ""
        for adiante in linhas[i + 1: i + 4]:
            if adiante.startswith("Cursando") or "Situação" in adiante:
                situacao = adiante.replace("Situação:", "").strip()
                break
        vistas.add(codigo)
        disciplinas.append(
            {
                "codigo": codigo,
                "nome": casou.group(2).strip(),
                "situacao": situacao or "Cursando",
            }
        )
    return {
        "ra": (RE_RA.search(texto).group(1) if RE_RA.search(texto) else None),
        "disciplinas": disciplinas,
        "recados_nao_lidos": _contador_de_recados(page),
    }


def _contador_de_recados(page):
    """Número no ícone de envelope. ``None`` quando não deu para ler.

    Zero e "não consegui ler" levam a frases diferentes, então não podem sair
    com o mesmo valor.
    """
    try:
        bruto = page.evaluate(
            """() => {
                const alvo = document.querySelector(
                    '.badge, .rf-ind-stg, [class*=notifica] span, .fa-envelope + span'
                );
                if (alvo) return alvo.textContent.trim();
                const envelope = [...document.querySelectorAll('a,span,div')]
                    .find(e => /envelope|recado|mensagem/i.test(e.className || ''));
                return envelope ? envelope.textContent.trim() : null;
            }"""
        )
    except PlaywrightError:
        return None
    if not bruto:
        return None
    numero = re.search(r"\d+", bruto)
    return int(numero.group()) if numero else None


def ler_notas(page):
    """Boletim oficial da secretaria, que não é o boletim do Moodle.

    Aqui aparecem as quatro parcelas que formam a média do bimestre
    (atividade no AVA, prova, média parcial e exame) e a situação da
    matrícula. É a única fonte que enxerga a nota da prova presencial.
    """
    texto = _texto(page, NOTAS_URL)
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]
    notas, atual = [], None
    for linha in linhas:
        casou = RE_DISCIPLINA.match(linha)
        if casou:
            atual = {
                "codigo": casou.group(1),
                "nome": casou.group(2).strip(),
                "parcelas": {},
                "situacao": "",
            }
            notas.append(atual)
            continue
        if not atual:
            continue
        if linha.upper() in ("ATIVIDADE AVA", "PROVA", "MÉDIA PARCIAL", "EXAME"):
            atual["_ultima"] = linha.upper()
            continue
        rotulo = atual.pop("_ultima", None)
        if rotulo:
            atual["parcelas"][rotulo] = "" if linha == "--" else linha
        elif linha.startswith("Cursando") or linha.startswith("Aprovado") \
                or linha.startswith("Reprovado"):
            atual["situacao"] = linha
    for nota in notas:
        nota.pop("_ultima", None)
    return notas


def _abrir_sistema_de_provas(page):
    """Segue o caminho do botão até ``prova.univesp.br``.

    Não dá para pular etapa: o clique prepara o token na sessão do SEI, e sem
    ele ``/MestreGRSV`` responde 404. A página nasce numa aba nova.
    """
    contexto = page.context
    page.goto(TELA_INICIAL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(1000)
    link = page.get_by_text("Sistema de Provas", exact=True).first
    if not link.count():
        return None, "não achei o link do Sistema de Provas na tela inicial"
    try:
        with contexto.expect_page(timeout=30000) as nova:
            link.click()
        aba = nova.value
    except PlaywrightError:
        return None, "o Sistema de Provas não abriu"
    try:
        aba.wait_for_load_state("domcontentloaded", timeout=30000)
        aba.wait_for_timeout(3000)
    except PlaywrightError:
        pass
    return aba, ""


def ler_provas(page):
    """As provas *dele*, com dia e hora, do Calendário de Atividades.

    O recado da secretaria dá a janela do ciclo ("de 14 a 25 de setembro") e o
    calendário geral publica todos os dias possíveis de cada disciplina.
    Nenhum dos dois responde a pergunta que importa, que é em qual desses dias
    ele tem prova. Só este calendário responde, e ele responde por aluno.
    """
    aba, problema = _abrir_sistema_de_provas(page)
    if not aba:
        return None, problema
    try:
        texto = aba.locator("body").inner_text()
    except PlaywrightError:
        texto = ""
    finally:
        try:
            aba.close()
        except PlaywrightError:
            pass
    if not texto:
        return None, "o Sistema de Provas abriu em branco"

    ano_corrente = datetime.now(BR_TZ).year
    provas = []
    for casou in RE_ATIVIDADE.finditer(texto):
        modalidade, titulo, dia_ini, hora_ini, dia_fim, hora_fim = casou.groups()
        titulo = titulo.strip()
        cabecalho = RE_TITULO_PROVA.match(titulo)
        ano = int(cabecalho.group(1)) if cabecalho else ano_corrente
        codigo = cabecalho.group(2) if cabecalho else ""
        provas.append(
            {
                "codigo": codigo,
                "titulo": titulo,
                "modalidade": modalidade.capitalize(),
                "inicio": _iso(dia_ini, hora_ini, ano),
                "fim": _iso(dia_fim, hora_fim, ano),
            }
        )
    return provas, ""


def _iso(dia_mes, hora, ano):
    """``05/11`` + ``19:40`` + ano viram data com fuso de Brasília.

    A tela não escreve o ano na linha da atividade; ele vem do título. Data
    que não fecha devolve ``None``, e prazo nenhum é melhor que prazo chutado.
    """
    try:
        dia, mes = dia_mes.split("/")
        return datetime(
            ano, int(mes), int(dia),
            int(hora[:2]), int(hora[3:5]), tzinfo=BR_TZ,
        ).isoformat()
    except (ValueError, IndexError):
        return None


def resultado(contexto, checked_at, cache=None):
    """Lê o portal numa aba própria, sem tocar na sessão do AVA."""
    if not _tem_credenciais():
        return SourceResult(
            status="nao_aplicavel",
            dados=cache or {},
            problemas=["sem credenciais para o portal do aluno"],
            checked_at=checked_at,
            from_cache=bool(cache),
        )

    def degradado(problemas):
        return SourceResult(
            status="falhou",
            dados=dict(cache or {}),
            problemas=problemas,
            checked_at=checked_at,
            from_cache=bool(cache),
            quantidade_atual=len(cache or {}),
        )

    page = contexto.new_page()
    try:
        ok, motivo = _logar(page)
        if not ok:
            return degradado([motivo])
        dados, problemas = {}, []
        try:
            dados.update(ler_tela_inicial(page))
        except PlaywrightError:
            problemas.append("não consegui ler a tela inicial do portal")
        try:
            dados["notas"] = ler_notas(page)
        except PlaywrightError:
            problemas.append("não consegui ler as notas no portal")
        try:
            provas, problema = ler_provas(page)
            if provas is None:
                problemas.append(problema or "não consegui ler o calendário de provas")
            else:
                dados["provas"] = provas
        except PlaywrightError:
            problemas.append("não consegui abrir o Sistema de Provas")

        if not dados:
            return degradado(problemas or ["o portal não devolveu nada"])
        # Leitura parcial mantém o que veio e diz o que faltou. O guia já sabe
        # tratar fonte parcial; o que ele não pode é publicar meia leitura como
        # se fosse inteira.
        dados["checked_at"] = checked_at
        return SourceResult(
            status="parcial" if problemas else "live",
            dados=dados,
            problemas=problemas,
            checked_at=checked_at,
            quantidade_atual=len(dados.get("provas") or []),
            last_live_at=checked_at,
            detalhes={
                "disciplinas": len(dados.get("disciplinas") or []),
                "provas": len(dados.get("provas") or []),
                "recados_nao_lidos": dados.get("recados_nao_lidos"),
            },
        )
    finally:
        try:
            page.close()
        except PlaywrightError:
            pass
