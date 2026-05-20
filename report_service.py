import io
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                  Spacer, PageBreak)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_PATHS = [
    '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
    '/System/Library/Fonts/Helvetica.ttc',
    '/Library/Fonts/Arial Unicode.ttf',
]

FONT_REGULAR = 'Helvetica'
FONT_BOLD    = 'Helvetica-Bold'

for path in FONT_PATHS:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont('TRFont', path))
            FONT_REGULAR = 'TRFont'
            FONT_BOLD    = 'TRFont'
            break
        except Exception:
            continue

CYAN  = HexColor('#0099cc')
DARK  = HexColor('#1a1f2e')
GRAY  = HexColor('#6b7280')
LIGHT = HexColor('#f3f4f6')
RED   = HexColor('#dc2626')
AMBER = HexColor('#f59e0b')
GREEN = HexColor('#10b981')
TEXT  = HexColor('#111827')


def get_styles():
    styles = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('CustomTitle', parent=styles['Title'],
            fontSize=24, textColor=DARK, alignment=TA_LEFT,
            spaceAfter=6, fontName=FONT_BOLD),
        'subtitle': ParagraphStyle('CustomSubtitle', parent=styles['Normal'],
            fontSize=11, textColor=GRAY, alignment=TA_LEFT,
            spaceAfter=20, fontName=FONT_REGULAR),
        'h1': ParagraphStyle('CustomH1', parent=styles['Heading1'],
            fontSize=15, textColor=DARK, alignment=TA_LEFT,
            spaceAfter=10, spaceBefore=14, fontName=FONT_BOLD),
        'h2': ParagraphStyle('CustomH2', parent=styles['Heading2'],
            fontSize=11, textColor=CYAN, alignment=TA_LEFT,
            spaceAfter=6, spaceBefore=8, fontName=FONT_BOLD),
        'body': ParagraphStyle('CustomBody', parent=styles['Normal'],
            fontSize=9, textColor=TEXT, alignment=TA_LEFT,
            leading=13, fontName=FONT_REGULAR),
    }


def build_summary_chart(acil_n, proaktif_n, sadakat_n):
    drawing = Drawing(450, 180)
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 30
    bc.height = 130
    bc.width = 350
    bc.data = [[acil_n, proaktif_n, sadakat_n]]
    bc.categoryAxis.categoryNames = ['Acil', 'Proaktif', 'Sadakat']
    bc.bars[0].fillColor = CYAN
    bc.bars.strokeColor = None
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = max(acil_n, proaktif_n, sadakat_n, 10) + 2
    bc.valueAxis.valueStep = 2
    bc.categoryAxis.labels.fontName = FONT_REGULAR
    bc.categoryAxis.labels.fontSize = 9
    bc.valueAxis.labels.fontName = FONT_REGULAR
    bc.valueAxis.labels.fontSize = 8
    bc.barWidth = 22
    drawing.add(bc)
    return drawing


def build_pie_chart(acil_n, proaktif_n, sadakat_n):
    drawing = Drawing(220, 180)
    pie = Pie()
    pie.x = 50
    pie.y = 20
    pie.width = 130
    pie.height = 130
    pie.data = [acil_n, proaktif_n, sadakat_n]
    pie.labels = [f'Acil ({acil_n})', f'Proaktif ({proaktif_n})', f'Sadakat ({sadakat_n})']
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white
    pie.slices[0].fillColor = RED
    pie.slices[1].fillColor = AMBER
    pie.slices[2].fillColor = GREEN
    pie.slices.fontName = FONT_REGULAR
    pie.slices.fontSize = 8
    pie.simpleLabels = 1
    pie.sideLabels = 1
    drawing.add(pie)
    return drawing


def build_segment_table(rows, segment_color):
    if not rows:
        empty_style = ParagraphStyle('empty', fontSize=9, textColor=GRAY,
                                      alignment=TA_CENTER, fontName=FONT_REGULAR)
        return Paragraph("Bu segmentte musteri bulunamadi.", empty_style)

    data = [['#', 'Musteri ID', 'Meslek', 'Hizmet (ay)', 'Aylik Gelir', 'Risk']]

    for i, r in enumerate(rows, 1):
        proba = r.get('churn_proba', 0)
        revenue = r.get('MonthlyRevenue', 0)
        revenue_str = f"${revenue:.2f}" if isinstance(revenue, (int, float)) else f"${revenue}"

        data.append([
            str(i),
            f"#{r.get('CustomerID', '-')}",
            str(r.get('Occupation', '-'))[:18],
            str(r.get('MonthsInService', '-')),
            revenue_str,
            f"%{int(proba * 100)}"
        ])

    table = Table(data, colWidths=[1*cm, 3*cm, 4*cm, 2.5*cm, 2.5*cm, 2*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
        ('FONTNAME',    (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE',    (0, 0), (-1, 0), 9),
        ('ALIGN',       (0, 0), (-1, 0), 'LEFT'),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',  (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('FONTNAME',    (0, 1), (-1, -1), FONT_REGULAR),
        ('FONTSIZE',    (0, 1), (-1, -1), 8.5),
        ('TEXTCOLOR',   (0, 1), (-1, -1), TEXT),
        ('TOPPADDING',  (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TEXTCOLOR',   (5, 1), (5, -1), segment_color),
        ('FONTNAME',    (5, 1), (5, -1), FONT_BOLD),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
        ('LINEBELOW',   (0, 0), (-1, -1), 0.3, GRAY),
        ('GRID',        (0, 0), (-1, -1), 0, colors.white),
    ]))
    return table


def add_page_decorations(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(CYAN)
    canvas.rect(0, A4[1] - 12, A4[0], 12, stroke=0, fill=1)
    canvas.setFont(FONT_REGULAR, 7)
    canvas.setFillColor(GRAY)
    footer_text = f"Pulse AI - Musteri Kayip Onleme Raporu - Sayfa {doc.page}"
    try:
        footer_text = f"Pulse AI · Müşteri Kayıp Önleme Raporu · Sayfa {doc.page}"
    except Exception:
        pass
    canvas.drawCentredString(A4[0] / 2, 1*cm, footer_text)
    canvas.restoreState()


def generate_pdf_report(data: dict) -> bytes:
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.2*cm, bottomMargin=1.8*cm,
        title='Pulse AI - Musteri Kayip Onleme Raporu',
        author='Pulse AI'
    )

    styles = get_styles()
    story = []

    acil     = data.get('acil', [])
    proaktif = data.get('proaktif', [])
    sadakat  = data.get('sadakat', [])
    toplam   = data.get('toplam', 0)

    story.append(Paragraph("Müşteri Kayıp Önleme Raporu", styles['title']))
    story.append(Paragraph(
        f"Oluşturulma: {datetime.now().strftime('%d.%m.%Y, %H:%M')}",
        styles['subtitle']
    ))

    story.append(Paragraph("Yönetici Özeti", styles['h1']))
    summary_text = (
        f"Bu rapor, sistemde analiz edilen <b>{toplam}</b> müşterinin churn riski "
        f"değerlendirmesine dayanmaktadır. Risk skorları, CatBoost makine öğrenimi "
        f"modeli ve SHAP açıklanabilirlik analizi kullanılarak hesaplanmıştır. "
        f"Müşteriler 3 risk segmentine ayrılmıştır:"
    )
    story.append(Paragraph(summary_text, styles['body']))
    story.append(Spacer(1, 8))

    summary_data = [
        ['Segment', 'Müşteri Sayısı', 'Eşik Aralığı', 'Önerilen Yaklaşım'],
        ['Acil',     str(len(acil)),     '%50 ve üzeri',  'Hızlı retention aksiyonu'],
        ['Proaktif', str(len(proaktif)), '%30 - %50',     'Önleyici temas'],
        ['Sadakat',  str(len(sadakat)),  '%30 altı',      'Sadakat güçlendirme'],
    ]
    summary_table = Table(summary_data, colWidths=[3*cm, 3*cm, 3.5*cm, 5.5*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
        ('FONTNAME',    (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE',    (0, 0), (-1, -1), 9),
        ('ALIGN',       (0, 0), (-1, 0), 'LEFT'),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',  (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('FONTNAME',    (0, 1), (-1, -1), FONT_REGULAR),
        ('TEXTCOLOR',   (0, 1), (0, 1), RED),
        ('TEXTCOLOR',   (0, 2), (0, 2), AMBER),
        ('TEXTCOLOR',   (0, 3), (0, 3), GREEN),
        ('FONTNAME',    (0, 1), (0, -1), FONT_BOLD),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
        ('LINEBELOW',   (0, 0), (-1, -1), 0.3, GRAY),
    ]))
    story.append(summary_table)

    story.append(Paragraph("Segment Dağılımı", styles['h1']))

    chart_data = [[
        build_pie_chart(len(acil), len(proaktif), len(sadakat)),
        build_summary_chart(len(acil), len(proaktif), len(sadakat))
    ]]
    chart_table = Table(chart_data, colWidths=[7*cm, 11*cm])
    chart_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(chart_table)

    story.append(PageBreak())

    story.append(Paragraph("1. Acil Aksiyon Gereken Müşteriler", styles['h1']))
    story.append(Paragraph(
        f"Churn olasılığı %50 ve üzerinde olan, hızlı retention "
        f"aksiyonu gerektiren {len(acil)} müşteri. Önümüzdeki 7 gün içinde "
        f"yüksek değerli, kişiselleştirilmiş tekliflerle iletişime geçilmesi "
        f"önerilir.", styles['body']))
    story.append(Spacer(1, 8))
    story.append(build_segment_table(acil, RED))

    story.append(Spacer(1, 16))

    story.append(Paragraph("2. Proaktif Yaklaşım Önerilen Müşteriler", styles['h1']))
    story.append(Paragraph(
        f"Churn olasılığı %30 - %50 arasında olan {len(proaktif)} müşteri. "
        f"Risk büyümeden, 30 gün içinde önleyici temas kurulması ve "
        f"hizmet kalitesi iyileştirmeleri önerilir.", styles['body']))
    story.append(Spacer(1, 8))
    story.append(build_segment_table(proaktif, AMBER))

    story.append(PageBreak())

    story.append(Paragraph("3. Sadakat Programı Adayları", styles['h1']))
    story.append(Paragraph(
        f"Churn olasılığı %30 altında olan {len(sadakat)} müşteri. "
        f"Bu müşteriler için düşük maliyetli sadakat programları, "
        f"teşekkür kampanyaları ve değerli müşteri bildirimleri önerilir.",
        styles['body']))
    story.append(Spacer(1, 8))
    story.append(build_segment_table(sadakat, GREEN))

    story.append(Spacer(1, 24))

    story.append(Paragraph("Metodoloji", styles['h1']))
    method_text = (
        "<b>Model:</b> CatBoost gradient boosting algoritması, ROC-AUC: 0.67, "
        "Recall (Churn): 0.83 ile eğitilmiştir.<br/><br/>"
        "<b>Açıklanabilirlik:</b> SHAP (SHapley Additive exPlanations) "
        "değerleri, her bireysel tahmini etkileyen en önemli faktörleri "
        "kantitatif olarak ortaya koymaktadır.<br/><br/>"
        "<b>Eşik değeri:</b> %27 (Youden ve Balanced Accuracy ortalaması ile "
        "belirlenmiştir).<br/><br/>"
        "<b>Veri Kaynağı:</b> Cell2Cell telekom müşteri veri seti."
    )
    story.append(Paragraph(method_text, styles['body']))

    doc.build(story, onFirstPage=add_page_decorations,
              onLaterPages=add_page_decorations)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
