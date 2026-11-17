from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output" / "pdf" / "arquitetura_pipeline_humano_x_ia.pdf"

NAVY = colors.HexColor("#183B56")
BLUE = colors.HexColor("#2E6F9E")
LIGHT_BLUE = colors.HexColor("#E8F2F8")
GREEN = colors.HexColor("#2D7D67")
LIGHT_GREEN = colors.HexColor("#E7F3EF")
ORANGE = colors.HexColor("#C56A24")
LIGHT_ORANGE = colors.HexColor("#FFF0E3")
GRAY = colors.HexColor("#5B6770")
LIGHT_GRAY = colors.HexColor("#F2F4F5")
RED = colors.HexColor("#A54242")


def box(c, x, y, w, h, text, fill, stroke=NAVY, font_size=8.5):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, 3 * mm, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", font_size)
    lines = text.split("\n")
    line_h = font_size + 2
    start = y + h / 2 + (len(lines) - 1) * line_h / 2 - font_size * 0.35
    for i, line in enumerate(lines):
        c.drawCentredString(x + w / 2, start - i * line_h, line)


def arrow(c, x1, y1, x2, y2, color=GRAY):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(1.2)
    c.line(x1, y1, x2, y2)
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 3.2 * mm
    for delta in (2.6, -2.6):
        c.line(x2, y2, x2 - size * math.cos(angle + delta), y2 - size * math.sin(angle + delta))


def draw_architecture(c, _doc):
    width, height = landscape(A4)
    c.saveState()
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(18 * mm, height - 19 * mm, "Arquitetura do pipeline Humano x IA")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 9)
    c.drawString(18 * mm, height - 26 * mm, "Coleta historica, geracao por LLM, scans equivalentes e consolidacao comparativa")

    bw, bh = 42 * mm, 18 * mm
    y1 = height - 58 * mm
    xs = [15 * mm, 67 * mm, 119 * mm, 171 * mm, 223 * mm]
    labels = [
        "Repositorios\nGitHub",
        "Commit ate\n31/12/2020",
        "Filtro de tamanho\n5 arquivos / 500 LOC",
        "Snapshot humano\ncongelado",
        "README + docs\nsem codigo humano",
    ]
    fills = [LIGHT_BLUE, LIGHT_BLUE, LIGHT_ORANGE, LIGHT_GREEN, LIGHT_BLUE]
    for x, label, fill in zip(xs, labels, fills):
        box(c, x, y1, bw, bh, label, fill)
    for i in range(len(xs) - 1):
        arrow(c, xs[i] + bw, y1 + bh / 2, xs[i + 1] - 2 * mm, y1 + bh / 2)

    human_x, branch_y = 32 * mm, 113 * mm
    prompt_x = 183 * mm
    box(c, human_x, branch_y, 52 * mm, 18 * mm, "PROJETO HUMANO\ncommit historico", LIGHT_GREEN, GREEN)
    box(c, prompt_x, branch_y, 52 * mm, 18 * mm, "PROMPT FUNCIONAL\nREADME + docs", LIGHT_ORANGE, ORANGE)
    arrow(c, xs[3] + bw / 2, y1, human_x + 26 * mm, branch_y + 18 * mm)
    arrow(c, xs[-1] + bw / 2, y1, prompt_x + 26 * mm, branch_y + 18 * mm)

    llm_y = 82 * mm
    llm_xs = [126 * mm, 184 * mm, 242 * mm]
    llms = ["OPENAI", "GEMINI", "CLAUDE"]
    for x, label in zip(llm_xs, llms):
        box(c, x, llm_y, 44 * mm, 16 * mm, f"{label}\nprojeto gerado", LIGHT_BLUE, BLUE)
        arrow(c, prompt_x + 26 * mm, branch_y, x + 22 * mm, llm_y + 16 * mm)

    scan_y = 50 * mm
    box(c, 18 * mm, scan_y, 38 * mm, 17 * mm, "Semgrep\np/default", LIGHT_ORANGE, ORANGE)
    box(c, 62 * mm, scan_y, 38 * mm, 17 * mm, "SonarQube\nPython only", LIGHT_ORANGE, ORANGE)
    arrow(c, human_x + 26 * mm, branch_y, 37 * mm, scan_y + 17 * mm)
    arrow(c, human_x + 26 * mm, branch_y, 81 * mm, scan_y + 17 * mm)

    ia_scan_x = 176 * mm
    box(c, ia_scan_x, scan_y, 66 * mm, 17 * mm, "MESMAS CONFIGURACOES\nSemgrep + SonarQube", LIGHT_ORANGE, ORANGE)
    for x in llm_xs:
        arrow(c, x + 22 * mm, llm_y, ia_scan_x + 33 * mm, scan_y + 17 * mm)

    result_y = 25 * mm
    box(c, 27 * mm, result_y, 64 * mm, 15 * mm, "resultados_scan_humano", LIGHT_GREEN, GREEN)
    box(c, 177 * mm, result_y, 64 * mm, 15 * mm, "resultados_scan_IA\nOpenAI / Gemini / Claude", LIGHT_BLUE, BLUE)
    arrow(c, 59 * mm, scan_y, 59 * mm, result_y + 15 * mm)
    arrow(c, ia_scan_x + 33 * mm, scan_y, 209 * mm, result_y + 15 * mm)

    final_y = 3 * mm
    box(c, 105 * mm, final_y, 86 * mm, 14 * mm, "TABELA FINAL HUMANO x IA\nCSV + XLSX / metricas por KLOC", colors.HexColor("#F0EAF8"), colors.HexColor("#72539B"), 8.5)
    arrow(c, 59 * mm, result_y, 125 * mm, final_y + 14 * mm)
    arrow(c, 209 * mm, result_y, 171 * mm, final_y + 14 * mm)
    c.restoreState()


def page_header(c, title, subtitle, page_number):
    width, height = landscape(A4)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(18 * mm, height - 18 * mm, title)
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 9.5)
    c.drawString(18 * mm, height - 25 * mm, subtitle)
    c.setFont("Helvetica", 8)
    c.drawRightString(width - 18 * mm, 4 * mm, f"Pagina {page_number}")


def draw_overview(c):
    width, height = landscape(A4)
    page_header(c, "Visao geral do pipeline", "Do GitHub ate a tabela comparativa Humano x IA", 1)
    center_x = width / 2
    w, h = 94 * mm, 19 * mm
    ys = [154, 125, 96, 67, 38, 9]
    labels = [
        "1. REPOSITORIOS GITHUB\nlista de candidatos Python",
        "2. SNAPSHOT HISTORICO\nultimo commit ate 31/12/2020",
        "3. FILTRO DE ELEGIBILIDADE\n5 arquivos Python e 500 LOC",
        "4. DUAS TRILHAS EXPERIMENTAIS\nprojeto humano e projetos gerados por IA",
        "5. ANALISE EQUIVALENTE\nSemgrep p/default e SonarQube Python",
        "6. RESULTADO COMPARATIVO\nCSV + XLSX e metricas normalizadas por KLOC",
    ]
    fills = [LIGHT_BLUE, LIGHT_BLUE, LIGHT_ORANGE, LIGHT_GREEN, LIGHT_ORANGE, colors.HexColor("#F0EAF8")]
    strokes = [BLUE, BLUE, ORANGE, GREEN, ORANGE, colors.HexColor("#72539B")]
    for idx, (y_mm, label, fill, stroke) in enumerate(zip(ys, labels, fills, strokes)):
        y = y_mm * mm
        box(c, center_x - w / 2, y, w, h, label, fill, stroke, 10)
        if idx < len(ys) - 1:
            arrow(c, center_x, y, center_x, (ys[idx + 1] * mm) + h)
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8.5)
    c.drawString(18 * mm, 16 * mm, "Principio: mesmas versoes, regras e escopo para humano e IA.")


def vertical_flow(c, center_x, start_y, labels, fills, strokes):
    w, h = 92 * mm, 19 * mm
    gap = 9 * mm
    y = start_y
    positions = []
    for label, fill, stroke in zip(labels, fills, strokes):
        box(c, center_x - w / 2, y, w, h, label, fill, stroke, 9.5)
        positions.append(y)
        y -= h + gap
    for i in range(len(positions) - 1):
        arrow(c, center_x, positions[i], center_x, positions[i + 1] + h)


def draw_comparison(c):
    width, height = landscape(A4)
    page_header(c, "Trilhas de analise: Humano e IA", "As duas trilhas usam as mesmas ferramentas antes da consolidacao", 2)
    c.setStrokeColor(colors.HexColor("#D3D9DE"))
    c.setLineWidth(0.8)
    c.line(width / 2, 18 * mm, width / 2, height - 33 * mm)

    left_x, right_x = width * 0.27, width * 0.73
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(left_x, height - 39 * mm, "TRILHA HUMANA")
    c.setFillColor(BLUE)
    c.drawCentredString(right_x, height - 39 * mm, "TRILHA IA")

    start = height - 68 * mm
    vertical_flow(c, left_x, start, [
        "SNAPSHOT HUMANO\ncommit historico congelado",
        "SCANS DE SEGURANCA\nSemgrep + SonarQube",
        "RESULTADOS HUMANOS\nresultados_scan_humano",
    ], [LIGHT_GREEN, LIGHT_ORANGE, LIGHT_GREEN], [GREEN, ORANGE, GREEN])

    vertical_flow(c, right_x, start, [
        "README + DOCUMENTACAO\nsem codigo-fonte humano",
        "PROMPT PADRONIZADO\nmesma especificacao funcional",
        "OPENAI / GEMINI / CLAUDE\nprojetos gerados separadamente",
        "MESMOS SCANS\nSemgrep + SonarQube",
        "RESULTADOS POR LLM\nresultados_scan_IA",
    ], [LIGHT_BLUE, LIGHT_ORANGE, LIGHT_BLUE, LIGHT_ORANGE, LIGHT_BLUE], [BLUE, ORANGE, BLUE, ORANGE, BLUE])

    final_y = 14 * mm
    final_w = 100 * mm
    box(c, width / 2 - final_w / 2, final_y, final_w, 16 * mm, "CONSOLIDACAO HUMANO x IA\ntotais, CWE, severidades e achados por KLOC", colors.HexColor("#F0EAF8"), colors.HexColor("#72539B"), 9.5)
    arrow(c, left_x, 86 * mm, width / 2 - 25 * mm, final_y + 16 * mm)
    arrow(c, right_x, 30 * mm, width / 2 + 25 * mm, final_y + 16 * mm)


def build_pdf():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    width, height = landscape(A4)
    c = canvas.Canvas(str(OUTPUT), pagesize=(width, height))
    draw_overview(c)
    c.showPage()
    draw_comparison(c)
    c.showPage()
    c.save()

    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=NAVY, alignment=TA_LEFT, spaceAfter=10)
    heading = ParagraphStyle("heading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=NAVY, spaceBefore=8, spaceAfter=5)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=colors.HexColor("#263238"))

    story = [Paragraph("Criterios de selecao e tamanho dos repositorios", title)]
    criterios = [
        "Commit obrigatoriamente anterior ou igual a 31/12/2020.",
        "No minimo 5 arquivos Python.",
        "No minimo 500 linhas Python aproximadas.",
        "README ou documentacao suficiente para gerar um sistema semelhante.",
        "Codigo humano excluido do prompt enviado as IAs.",
        "Para o grupo com achados: pelo menos 1 achado do Semgrep.",
    ]
    story.append(Paragraph("Criterios utilizados", heading))
    for item in criterios:
        story.append(Paragraph(f"- {item}", body))
    story.append(Spacer(1, 6 * mm))

    data = [
        ["Repositorio", "Grupo", "Arquivos .py", "LOC Python", "Resultado"],
        ["adeyosemanputra/pygoat", "Controle positivo", "15", "224", "Excluido: abaixo de 500 LOC"],
        ["anxolerd/dvpwa", "Controle positivo", "21", "674", "Selecionado"],
        ["erev0s/VAmPI", "Controle positivo", "11", "496", "Excluido: abaixo de 500 LOC"],
        ["bottlepy/bottle", "Projeto real", "32", "8.372", "Selecionado"],
    ]
    table = Table(data, colWidths=[58 * mm, 37 * mm, 28 * mm, 28 * mm, 69 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("BACKGROUND", (0, 2), (-1, 2), LIGHT_GREEN),
        ("BACKGROUND", (0, 4), (-1, 4), LIGHT_GREEN),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C5CDD3")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (3, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(Paragraph("Repositorios avaliados", heading))
    story.append(table)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Baseline final: 2 repositorios selecionados, 53 arquivos Python e aproximadamente 9.046 linhas Python.", body))
    story.append(Paragraph("Observacao metodologica: os dois repositorios selecionados possuem achados. Para avaliar se uma IA introduz vulnerabilidades em um baseline limpo, recomenda-se adicionar pelo menos um repositorio elegivel sem achados.", body))

    doc = SimpleDocTemplate(str(OUTPUT), pagesize=landscape(A4), rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=14 * mm, title="Arquitetura do pipeline Humano x IA", author="Pipeline de pesquisa")
    # Append the criteria page to the existing diagram PDF through a temporary file.
    temp = OUTPUT.with_name("arquitetura_criterios_temp.pdf")
    doc.filename = str(temp)
    doc.build(story)

    from pypdf import PdfReader, PdfWriter
    architecture_reader = PdfReader(str(OUTPUT))
    criteria_reader = PdfReader(str(temp))
    writer = PdfWriter()
    for page in architecture_reader.pages:
        writer.add_page(page)
    for page in criteria_reader.pages:
        writer.add_page(page)
    writer.add_metadata({"/Title": "Arquitetura do pipeline Humano x IA", "/Author": "Pipeline de pesquisa"})
    with OUTPUT.open("wb") as stream:
        writer.write(stream)
    temp.unlink()
    print(OUTPUT.resolve())


if __name__ == "__main__":
    build_pdf()
