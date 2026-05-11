import logging
from datetime import datetime
from io import BytesIO
from uuid import UUID

from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai.agents.aptitude.schema import (
    AptitudeQuestionResponse,
    AptitudeReportResponse,
    StartAptitudeRequest,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.api.ai.agents.aptitude.service import AptitudeService
from app.core.database import get_db
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_user_id(user) -> str:
    uid = user.id if hasattr(user, "id") else user.get("id")
    if uid is None:
        raise HTTPException(status_code=403, detail="Admin accounts cannot use aptitude")
    return str(uid)


@router.get("/health")
async def health():
    return {"status": "AI aptitude router loaded"}


@router.post("/start", response_model=AptitudeQuestionResponse)
async def start_aptitude(
    body: StartAptitudeRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AptitudeQuestionResponse:
    user_id = _get_user_id(current_user)
    return await AptitudeService.start_session(
        user_id=user_id,
        total_questions=body.total_questions,
        category=body.category,
        db=db,
    )


@router.get("/next", response_model=AptitudeQuestionResponse)
async def next_question(
    session_id: UUID,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AptitudeQuestionResponse:
    user_id = _get_user_id(current_user)
    return await AptitudeService.get_next_question(session_id=session_id, user_id=user_id, db=db, category=category)


@router.post("/answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    body: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SubmitAnswerResponse:
    user_id = _get_user_id(current_user)
    return await AptitudeService.submit_answer(
        session_id=body.session_id,
        user_id=user_id,
        question_id=body.question_id,
        selected_option=body.selected_option,
        time_taken=body.time_taken,
        db=db,
    )


@router.get("/report/{session_id}", response_model=AptitudeReportResponse)
async def report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AptitudeReportResponse:
    user_id = _get_user_id(current_user)
    return await AptitudeService.get_report(session_id=session_id, user_id=user_id, db=db)


@router.get("/report/{session_id}/download")
async def download_report_pdf(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = _get_user_id(current_user)
    report_data = await AptitudeService.get_report(session_id=session_id, user_id=user_id, db=db)

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:
        logger.exception("reportlab is not available")
        raise HTTPException(status_code=500, detail=f"PDF generation library not available: {exc}") from exc

    student_name = None
    for key in ("name", "full_name", "username", "email"):
        if hasattr(current_user, key):
            student_name = getattr(current_user, key)
            break
        if isinstance(current_user, dict) and current_user.get(key):
            student_name = current_user.get(key)
            break

    def _p(text: str) -> str:
        return escape(str(text or "")).replace("\n", "<br/>")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="Aptitude Test Report",
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="SmallMuted",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.grey,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeader",
            parent=styles["Heading2"],
            spaceBefore=6,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="QuestionText",
            parent=styles["BodyText"],
            fontSize=11,
            leading=14,
            spaceAfter=4,
        )
    )
    story = []

    title_style = styles["Title"]
    title_style.alignment = 1
    title_style.fontSize = 22
    title_style.leading = 26

    story.append(Paragraph("<b>Aptitude Test Report</b>", title_style))
    story.append(Spacer(1, 6))

    if student_name:
        story.append(Paragraph(f"<b>User:</b> {_p(student_name)}", styles["Normal"]))
    story.append(Paragraph(f"<b>Date:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey, spaceBefore=6, spaceAfter=12))

    score = report_data.get("score", 0)
    accuracy = report_data.get("accuracy", report_data.get("accuracy_percent", 0.0))
    attempted = report_data.get("attempted", 0)
    total = report_data.get("total", report_data.get("total_questions", 0))

    story.append(Paragraph("Summary", styles["SectionHeader"]))
    summary_table = Table(
        [
            ["Score", f"{score} / {total}"],
            ["Accuracy", f"{accuracy}%"],
            ["Attempted", f"{attempted} / {total}"],
        ],
        colWidths=[120, 360],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey, spaceBefore=6, spaceAfter=12))

    story.append(Paragraph("Category Breakdown", styles["SectionHeader"]))
    breakdown = report_data.get("category_breakdown") or {}
    rows = [["Category", "Attempted", "Correct", "Accuracy"]]
    for cat, vals in breakdown.items():
        rows.append(
            [
                str(cat),
                str(vals.get("attempted", 0)),
                str(vals.get("correct", 0)),
                f"{vals.get('accuracy_percent', 0.0)}%",
            ]
        )
    breakdown_table = Table(rows, colWidths=[180, 100, 100, 100])
    breakdown_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]
        )
    )
    story.append(breakdown_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey, spaceBefore=6, spaceAfter=12))

    story.append(Paragraph("Question Analysis", styles["SectionHeader"]))
    story.append(Paragraph("Detailed review of each attempted question.", styles["SmallMuted"]))
    story.append(Spacer(1, 6))
    attempts = report_data.get("attempts") or []
    for idx, a in enumerate(attempts, start=1):
        q_text = _p(a.get("question", ""))
        your_answer = _p(a.get("your_answer", ""))
        correct_answer = _p(a.get("correct_answer", ""))
        explanation = a.get("explanation")
        is_correct = bool(a.get("is_correct", False))

        verdict = "Correct" if is_correct else "Incorrect"
        verdict_color = colors.HexColor("#1f7a34") if is_correct else colors.HexColor("#b00020")
        prefix = "✓" if is_correct else "✗"

        story.append(Paragraph(f"<b>{prefix} Q{idx}</b>", styles["Heading3"]))
        story.append(Paragraph(q_text or "-", styles["QuestionText"]))

        qa_table = Table(
            [
                ["Your Answer", your_answer or "-"],
                ["Correct Answer", correct_answer or "-"],
                ["Status", verdict],
            ],
            colWidths=[110, 370],
        )
        qa_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                    ("TEXTCOLOR", (1, 2), (1, 2), verdict_color),
                    ("FONTNAME", (1, 2), (1, 2), "Helvetica-Bold"),
                ]
            )
        )
        story.append(qa_table)

        if explanation:
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Explanation</b><br/>{_p(explanation)}", styles["BodyText"]))

        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceBefore=2, spaceAfter=10))

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=aptitude_report.pdf"},
    )
