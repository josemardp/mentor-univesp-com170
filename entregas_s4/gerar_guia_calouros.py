from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)


OUT = "C:/projetos/mentor-univesp/entregas_s4/guia_dos_calouros_faq.pdf"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#1E6A9A")
TEAL = colors.HexColor("#2E8B83")
LIGHT = colors.HexColor("#F1F6F8")
MID = colors.HexColor("#D5E4EA")
TEXT = colors.HexColor("#24313A")
MUTED = colors.HexColor("#5D6B73")


def link(url, label):
    return f'<link href="{url}" color="#1E6A9A"><u>{label}</u></link>'


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=24, leading=29, textColor=NAVY, alignment=TA_CENTER, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="CoverSub", parent=styles["Normal"], fontName="Helvetica",
    fontSize=12, leading=17, textColor=MUTED, alignment=TA_CENTER, spaceAfter=18,
))
styles.add(ParagraphStyle(
    name="H1Custom", parent=styles["Heading1"], fontName="Helvetica-Bold",
    fontSize=17, leading=21, textColor=NAVY, spaceBefore=4, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="Question", parent=styles["Heading2"], fontName="Helvetica-Bold",
    fontSize=11.5, leading=15, textColor=BLUE, spaceBefore=6, spaceAfter=4,
))
styles.add(ParagraphStyle(
    name="BodyCustom", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=9.6, leading=14, textColor=TEXT, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="Small", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8, leading=11, textColor=MUTED, spaceAfter=3,
))
styles.add(ParagraphStyle(
    name="Source", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=7.8, leading=10.5, textColor=MUTED, leftIndent=8, spaceAfter=7,
))
styles.add(ParagraphStyle(
    name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=10, leading=14, textColor=NAVY, alignment=TA_LEFT, spaceAfter=4,
))


def footer(canvas, doc):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(MID)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "Guia dos Calouros • FAQ verificada em fontes oficiais")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Página {doc.page}")
    canvas.restoreState()


doc = BaseDocTemplate(
    OUT, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
    topMargin=17 * mm, bottomMargin=20 * mm, title="Guia dos Calouros - FAQ",
    author="Grupo de estudantes - UNIVESP",
)
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
doc.addPageTemplates([PageTemplate(id="all", frames=frame, onPage=footer)])

story = []

# Capa
story += [Spacer(1, 28 * mm)]
story.append(Paragraph("GUIA DOS CALOUROS", styles["CoverTitle"]))
story.append(Paragraph("FAQ prático para começar na UNIVESP", styles["CoverSub"]))
story.append(Spacer(1, 9 * mm))
cover_table = Table([
    [Paragraph("Grupo", styles["Small"]), Paragraph("Grupo 4 (G4)", styles["BodyCustom"])],
    [Paragraph("Representante", styles["Small"]), Paragraph("(nome do representante)", styles["BodyCustom"])],
    [Paragraph("Curso representado", styles["Small"]), Paragraph("Inteligência Artificial na Prática Acadêmica e Profissional (COM170)", styles["BodyCustom"])],
    [Paragraph("Turma", styles["Small"]), Paragraph("COM170-BIA-DRP12-2026S2-T001", styles["BodyCustom"])],
], colWidths=[42 * mm, 123 * mm])
cover_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
    ("BOX", (0, 0), (-1, -1), 0.8, MID),
    ("INNERGRID", (0, 0), (-1, -1), 0.4, MID),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 9),
    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
]))
story.append(cover_table)
story.append(Spacer(1, 12 * mm))
story.append(Paragraph(
    "Este material reúne dez respostas curtas para dúvidas reais de quem está começando. "
    "As orientações foram conferidas no AVA da disciplina e nos atalhos oficiais disponibilizados pela UNIVESP. "
    "Material preparado para o Grupo 4, com base nas informações oficiais consultadas no AVA.", styles["BodyCustom"]))
story.append(Spacer(1, 8 * mm))
story.append(Paragraph("Atualizado em 14/07/2026", styles["Small"]))
story.append(PageBreak())

story.append(Paragraph("10 respostas para começar sem se perder", styles["H1Custom"]))
story.append(Paragraph(
    "Use os links indicados em cada item. Quando houver prazo ou regra de uma atividade específica, "
    "vale a instrução da própria página no AVA.", styles["BodyCustom"]))

items = [
    (
        "1. Onde entro no AVA e encontro minhas disciplinas?",
        "Acesse o <b>AVA UNIVESP</b> pelo endereço oficial e faça login. Depois, abra a área de cursos "
        "(“Meus cursos”) e selecione a disciplina desejada. Dentro dela, acompanhe as seções semanais "
        "e as atividades publicadas.",
        [("AVA UNIVESP", "https://ava.univesp.br/")],
    ),
    (
        "2. Onde vejo as atividades e os prazos?",
        "Entre na disciplina e consulte a seção da semana. A página de cada missão informa o que deve ser feito; "
        "a ferramenta de envio informa a janela de submissão. Na S4, por exemplo, o laboratório indicou envio "
        "até <b>15/07/2026, às 23h59</b> e permitiu substituir o arquivo até o fechamento.",
        [("S4 — Atividades da semana", "https://ava.univesp.br/mod/page/view.php?id=154856"),
         ("S4 — Laboratório", "https://ava.univesp.br/mod/workshop/view.php?id=154862")],
    ),
    (
        "3. Como envio um trabalho em grupo?",
        "Leia a instrução da ferramenta da atividade. Na entrega da S4, somente o representante do grupo deve enviar "
        "o arquivo; para este grupo, use o título <b>“Trabalho final - Grupo 4”</b>. Depois, anexe o material, salve as "
        "alterações e confira se o arquivo aparece como enviado antes do prazo.",
        [("S4 — Laboratório: fase de envio", "https://ava.univesp.br/mod/workshop/view.php?id=154862")],
    ),
    (
        "4. O que faço se tiver um problema no AVA ou precisar de atendimento?",
        "Use o <b>Sistema de Atendimento Eletrônico (SAE)</b>, disponibilizado no painel oficial do aluno. "
        "Ao abrir um chamado, descreva o problema com objetividade e, se for necessário, informe a disciplina, "
        "a atividade e o prazo envolvido.",
        [("SAE — atendimento eletrônico", "http://atendimento.univesp.br/sae/portal.html")],
    ),
    (
        "5. Onde encontro as orientações oficiais da universidade?",
        "Consulte o <b>Manual do Aluno</b>. Ele é o ponto de referência para orientações institucionais e acadêmicas; "
        "use sempre a versão online indicada nos canais oficiais e confira se a informação é aplicável ao seu curso "
        "e ao período atual.",
        [("Manual do Aluno", "https://apps.univesp.br/manual-do-aluno/")],
    ),
    (
        "6. Para que serve o Portal do Aluno?",
        "O Portal do Aluno é um dos sistemas oficiais indicados no painel da UNIVESP. Quando precisar de um serviço "
        "do aluno que não esteja dentro da sala do AVA, comece pelo atalho do portal e siga as orientações exibidas "
        "no próprio sistema.",
        [("Portal do Aluno", "https://sei.univesp.br/")],
    ),
    (
        "7. Onde acesso e-mail, Teams e outras ferramentas do Office 365?",
        "O painel oficial disponibiliza um atalho específico para <b>e-mail, Teams e outras ferramentas Office 365</b>. "
        "Use esse link institucional para entrar com a conta de estudante, em vez de procurar um endereço aleatório na internet.",
        [("E-mail, Teams e Office 365", "https://login.microsoftonline.com/login.srf?wa=wsignin1.0&whr=aluno.univesp.br")],
    ),
    (
        "8. Onde encontro livros e outros recursos de estudo?",
        "No painel da UNIVESP, há atalhos para <b>Pearson</b>, <b>Minha Biblioteca</b> e para o "
        "<b>Repositório de Recursos Educacionais Abertos</b>. Escolha o recurso indicado na disciplina e use o login "
        "institucional quando o sistema solicitar.",
        [("Pearson", "https://login.univesp.br/simplesaml/module.php/core/pearson.php"),
         ("Minha Biblioteca", "https://login.univesp.br/simplesaml/module.php/core/mb.php"),
         ("Repositório de REAs", "https://apps.univesp.br/repositorio/")],
    ),
    (
        "9. Onde consulto o calendário geral de provas?",
        "Acesse o calendário geral pelo Manual do Aluno. Como datas podem ser atualizadas, consulte o calendário "
        "online antes de se organizar e compare a informação com os avisos publicados no AVA da sua turma.",
        [("Calendário geral de provas", "https://apps.univesp.br/manual-do-aluno/calendario-provas/")],
    ),
    (
        "10. O que é o PPC e como ele ajuda o calouro?",
        "O <b>Projeto Pedagógico de Curso (PPC)</b> é o documento usado para entender a formação prevista para o curso. "
        "Na atividade da S3, ele é a fonte para identificar o eixo do curso, o perfil profissional, competências, "
        "a trilha estruturante e a diferença entre disciplinas regulares e estruturantes. A melhor prática é ler o PPC "
        "e reescrever as informações em linguagem simples, sem inventar conteúdo.",
        [("S3 — Meu curso em 6 pistas", "https://ava.univesp.br/mod/page/view.php?id=153336"),
         ("Manual do Aluno — sobre os cursos", "https://apps.univesp.br/manual-do-aluno/#sobre-os-cursos")],
    ),
]

for question, answer, sources in items:
    source_text = "<b>Fonte oficial:</b> " + " • ".join(link(url, name) for name, url in sources)
    story.append(KeepTogether([
        Paragraph(question, styles["Question"]),
        Paragraph(answer, styles["BodyCustom"]),
        Paragraph(source_text, styles["Source"]),
    ]))

story.append(PageBreak())
story.append(Paragraph("Checklist antes de enviar", styles["H1Custom"]))
checklist = [
    "Confirmar no AVA se o representante deve usar o título “Trabalho final - Grupo 4”.",
    "Conferir se os dez itens estão claros para alguém que nunca usou o AVA.",
    "Testar os links oficiais e corrigir qualquer endereço que tenha sido atualizado.",
    "Revisar ortografia, nomes de sistemas e prazos publicados na atividade.",
    "Salvar o PDF com o nome <b>Trabalho final - Grupo 4.pdf</b>.",
    "O representante deve anexar o arquivo no laboratório da S4 e confirmar o envio antes de 15/07/2026, 23h59.",
]
for line in checklist:
    story.append(Paragraph(f"[ ] {line}", styles["BodyCustom"]))

story.append(Spacer(1, 8 * mm))
story.append(Paragraph("Critério de verificação", styles["H1Custom"]))
story.append(Paragraph(
    "Este FAQ foi montado a partir das páginas oficiais acessadas no AVA da turma e dos links institucionais exibidos "
    "no painel do aluno. A atividade da S2 exige que cada resposta tenha fonte oficial; por isso, cada item deste arquivo "
    "mantém sua fonte indicada. Informações específicas de outro curso, polo ou período devem ser confirmadas no documento "
    "oficial correspondente antes da entrega.", styles["BodyCustom"]))

doc.build(story)
print(OUT)
