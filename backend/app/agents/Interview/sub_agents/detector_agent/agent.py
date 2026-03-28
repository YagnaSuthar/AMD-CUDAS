"""
Detector Agent — Proctoring Security Sub-Agent.

Handles interview proctoring by:
1. Receiving violation reports from the frontend (browser-side TF.js models)
2. Logging violations to the database per session
3. Evaluating severity and deciding if the interview should auto-terminate
4. Providing a proctoring summary for the final interview report

Violation Types:
- NO_FACE: Candidate face not visible for extended period
- MULTIPLE_FACES: More than one face detected in frame
- LOOKING_AWAY: Candidate not looking at camera
- PHONE_DETECTED: Mobile phone detected via COCO-SSD
- BOOK_DETECTED: Book/notes detected
- MULTIPLE_PEOPLE: Multiple people in frame
- TAB_SWITCH: Browser tab switch detected
- CAMERA_OFF: Camera turned off or disconnected

Security Levels:
- WARNING: Non-critical, logged but interview continues
- VIOLATION: Critical, may auto-terminate interview
- AUTO_END: Immediate termination triggered
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Violation Severity Classification ─────────────────────────────────────

CRITICAL_VIOLATIONS = {
    "PHONE_DETECTED",
    "MULTIPLE_PEOPLE",
    "NO_FACE_TIMEOUT",
    "CAMERA_OFF",
}

WARNING_VIOLATIONS = {
    "NO_FACE",
    "MULTIPLE_FACES",
    "LOOKING_AWAY",
    "BOOK_DETECTED",
    "TAB_SWITCH",
}

# Maximum warnings before auto-end
MAX_WARNINGS_BEFORE_END = 5
# Maximum critical violations (immediate end on first)
MAX_CRITICAL_BEFORE_END = 1


class DetectorAgent:
    """
    Proctoring detector sub-agent.

    Tracks violations per session and provides:
    - Violation logging with timestamps
    - Severity assessment
    - Auto-termination decision
    - Proctoring summary generation for reports
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_violation(
        self,
        session_id: UUID,
        violation_type: str,
        message: str,
        severity: str = "warning",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Log a proctoring violation for a session.

        Returns:
            {
                "logged": True,
                "should_end": bool,  — whether interview should auto-terminate
                "reason": str,       — reason if should_end is True
                "warning_count": int,
                "violation_count": int,
            }
        """
        from app.models.interview import InterviewSession, ProctoringViolation

        # Verify session exists and is active
        sess_result = await self.db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
            )
        )
        session = sess_result.scalar_one_or_none()
        if not session:
            logger.warning("DetectorAgent: session %s not found", session_id)
            return {"logged": False, "should_end": False, "reason": "Session not found"}

        # Create violation record
        violation = ProctoringViolation(
            session_id=session_id,
            violation_type=violation_type,
            message=message,
            severity=severity,
            metadata_json=metadata or {},
            detected_at=datetime.utcnow(),
        )
        self.db.add(violation)
        await self.db.flush()

        logger.info(
            "DetectorAgent: logged violation [%s] severity=%s for session %s: %s",
            violation_type, severity, session_id, message,
        )

        # Count total violations for this session
        all_violations = await self._get_session_violations(session_id)
        warning_count = sum(1 for v in all_violations if v.severity == "warning")
        critical_count = sum(1 for v in all_violations if v.severity == "critical")

        # Determine if interview should auto-end
        should_end = False
        end_reason = ""

        if violation_type in CRITICAL_VIOLATIONS:
            should_end = True
            end_reason = f"Critical violation: {violation_type}"
        elif warning_count >= MAX_WARNINGS_BEFORE_END:
            should_end = True
            end_reason = f"Too many warnings ({warning_count})"

        if should_end:
            logger.warning(
                "DetectorAgent: auto-ending session %s — %s",
                session_id, end_reason,
            )

        return {
            "logged": True,
            "should_end": should_end,
            "reason": end_reason,
            "warning_count": warning_count,
            "violation_count": critical_count,
        }

    async def get_proctoring_summary(
        self,
        session_id: UUID,
    ) -> Dict[str, Any]:
        """
        Generate a proctoring summary for the interview report.

        Returns a summary dict with:
        - total_violations: int
        - violation_breakdown: dict of type -> count
        - integrity_score: float (0-1, 1 = clean)
        - flags: list of notable issues
        - summary: str — human-readable summary
        """
        violations = await self._get_session_violations(session_id)

        if not violations:
            return {
                "total_violations": 0,
                "violation_breakdown": {},
                "integrity_score": 1.0,
                "flags": [],
                "summary": "No proctoring violations detected. Clean session.",
            }

        # Build breakdown
        breakdown = {}
        for v in violations:
            breakdown[v.violation_type] = breakdown.get(v.violation_type, 0) + 1

        total = len(violations)
        critical_count = sum(1 for v in violations if v.severity == "critical")
        warning_count = sum(1 for v in violations if v.severity == "warning")

        # Calculate integrity score (1.0 = clean, 0.0 = heavily flagged)
        # Each critical violation costs 0.3, each warning costs 0.08
        penalty = (critical_count * 0.3) + (warning_count * 0.08)
        integrity_score = max(0.0, 1.0 - penalty)

        # Build flags
        flags = []
        if "PHONE_DETECTED" in breakdown:
            flags.append("📱 Phone was detected during the interview")
        if "MULTIPLE_PEOPLE" in breakdown:
            flags.append("👥 Multiple people were detected in frame")
        if "NO_FACE" in breakdown:
            flags.append(f"👤 Face was not visible {breakdown['NO_FACE']} time(s)")
        if "LOOKING_AWAY" in breakdown:
            flags.append(f"👀 Candidate looked away {breakdown['LOOKING_AWAY']} time(s)")
        if "TAB_SWITCH" in breakdown:
            flags.append(f"🖥️ Tab switched {breakdown['TAB_SWITCH']} time(s)")
        if "BOOK_DETECTED" in breakdown:
            flags.append("📖 Book/notes were detected")

        # Human-readable summary
        if critical_count > 0:
            summary = f"⚠️ {critical_count} critical violation(s) and {warning_count} warning(s) detected. Integrity score: {integrity_score:.0%}."
        elif warning_count > 3:
            summary = f"Multiple warnings ({warning_count}) detected during the session. Integrity score: {integrity_score:.0%}."
        else:
            summary = f"{total} minor issue(s) detected. Integrity score: {integrity_score:.0%}. Generally clean session."

        return {
            "total_violations": total,
            "violation_breakdown": breakdown,
            "integrity_score": round(integrity_score, 2),
            "flags": flags,
            "summary": summary,
        }

    async def _get_session_violations(self, session_id: UUID) -> list:
        """Fetch all proctoring violations for a session."""
        from app.models.interview import ProctoringViolation

        result = await self.db.execute(
            select(ProctoringViolation)
            .where(ProctoringViolation.session_id == session_id)
            .order_by(ProctoringViolation.detected_at.asc())
        )
        return list(result.scalars().all())
