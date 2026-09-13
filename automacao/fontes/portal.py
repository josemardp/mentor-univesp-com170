# -*- coding: utf-8 -*-
"""Portal do aluno (SEI), que é outro sistema, com outro login.

Por que existe: até 15/08/2026 o guia só olhava o AVA, e o AVA não sabe de
tudo. Três coisas grandes moram só aqui:

1. **A data da prova presencial.** O Sistema de Provas publica o dia e a hora
   de cada prova *daquele aluno*, e não é o mesmo dia para todo mundo, nem o
   mesmo do calendário geral.
2. **As disciplinas em que ele está matriculado.** O portal lista mais que o
   AVA. Disciplina que ainda não abriu turma no Moodle não existe para o
   guia, e mesmo assim conta carga horária e pode cair em prova.
3. **Recados da secretaria**, que trazem prazo próprio (matrícula em
   disciplina optativa, requerimento, ciclo de provas) e não passam por fórum
   nenhum.

Duas regras valem para esta fonte inteira:

**Ela nunca escreve.** Nem marca recado como lido, nem envia formulário. O
que ela lê é o contador de não lidos que já vem pronto na tela inicial
(``.badge-notification`` do ícone de mensagens), que é informação suficiente
para dizer "tem recado esperando" sem consumir o aviso no lugar dele. Por
isso o robô nunca abre ``recadoAluno.xhtml``.

**Ela nunca derruba o robô.** O portal é um JSF com sessão curta (44 minutos,
a própria tela avisa) e login próprio. Se qualquer etapa falhar, a fonte
devolve ``falhou`` e o guia segue com o que o AVA deu, do mesmo jeito que já
faz com boletim e participação.

## A troca de 25/08/2026

A Univesp avisou por e-mail em 20/08 ("No dia 25 de agosto, entra no ar o seu
Novo Portal do Aluno totalmente reformulado") e a fonte antiga morreu no dia
certo: a tela de login mudou de formato. Remapeado ao vivo em 29/08/2026,
navegador logado, sem contornar nada.

O que mudou de fato:

- **Domínio novo.** O portal virou ``sa.univesp.br`` (era ``sei.univesp.br``,
  que hoje só redireciona para o portal de acesso unificado). Por baixo é o
  mesmo sistema — mesmo produto "SEI" da Otimize-TI, mesmos caminhos JSF
  (``/visaoAluno/telaInicialVisaoAluno.xhtml``,
  ``/visaoAluno/minhasNotasAlunos.xhtml`` são literalmente as mesmas URLs, só
  com domínio trocado), mesma sessão de 44 minutos.
- **Login virou um portão único.** Existe agora ``acesso.univesp.br``, que
  reúne AVA, Portal do Aluno, Sistema de Provas, Office 365 e Google atrás de
  um só campo de usuário. Ele decide sozinho se a sessão SAML
  (``login.univesp.br``, a mesma do AVA) já vale: se valer, mostra o menu na
  hora, sem pedir senha de novo; se não valer, redireciona pra
  ``login.univesp.br/simplesaml/...`` e pede a senha lá — é o mesmo SSO que
  ``sessao.py`` sempre usou, só o caminho até ele que mudou. Confirmado ao
  vivo nos dois cenários (sessão quente e fria).
- **Consequência boa para o robô:** como o `pipeline` sempre loga no AVA
  *antes* de chamar esta fonte, no mesmo `contexto` (mesmos cookies), a
  sessão SAML já está quente quando `portal.resultado` roda. Por isso o login
  daqui tenta primeiro ir direto na tela do aluno; só passa pelo portão
  unificado quando isso falha (sessão realmente fria, ou primeira vez).
- **Duas armadilhas de leitura que a UI nova introduziu**, as duas
  confirmadas na tela: o rótulo "RA:" trocou de "Registro Acadêmico:"; e a
  tabela de notas passou a mostrar "CH: Nh" colado no nome da disciplina na
  mesma célula, e "(Em Recuperação)" sozinho na coluna de situação (antes
  vinha "Cursando (Em Recuperação)" junto).

O caminho até o Sistema de Provas continua não sendo uma URL que se chame
direto: o atalho da tela inicial dispara um ``PrimeFaces.ab`` (era
``RichFaces.ajax`` no sistema velho) que prepara um token na sessão, e só
depois ``prova.univesp.br`` abre numa aba nova. A leitura clica no atalho e
acompanha a aba que nasce, como sempre.
"""
import os
import re
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError

from configuracao import BR_TZ
from dominio.datas import sem_acento
from modelos import SourceResult

# Portão único de login, na frente de AVA/Portal/Provas/Office/Google.
ACESSO_URL = "https://acesso.univesp.br/"
# Domínio dos dados do aluno em si (era sei.univesp.br até 25/08/2026).
PORTAL = "https://sa.univesp.br"
TELA_INICIAL = f"{PORTAL}/visaoAluno/telaInicialVisaoAluno.xhtml"
NOTAS_URL = f"{PORTAL}/visaoAluno/minhasNotasAlunos.xhtml"

# Campo único da tela unificada. Só aceita o e-mail institucional completo
# (confirmado ao vivo: o RA sozinho não foi testado e o e-mail é o que
# AVA_USUARIO já traz, então não há motivo pra manter dois caminhos como a
# versão anterior fazia).
CAMPO_USUARIO = "#inputEmailAccess"

ERROS_LOGIN = (
    "usuario ou senha",
    "usuário ou senha",
    "senha inválida",
    "senha invalida",
    "não cadastrado",
    "nao cadastrado",
    "inválidos",
    "invalidos",
    "invalid login",
)

# Trocou de "Registro Acadêmico: 90011122" pra "RA: 90011122" na tela nova.
RE_RA = re.compile(r"\bRA:\s*(\d+)")
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


def _identidade():
    """O valor único que o campo de usuário do portão unificado espera.

    Precisa vir com o domínio (``ra@aluno.univesp.br``): foi o formato
    confirmado ao vivo, é o mesmo que o SSO do AVA usa, e ``AVA_USUARIO`` já
    chega assim. ``PORTAL_USUARIO``, quando existe, tem prioridade — mesma
    regra da versão anterior — e ganha o domínio se vier só o RA.
    """
    valor = (os.environ.get("PORTAL_USUARIO") or os.environ.get("AVA_USUARIO") or "").strip()
    if valor and "@" not in valor:
        valor = f"{valor}@aluno.univesp.br"
    return valor


def _logado(page):
    try:
        return bool(RE_RA.search(page.locator("body").inner_text()[:3000]))
    except PlaywrightError:
        return False


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


def _onde_parou(page):
    """Caminho da página atual, sem query string.

    A query pode carregar token de sessão, então ela não entra em log. O
    caminho basta para distinguir "parou no login", "parou no SSO" e "chegou
    e eu não reconheci a tela".
    """
    url = page.url or ""
    return url.split("?")[0].replace(PORTAL, "") or "(sem url)"


def _logar(page):
    """Entra no portal. Devolve ``(ok, motivo)``.

    Dois caminhos, nesta ordem:

    1. **Direto na tela do aluno.** Quando o pipeline já logou no AVA nesta
       mesma aba/contexto — o caso normal de toda rodada —, a sessão SAML já
       está quente e a tela do aluno abre sem pedir nada. Testar isto primeiro
       evita bater no portão unificado (e, por tabela, no SSO institucional)
       a cada rodada, dez vezes por dia, à toa.
    2. **Portão unificado (`acesso.univesp.br`).** Só quando o caminho 1
       falha. Preenche o e-mail e clica "Acessar"; a página decide sozinha se
       a sessão SAML basta (aí volta com um HUB de atalhos, sem pedir senha)
       ou se precisa dela (aí redireciona pra `login.univesp.br`, onde a
       senha é preenchida). Os dois casos foram confirmados ao vivo — e no
       caso sem senha o HUB **não é** o portal: é preciso clicar no atalho
       "PORTAL DO ALUNO" ali dentro pra sessão valer em `sa.univesp.br`
       (achado de 29/08/2026, reproduzindo um login frio local).
    """
    try:
        page.goto(TELA_INICIAL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1000)
    except PlaywrightError as erro:
        return False, f"não consegui abrir o portal ({type(erro).__name__})"
    if _logado(page):
        return True, "sessão do AVA já valia para o portal"

    email = _identidade()
    senha = os.environ.get("AVA_SENHA")
    if not (email and senha):
        return False, "sem credenciais para entrar no portal"

    try:
        page.goto(ACESSO_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(800)
        campo = page.locator(CAMPO_USUARIO).first
        if not (campo.count() and campo.is_visible()):
            return False, "a tela de login do portal mudou de formato"
        campo.fill(email)
        botao = page.get_by_role("button", name="Acessar").first
        if botao.count():
            botao.click()
        else:
            campo.press("Enter")
        page.wait_for_timeout(2500)
        page.wait_for_load_state("domcontentloaded", timeout=30000)

        # Sessão fria: o portão redireciona pro SSO e pede a senha ali.
        campo_senha = page.locator('input[type="password"]').first
        if campo_senha.count() and campo_senha.is_visible():
            campo_senha.fill(senha)  # o valor não vai pra log
            botao_senha = page.locator(
                'button[type="submit"], input[type="submit"], #loginbtn'
            ).first
            if botao_senha.count():
                botao_senha.click()
            else:
                campo_senha.press("Enter")
            page.wait_for_timeout(3000)
            page.wait_for_load_state("domcontentloaded", timeout=30000)

        # Sessão quente: o portão nem pede senha, só devolve o HUB com os
        # atalhos (ACESSAR O AVA, PORTAL DO ALUNO, SISTEMA DE PROVAS...).
        # Confirmado ao vivo em 29/08/2026, reproduzindo um login frio igual
        # ao do runner: sem clicar no atalho, a sessão nunca chega a valer em
        # sa.univesp.br, e o robô caía de volta em /index.xhtml como se o
        # portão não tivesse feito nada — mesmo tendo autenticado de verdade.
        if "acesso.univesp.br" in (page.url or ""):
            atalho = page.get_by_text("PORTAL DO ALUNO", exact=False).first
            if atalho.count():
                atalho.click()
                page.wait_for_timeout(1500)
                page.wait_for_load_state("domcontentloaded", timeout=30000)
    except PlaywrightError as erro:
        return False, f"falhei ao entrar no portal ({type(erro).__name__})"

    recusa = _erro_visivel(page)
    if recusa:
        return False, recusa

    try:
        page.goto(TELA_INICIAL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1200)
    except PlaywrightError as erro:
        return False, f"não consegui abrir a tela do aluno ({type(erro).__name__})"

    if _logado(page):
        return True, "entrei no portal"
    return False, (
        "o portal não abriu a tela do aluno depois do login "
        f"(parou em {_onde_parou(page)})"
    )


def _texto(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(1200)
    return page.locator("body").inner_text()


# Estados de matrícula/nota que a tela mostra, sem acento e minúsculo. Vale
# tanto pra "situação" do card de disciplina na tela inicial (que hoje vem
# sozinha, tipo "CURSANDO") quanto pra coluna Situação do boletim (que hoje
# separou "Cursando" de "(Em Recuperação)" em vez de vir junto como antes).
SITUACOES = ("cursando", "aprovado", "reprovado", "trancad", "cancelad", "recupera")


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
            if sem_acento(adiante).lower().strip() in SITUACOES:
                situacao = adiante
                break
        vistas.add(codigo)
        disciplinas.append(
            {
                "codigo": codigo,
                "nome": casou.group(2).strip(),
                # Sem "Cursando" de reserva: a situação vem da tela ou não
                # vem. A ausência de estado real é diferença que importa.
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
    com o mesmo valor. Na tela nova o número mora em
    ``#btnMsg .badge-notification`` (confirmado ao vivo, único elemento com
    essa classe na página); os seletores de reserva cobrem uma troca de nome
    de classe sem exigir outra sessão de mapeamento.
    """
    try:
        bruto = page.evaluate(
            """() => {
                const proprio = document.querySelector(
                    '#btnMsg .badge-notification, .badge-notification'
                );
                if (proprio) return proprio.textContent.trim();
                const alvo = document.querySelector(
                    '.badge, .rf-ind-stg, [class*=notifica] span, .fa-envelope + span, .pi-envelope + span'
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
# A tela nova cola "CH: 40h" no fim do nome, na mesma célula. Tira daqui, não
# do nome exibido no guia.
RE_CH_SUFIXO = re.compile(r"\s*CH:\s*\d+\s*h\s*$", re.IGNORECASE)
RE_FREQUENCIA = re.compile(r"^[\d.,]+\s*\(%\)$")


def ler_notas(page):
    """Boletim oficial da secretaria, que não é o boletim do Moodle.

    Aqui aparecem as quatro parcelas que formam a média do bimestre (atividade
    no AVA, prova, média parcial e exame) e a situação da matrícula. É a
    única fonte que enxerga a nota da prova presencial.

    Duas armadilhas, herdadas da versão anterior e ainda válidas na tela
    nova:

    1. **A tabela não existe quando se chega pela URL.** Às vezes a página
       carrega só o cabeçalho e a lista só é montada depois. Navegar e ler
       devolvia lista vazia, que é indistinguível de "não tem nota" — por
       isso o cutucão no seletor de período abaixo.
    2. **A célula da disciplina pode trazer um rótulo escondido na frente**
       (``"Disciplina "``, da coluna que só aparece no layout estreito da
       tabela responsiva). Casar o código no início da linha ignorando esse
       rótulo evita que a leitura dependa do tamanho de tela do headless.

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
            elif any(s in sem_acento(celula).lower() for s in SITUACOES):
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
        limpa = celula[len("Disciplina "):] if celula.startswith("Disciplina ") else celula
        casou = RE_CODIGO_NOME.match(limpa)
        if casou:
            nome = RE_CH_SUFIXO.sub("", casou.group(2)).strip()
            return casou.group(1), nome
    return None


def _abrir_sistema_de_provas(page):
    """Segue o caminho do atalho até ``prova.univesp.br``.

    Não dá para pular etapa: o clique prepara um token na sessão do portal
    (a própria página nomeia o atalho ``botaoAcessoSistemaProvasMestreGR``,
    mesma raiz ``MestreGR`` do sistema antigo), e a página nasce numa aba
    nova.
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
    # A aba pode nascer numa página de espera antes do calendário aparecer.
    # Ler o corpo aqui sem esperar devolveria esse texto de transição.
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
    """``03/12`` + ``14:05`` + ano viram data com fuso de Brasília.

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
