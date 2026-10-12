"""Render the maintained manual and traceability matrix into a readable PDF."""
import csv
import re
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, String, Line

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'output' / 'pdf' / 'SafeRouteAI-manual.pdf'
BLUE = colors.HexColor('#176FE8')
INK = colors.HexColor('#12324D')
IVORY = colors.HexColor('#F8F5ED')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodySafe', fontName='Helvetica', fontSize=10, leading=15, textColor=INK, spaceAfter=8))
styles.add(ParagraphStyle(name='TitleSafe', fontName='Helvetica-Bold', fontSize=36, leading=40, textColor=INK, spaceAfter=16))
styles.add(ParagraphStyle(name='SubSafe', fontName='Helvetica', fontSize=17, leading=23, textColor=BLUE, spaceAfter=15))
styles.add(ParagraphStyle(name='SectionSafe', fontName='Helvetica-Bold', fontSize=20, leading=25, textColor=INK, spaceAfter=15))
styles.add(ParagraphStyle(name='CellSafe', fontName='Helvetica', fontSize=8, leading=11, textColor=INK, spaceAfter=0))
styles.add(ParagraphStyle(name='CodeSafe', fontName='Courier', fontSize=8.8, leading=12, textColor=INK, backColor=colors.HexColor('#E9F1FF'), borderPadding=9, spaceAfter=12))


def para(text, style='BodySafe'):
    formatted = re.sub(r'`([^`]+)`', r'<font name="Courier">\1</font>', escape(text))
    return Paragraph(formatted, styles[style])


def diagram():
    drawing = Drawing(475, 205)
    boxes = [(0, 130, 135, 60, 'APP MÓVIL', 'React Native + Expo'), (170, 130, 135, 60, 'API / BACKEND', 'FastAPI + Python'), (340, 130, 135, 60, 'DATOS', 'PostgreSQL / PostGIS'), (0, 10, 135, 60, 'MAPAS', 'Azure online / OSM local'), (170, 10, 135, 60, 'INTELIGENCIA', 'Reglas / Pandas / NumPy'), (340, 10, 135, 60, 'MEDIA', 'Blob privado / Azurite')]
    for x, y, w, h, title, detail in boxes:
        drawing.add(Rect(x, y, w, h, rx=9, ry=9, fillColor=colors.HexColor('#E9F1FF'), strokeColor=colors.HexColor('#DBE4ED')))
        drawing.add(String(x+10, y+38, title, fontName='Helvetica-Bold', fontSize=10, fillColor=INK))
        drawing.add(String(x+10, y+18, detail, fontName='Helvetica', fontSize=8, fillColor=INK))
    for x1, y1, x2, y2 in [(135,160,170,160),(305,160,340,160),(237,130,237,70),(68,130,68,70),(407,130,407,70),(135,40,170,40),(305,40,340,40)]:
        drawing.add(Line(x1,y1,x2,y2,strokeColor=BLUE,strokeWidth=1.5))
    return drawing


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BLUE); canvas.rect(0, A4[1]-8, A4[0], 8, fill=1, stroke=0)
    canvas.setFillColor(INK); canvas.setFont('Helvetica', 8)
    canvas.drawString(44, 25, 'SafeRouteAI | Manual técnico y de usuario | 1.0.0')
    canvas.drawRightString(A4[0]-44, 25, str(doc.page))
    canvas.restoreState()


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    flow = [Spacer(1, 70), para('SafeRouteAI', 'TitleSafe'), para('Manual técnico y de usuario', 'SubSafe'), para('Versión 1.0.0 · Salamanca, Guanajuato'), Spacer(1, 25), diagram(), Spacer(1, 25), para('Rutas, reportes comunitarios y alertas en una aplicación móvil.'), para('Código, configuración, reglas de riesgo, uso cotidiano y trazabilidad de requisitos.'), Spacer(1, 15), para('La aceptación final con Azure, PostGIS y dispositivos se documenta por separado de las pruebas automáticas.'), PageBreak()]
    lines = (ROOT/'manual.md').read_text(encoding='utf-8').splitlines()
    body, code, in_code = [], [], False
    def flush():
        if body:
            text = ' '.join(body)
            # URLs largas: enlaces con titulo visible corto en el PDF.
            match = re.search(r'(https://\S+)', text)
            if match:
                text = text[:match.start()].rstrip(': ')
                flow.append(Paragraph(escape(text)+': <link href="'+escape(match.group(1))+'" color="#176FE8">Consultar documentación oficial</link>', styles['BodySafe']))
            else:
                flow.append(para(text))
            body.clear()
    for line in lines:
        if line.startswith('```'):
            flush()
            if in_code:
                # Long command lines wrap visually without losing their text.
                wrapped = []
                for cmd in code:
                    while len(cmd) > 92:
                        cut = cmd.rfind(' ', 0, 92)
                        cut = cut if cut > 10 else 92
                        wrapped.append(cmd[:cut]); cmd = '  '+cmd[cut:].lstrip()
                    wrapped.append(cmd)
                flow.append(Preformatted('\n'.join(wrapped), styles['CodeSafe']))
                code.clear()
            in_code = not in_code
        elif in_code:
            code.append(line)
        elif line.startswith('## '):
            flush()
            if line.startswith('## Manual'):
                continue
            if flow and not isinstance(flow[-1], PageBreak) and not line.startswith('## 1.'):
                flow.append(PageBreak())
            flow.append(para(line[3:], 'SectionSafe'))
        elif line.startswith('# '):
            continue
        elif not line.strip():
            flush()
        elif line.startswith('- '):
            flush()
            body.append(line[2:])
            flush()
        else:
            body.append(line.lstrip('- '))
    flush()
    flow.append(PageBreak()); flow.append(para('11. Matriz de requisitos', 'SectionSafe'))
    flow.append(para('Código implementado y evidencia de validación. Pendiente significa que se necesita un servicio externo, credencial o dispositivo; no equivale a una prueba aprobada.'))
    with (ROOT/'requirements.csv').open(encoding='utf-8', newline='') as stream:
        rows = list(csv.reader(stream))
    table = Table([[para(cell, 'CellSafe') for cell in row] for row in rows], colWidths=[43, 115, 174, 155], repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E9F1FF')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),1,BLUE),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, IVORY]),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    flow.append(table)
    document = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=44, leftMargin=44, topMargin=38, bottomMargin=45, title='SafeRouteAI - Manual técnico y de usuario', author='SafeRouteAI')
    document.build(flow, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == '__main__':
    build()
