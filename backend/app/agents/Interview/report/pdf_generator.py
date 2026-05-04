import logging
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger(__name__)

# Color Palette
PRIMARY_BLUE = colors.HexColor("#1e3a8a")    # Dark Blue
SECONDARY_BLUE = colors.HexColor("#3b82f6")  # Brighter Blue
TEXT_DARK = colors.HexColor("#1f2937")       # Near Black
TEXT_LIGHT = colors.HexColor("#4b5563")      # Soft Grey
SUCCESS_GREEN = colors.HexColor("#059669")
DANGER_RED = colors.HexColor("#dc2626")
BG_LIGHT = colors.HexColor("#f8fafc")        # Very Light Blue/Grey
BORDER_COLOR = colors.HexColor("#e2e8f0")

def draw_progress_bar(val, max_val=10, width=150, color=SECONDARY_BLUE):
    """Creates a text-based progress bar simulation inside a table."""
    filled_width = (val / max_val) * width
    return Table(
        [[ "" ]],
        colWidths=[width],
        rowHeights=[10],
        style=[
            ('BACKGROUND', (0,0), (0,0), colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
            # This is tricky with pure platypus table to do partial fill
            # We'll use a nested table for the fill
        ]
    )

def generate_report_pdf(report: dict) -> bytes:
    """
    Upgraded PDF report generation using ReportLab.
    Features professional layout, visual hierarchy, and scorecard dashboards.
    """
    summary = report.get("summary", {})
    strengths = report.get("strengths", [])
    weaknesses = report.get("weaknesses", [])
    critical_issues = report.get("critical_issues", [])
    questions = report.get("questions", [])
    improvement_plan = report.get("improvement_plan", [])
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=50, 
        leftMargin=50, 
        topMargin=50, 
        bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    
    # --- Custom Styles ---
    style_h1 = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=PRIMARY_BLUE,
        fontName='Helvetica-Bold',
        spaceAfter=5
    )
    
    style_date = ParagraphStyle(
        'HeaderDate',
        parent=styles['Normal'],
        fontSize=10,
        textColor=TEXT_LIGHT,
        alignment=TA_RIGHT
    )
    
    style_section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=PRIMARY_BLUE,
        fontName='Helvetica-Bold',
        spaceBefore=20,
        spaceAfter=12,
        borderPadding=(0, 0, 3, 0),
        borderWidth=0,
        underlineWidth=1
    )
    
    style_body = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontSize=10.5,
        textColor=TEXT_DARK,
        leading=15,
        alignment=TA_LEFT
    )

    style_metric_label = ParagraphStyle(
        'MetricLabel',
        parent=style_body,
        fontSize=9,
        textColor=TEXT_LIGHT,
        fontName='Helvetica-Bold',
        textTransform='uppercase'
    )

    style_metric_value = ParagraphStyle(
        'MetricValue',
        parent=style_body,
        fontSize=16,
        textColor=PRIMARY_BLUE,
        fontName='Helvetica-Bold'
    )
    
    style_bullet = ParagraphStyle(
        'Bullet',
        parent=style_body,
        leftIndent=15,
        bulletIndent=5,
        spaceAfter=6
    )

    style_q_box = ParagraphStyle(
        'QuestionBox',
        parent=style_body,
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=PRIMARY_BLUE
    )

    style_feedback_box = ParagraphStyle(
        'FeedbackBox',
        parent=style_body,
        fontSize=9.5,
        textColor=TEXT_LIGHT,
        fontName='Helvetica-Oblique'
    )
    
    elements = []
    
    # ─── HEADER SECTION ──────────────────────────────────────────────────
    header_data = [
        [Paragraph("Interview Report", style_h1), Paragraph(datetime.now().strftime("%B %d, %Y"), style_date)]
    ]
    header_table = Table(header_data, colWidths=[350, 150])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY_BLUE, spaceBefore=5, spaceAfter=20))
    
    # ─── OVERALL SCORE DASHBOARD ──────────────────────────────────────────
    verdict = summary.get("verdict", "Needs Review")
    verdict_color = SUCCESS_GREEN if "HIRE" in verdict.upper() else DANGER_RED if "REJECT" in verdict.upper() else SECONDARY_BLUE
    
    overall_score = summary.get("overall_score", 0)
    
    # Scorecard Dashboard
    dash_data = [
        [
            Paragraph("OVERALL SCORE", style_metric_label), 
            Paragraph("VERDICT", style_metric_label)
        ],
        [
            Paragraph(f"{overall_score}/10", style_metric_value),
            Paragraph(verdict, ParagraphStyle('VerdictVal', parent=style_metric_value, textColor=verdict_color))
        ],
        [Spacer(1, 10), Spacer(1, 10)],
        [
            Paragraph("CORRECTNESS", style_metric_label),
            Paragraph("COMMUNICATION", style_metric_label)
        ],
        [
            Paragraph(f"{summary.get('average_correctness', 0)} / 10", style_body),
            Paragraph(f"{summary.get('average_communication', 0)} / 10", style_body)
        ]
    ]
    
    dash_table = Table(dash_data, colWidths=[245, 245])
    dash_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('ROUNDEDCORNERS', [10, 10, 10, 10]),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('LEFTPADDING', (0,0), (-1,-1), 20),
        ('RIGHTPADDING', (0,0), (-1,-1), 20),
        ('TOPPADDING', (0,0), (-1,-1), 15),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
        ('SPAN', (1, 1), (1, 1)),
    ]))
    elements.append(dash_table)
    elements.append(Spacer(1, 25))
    
    # ─── PROFESSIONAL SUMMARY ───────────────────────────────────────────
    elements.append(Paragraph("Executive Summary", style_section_title))
    elements.append(Paragraph(summary.get("communication_summary", "Detailed assessment summary is pending."), style_body))
    elements.append(Spacer(1, 15))
    
    # ─── STRENGTHS & WEAKNESSES (2-COLUMN) ─────────────────────────────
    elements.append(Paragraph("Performance Breakdown", style_section_title))
    
    s_list = [Paragraph(f"• {s}", style_bullet) for s in strengths] or [Paragraph("None identified.", style_body)]
    w_list = [Paragraph(f"• {w}", style_bullet) for w in weaknesses] or [Paragraph("None identified.", style_body)]
    
    sw_data = [
        [Paragraph("<b>STRENGTHS</b>", ParagraphStyle('colH', parent=style_body, textColor=SUCCESS_GREEN)), 
         Paragraph("<b>AREAS FOR GROWTH</b>", ParagraphStyle('colH', parent=style_body, textColor=DANGER_RED))],
        [s_list, w_list]
    ]
    
    sw_table = Table(sw_data, colWidths=[245, 245])
    sw_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.transparent),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
    ]))
    elements.append(sw_table)
    
    # ─── CRITICAL ISSUES ────────────────────────────────────────────────
    if critical_issues:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Critical Observations", style_section_title))
        for issue in critical_issues:
            issue_para = Paragraph(f"<b>!</b> {issue}", ParagraphStyle('CritPara', parent=style_body, textColor=DANGER_RED, leftIndent=5))
            elements.append(issue_para)
            elements.append(Spacer(1, 5))

    # ─── DETAILED QUESTION ANALYSIS ─────────────────────────────────────
    elements.append(Paragraph("Detailed Question Breakdown", style_section_title))
    
    for idx, q in enumerate(questions):
        q_text = q.get('question', 'N/A')
        ans_text = q.get('answer', 'No answer recorded.')
        feedback = q.get('feedback', 'No specific feedback provided.')
        score = q.get('correctness', 0)
        
        q_data = [
            [Paragraph(f"Question {idx+1}", style_metric_label), Paragraph(f"Score: {score}/10", style_date)],
            [Paragraph(q_text, style_q_box), ""],
            [Paragraph("Candidate Answer:", ParagraphStyle('ansL', parent=style_body, fontSize=8, textColor=TEXT_LIGHT)), ""],
            [Paragraph(f"\"{ans_text}\"", ParagraphStyle('ansT', parent=style_body, leftIndent=10, fontName='Helvetica-Oblique')), ""],
            [Paragraph("Feedback:", ParagraphStyle('ansL', parent=style_body, fontSize=8, textColor=TEXT_LIGHT)), ""],
            [Paragraph(feedback, style_feedback_box), ""]
        ]
        
        q_table = Table(q_data, colWidths=[400, 90])
        q_table.setStyle(TableStyle([
            ('SPAN', (0, 1), (1, 1)),
            ('SPAN', (0, 3), (1, 3)),
            ('SPAN', (0, 5), (1, 5)),
            ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
            ('BACKGROUND', (0,0), (-1,0), BG_LIGHT),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        elements.append(KeepTogether(q_table))
        elements.append(Spacer(1, 15))
        
    # ─── IMPROVEMENT PLAN ──────────────────────────────────────────────
    if improvement_plan:
        elements.append(Paragraph("Personalized Improvement Roadmap", style_section_title))
        for step in improvement_plan:
            elements.append(Paragraph(step, style_bullet))
            elements.append(Spacer(1, 4))
            
    # Build Document
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
