"""
Feedback & Report Agent.
Aggregates session data and generates a final interview report using the LLM.
"""

import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.Interview.prompts import FEEDBACK_REPORT_PROMPT
from app.agents.Interview.utils import parse_json_response
from app.models.interview import (
    Answer,
    AnswerScore,
    InterviewMemory,
    InterviewReport,
    InterviewSession,
)

logger = logging.getLogger(__name__)


async def generate_report(
    session_id: UUID,
    db: AsyncSession,
    llm: Any,
) -> Dict[str, Any]:
    """
    Aggregate all answer scores and memory, invoke LLM for a final report,
    and persist it in the DB.

    Returns
    -------
    dict   {"final_score": float, "strengths": [...], "weaknesses": [...], "recommendation": str}
    """
    logger.info("FeedbackAgent: generating report for session %s", session_id)

    # ── Fetch memory ─────────────────────────────────────────────────────
    mem_result = await db.execute(
        select(InterviewMemory).where(InterviewMemory.session_id == session_id)
    )
    memory: InterviewMemory | None = mem_result.scalar_one_or_none()
    session_summary = memory.summary if memory else "No session summary available."
    weak_areas: List[str] = list(memory.weak_areas) if memory and memory.weak_areas else []
    strong_areas: List[str] = list(memory.strong_areas) if memory and memory.strong_areas else []

    # ── Fetch all answer scores ──────────────────────────────────────────
    scores_result = await db.execute(
        select(AnswerScore)
        .join(Answer, AnswerScore.answer_id == Answer.answer_id)
        .where(Answer.session_id == session_id)
    )
    scores: List[AnswerScore] = list(scores_result.scalars().all())

    avg_overall: float = 0.0

    if scores:
        avg_clarity: float = sum(s.clarity for s in scores) / len(scores)
        avg_depth: float = sum(s.depth for s in scores) / len(scores)
        avg_confidence: float = sum(s.confidence for s in scores) / len(scores)
        avg_overall = float(sum(s.overall_score for s in scores) / len(scores))
        score_summary = (
            f"Average clarity: {avg_clarity:.1f}/10, "
            f"depth: {avg_depth:.1f}/10, "
            f"confidence: {avg_confidence:.1f}/10, "
            f"overall: {avg_overall:.1f}/10 "
            f"(across {len(scores)} answers)"
        )
    else:
        score_summary = "No scored answers available."

    # ── Build prompt & call LLM ──────────────────────────────────────────
    prompt = FEEDBACK_REPORT_PROMPT.format(
        session_summary=session_summary,
        score_summary=score_summary,
        weak_areas=", ".join(weak_areas) if weak_areas else "None identified",
        strong_areas=", ".join(strong_areas) if strong_areas else "None identified",
    )

    try:
        response = await llm.ainvoke(prompt)
        content: str = getattr(response, "content", str(response))
        result = parse_json_response(content)
        final_score = float(result.get("final_score", avg_overall))
        strengths = result.get("strengths", strong_areas)
        weaknesses = result.get("weaknesses", weak_areas)
        recommendation = result.get("recommendation", "Unable to determine")
    except Exception as exc:
        logger.error("FeedbackAgent LLM error: %s", exc)
        final_score = float(round(avg_overall, 2))
        strengths = strong_areas
        weaknesses = weak_areas
        recommendation = "Review manually — LLM evaluation unavailable."

    # ── Persist report to DB ─────────────────────────────────────────────
    existing = await db.execute(
        select(InterviewReport).where(InterviewReport.session_id == session_id)
    )
    report = existing.scalar_one_or_none()

    if report is None:
        report = InterviewReport(
            session_id=session_id,
            final_score=final_score,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendation=recommendation,
        )
        db.add(report)
    else:
        report.final_score = final_score
        report.strengths = strengths
        report.weaknesses = weaknesses
        report.recommendation = recommendation

    await db.flush()

    logger.info("FeedbackAgent: report saved for session %s (score=%.1f)", session_id, final_score)
    return {
        "final_score": final_score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendation": recommendation,
    }
