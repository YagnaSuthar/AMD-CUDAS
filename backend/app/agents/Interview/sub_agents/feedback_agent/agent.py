"""
Feedback & Report Agent (Upgraded).
Generates DUAL reports:
  1. Student Report — friendly, developmental, with learning path
  2. Recruiter Report — professional, with STRONGLY_HIRE/SHOULD_HIRE/WEAK_HIRE/REJECT
"""

import json
import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.Interview.prompts import (
    FEEDBACK_REPORT_PROMPT,
    STUDENT_REPORT_PROMPT,
    RECRUITER_REPORT_PROMPT,
)
from app.agents.Interview.utils import parse_json_response
from app.models.interview import (
    Answer,
    AnswerScore,
    InterviewMemory,
    InterviewReport,
    InterviewSession,
    SessionStatus,
)

logger = logging.getLogger(__name__)


async def generate_report(
    session_id: UUID,
    db: AsyncSession,
    llm: Any,
    ended_reason: str = "normal",
) -> Dict[str, Any]:
    """
    Generate dual reports (student + recruiter) and persist to DB.

    Uses weighted scoring: final = 0.5*tech + 0.3*comm + 0.2*behavior
    """
    logger.info("FeedbackAgent: generating dual reports for session %s", session_id)

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

    # Count total questions
    from sqlalchemy import func
    from app.models.interview import Question
    q_count_result = await db.execute(
        select(func.count()).select_from(Question).where(Question.session_id == session_id)
    )
    total_questions = q_count_result.scalar() or 0

    # ── Compute weighted averages ─────────────────────────────────────────
    avg_technical: float = 0.5
    avg_communication: float = 0.5
    avg_behavior: float = 0.5
    behavior_counts: Dict[str, int] = {"polite": 0, "arrogant": 0, "neutral": 0}

    if scores:
        # Use new 0-1 scores if available, fallback to normalized integers
        tech_scores = []
        comm_scores = []
        behav_scores = []

        for s in scores:
            # Communication: use communication_score if available, else fallback to clarity/10
            if hasattr(s, 'communication_score') and s.communication_score is not None:
                comm_scores.append(float(s.communication_score))
            else:
                comm_scores.append(float(s.clarity) / 10.0)

            # Behavior: use behavior_score if available, else fallback to confidence/10
            if hasattr(s, 'behavior_score') and s.behavior_score is not None:
                behav_scores.append(float(s.behavior_score))
            else:
                behav_scores.append(float(s.confidence) / 10.0)

            # Technical can be 0-1 float or 0-10 int
            tech_val = float(s.technical_score)
            if tech_val > 1.0:
                tech_val = tech_val / 10.0
            tech_scores.append(tech_val)

            flag = s.behavior_flag if isinstance(s.behavior_flag, str) else s.behavior_flag.value
            behavior_counts[flag] = behavior_counts.get(flag, 0) + 1

        avg_technical = sum(tech_scores) / len(tech_scores)
        avg_communication = sum(comm_scores) / len(comm_scores)
        avg_behavior = sum(behav_scores) / len(behav_scores)

    # Weighted final score
    final_score = 0.5 * avg_technical + 0.3 * avg_communication + 0.2 * avg_behavior

    if ended_reason != "normal":
        final_score = 0.0
        avg_technical = 0.0
        avg_communication = 0.0
        avg_behavior = 0.0
        logger.warning(f"FeedbackAgent: Session {session_id} ended due to {ended_reason}. Zeroing scores.")
        weak_areas.append(f"CRITICAL: Failed proctoring validation. Reason: {ended_reason}")

    # Build behavior summary string
    behavior_summary_str = ", ".join(
        f"{k}: {v}" for k, v in behavior_counts.items() if v > 0
    ) or "No behavior data"
    
    if ended_reason != "normal":
        behavior_summary_str = f"PROCTORING VIOLATION: {ended_reason}. " + behavior_summary_str

    # Legacy score summary for backward compat prompt
    score_summary = (
        f"Technical: {avg_technical:.2f}/1.0, "
        f"Communication: {avg_communication:.2f}/1.0, "
        f"Behavior: {avg_behavior:.2f}/1.0, "
        f"Final Weighted: {final_score:.2f}/1.0 "
        f"({len(scores)} answers)"
    )

    # ── Generate Student Report ──────────────────────────────────────────
    student_report_data = {}
    try:
        student_prompt = STUDENT_REPORT_PROMPT.format(
            session_summary=session_summary,
            avg_technical=avg_technical,
            avg_communication=avg_communication,
            avg_behavior=avg_behavior,
            final_score=final_score,
            weak_areas=", ".join(weak_areas) if weak_areas else "None identified",
            strong_areas=", ".join(strong_areas) if strong_areas else "None identified",
            total_questions=total_questions,
        )
        response = await llm.ainvoke(student_prompt)
        content = getattr(response, "content", str(response))
        student_report_data = parse_json_response(content)
    except Exception as exc:
        logger.error("FeedbackAgent: Student report generation failed: %s", exc)
        student_report_data = {
            "weak_areas": weak_areas,
            "missing_skills": [],
            "improvements": ["Review the topics where you struggled."],
            "learning_path": [],
            "encouragement": "Keep practicing! Every interview is a learning opportunity.",
        }

    # ── Generate Recruiter Report ────────────────────────────────────────
    recruiter_report_data = {}
    try:
        recruiter_prompt = RECRUITER_REPORT_PROMPT.format(
            session_summary=session_summary,
            avg_technical=avg_technical,
            avg_communication=avg_communication,
            avg_behavior=avg_behavior,
            final_score=final_score,
            weak_areas=", ".join(weak_areas) if weak_areas else "None identified",
            strong_areas=", ".join(strong_areas) if strong_areas else "None identified",
            behavior_summary=behavior_summary_str,
            total_questions=total_questions,
            ended_reason=ended_reason,
        )
        response = await llm.ainvoke(recruiter_prompt)
        content = getattr(response, "content", str(response))
        recruiter_report_data = parse_json_response(content)
    except Exception as exc:
        logger.error("FeedbackAgent: Recruiter report generation failed: %s", exc)
        # Compute recommendation from score
        if final_score >= 0.8:
            rec = "STRONGLY_HIRE"
        elif final_score >= 0.6:
            rec = "SHOULD_HIRE"
        elif final_score >= 0.4:
            rec = "WEAK_HIRE"
        else:
            rec = "REJECT"
        recruiter_report_data = {
            "technical_assessment": f"Technical score: {avg_technical:.2f}",
            "communication_assessment": f"Communication score: {avg_communication:.2f}",
            "behavior_analysis": behavior_summary_str,
            "strengths": strong_areas,
            "weaknesses": weak_areas,
            "recommendation": rec,
            "justification": "Auto-generated based on scores.",
        }

    # ── Also generate legacy report via old prompt for backward compat ────
    recommendation = recruiter_report_data.get("recommendation", "REVIEW")
    justification = recruiter_report_data.get("justification", "")
    full_recommendation = f"{recommendation}: {justification}" if justification else recommendation
    strengths = recruiter_report_data.get("strengths", strong_areas)
    weaknesses = recruiter_report_data.get("weaknesses", weak_areas)

    # ── Persist report to DB ─────────────────────────────────────────────
    existing = await db.execute(
        select(InterviewReport).where(InterviewReport.session_id == session_id)
    )
    report = existing.scalar_one_or_none()

    if report is None:
        # Build kwargs with only columns that exist on the model
        report_kwargs = dict(
            session_id=session_id,
            final_score=final_score,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendation=full_recommendation,
        )
        # Only add optional columns if they exist on the model
        report_test = InterviewReport.__table__.columns
        if 'student_report' in report_test:
            report_kwargs['student_report'] = json.dumps(student_report_data)
        if 'recruiter_report' in report_test:
            report_kwargs['recruiter_report'] = json.dumps(recruiter_report_data)
        if 'behavior_analysis' in report_test:
            report_kwargs['behavior_analysis'] = behavior_summary_str
        report = InterviewReport(**report_kwargs)
        db.add(report)
    else:
        report.final_score = final_score
        report.strengths = strengths
        report.weaknesses = weaknesses
        report.recommendation = full_recommendation
        if hasattr(report, 'student_report'):
            report.student_report = json.dumps(student_report_data)
        if hasattr(report, 'recruiter_report'):
            report.recruiter_report = json.dumps(recruiter_report_data)
        if hasattr(report, 'behavior_analysis'):
            report.behavior_analysis = behavior_summary_str

    # ── Update session-level summary fields ──────────────────────────────
    sess_result = await db.execute(
        select(InterviewSession).where(InterviewSession.session_id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    if session:
        session.overall_score = final_score
        if hasattr(session, 'final_score'):
            session.final_score = final_score
        if hasattr(session, 'communication_score'):
            session.communication_score = avg_communication

    await db.flush()

    logger.info(
        "FeedbackAgent: dual reports saved for session %s (score=%.2f, rec=%s)",
        session_id, final_score, recommendation,
    )
    return {
        "final_score": final_score,
        "communication_score": avg_communication,
        "behavior_score": avg_behavior,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "behavior_summary": behavior_summary_str,
        "recommendation": full_recommendation,
        "student_report": student_report_data,
        "recruiter_report": recruiter_report_data,
    }
