"""
Interview API routes.
All endpoints secured with JWT auth. Student ID extracted from token.
Updated with greeting handshake, interview history, and session detail.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai.agents.interview.schema import (
    EndInterviewRequest,
    EndInterviewResponse,
    GreetingRequest,
    GreetingResponse,
    InterviewConfigResponse,
    InterviewHistoryResponse,
    InterviewReportResponse,
    NextQuestionResponse,
    SessionDetailResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.api.ai.agents.interview.service import InterviewService
from app.core.database import get_db
from app.core.security import get_current_user

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

        return await InterviewService.start_interview(
            student_id=student_id,
            student_name=student_name,
            job_role=request.job_role,
            db=db,
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