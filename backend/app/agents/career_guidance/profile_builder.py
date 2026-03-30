"""
Profile Builder for the Career Guidance Agent.

Constructs a structured user profile from the database,
including academic data, skills, certifications, projects,
interview history, and resume content.
"""

import logging
import os
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
        department, semester, average_percentage, subjects,
        projects, interview_history, resume_summary
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
            "description": getattr(c, "description", None),
            "is_verified": getattr(c, "is_verified", False),
        }
        for c in certificates
    ]

    # 4) Projects
    projects_list = await _fetch_projects(user_id, db)

    # 5) Interview history
    interview_history = await _fetch_interview_history(user_id, db)

    # 6) Resume summary
    resume_summary = await _fetch_resume_summary(user)

    # 7) Determine experience level from semester
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
        "projects": projects_list,
        "interview_history": interview_history,
        "resume_summary": resume_summary,
    }

    logger.info(
        "Built profile for user %s: %d skills, %d certs, %d projects, %d interviews, avg=%.1f%%",
        user_id, len(profile["skills"]), len(cert_list),
        len(projects_list), len(interview_history), average_percentage,
    )
    return profile


async def _fetch_projects(user_id: uuid.UUID, db: AsyncSession) -> list[dict[str, Any]]:
    """Fetch user's projects from the database."""
    try:
        from app.models.project import Project

        result = await db.execute(
            select(Project).where(Project.student_id == user_id)
        )
        projects = result.scalars().all()

        return [
            {
                "name": p.project_name,
                "description": p.description,
                "tech_stack": p.tech_stack,
                "github_url": p.github_url,
                "verification_status": p.verification_status or "pending",
            }
            for p in projects
        ]
    except Exception as e:
        logger.warning("Failed to fetch projects for user %s: %s", user_id, e)
        return []


async def _fetch_interview_history(
    user_id: uuid.UUID, db: AsyncSession
) -> list[dict[str, Any]]:
    """Fetch user's interview reports from the database."""
    try:
        from app.models.interview import InterviewReport, InterviewSession

        sessions_result = await db.execute(
            select(InterviewSession).where(InterviewSession.student_id == user_id)
        )
        sessions = sessions_result.scalars().all()
        if not sessions:
            return []

        session_ids = [s.session_id for s in sessions]

        reports_result = await db.execute(
            select(InterviewReport).where(
                InterviewReport.session_id.in_(session_ids)
            )
        )
        reports = reports_result.scalars().all()

        return [
            {
                "score": getattr(r, "final_score", None),
                "strengths": getattr(r, "strengths", None),
                "weaknesses": getattr(r, "weaknesses", None),
                "feedback": getattr(r, "overall_feedback", None),
            }
            for r in reports
        ]
    except Exception as e:
        logger.warning("Failed to fetch interview history for user %s: %s", user_id, e)
        return []


async def _fetch_resume_summary(user: AuthUser) -> str | None:
    """Try to extract a brief summary from the user's resume file."""
    resume_url = getattr(user, "resume_url", None)
    if not resume_url:
        return None

    try:
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        resume_path = os.path.join(base_dir, "resumes", os.path.basename(resume_url))

        if not os.path.exists(resume_path):
            resume_path = resume_url
        if not os.path.exists(resume_path):
            return None

        if resume_path.lower().endswith(".pdf"):
            from app.services.chunking_service import ChunkingService
            with open(resume_path, "rb") as f:
                text = ChunkingService.extract_text_from_pdf(f.read())
        else:
            with open(resume_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

        # Return first 500 chars as summary
        if text and text.strip():
            return text.strip()[:500]
        return None

    except Exception as e:
        logger.warning("Failed to read resume for user %s: %s", user.id, e)
        return None


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
        "projects": [],
        "interview_history": [],
        "resume_summary": None,
    }
