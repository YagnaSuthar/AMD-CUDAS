"""
Deterministic Feedback & Report Agent.
Generates structured reports solely from stored evaluation data.
NO LLM CALLS.
"""

import logging
import json
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import (
    InterviewReport,
    InterviewSession,
    InterviewTurn,
)
from app.agents.Interview.report.report_builder import build_report

logger = logging.getLogger(__name__)


async def generate_report(
    session_id: UUID,
    db: AsyncSession,
    llm: Any = None,  # Kept for signature compatibility but NOT USED
    ended_reason: str = "normal",
) -> Dict[str, Any]:
    """
    Generate a deterministic report from InterviewTurn data.
    NO LLM usage.
    """
    logger.info("FeedbackAgent: generating deterministic report for session %s", session_id)

    # 1. Fetch all turns (source of truth)
    turn_result = await db.execute(
        select(InterviewTurn)
        .where(InterviewTurn.session_id == session_id)
        .order_by(InterviewTurn.timestamp)
    )
    turns = list(turn_result.scalars().all())

    # 2. Build turn dicts for report_builder
    turn_dicts = []
    for t in turns:
        turn_dicts.append({
            "question": t.question or "",
            "answer": t.answer or "",
            "evaluation": t.evaluation or {}
        })

    # 3. Use deterministic builder
    report_dict = build_report(turn_dicts)

    # 4. Deterministic scoring from stored turns (source of truth)
    # Rule: report overall_score must equal average of per-turn scores.
    per_turn_scores: List[float] = []
    for t in turns:
        ev = t.evaluation if isinstance(t.evaluation, dict) else {}
        try:
            s = float(ev.get("overall_score", 0.0))
        except Exception:
            s = 0.0
        per_turn_scores.append(s)

    avg_score = round(sum(per_turn_scores) / len(per_turn_scores), 2) if per_turn_scores else 0.0
    report_dict.setdefault("summary", {})
    report_dict["summary"]["overall_score"] = avg_score
    report_dict["final_score"] = float(avg_score)

    # 5. Handle proctoring/ended reason (override score deterministically)
    # Only proctoring-related terminations should force score to 0.
    # User-driven termination or generic errors should still produce an average-based score.
    def _is_proctoring_reason(reason: str) -> bool:
        r = (reason or "").strip()
        if not r or r.lower() == "normal":
            return False

        # Frontend values
        proctor_values = {
            "TAB_SWITCH",
            "NO_FACE",
            "NO_FACE_TIMEOUT",
            "CAMERA_OFF",
            "MULTIPLE_FACES",
            "MULTIPLE_PEOPLE",
            "LOOKING_AWAY",
            "PHONE_DETECTED",
            "BOOK_DETECTED",
        }
        if r in proctor_values:
            return True

        # Backend/DetectorAgent values
        low = r.lower()
        if "proctor" in low or "violation" in low:
            return True

        return False

    if _is_proctoring_reason(ended_reason):
        report_dict["summary"]["overall_score"] = 0.0
        report_dict["final_score"] = 0.0
        report_dict["summary"]["verdict"] = "Failed (Proctoring Violation)"
        report_dict.setdefault("critical_issues", [])
        report_dict["critical_issues"].insert(
            0,
            f"Session terminated early due to proctoring violation: {ended_reason}",
        )

    # 5. Persist to DB for UI/Recruiter/Student consistency
    existing = await db.execute(
        select(InterviewReport).where(InterviewReport.session_id == session_id)
    )
    report = existing.scalar_one_or_none()

    # Prep structured data for storage
    # We store the same dict in both student and recruiter fields for now to ensure consistency,
    # or we can keep them distinct if needed, but the user requested consistency.
    structured_report_json = json.dumps(report_dict)

    if report is None:
        report = InterviewReport(
            session_id=session_id,
            final_score=report_dict["summary"]["overall_score"],
            strengths=report_dict["strengths"],
            weaknesses=report_dict["weaknesses"],
            recommendation=report_dict["summary"]["verdict"],
        )
        # Check for extended columns on model
        if hasattr(report, 'student_report'):
            report.student_report = structured_report_json
        if hasattr(report, 'recruiter_report'):
            report.recruiter_report = structured_report_json
        db.add(report)
    else:
        report.final_score = report_dict["summary"]["overall_score"]
        report.strengths = report_dict["strengths"]
        report.weaknesses = report_dict["weaknesses"]
        report.recommendation = report_dict["summary"]["verdict"]
        if hasattr(report, 'student_report'):
            report.student_report = structured_report_json
        if hasattr(report, 'recruiter_report'):
            report.recruiter_report = structured_report_json

    # Update session-level summary fields
    sess_result = await db.execute(
        select(InterviewSession).where(InterviewSession.session_id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    if session:
        session.overall_score = report_dict["summary"]["overall_score"]
        if hasattr(session, 'communication_score'):
            session.communication_score = report_dict["summary"]["average_communication"]

    await db.flush()
    logger.info("FeedbackAgent: deterministic report saved for session %s", session_id)

    return report_dict
