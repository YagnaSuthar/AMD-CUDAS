"""
Profile Builder for the Career Guidance Agent.

Constructs a structured user profile from the database,
including academic data, skills, certifications, and resume content.
"""

import logging
import uuid
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import AuthUser, Certificate, InternalMarks

logger = logging.getLogger(__name__)


async def build_user_profile(
    user_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Build a structured career-guidance profile for the user.

    Returns
    -------
    dict with keys:
        skills, experience_level, education, goals, certifications,
        department, semester, average_percentage, subjects
    """
    # 1) Fetch user record
    result = await db.execute(select(AuthUser).where(AuthUser.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("build_user_profile: user %s not found", user_id)
        return _empty_profile()

    # 2) Academic data
    marks_result = await db.execute(
        select(InternalMarks).where(InternalMarks.student_id == user_id)
    )
    marks = marks_result.scalars().all()

    subjects: list[dict[str, Any]] = []
    total_obtained = 0
    total_max = 0
    for m in marks:
        pct = round(m.marks_obtained / m.max_marks * 100, 2) if m.max_marks else 0
        subjects.append({"name": m.subject_name, "percentage": pct, "semester": m.semester})
        total_obtained += m.marks_obtained
        total_max += m.max_marks

    average_percentage = round(total_obtained / total_max * 100, 2) if total_max else 0.0

    # 3) Certificates
    cert_result = await db.execute(
        select(Certificate).where(Certificate.student_id == user_id)
    )
    certificates = cert_result.scalars().all()
    cert_list = [
        {
            "title": c.title,
            "issuer": getattr(c, "issuer", None),
            "points": c.points,
        }
        for c in certificates
    ]

    # 4) Determine experience level from semester
    semester = user.semester or 0
    if semester <= 2:
        experience_level = "beginner"
    elif semester <= 5:
        experience_level = "intermediate"
    else:
        experience_level = "advanced"

    profile = {
        "skills": user.skills or [],
        "experience_level": experience_level,
        "education": {
            "department": user.department or "Not specified",
            "semester": semester,
            "average_percentage": average_percentage,
        },
        "goals": [user.goal] if user.goal else [],
        "certifications": cert_list,
        "subjects": subjects,
        "resume_url": user.resume_url if hasattr(user, "resume_url") else None,
    }

    logger.info("Built profile for user %s: %d skills, %d certs, avg=%.1f%%",
                 user_id, len(profile["skills"]), len(cert_list), average_percentage)
    return profile


def _empty_profile() -> dict[str, Any]:
    """Return an empty profile dict for missing users."""
    return {
        "skills": [],
        "experience_level": "unknown",
        "education": {"department": "Unknown", "semester": 0, "average_percentage": 0},
        "goals": [],
        "certifications": [],
        "subjects": [],
        "resume_url": None,
    }
