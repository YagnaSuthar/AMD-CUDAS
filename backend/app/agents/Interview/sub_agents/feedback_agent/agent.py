"""
Deterministic Feedback & Report Agent (Upgraded with LLM refinement).
Generates structured reports from stored evaluation data, then refines
insights using an LLM while preserving deterministic scoring and metrics.
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
from .prompt import build_feedback_prompt

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

    # Fetch session with violations
    from sqlalchemy.orm import selectinload
    sess_result = await db.execute(
        select(InterviewSession)
        .options(selectinload(InterviewSession.violations))
        .where(InterviewSession.session_id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    proctoring_violations = session.proctoring_violations if session else []

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
        ev = t.evaluation or {}
        qm = ev.get("question_meta", {}) if isinstance(ev, dict) else {}
        turn_dicts.append({
            "question": t.question or "",
            "answer": t.answer or "",
            "evaluation": ev,
            "topic": qm.get("topic") or qm.get("concept") or t.phase or "Technical",
            "concept": qm.get("concept") or "",
            "difficulty": qm.get("difficulty") or t.difficulty or "medium",
            "phase": qm.get("phase") or t.phase or "core_technical",
            "project": qm.get("project") or "",
        })

    # 3. Use deterministic builder
    report_dict = build_report(turn_dicts, proctoring_violations)

    # 3.5. LLM Refinement Step (optional, non-blocking with timeout)
    if llm:
        try:
            import asyncio as _asyncio

            logger.info("FeedbackAgent: Refining report insights via LLM.")
            raw_json = json.dumps(report_dict, default=str)
            overall_score = report_dict.get("summary", {}).get("overall_score", 0.0)
            tier = report_dict.get("hiring_readiness", {}).get("tier", "Developing")
            prompt = build_feedback_prompt(raw_json, overall_score, tier)
            
            # Timeout after 2.0 seconds — fall back to deterministic report on slow LLM
            response = await _asyncio.wait_for(llm.ainvoke(prompt), timeout=2.0)
            content = getattr(response, "content", str(response))
            
            if "```" in content:
                import re
                m = re.search(r"```(?:\w*)\s*\n?(.*?)\n?\s*```", content, re.DOTALL)
                if m:
                    content = m.group(1).strip()
            
            first = content.find("{")
            last = content.rfind("}")
            if first != -1 and last != -1:
                content = content[first:last+1]
                
            refined_data = json.loads(content)
            
            # Apply refined insights
            if "executive_summary" in refined_data:
                report_dict["executive_summary"] = refined_data["executive_summary"]
            if "interviewer_remarks" in refined_data:
                report_dict["interviewer_remarks"] = refined_data["interviewer_remarks"]
            if "strengths" in refined_data and isinstance(refined_data["strengths"], list):
                report_dict["strengths"] = refined_data["strengths"]
                
            if "growth_areas" in refined_data and isinstance(refined_data["growth_areas"], list):
                report_dict["weaknesses"] = [ga.get("topic", "") for ga in refined_data["growth_areas"]]

            if "learning_roadmap" in refined_data and isinstance(refined_data["learning_roadmap"], list):
                report_dict["improvement_roadmap"] = refined_data["learning_roadmap"]
                
            if "hiring_readiness_explanation" in refined_data:
                hr_exp = refined_data["hiring_readiness_explanation"]
                if "hiring_readiness" in report_dict:
                    report_dict["hiring_readiness"]["reason"] = hr_exp.get("reason", "")
                    report_dict["hiring_readiness"]["next_milestone"] = hr_exp.get("next_milestone", "")
                    # For legacy compatibility
                    report_dict["hiring_readiness"]["recommendation_text"] = hr_exp.get("reason", "")

            if "recommendations" in refined_data and isinstance(refined_data["recommendations"], list):
                report_dict["improvement_plan"] = refined_data["recommendations"]

            if "questions" in refined_data and isinstance(refined_data["questions"], list):
                ref_q_map = {rq.get("question_text", ""): rq for rq in refined_data["questions"]}
                for q in report_dict.get("questions", []):
                    q_text = q.get("question", "")
                    if q_text in ref_q_map:
                        rq = ref_q_map[q_text]
                        if "key_strength" in rq:
                            q["key_strength"] = rq["key_strength"]
                        if "improvement_opportunity" in rq:
                            q["improvement_opportunity"] = rq["improvement_opportunity"]
                            
            logger.info("FeedbackAgent: Successfully refined report via LLM.")
        except Exception as e:
            logger.warning("FeedbackAgent: LLM refinement failed, falling back to deterministic report. Error: %s", e)

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

    # 4.5. Get proctoring summary from DetectorAgent
    try:
        from app.agents.Interview.sub_agents.detector_agent.agent import DetectorAgent
        detector = DetectorAgent(db)
        proctoring_summary = await detector.get_proctoring_summary(session_id)
        report_dict["proctoring_summary"] = proctoring_summary
    except Exception as exc:
        logger.warning("FeedbackAgent: Proctoring summary failed (non-fatal): %s", exc)
        report_dict["proctoring_summary"] = None

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
