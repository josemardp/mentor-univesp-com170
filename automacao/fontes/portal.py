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
from dominio.datas import sem_acento
from modelos import SourceResult

PORTAL = "https://sei.univesp.br"
LOGIN_URL = f"{PORTAL}/index.xhtml"
TELA_INICIAL = f"{PORTAL}/visaoAluno/telaInicialVisaoAluno.xhtml"
NOTAS_URL = f"{PORTAL}/visaoAluno/minhasNotasAlunos.xhtml"
# A tela "Minhas Disciplinas" (``/visaoAluno/minhasDisciplinasAluno.xhtml``)
# não é lida: a tela inicial já traz a mesma lista de matrículas, e uma página
# a menos por rodada é uma chance a menos de a sessão de 44 minutos vencer no
# meio da leitura.

# O formulário de acesso do SEI tem duas entradas para a mesma senha: e-mail
# institucional, que leva ao SSO SAML da Univesp (`login.univesp.br`, o mesmo
# do AVA), e usuário/senha local, que é o RA. As duas servem, e a automação
# tenta as duas — a local primeiro, por não depender de redirecionamento.
CAMPO_USUARIO = "#form\\:usuario"
CAMPO_EMAIL = "#form\\:email"
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
# Marca que prova que a tela lida é mesmo a do calendário. Vale tanto a
# listagem com atividades quanto a que diz que não há nenhuma agora.
RE_TELA_DE_PROVAS = re.compile(
    r"CALEND[ÁA]RIO DE ATIVIDADES|Suas atividades|Nenhuma atividade",
    re.IGNORECASE,
)
# O prova.univesp.br fica atrás de uma verificação anti-robô. Do navegador
# dele, logado, ela não aparece; do servidor da Action, aparece sempre. Não se
# contorna verificação de robô aqui, nem com a conta do dono: quando esta tela
# surge, a leitura para e diz por quê, e a data da prova passa a vir do
# registro conferido à mão (docs/provas.json).
RE_ANTIBOT = re.compile(
    r"confirm you are human|security check|verifica(ç|c)(ã|a)o de seguran|"
    r"n(ã|a)o (é|e) um rob(ô|o)|captcha|cloudflare",
    re.IGNORECASE,
)
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
    """Como tentar entrar, na ordem. Cada item é ``(campo, valor)``.

    A tela tem dois campos e **um só botão "Entrar"**, então os dois caminhos
    valem com a mesma senha, e a diferença está em qual campo recebe o quê:

    - ``form:usuario`` quer o **registro acadêmico** (``90011122``). É o que o
      gerenciador de senhas dele guarda para ``sei.univesp.br``.
    - ``form:email`` quer o **endereço inteiro**
      (``90011122@aluno.univesp.br``), o mesmo do AVA.

    Preencher o e-mail no campo do usuário não é a mesma coisa que usar o
    caminho do e-mail, e era esse o erro da versão anterior. Agora cada valor
    vai no campo que o espera. O registro acadêmico vem primeiro por ser o
    caminho local, sem redirecionamento; o e-mail fica como segunda tentativa.

    O registro acadêmico é derivado do e-mail em vez de virar mais um segredo
    para manter em dia. ``PORTAL_USUARIO``, quando existe, tem prioridade.
    """
    vistos, ordem = set(), []

    def juntar(campo, valor):
        valor = (valor or "").strip()
        chave = (campo, valor)
        if valor and chave not in vistos:
            vistos.add(chave)
            ordem.append(chave)

    juntar(CAMPO_USUARIO, os.environ.get("PORTAL_USUARIO"))
    do_ava = (os.environ.get("AVA_USUARIO") or "").strip()
    if "@" in do_ava:
        juntar(CAMPO_USUARIO, do_ava.split("@", 1)[0])
        juntar(CAMPO_EMAIL, do_ava)
    else:
        juntar(CAMPO_USUARIO, do_ava)
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


def _escolher_perfil_aluno(page):
    """O SEI atende aluno, professor e coordenador na mesma porta.

    Depois de autenticar, ele pode parar numa tela de escolha de perfil em vez
    de abrir direto o painel. Quem não clica ali fica numa página que não é a
    de login nem a do aluno, que é exatamente o estado em que as rodadas de
    15/08 empacaram.

    Silencioso de propósito: se o botão não existe, é porque não havia escolha
    a fazer.
    """
    for seletor in ("#panelAlunoFirstHref", '[name="panelAlunofirstHref"]'):
        alvo = page.locator(seletor).first
        try:
            if alvo.count() and alvo.is_visible():
                alvo.click()
                page.wait_for_timeout(3000)
                page.wait_for_load_state("domcontentloaded", timeout=30000)
                return True
        except PlaywrightError:
            continue
    return False


def _onde_parou(page):
    """Caminho da página atual, sem query string.

    A query do SEI carrega token de sessão, então ela não entra em log. O
    caminho basta para distinguir "parou no login", "parou na escolha de
    perfil" e "chegou e eu não reconheci a tela".
    """
    url = page.url or ""
    return url.split("?")[0].replace(PORTAL, "") or "(sem url)"


def _passar_pelo_sso(page, senha):
    """A tela do ``login.univesp.br``, quando o caminho do e-mail cai nela.

    O campo "E-mail institucional" não é um login local: ele manda para o SSO
    SAML da Univesp, o mesmo do AVA. Duas coisas podem acontecer ali, e as
    duas são normais:

    - a sessão SAML ainda vale, e o SSO devolve para o portal já autenticado,
      sem pedir nada. É o caso comum quando o robô acabou de entrar no AVA
      pelo mesmo navegador;
    - a sessão não vale, e ele mostra o e-mail já preenchido pedindo só a
      senha.

    Devolve ``True`` quando havia uma tela de senha e ela foi preenchida.
    """
    if "login.univesp.br" not in (page.url or ""):
        return False
    campo = page.locator('input[type="password"]').first
    if not (campo.count() and campo.is_visible()):
        return False
    campo.fill(senha)  # o valor não vai pra log
    botao = page.locator(
        'button[type="submit"], input[type="submit"], #loginbtn'
    ).first
    if botao.count():
        botao.click()
    else:
        campo.press("Enter")
    page.wait_for_timeout(4000)
    page.wait_for_load_state("domcontentloaded", timeout=30000)
    return True


def _tentar_login(page, seletor, valor, senha):
    """Uma tentativa completa, pelo campo indicado. Devolve (ok, motivo)."""
    pelo_sso = seletor == CAMPO_EMAIL
    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1000)
        campo = page.locator(seletor).first
        if not campo.count():
            return False, "a tela de login do portal mudou de formato"
        campo.fill(valor)
        # No caminho do e-mail a senha não é digitada aqui: quem pergunta por
        # ela é o SSO, na tela seguinte, e às vezes nem pergunta.
        if not pelo_sso:
            page.locator(CAMPO_SENHA).first.fill(senha)
        botao = page.locator(BOTAO_ENTRAR).first
        if not botao.count():
            return False, 'não achei o botão "Entrar" na tela de login do portal'
        botao.click()
        page.wait_for_timeout(4000)
        page.wait_for_load_state("domcontentloaded", timeout=30000)
        if pelo_sso:
            _passar_pelo_sso(page, senha)
        if not _logado(page):
            _escolher_perfil_aluno(page)
        if not _logado(page):
            # Autenticado, o SEI pode devolver para a raiz em vez da tela do
            # aluno; sem este passo um login bem-sucedido parecia falha.
            page.goto(TELA_INICIAL, wait_until="domcontentloaded",
                      timeout=45000)
            page.wait_for_timeout(1500)
    except PlaywrightError as erro:
        return False, f"falhei ao entrar no portal ({type(erro).__name__})"
    if _logado(page):
        return True, "entrei no portal"
    recusa = _erro_visivel(page)
    if recusa:
        return False, recusa
    return False, (
        "o portal não abriu a tela do aluno depois do login "
        f"(parou em {_onde_parou(page)})"
    )


def _logar(page, ja_funcionou=None):
    """Entra no portal. Devolve ``(ok, motivo, identidade)``.

    ``ja_funcionou`` é o caminho que deu certo na rodada anterior. Existindo,
    é o único tentado: descobrir qual campo o portal quer é trabalho de uma
    vez só, e repetir a descoberta a cada rodada significa bater duas vezes
    por rodada, dez vezes por dia, numa conta institucional. Senha trocada
    passa a custar uma recusa por rodada, não duas.
    """
    senha = os.environ.get("AVA_SENHA")
    identidades = _identidades()
    if ja_funcionou:
        conhecida = [i for i in identidades if list(i) == list(ja_funcionou)]
        if conhecida:
            identidades = conhecida
    if not (identidades and senha):
        return False, "sem credenciais para entrar no portal", None
    motivo = ""
    for seletor, valor in identidades:
        ok, motivo = _tentar_login(page, seletor, valor, senha)
        if ok:
            return True, motivo, (seletor, valor)
        # Só vale insistir com outro caminho quando a recusa foi de credencial
        # ou quando a tela simplesmente não abriu o painel: pode ser o campo
        # errado para aquele identificador. Erro de navegação se repetiria.
        if "falhei ao entrar" in motivo or "mudou de formato" in motivo:
            break
    return False, motivo, None


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
                # Sem "Cursando" de reserva: a situação vem da tela ou não vem.
                # A tela de notas mostra "Cursando (Em Recuperação)" em três
                # disciplinas, então o padrão silencioso escondia diferença
                # real em vez de completar informação que faltava.
                "situacao": situacao,
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
                // O contador tem classe própria (.text-alerta-contador). Ela
                // vem primeiro de propósito: pegar "o primeiro .badge da
                // página" acerta hoje e passa a errar no dia em que aparecer
                // qualquer outro selo numérico antes dele.
                const proprio = document.querySelector('.text-alerta-contador');
                if (proprio) return proprio.textContent.trim();
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


# Cada linha da tabela vira uma lista de células. Ler por célula, e não pelo
# texto corrido da página, é o que permite não depender da ordem das colunas
# nem de quantas linhas separam um rótulo do seu valor.
JS_LINHAS_DE_NOTA = """
() => [...document.querySelectorAll('tbody tr')]
  .map(tr => [...tr.querySelectorAll('td')]
    .map(td => td.innerText.replace(/\\s+/g, ' ').trim()))
  .filter(celulas => celulas.length >= 4)
"""

# "ATIVIDADE AVA -- PROVA -- MÉDIA PARCIAL -- EXAME --" numa célula só. O valor
# é o que vem colado no rótulo, então o casamento é por par, não por posição:
# linha intermediária nova (um "Peso 4", por exemplo) deixa de virar nota.
RE_PARCELA = re.compile(
    r"(ATIVIDADE AVA|M[ÉE]DIA PARCIAL|PROVA|EXAME)\s*(--|[\d.,]+)",
    re.IGNORECASE,
)
RE_CODIGO_NOME = re.compile(r"^([A-Z]{3}\d{3})\s*-\s*(.+)$")
RE_FREQUENCIA = re.compile(r"^[\d.,]+\s*\(%\)$")
SITUACOES = ("cursando", "aprovado", "reprovado", "trancad", "cancelad")


def ler_notas(page):
    """Boletim oficial da secretaria, que não é o boletim do Moodle.

    Aqui aparecem as quatro parcelas que formam a média do bimestre (atividade
    no AVA, prova, média parcial e exame), a frequência e a situação da
    matrícula. É a única fonte que enxerga a nota da prova presencial.

    Duas armadilhas, as duas confirmadas na tela em 15/08:

    1. **A tabela não existe quando se chega pela URL.** A página carrega só o
       cabeçalho e o seletor de ano/semestre, já preenchido, e a lista só é
       montada quando esse seletor dispara um ``change``. Navegar e ler devolvia
       lista vazia, que é indistinguível de "não tem nota".
    2. **A linha não começa pelo código da disciplina**, começa pela turma
       (``Valparaiso-BIA-BIA-1-1P-NOT``). Casar o código no início da linha
       nunca deu certo, e como o resultado era lista vazia, o defeito ficou
       invisível.

    Devolve ``None`` quando a tabela não pôde ser lida. Lista vazia aqui seria
    uma afirmação, e a afirmação estaria errada.
    """
    page.goto(NOTAS_URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(1200)
    linhas = page.evaluate(JS_LINHAS_DE_NOTA)
    if not any(_codigo_da_linha(celulas) for celulas in linhas):
        # Cutuca o seletor e espera a tabela nascer.
        try:
            page.evaluate(
                """() => {
                    const sel = document.querySelector('select');
                    if (sel) sel.dispatchEvent(new Event('change', {bubbles:true}));
                }"""
            )
            page.wait_for_timeout(3000)
        except PlaywrightError:
            return None
        linhas = page.evaluate(JS_LINHAS_DE_NOTA)

    notas = []
    for celulas in linhas:
        achado = _codigo_da_linha(celulas)
        if not achado:
            continue
        codigo, nome = achado
        parcelas, frequencia, situacao = {}, "", ""
        for celula in celulas:
            for rotulo, valor in RE_PARCELA.findall(celula):
                rotulo = sem_acento(rotulo).upper().replace("MEDIA", "MÉDIA")
                parcelas[rotulo] = "" if valor == "--" else valor
            if RE_FREQUENCIA.match(celula):
                frequencia = celula
            elif any(s in sem_acento(celula) for s in SITUACOES):
                situacao = celula
        notas.append(
            {
                "codigo": codigo,
                "nome": nome.strip(),
                "frequencia": frequencia,
                "parcelas": parcelas,
                "situacao": situacao,
            }
        )
    return notas or None


def _codigo_da_linha(celulas):
    """``(codigo, nome)`` da célula que tiver a disciplina, em qualquer coluna."""
    for celula in celulas:
        casou = RE_CODIGO_NOME.match(celula)
        if casou:
            return casou.group(1), casou.group(2)
    return None


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
    # A aba nasce em ``/MestreGRSV``, que é só a página "estamos
    # redirecionando" com um formulário que se posta sozinho. Ler o corpo aqui
    # devolve esse texto de espera, e foi o que aconteceu na rodada de 15/08
    # às 13:49: o login funcionou, a aba abriu e o guia leu zero prova.
    try:
        aba.wait_for_load_state("domcontentloaded", timeout=30000)
        aba.wait_for_url("**prova.univesp.br/**", timeout=30000)
        aba.wait_for_selector(
            "text=/CALEND[ÁA]RIO DE ATIVIDADES|ATIVIDADES DISPON/i",
            timeout=25000,
        )
        aba.wait_for_timeout(1500)
    except PlaywrightError:
        # Segue mesmo assim: quem decide se a leitura serve é a conferência do
        # texto, logo abaixo, e ela sabe dizer "não reconheci esta tela".
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
    onde = ""
    try:
        texto = aba.locator("body").inner_text()
        onde = (aba.url or "").split("?")[0]
    except PlaywrightError:
        texto = ""
    finally:
        try:
            aba.close()
        except PlaywrightError:
            pass
    if not texto:
        return None, "o Sistema de Provas abriu em branco"

    # Zero atividade só pode ser afirmado numa tela que a gente reconheceu
    # como o calendário. Sem esta conferência, a página de redirecionamento
    # (ou qualquer tela nova) viraria "você não tem prova marcada", que é a
    # frase mais perigosa que este guia pode dizer.
    if RE_ANTIBOT.search(texto):
        # Estado esperado, não defeito: o robô não tem como passar por aqui, e
        # não é para ter. Quem confere é o Josemar, e o que ele conferir fica
        # em docs/provas.json.
        return None, (
            "o Sistema de Provas pediu verificação de robô, então a data da "
            "prova vem do que foi conferido à mão"
        )
    if not RE_TELA_DE_PROVAS.search(texto):
        # O começo do texto e a URL sem query dizem, na próxima rodada, se ele
        # ficou na página de espera, se caiu numa tela de erro ou se o
        # calendário mudou de cara. Sem isso o diagnóstico é adivinhação, e
        # cada tentativa custa uma rodada inteira.
        return None, (
            "abri o Sistema de Provas mas não reconheci a tela do calendário "
            f"(parou em {onde or 'url desconhecida'}; a tela começa com "
            f"\"{' '.join(texto.split())[:120]}\")"
        )

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
        ok, motivo, identidade = _logar(page, (cache or {}).get("_login_ok"))
        if not ok:
            return degradado([motivo])
        dados, problemas = {}, []
        try:
            dados.update(ler_tela_inicial(page))
        except PlaywrightError:
            problemas.append("não consegui ler a tela inicial do portal")
        try:
            notas = ler_notas(page)
            if notas is None:
                problemas.append(
                    "abri o boletim da secretaria mas não consegui ler a tabela"
                )
            else:
                dados["notas"] = notas
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

        # Sessão que cai no meio da leitura devolve as chaves vazias, e
        # ``if not dados`` nunca dispara: o resultado sairia "live" com zero
        # disciplinas, que é uma afirmação falsa sobre a matrícula dele. A
        # prova de que houve leitura é a lista de disciplinas, não o dicionário.
        if not dados.get("disciplinas"):
            return degradado(
                problemas
                + ["li o portal sem encontrar disciplina nenhuma; trato como "
                   "leitura falhada, não como matrícula vazia"]
            )
        # Leitura parcial mantém o que veio e diz o que faltou. O guia já sabe
        # tratar fonte parcial; o que ele não pode é publicar meia leitura como
        # se fosse inteira.
        dados["checked_at"] = checked_at
        # Guardar qual caminho de login funcionou vale por segurança, não por
        # velocidade: sem isso, senha trocada gera duas recusas por rodada e
        # dez por dia numa conta institucional, que é como se bloqueia acesso
        # sem querer.
        dados["_login_ok"] = identidade
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
