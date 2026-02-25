"""
Interview API routes.
All 5 endpoints call the InterviewService which orchestrates sub-agents.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai.agents.interview.schema import (
    EndInterviewRequest,
    EndInterviewResponse,
    InterviewReportResponse,
    NextQuestionRequest,
    NextQuestionResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.api.ai.agents.interview.service import InterviewService
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/start",
    response_model=StartInterviewResponse,
    summary="Start a new interview session",
)
async def start_interview(
    request: StartInterviewRequest,
    db: AsyncSession = Depends(get_db),
) -> StartInterviewResponse:
    """
    Create a new interview session, profile the student, and return the
    first dynamically-generated question.
    """
    try:
        return await InterviewService.start_interview(
            student_id=request.student_id,
            job_role=request.job_role,
            db=db,
        )
    except Exception as exc:
        logger.exception("Failed to start interview")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/next",
    response_model=NextQuestionResponse,
    summary="Get the next interview question",
)
async def next_question(
    request: NextQuestionRequest,
    db: AsyncSession = Depends(get_db),
) -> NextQuestionResponse:
    """
    Generate and return the next question based on session context
    and adaptive difficulty.
    """
    try:
        return await InterviewService.next_question(
            student_id=request.student_id,
            session_id=request.session_id,
            db=db,
        )
    except Exception as exc:
        logger.exception("Failed to get next question")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/answer",
    response_model=SubmitAnswerResponse,
    summary="Submit an answer to a question",
)
async def submit_answer(
    request: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
) -> SubmitAnswerResponse:
    """
    Submit the candidate's answer. The system evaluates it, updates
    session memory, adjusts difficulty, and returns the next question
    or signals the end of the interview.
    """
    try:
        return await InterviewService.submit_answer(
            student_id=request.student_id,
            session_id=request.session_id,
            question_id=request.question_id,
            answer_text=request.answer_text,
            audio_path=request.audio_path,
            db=db,
        )
    except Exception as exc:
        logger.exception("Failed to submit answer")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/end",
    response_model=EndInterviewResponse,
    summary="End the interview session",
)
async def end_interview(
    request: EndInterviewRequest,
    db: AsyncSession = Depends(get_db),
) -> EndInterviewResponse:
    """
    End the active interview session and generate a comprehensive
    feedback report.
    """
    try:
        return await InterviewService.end_interview(
            student_id=request.student_id,
            session_id=request.session_id,
            db=db,
        )
    except Exception as exc:
        logger.exception("Failed to end interview")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/report/{session_id}",
    response_model=InterviewReportResponse,
    summary="Get the interview report",
)
async def get_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> InterviewReportResponse:
    """
    Retrieve the final interview report for a completed session.
    """
    try:
        return await InterviewService.get_report(
            session_id=session_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to get report")
        raise HTTPException(status_code=500, detail=str(exc)) from exc