"""
Interview API routes.
All endpoints secured with JWT auth. Student ID extracted from token.
Updated with greeting handshake, interview history, and session detail.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.ai.agents.interview.schema import (
    EndInterviewRequest,
    EndInterviewResponse,
    GreetingRequest,
    GreetingResponse,
    InterviewConfigResponse,
    InterviewHistoryResponse,
    InterviewReportResponse,
    VisualizationReportResponse,
    InterviewSessionReportResponse,
    NextQuestionResponse,
    ProctoringViolationRequest,
    ProctoringViolationResponse,
    SessionDetailResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.api.ai.agents.interview.service import InterviewService
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.modes import normalize_interview_mode
from app.models.interview import InterviewSession, InterviewTurn
from app.agents.Interview.report.report_builder import build_report
from app.agents.Interview.report.pdf_generator import generate_report_pdf

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "AI interview router loaded"}


def _get_user_id(user) -> UUID:
    """Extract the user ID from the auth user (supports both ORM and dict)."""
    uid = user.id if hasattr(user, "id") else user.get("id")
    if uid is None:
        raise HTTPException(status_code=403, detail="Admin accounts cannot use interview")
    return uid


def _get_user_name(user) -> str:
    """Extract the user name from the auth user."""
    return user.name if hasattr(user, "name") else user.get("name", "Student")


# ── POST /interview/start ─────────────────────────────────────────────────

@router.post(
    "/start",
    response_model=StartInterviewResponse,
    summary="Start a new interview session",
)
async def start_interview(
    request: StartInterviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> StartInterviewResponse:
    """
    Create a new interview session and return the greeting.
    The greeting asks if the student is comfortable. No LLM call at this stage.
    """
    try:
        student_id = _get_user_id(current_user)
        student_name = _get_user_name(current_user)

        try:
            mode = normalize_interview_mode(getattr(request, "mode", None))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return await InterviewService.start_interview(
            student_id=student_id,
            student_name=student_name,
            job_role=request.job_role,
            db=db,
            mode=mode,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to start interview")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── POST /interview/greet ─────────────────────────────────────────────────

@router.post(
    "/greet",
    response_model=GreetingResponse,
    summary="Respond to the greeting handshake (Yes/No)",
)
async def respond_greeting(
    request: GreetingRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> GreetingResponse:
    """
    Handle the student's Yes/No response during the greeting handshake.
    Step 1: 'Are you comfortable?' → Yes → 'Can we start?'
    Step 2: 'Can we start?' → Yes → Generate first question
    Any 'No' → Close session.
    """
    try:
        student_id = _get_user_id(current_user)
        student_name = _get_user_name(current_user)

        return await InterviewService.respond_greeting(
            student_id=student_id,
            student_name=student_name,
            session_id=request.session_id,
            answer=request.answer,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to process greeting response")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── POST /interview/answer ────────────────────────────────────────────────

@router.post(
    "/answer",
    response_model=SubmitAnswerResponse,
    summary="Submit an answer to a question",
)
async def submit_answer(
    request: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SubmitAnswerResponse:
    """
    Submit the candidate's answer. The system evaluates it, classifies
    behavior, updates session memory, adjusts difficulty, and returns
    the next question or signals the end of the interview.
    """
    try:
        student_id = _get_user_id(current_user)
        return await InterviewService.submit_answer(
            student_id=student_id,
            session_id=request.session_id,
            question_id=request.question_id,
            answer_text=request.answer_text,
            audio_path=request.audio_path,
            db=db,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to submit answer")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── POST /interview/end ───────────────────────────────────────────────────

@router.post(
    "/end",
    response_model=EndInterviewResponse,
    summary="End the interview session",
)
async def end_interview(
    request: EndInterviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EndInterviewResponse:
    """
    End the active interview session and generate a comprehensive
    feedback report with behavior analysis.
    """
    try:
        student_id = _get_user_id(current_user)
        return await InterviewService.end_interview(
            student_id=student_id,
            session_id=request.session_id,
            ended_reason=request.ended_reason,
            db=db,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to end interview")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── GET /interview/report/{session_id} ────────────────────────────────────

@router.get(
    "/report/{session_id}",
    response_model=InterviewReportResponse,
    summary="Get the interview report",
)
async def get_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> InterviewReportResponse:
    """Retrieve the final interview report for a completed session."""
    logger.info("get_report endpoint called for session_id=%s", session_id)
    try:
        return await InterviewService.get_report(
            session_id=session_id,
            db=db,
        )
    except ValueError as exc:
        logger.warning("get_report failed: %s", exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to get report")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── GET /interview/{session_id}/report ────────────────────────────────────

@router.get(
    "/{session_id}/report",
    response_model=InterviewSessionReportResponse,
    summary="Get detailed interview report for history",
)
async def get_session_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> InterviewSessionReportResponse:
    """Retrieve a detailed report for a session (works for partial/failed sessions)."""
    try:
        student_id = _get_user_id(current_user)
        return await InterviewService.get_session_report(
            student_id=student_id,
            session_id=session_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to get session report")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── GET /interview/{session_id}/download ──────────────────────────────────

@router.get(
    "/{session_id}/download",
    summary="Download interview report as PDF",
)
async def get_session_report_pdf(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Fetch session data, build a structured report, and return it as a downloadable PDF.
    """
    try:
        student_id = _get_user_id(current_user)

        # 1. Fetch session to verify ownership and existence
        result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
                InterviewSession.student_id == student_id
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found.")

        # 2. Fetch all turns (questions and answers) for this session
        turns_result = await db.execute(
            select(InterviewTurn)
            .where(InterviewTurn.session_id == session_id)
            .order_by(InterviewTurn.timestamp.asc())
        )
        turns = turns_result.scalars().all()

        # 3. Prepare data for report_builder
        # build_report expects a list of dicts with 'question', 'answer', and 'evaluation'
        turn_dicts = []
        for t in turns:
            turn_dicts.append({
                "question": t.question,
                "answer": t.answer,
                "evaluation": t.evaluation if t.evaluation else {}
            })

        # 4. Generate structured report data
        report_dict = build_report(turn_dicts)

        # Calculate duration in minutes if end_time and start_time are available
        duration_minutes = "—"
        if session.end_time and session.start_time:
            duration_minutes = str(int(round((session.end_time - session.start_time).total_seconds() / 60)))
        elif session.start_time:
            now = datetime.now(session.start_time.tzinfo) if session.start_time.tzinfo else datetime.utcnow()
            duration_minutes = str(int(round((now - session.start_time).total_seconds() / 60)))

        session_meta = {
            "candidate_name": _get_user_name(current_user),
            "job_role": session.job_role,
            "interview_date": session.start_time.strftime("%B %d, %Y") if session.start_time else datetime.now().strftime("%B %d, %Y"),
            "duration_minutes": duration_minutes,
            "total_questions": len(turns),
        }

        # 5. Generate PDF bytes using ReportLab
        pdf_bytes = generate_report_pdf(report_dict, session_meta)

        # 6. Return as downloadable response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Interview_Report_{session_id.hex[:8]}.pdf"
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to generate PDF report")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── GET /interview/config ─────────────────────────────────────────────────

@router.get(
    "/config",
    response_model=InterviewConfigResponse,
    summary="Get interview configuration",
)
async def get_interview_config(
    current_user=Depends(get_current_user),
) -> InterviewConfigResponse:
    """Return client-side interview configuration (timeouts, max questions)."""
    return await InterviewService.get_config()


# ── GET /interview/history ────────────────────────────────────────────────

@router.get(
    "/history",
    response_model=InterviewHistoryResponse,
    summary="Get interview history for the logged-in student",
)
async def get_interview_history(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> InterviewHistoryResponse:
    """Fetch all past interview sessions for the current student."""
    try:
        student_id = _get_user_id(current_user)
        return await InterviewService.get_history(
            student_id=student_id,
            db=db,
        )
    except Exception as exc:
        logger.exception("Failed to get interview history")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── GET /interview/session/{session_id} ───────────────────────────────────

@router.get(
    "/session/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get session detail with questions and answers",
)
async def get_session_detail(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SessionDetailResponse:
    """Fetch questions and answers for a specific session. Only own sessions."""
    try:
        student_id = _get_user_id(current_user)
        return await InterviewService.get_session_detail(
            student_id=student_id,
            session_id=session_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to get session detail")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── POST /interview/upload-audio ──────────────────────────────────────────

@router.post(
    "/upload-audio",
    summary="Upload an audio recording",
)
async def upload_audio(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """Upload an audio file for server-side transcription (optional)."""
    import aiofiles
    from pathlib import Path
    from app.core.config import settings

    upload_dir = Path(settings.AUDIO_UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    import uuid as _uuid
    filename = f"{_uuid.uuid4().hex[:12]}_{file.filename}"
    filepath = upload_dir / filename

    async with aiofiles.open(filepath, "wb") as f:
        content = await file.read()
        await f.write(content)

    return {"audio_path": str(filepath), "filename": filename}


# ── DELETE /interview/session/{session_id} ────────────────────────────────

@router.delete(
    "/session/{session_id}",
    summary="Delete an interview session and its history",
)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete an interview session and all its related answers/scores."""
    try:
        student_id = _get_user_id(current_user)
        await InterviewService.delete_session(
            student_id=student_id,
            session_id=session_id,
            db=db,
        )
        return {"message": "Session deleted successfully"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to delete session")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── DELETE /interview/history/all ─────────────────────────────────────────

@router.delete(
    "/history/all",
    summary="Delete all interview sessions for the logged-in student",
)
async def delete_all_history(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete ALL interview sessions and related data for this student."""
    try:
        student_id = _get_user_id(current_user)
        count = await InterviewService.delete_all_sessions(
            student_id=student_id,
            db=db,
        )
        return {"message": f"Deleted {count} interview sessions"}
    except Exception as exc:
        logger.exception("Failed to delete all sessions")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── POST /interview/violation ─────────────────────────────────────────────

@router.post(
    "/violation",
    response_model=ProctoringViolationResponse,
    summary="Report a proctoring violation from the frontend detector",
)
async def report_violation(
    body: ProctoringViolationRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Log a proctoring violation detected by the browser-side detector agent."""
    try:
        from app.agents.Interview.sub_agents.detector_agent.agent import DetectorAgent

        detector = DetectorAgent(db)
        result = await detector.log_violation(
            session_id=body.session_id,
            violation_type=body.violation_type,
            message=body.message,
            severity=body.severity,
        )
        await db.commit()
        return ProctoringViolationResponse(**result)
    except Exception as exc:
        logger.exception("Failed to log proctoring violation")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── GET /interview/report/{session_id}/recruiter ──────────────────────────

@router.get(
    "/report/{session_id}/recruiter",
    summary="Get recruiter-facing AI interview report",
)
async def get_recruiter_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Fetch the recruiter-specific report with technical/communication/behavior scores."""
    try:
        return await InterviewService.get_recruiter_report(
            session_id=session_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to get recruiter report")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── GET /interview/report/{session_id}/student ────────────────────────────

@router.get(
    "/report/{session_id}/student",
    summary="Get student-facing AI interview report",
)
async def get_student_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Fetch the student-specific report with encouragement and learning resources."""
    try:
        return await InterviewService.get_student_report(
            session_id=session_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to get student report")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── GET /interview/report/{session_id}/visualization ─────────────────────

@router.get(
    "/report/{session_id}/visualization",
    response_model=VisualizationReportResponse,
    summary="Get visualization metrics (donut + radar) for an interview session",
)
async def get_visualization_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> VisualizationReportResponse:
    """Aggregate multi-question metrics for charts.

    Deterministic: uses stored per-turn evaluation payloads.
    """
    try:
        student_id = _get_user_id(current_user)
        data = await InterviewService.get_visualization_report(
            student_id=student_id,
            session_id=session_id,
            db=db,
        )
        return VisualizationReportResponse(**data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to get visualization report")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── GET /interview/report/pdf/{session_id} ─────────────────────────────

@router.get(
    "/report/pdf/{session_id}",
    summary="Download interview report as PDF",
)
async def get_report_pdf(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Fetch session data, build a structured report, and return it as a downloadable PDF.
    """
    try:
        student_id = _get_user_id(current_user)

        # 1. Fetch session to verify ownership and existence
        result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
                InterviewSession.student_id == student_id
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found.")

        # 2. Fetch all turns (questions and answers) for this session
        turns_result = await db.execute(
            select(InterviewTurn)
            .where(InterviewTurn.session_id == session_id)
            .order_by(InterviewTurn.timestamp.asc())
        )
        turns = turns_result.scalars().all()

        # 3. Prepare data for report_builder
        # build_report expects a list of dicts with 'question', 'answer', and 'evaluation'
        turn_dicts = []
        for t in turns:
            turn_dicts.append({
                "question": t.question,
                "answer": t.answer,
                "evaluation": t.evaluation if t.evaluation else {}
            })

        # 4. Generate structured report data
        report_dict = build_report(turn_dicts)

        # Calculate duration in minutes if end_time and start_time are available
        duration_minutes = "—"
        if session.end_time and session.start_time:
            duration_minutes = str(int(round((session.end_time - session.start_time).total_seconds() / 60)))
        elif session.start_time:
            now = datetime.now(session.start_time.tzinfo) if session.start_time.tzinfo else datetime.utcnow()
            duration_minutes = str(int(round((now - session.start_time).total_seconds() / 60)))

        session_meta = {
            "candidate_name": _get_user_name(current_user),
            "job_role": session.job_role,
            "interview_date": session.start_time.strftime("%B %d, %Y") if session.start_time else datetime.now().strftime("%B %d, %Y"),
            "duration_minutes": duration_minutes,
            "total_questions": len(turns),
        }

        # 5. Generate PDF bytes using ReportLab
        pdf_bytes = generate_report_pdf(report_dict, session_meta)

        # 6. Return as downloadable response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Interview_Report_{session_id.hex[:8]}.pdf"
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to generate PDF report")
        raise HTTPException(status_code=500, detail=str(exc)) from exc