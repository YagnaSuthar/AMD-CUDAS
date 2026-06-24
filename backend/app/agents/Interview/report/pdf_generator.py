"""
Professional Interview Assessment Report – PDF Generator V4 (Phase 4B).

Market-ready, recruiter-grade PDF using ReportLab.
Consumes the enriched dict returned by ``report_builder.build_report()``.

Design principles:
  • Compact enterprise layout — 4–6 pages for a 4-question interview
  • Smart page breaks — no forced blank pages
  • KeepTogether for all logical card units
  • Zero evaluator leakage (handled upstream in report_builder)
  • Side-by-side radar + score breakdown on cover page
"""

from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from reportlab.graphics.charts.spider import SpiderChart
from reportlab.graphics.shapes import Drawing, String, Rect
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# COLOR PALETTE
# ═══════════════════════════════════════════════════════════════════════════

C_PRIMARY      = colors.HexColor("#0F172A")
C_SECONDARY    = colors.HexColor("#1E293B")
C_ACCENT       = colors.HexColor("#2563EB")
C_SUCCESS      = colors.HexColor("#059669")
C_WARNING      = colors.HexColor("#D97706")
C_DANGER       = colors.HexColor("#DC2626")
C_BG           = colors.HexColor("#FFFFFF")
C_CARD_BG      = colors.HexColor("#F8FAFC")
C_BORDER       = colors.HexColor("#E2E8F0")
C_TEXT         = colors.HexColor("#111827")
C_TEXT_SEC     = colors.HexColor("#6B7280")
C_HEADER_BG    = colors.HexColor("#0F172A")

# ═══════════════════════════════════════════════════════════════════════════
# SPACING SYSTEM  (Phase 4B — tightened)
# ═══════════════════════════════════════════════════════════════════════════

GAP_SECTION   = 18   # was 32
GAP_CARD      = 10   # was 20
PAD_INTERNAL  = 10   # was 16
GAP_HEADER    = 8    # was 12

PAGE_W, PAGE_H = A4
MARGIN = 36          # tighter margin

# Maximum answer length (chars) rendered in a question card.
# Longer responses are truncated to prevent LayoutError on oversized cards.
MAX_ANSWER_CHARS = 1500

# Approximate frame height (pts) available on a single page.
# Cards taller than this are rendered WITHOUT KeepTogether so they can split.
FRAME_H = PAGE_H - 2 * MARGIN - 12  # ≈ 746 pts

# ═══════════════════════════════════════════════════════════════════════════
# PARAGRAPH STYLES
# ═══════════════════════════════════════════════════════════════════════════

_base = getSampleStyleSheet()

S_TITLE = ParagraphStyle(
    "RptTitle", parent=_base["Heading1"],
    fontName="Helvetica-Bold", fontSize=20, leading=26,
    textColor=C_PRIMARY, spaceAfter=4, alignment=TA_CENTER,
)
S_SUBTITLE = ParagraphStyle(
    "RptSubTitle", parent=_base["Normal"],
    fontName="Helvetica", fontSize=8.5, leading=12,
    textColor=C_TEXT_SEC, alignment=TA_CENTER, spaceAfter=10,
)
S_SECTION = ParagraphStyle(
    "RptSection", parent=_base["Heading2"],
    fontName="Helvetica-Bold", fontSize=13, leading=17,
    textColor=C_PRIMARY, spaceBefore=GAP_SECTION, spaceAfter=GAP_HEADER,
)
S_CARD_TITLE = ParagraphStyle(
    "RptCardTitle", parent=_base["Heading3"],
    fontName="Helvetica-Bold", fontSize=11, leading=14,
    textColor=C_SECONDARY, spaceBefore=0, spaceAfter=6,
)
S_BODY = ParagraphStyle(
    "RptBody", parent=_base["Normal"],
    fontName="Helvetica", fontSize=9.5, leading=14,
    textColor=C_TEXT, alignment=TA_LEFT,
)
S_BODY_SM = ParagraphStyle(
    "RptBodySm", parent=S_BODY,
    fontSize=9, leading=13, textColor=C_TEXT_SEC,
)
S_BODY_ITALIC = ParagraphStyle(
    "RptBodyItalic", parent=S_BODY,
    fontName="Helvetica-Oblique", textColor=C_TEXT_SEC, fontSize=9,
)
S_METRIC_LABEL = ParagraphStyle(
    "RptMetricLabel", parent=S_BODY,
    fontName="Helvetica-Bold", fontSize=8, leading=11,
    textColor=C_TEXT_SEC, spaceAfter=2,
)
S_METRIC_VALUE = ParagraphStyle(
    "RptMetricValue", parent=S_BODY,
    fontName="Helvetica-Bold", fontSize=22, leading=28,
    textColor=C_PRIMARY,
)
S_BULLET = ParagraphStyle(
    "RptBullet", parent=S_BODY,
    leftIndent=12, bulletIndent=2, spaceAfter=4,
)
S_Q_TITLE = ParagraphStyle(
    "RptQTitle", parent=S_BODY,
    fontName="Helvetica-Bold", fontSize=10.5, textColor=C_PRIMARY,
)
S_FOOTER = ParagraphStyle(
    "RptFooter", parent=S_BODY,
    fontName="Helvetica", fontSize=7.5, textColor=C_TEXT_SEC,
    alignment=TA_CENTER,
)
S_PRIORITY_LABEL = ParagraphStyle(
    "RptPrioLabel", parent=S_BODY,
    fontName="Helvetica-Bold", fontSize=7.5, leading=10, spaceAfter=1,
)


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _score_color(val: float, max_val: float = 10.0) -> colors.HexColor:
    ratio = val / max_val if max_val else 0
    if ratio >= 0.75:
        return C_SUCCESS
    if ratio >= 0.50:
        return C_ACCENT
    if ratio >= 0.35:
        return C_WARNING
    return C_DANGER


def _verdict_color(verdict: str) -> colors.HexColor:
    v = (verdict or "").lower()
    if "excellent" in v or "strong" in v or "ready" in v:
        return C_SUCCESS
    if "good" in v or "almost" in v or "placement" in v:
        return C_ACCENT
    if "developing" in v or "internship" in v:
        return C_WARNING
    return C_DANGER


def _sf(val, decimals=1):
    try:
        return f"{float(val):.{decimals}f}"
    except (ValueError, TypeError):
        return "0.0"


def _horizontal_bar_row(
    label: str, value: float, max_val: float = 10.0, bar_width: float = 160,
) -> Table:
    """Compact horizontal bar row for score breakdowns."""
    fill_w = max(0.0, min(1.0, value / max_val)) * bar_width
    bar_d = Drawing(bar_width, 8)
    bar_d.add(Rect(0, 1, bar_width, 6, fillColor=colors.HexColor("#EFF6FF"),
                   strokeColor=None, rx=3, ry=3))
    if fill_w > 0:
        bar_d.add(Rect(0, 1, fill_w, 6, fillColor=_score_color(value, max_val),
                       strokeColor=None, rx=3, ry=3))

    lbl_p  = Paragraph(label, S_METRIC_LABEL)
    val_p  = Paragraph(
        f"<b>{value:.1f}</b><font color='#94A3B8'>/10</font>",
        ParagraphStyle("bv", parent=S_BODY, fontSize=8, alignment=TA_RIGHT),
    )
    t = Table([[lbl_p, bar_d, val_p]], colWidths=[105, bar_width + 6, 42])
    t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _radar_chart_drawing(
    labels: List[str], values: List[float], max_val: float = 10.0,
    width: float = 230, height: float = 200,
) -> Drawing:
    """Radar chart — properly centered with visible labels."""
    d = Drawing(width, height)
    chart = SpiderChart()

    # Generous padding so labels never clip
    pad_x, pad_y = 52, 42
    chart.x      = pad_x
    chart.y      = pad_y
    chart.width  = width  - pad_x * 2
    chart.height = height - pad_y * 2

    chart.labels = labels
    chart.data = [
        [2.0]  * len(labels),
        [4.0]  * len(labels),
        [6.0]  * len(labels),
        [8.0]  * len(labels),
        [10.0] * len(labels),
        values,
    ]

    # Scale rings
    for i in range(5):
        chart.strands[i].fillColor   = None
        chart.strands[i].strokeColor = colors.HexColor("#E2E8F0")
        chart.strands[i].strokeWidth = 0.5

    # Actual data strand
    chart.strands[5].fillColor   = colors.Color(0.145, 0.388, 0.922, 0.22)
    chart.strands[5].strokeColor = C_ACCENT
    chart.strands[5].strokeWidth = 2.0

    for i, _lbl in enumerate(labels):
        chart.spokes[i].strokeColor = C_BORDER
        chart.spokes[i].strokeWidth = 0.5
        try:
            chart.spokeLabels[i].fontName  = "Helvetica-Bold"
            chart.spokeLabels[i].fontSize  = 7.5
            chart.spokeLabels[i].fillColor = C_SECONDARY
        except Exception:
            pass

    d.add(chart)

    # Numerical scale labels along the top spoke
    cx     = chart.x + chart.width / 2
    cy     = chart.y + chart.height / 2
    radius = chart.height / 2
    for val in [2, 4, 6, 8, 10]:
        r = (val / 10.0) * radius
        s = String(cx + 3, cy + r - 3, str(val))
        s.fontName  = "Helvetica"
        s.fontSize  = 6.5
        s.fillColor = colors.HexColor("#94A3B8")
        d.add(s)

    return d


def _card(content_rows: list, col_widths: list, pad: int = PAD_INTERNAL) -> Table:
    """Universal card container — no fixed row heights to prevent clipping."""
    t = Table(content_rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, -1), C_CARD_BG),
        ("BOX",            (0, 0), (-1, -1), 0.6, C_BORDER),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",    (0, 0), (-1, -1), pad),
        ("RIGHTPADDING",   (0, 0), (-1, -1), pad),
        ("TOPPADDING",     (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), pad),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    return t


def _divider(usable_w: float) -> Table:
    """Thin horizontal rule."""
    t = Table([[""]], colWidths=[usable_w])
    t.setStyle(TableStyle([
        ("LINEABOVE",      (0, 0), (-1, 0), 0.5, C_BORDER),
        ("TOPPADDING",     (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 0),
        ("LEFTPADDING",    (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 0),
    ]))
    return t


# ═══════════════════════════════════════════════════════════════════════════
# SECTION BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def _build_cover_page(
    elements: list,
    usable_w: float,
    candidate_name: str,
    job_role: str,
    interview_type: str,
    interview_date: str,
    duration_min,
    total_q: int,
    overall_score: float,
    verdict_label: str,
    hiring_readiness: dict,
    avg_corr: float,
    avg_depth: float,
    avg_comm: float,
    avg_conf: float,
) -> None:
    """Build a compact, single-page cover section."""

    # ── Header ──────────────────────────────────────────────────────────────
    elements.append(Paragraph("Interview Assessment Report", S_TITLE))
    elements.append(Paragraph(
        f"Generated on {interview_date}  •  Confidential  •  CUDAS AI Platform",
        S_SUBTITLE,
    ))

    # ── Candidate Summary Card (horizontal, single row) ─────────────────────
    info_items = [
        ("Candidate", candidate_name),
        ("Interview Type", interview_type),
        ("Role",      job_role),
        ("Date",      interview_date),
        ("Duration",  f"{duration_min} min"),
        ("Questions", str(total_q)),
    ]
    n = len(info_items)
    col_w = usable_w / n

    label_row = [
        Paragraph(f"<b>{k}</b>", ParagraphStyle("ilbl", parent=S_METRIC_LABEL, alignment=TA_CENTER))
        for k, _ in info_items
    ]
    value_row = [
        Paragraph(v, ParagraphStyle("ival", parent=S_BODY, fontSize=9.5, alignment=TA_CENTER))
        for _, v in info_items
    ]
    info_t = Table([label_row, value_row], colWidths=[col_w] * n)
    info_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_CARD_BG),
        ("BOX",           (0, 0), (-1, -1), 0.6, C_BORDER),
        ("ROUNDEDCORNERS",[6, 6, 6, 6]),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    elements.append(info_t)
    elements.append(Spacer(1, GAP_CARD))

    # ── Performance Overview: Score + Verdict + Tier in one compact row ─────
    score_color   = _score_color(overall_score)
    verdict_color = _verdict_color(verdict_label)
    tier          = hiring_readiness.get("tier", hiring_readiness.get("level", "Developing"))
    tier_color    = _verdict_color(tier)

    def _perf_col(label: str, value: str, val_color: str) -> Table:
        inner = Table([
            [Paragraph(label, ParagraphStyle("plbl", parent=S_METRIC_LABEL, alignment=TA_CENTER))],
            [Paragraph(
                f'<font size="18" color="{val_color}"><b>{value}</b></font>',
                ParagraphStyle("pval", parent=S_BODY, alignment=TA_CENTER),
            )],
        ], colWidths=[(usable_w / 3) - PAD_INTERNAL * 2 - 8])
        inner.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ]))
        return inner

    perf_t = Table(
        [[
            _perf_col("OVERALL SCORE",  f"{_sf(overall_score)} / 10", score_color.hexval()),
            _perf_col("VERDICT",        verdict_label,                 verdict_color.hexval()),
            _perf_col("READINESS TIER", tier,                          tier_color.hexval()),
        ]],
        colWidths=[usable_w / 3] * 3,
    )
    perf_t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, -1), C_CARD_BG),
        ("BOX",            (0, 0), (-1, -1), 0.6, C_BORDER),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER",      (0, 0), (1, 0),   0.5, C_BORDER),
        ("LEFTPADDING",    (0, 0), (-1, -1), PAD_INTERNAL),
        ("RIGHTPADDING",   (0, 0), (-1, -1), PAD_INTERNAL),
        ("TOPPADDING",     (0, 0), (-1, -1), PAD_INTERNAL),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), PAD_INTERNAL),
    ]))
    elements.append(perf_t)
    elements.append(Spacer(1, GAP_CARD))

    # ── Radar + Score Breakdown (side by side) ──────────────────────────────
    half_w = usable_w / 2

    radar_labels = ["Technical", "Communication", "Problem Solving", "Confidence", "Depth", "Accuracy"]
    radar_values = [
        float(avg_corr), float(avg_comm), float(avg_depth),
        float(avg_conf), float(avg_depth), float(avg_corr),
    ]
    radar_d = _radar_chart_drawing(radar_labels, radar_values, width=half_w - PAD_INTERNAL * 2, height=195)

    bar_rows = [
        [_horizontal_bar_row("Technical Accuracy", float(avg_corr))],
        [_horizontal_bar_row("Problem Solving",    float(avg_depth))],
        [_horizontal_bar_row("Communication",      float(avg_comm))],
        [_horizontal_bar_row("Confidence",         float(avg_conf))],
    ]
    bars_t = Table(bar_rows, colWidths=[half_w - PAD_INTERNAL * 2])
    bars_t.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    combo = Table(
        [
            [
                Paragraph("COMPETENCY RADAR", S_METRIC_LABEL),
                Paragraph("SCORE BREAKDOWN",  S_METRIC_LABEL),
            ],
            [Spacer(1, 6), Spacer(1, 6)],
            [radar_d, bars_t],
        ],
        colWidths=[half_w, half_w],
    )
    combo.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, -1), C_CARD_BG),
        ("BOX",            (0, 0), (-1, -1), 0.6, C_BORDER),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("VALIGN",         (0, 2), (-1, 2),  "MIDDLE"),
        ("TOPPADDING",     (0, 0), (-1, -1), PAD_INTERNAL),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), PAD_INTERNAL),
        ("LEFTPADDING",    (0, 0), (-1, -1), PAD_INTERNAL),
        ("RIGHTPADDING",   (0, 0), (-1, -1), PAD_INTERNAL),
        ("LINEAFTER",      (0, 0), (0, -1),  0.5, C_BORDER),
    ]))
    elements.append(combo)


def _build_question_card(
    q: dict, idx: int, usable_w: float,
) -> list:
    """Build a compact question analysis card. Returns a list of flowables."""
    difficulty  = q.get("difficulty", "medium").lower()
    diff_colors = {"easy": C_SUCCESS, "hard": C_DANGER}
    diff_color  = diff_colors.get(difficulty, C_WARNING)
    correctness = q.get("correctness", 0)
    sc          = _score_color(float(correctness))

    card_w = usable_w - PAD_INTERNAL * 2

    # ── Header row ──────────────────────────────────────────────────────────
    header_t = Table(
    [[
        Paragraph(
            f"<b>Question {idx + 1}</b>",
            ParagraphStyle(
                "qtitle",
                parent=S_Q_TITLE,
                fontSize=10,
            ),
        ),

        Paragraph(
            f'<font color="{diff_color.hexval()}"><b>{difficulty.capitalize()}</b></font>',
            ParagraphStyle(
                "qdiff",
                parent=S_METRIC_LABEL,
                alignment=TA_CENTER,
                fontSize=8,
            ),
        ),

        Paragraph(
            f'<para align="right">'
            f'<font color="{sc.hexval()}" size="9"><b>{correctness}</b></font>'
            f'<font color="#94A3B8" size="8"> / 10</font>'
            f'</para>',
            ParagraphStyle(
                "qscore",
                parent=S_BODY,
                alignment=TA_RIGHT,
                leading=10,
            ),
        ),
    ]],

    # Give more width to score column
    colWidths=[
        card_w * 0.55,
        card_w * 0.15,
        card_w * 0.30,
    ],
)
    
    header_t.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

    ("LINEBELOW", (0, 0), (-1, 0), 0.5, C_BORDER),

    ("TOPPADDING", (0, 0), (-1, -1), 4),

    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),

    ("LEFTPADDING", (0, 0), (-1, -1), 2),

    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
]))

    card_rows = [[header_t], [Spacer(1, 8)]]

    # Question text
    card_rows.append([Paragraph(q.get("question", "N/A"), ParagraphStyle(
        "qt", parent=S_BODY, fontName="Helvetica-Bold", textColor=C_PRIMARY, fontSize=9.5,
    ))])
    card_rows.append([Spacer(1, 6)])

    # Candidate response
    ans = q.get("cleaned_answer", q.get("answer", "No response recorded."))
    # Truncate overly long answers to avoid layout overflow
    if isinstance(ans, str) and len(ans) > MAX_ANSWER_CHARS:
        ans = ans[:MAX_ANSWER_CHARS] + "..."
    if ans:
        card_rows.append([Paragraph("CANDIDATE RESPONSE", S_METRIC_LABEL)])
        card_rows.append([Paragraph(f'"{ans}"', S_BODY_ITALIC)])
        card_rows.append([Spacer(1, 6)])

        # Key Strength (only if non-empty)
        key_str = (q.get("key_strength") or "").strip()
        if key_str:
            card_rows.append([Paragraph(
                f'<font color="{C_SUCCESS.hexval()}">✓</font> Correct', S_METRIC_LABEL,
            )])
            card_rows.append([Paragraph(key_str, S_BODY)])
            card_rows.append([Spacer(1, 4)])

        # What Was Missing (only if non-empty)
        missing = (q.get("what_was_missing") or q.get("improvement_opportunity") or "").strip()
        if missing:
            card_rows.append([Paragraph(
                f'<font color="{C_WARNING.hexval()}">⚠</font> Missing Only', S_METRIC_LABEL,
            )])
            card_rows.append([Paragraph(missing, S_BODY)])
            card_rows.append([Spacer(1, 4)])

    q_card = _card(card_rows, col_widths=[card_w])
    # Allow the card to flow across pages if it exceeds a single page height
    return [q_card, Spacer(1, GAP_CARD)]


def _build_roadmap_card(item: dict, usable_w: float) -> KeepTogether:
    """Build a compact single roadmap card."""
    prio   = str(item.get("priority", "1"))
    topic  = item.get("topic", "")
    reason = item.get("reason", "")
    pplan  = item.get("practice_plan", "")
    effort = item.get("estimated_effort", "")

    try:
        prio_int = int(prio)
    except ValueError:
        prio_int = 2
    prio_c = C_DANGER if prio_int == 1 else (C_WARNING if prio_int == 2 else C_SUCCESS)
    prio_label = {1: "HIGH", 2: "MEDIUM", 3: "LOW"}.get(prio_int, "MEDIUM")

    card_w = usable_w - PAD_INTERNAL * 2
    rows = [
        [Paragraph(
            f'<font color="{prio_c.hexval()}"><b>{prio_label} PRIORITY</b></font>',
            S_PRIORITY_LABEL,
        )],
        [Paragraph(f"<b>{topic}</b>", ParagraphStyle("rt", parent=S_BODY, fontSize=10.5, textColor=C_PRIMARY))],
    ]
    if reason:
        rows += [
            [Spacer(1, 5)],
            [Paragraph("WHY IT MATTERS", S_METRIC_LABEL)],
            [Paragraph(reason, S_BODY_SM)],
        ]
    if pplan:
        rows += [
            [Spacer(1, 5)],
            [Paragraph("PRACTICE PLAN", S_METRIC_LABEL)],
            [Paragraph(pplan, S_BODY_SM)],
        ]
    if effort:
        rows += [
            [Spacer(1, 5)],
            [Paragraph(f"<b>Estimated Effort:</b>  {effort}", S_BODY_SM)],
        ]

    return KeepTogether(_card(rows, col_widths=[card_w], pad=PAD_INTERNAL))


# ═══════════════════════════════════════════════════════════════════════════
# MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def generate_report_pdf(
    report: Dict[str, Any],
    session_meta: Optional[Dict[str, Any]] = None,
) -> bytes:
    meta               = session_meta or {}
    summary            = report.get("summary", {})
    strengths          = report.get("strengths", [])
    questions          = report.get("questions", [])
    exec_summary       = report.get("executive_summary", "")
    comm_analysis      = report.get("communication_analysis", {})
    improvement_roadmap= report.get("improvement_roadmap", [])
    hiring_readiness   = report.get("hiring_readiness", {})
    interviewer_remarks= report.get("interviewer_remarks", "")
    proctoring_violations = report.get("proctoring_violations", [])
    verdict_label      = report.get("verdict_label", summary.get("verdict", ""))
    recommendations    = report.get("improvement_plan", [])

    overall_score = float(summary.get("overall_score", 0))
    avg_corr      = float(summary.get("average_correctness", 0))
    avg_depth     = float(summary.get("average_concept_depth", 0))
    avg_comm      = float(summary.get("average_communication", 0))
    avg_conf      = float(summary.get("average_confidence", 0))

    candidate_name = meta.get("candidate_name", "Candidate")
    job_role       = meta.get("job_role", "Software Developer")
    interview_date = meta.get("interview_date", datetime.now().strftime("%B %d, %Y"))
    duration_min   = meta.get("duration_minutes", "—")
    total_q        = len(questions) or meta.get("total_questions", 0)
    interview_type = meta.get("interview_type", "Role-Based Interview")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN + 12,
    )

    usable_w = PAGE_W - 2 * MARGIN
    elements: list = []

    # ───────────────────────────────────────────────────────────────────────
    # COVER PAGE
    # ───────────────────────────────────────────────────────────────────────
    _build_cover_page(
        elements, usable_w,
        candidate_name, job_role, interview_type, interview_date, duration_min, total_q,
        overall_score, verdict_label, hiring_readiness,
        avg_corr, avg_depth, avg_comm, avg_conf,
    )

    # ───────────────────────────────────────────────────────────────────────
    # EXECUTIVE SUMMARY & KEY STRENGTHS  (no forced page break — pack onto cover)
    # ───────────────────────────────────────────────────────────────────────
    elements.append(Paragraph("Executive Summary", S_SECTION))
    elements.append(Paragraph(exec_summary or "Detailed per-question analysis follows.", S_BODY))



    # Communication Analysis
    comm_text = comm_analysis.get("analysis_text", "")
    if comm_text:
        elements.append(Paragraph("Communication Analysis", ParagraphStyle(
            "ca", parent=S_SECTION, spaceBefore=12, spaceAfter=6,
        )))
        comm_metrics = [
            ("Clarity",             comm_analysis.get("clarity", avg_comm)),
            ("Confidence",          comm_analysis.get("confidence", avg_conf)),
            ("Technical Vocabulary",comm_analysis.get("technical_vocabulary", round((avg_corr + avg_depth) / 2, 2))),
        ]
        comm_rows = [[_horizontal_bar_row(lbl, float(val), bar_width=180)] for lbl, val in comm_metrics]
        comm_rows.append([Spacer(1, 4)])
        comm_rows.append([Paragraph(comm_text, S_BODY_SM)])
        elements.append(_card(comm_rows, col_widths=[usable_w - PAD_INTERNAL * 2]))

    # ───────────────────────────────────────────────────────────────────────
    # QUESTION ANALYSIS  (smart break — only if content won't fit)
    # ───────────────────────────────────────────────────────────────────────
    if questions:
        elements.append(Paragraph("Question-by-Question Analysis", S_SECTION))
        for idx, q in enumerate(questions):
            elements.extend(_build_question_card(q, idx, usable_w))

    # ───────────────────────────────────────────────────────────────────────
    # LEARNING ROADMAP
    # ───────────────────────────────────────────────────────────────────────
    if improvement_roadmap:
        elements.append(Paragraph("Learning Roadmap", S_SECTION))
        for item in improvement_roadmap[:3]:
            elements.append(_build_roadmap_card(item, usable_w))
            elements.append(Spacer(1, GAP_CARD))

    # ───────────────────────────────────────────────────────────────────────
    # HIRING READINESS (compact inline block)
    # ───────────────────────────────────────────────────────────────────────
    if hiring_readiness:
        tier   = hiring_readiness.get("tier", hiring_readiness.get("level", "Developing"))
        reason = hiring_readiness.get("reason", "")
        nxt    = hiring_readiness.get("next_milestone", "")
        hr_c   = _verdict_color(tier)

        hr_rows = [
            [Paragraph(
                f'<font color="{hr_c.hexval()}"><b>{tier}</b></font>  '
                f'<font color="#6B7280" size="9">Hiring Readiness Tier</font>',
                ParagraphStyle("hrtier", parent=S_BODY, fontSize=11),
            )],
        ]
        if reason:
            hr_rows += [[Spacer(1, 4)], [Paragraph(reason, S_BODY_SM)]]
        if nxt:
            hr_rows += [
                [Spacer(1, 4)],
                [Paragraph(f"<b>Next Milestone:</b>  {nxt}", S_BODY_SM)],
            ]
        elements.append(KeepTogether(_card(hr_rows, col_widths=[usable_w - PAD_INTERNAL * 2])))
        elements.append(Spacer(1, GAP_CARD))

    # ───────────────────────────────────────────────────────────────────────
    # IMPROVEMENT AREAS  (replaces Roadmap + Recommendations)
    # ───────────────────────────────────────────────────────────────────────
    # if recommendations:
    #     elements.append(Paragraph("Improvement Areas", S_SECTION))
    #     rec_rows = [
    #         [Paragraph(
    #             f'<font color="{C_WARNING.hexval()}">•</font>  {r}', S_BULLET,
    #         )]
    #         for r in recommendations[:5]
    #         if r and r.strip()
    #     ]
    #     if rec_rows:
    #         elements.append(KeepTogether(_card(rec_rows, col_widths=[usable_w - PAD_INTERNAL * 2])))
    #     elements.append(Spacer(1, GAP_CARD))

    # ───────────────────────────────────────────────────────────────────────
    # INTERVIEWER REMARKS
    # ───────────────────────────────────────────────────────────────────────
    if interviewer_remarks and interviewer_remarks.strip():
        elements.append(Paragraph("Interviewer Remarks", S_SECTION))
        elements.append(KeepTogether(_card(
            [[Paragraph(f'<i>"{interviewer_remarks}"</i>', S_BODY)]],
            col_widths=[usable_w - PAD_INTERNAL * 2],
        )))
        elements.append(Spacer(1, GAP_CARD))

    # ───────────────────────────────────────────────────────────────
    # PROCTORING SUMMARY
    # ───────────────────────────────────────────────────────────────
    if proctoring_violations:
        elements.append(Paragraph("Proctoring Summary", S_SECTION))
        rows = []
        for idx, violation in enumerate(proctoring_violations, start=1):
            if isinstance(violation, dict):
                violation_type = violation.get(
                    "type",
                    violation.get("violation", "Unknown"),
                )
                timestamp = violation.get("timestamp", "")
                count = violation.get("count", 1)
            else:
                violation_type = str(violation)
                timestamp = ""
                count = 1

            text = f"<b>{idx}.</b> {violation_type}"
            if count > 1:
                text += f" (Occurred {count} times)"
            if timestamp:
                text += f"<br/><font size='8' color='#6B7280'>{timestamp}</font>"

            rows.append([Paragraph(text, S_BODY)])

        elements.append(
            KeepTogether(
                _card(
                    rows,
                    col_widths=[usable_w - PAD_INTERNAL * 2],
                )
            )
        )
        elements.append(Spacer(1, GAP_CARD))

    # ───────────────────────────────────────────────────────────────────────
    # FOOTER
    # ───────────────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 18))
    elements.append(_divider(usable_w))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"CUDAS AI Interview Platform  •  {interview_date}  •  Confidential",
        S_FOOTER,
    ))

    doc.build(elements)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
