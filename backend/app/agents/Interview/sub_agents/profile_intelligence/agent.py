"""
Profile Intelligence Agent.
Analyses a student's profile (resume, skills, portfolio) and produces
a structured profile summary for the interviewer and question generator.
Updated to also fetch from AuthUser for skills/resume data.
"""

import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.Interview.prompts import PROFILE_ANALYSIS_PROMPT
from app.agents.Interview.utils import parse_json_response
from app.models.interview import Skill, StudentProfile
from app.models.auth import AuthUser

logger = logging.getLogger(__name__)


async def analyze_profile(
    student_id: UUID,
    db: AsyncSession,
    llm: Any,
) -> Dict[str, Any]:
    """
    Fetch the student's profile + skills from the DB, then invoke the LLM
    to produce a structured profile analysis.
    Also fetches from AuthUser for skills and resume_url.

    Returns
    -------
    dict   {"skills": [...], "experience_level": str, "domains": [...],
            "has_projects": bool, "project_summary": str}
    """
    logger.info("ProfileIntelligenceAgent: analysing student %s", student_id)

    # ── Fetch from AuthUser (primary source for skills/resume) ──────────
    auth_result = await db.execute(
        select(AuthUser).where(AuthUser.id == student_id)
    )
    auth_user: AuthUser | None = auth_result.scalar_one_or_none()

    auth_skills: List[str] = []
    resume_url: str = ""
    if auth_user:
        auth_skills = auth_user.skills or []
        resume_url = auth_user.resume_url or ""

    # ── Fetch StudentProfile from interview tables ──────────────────────
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.student_id == student_id)
    )
    profile: StudentProfile | None = profile_result.scalar_one_or_none()

    # ── Fetch skills from interview Skill table ─────────────────────────
    skills_result = await db.execute(
        select(Skill).where(Skill.student_id == student_id)
    )
    skills: List[Skill] = list(skills_result.scalars().all())

    # Merge all skill sources
    all_skills = list(set(
        auth_skills
        + [s.skill_name for s in skills]
    ))

    if not all_skills and not profile:
        logger.warning("No profile found for student %s — returning defaults", student_id)
        return {
            "skills": [],
            "experience_level": "junior",
            "domains": ["general"],
            "has_projects": False,
            "project_summary": "",
        }

    # Build skills string for LLM
    skills_str = ", ".join(all_skills) if all_skills else "None listed"

    resume_text = ""
    portfolio_text = ""
    experience_years = 0

    if profile:
        resume_text = profile.resume_text or ""
        portfolio_text = profile.portfolio_text or ""
        experience_years = profile.experience_years

    # ── Build prompt & call LLM ──────────────────────────────────────────
    prompt = PROFILE_ANALYSIS_PROMPT.format(
        resume_text=resume_text or "Not provided",
        portfolio_text=portfolio_text or "Not provided",
        experience_years=experience_years,
        skills=skills_str,
    )

    try:
        response = await llm.ainvoke(prompt)
        content: str = getattr(response, "content", str(response))
        result = parse_json_response(content)
        logger.info("ProfileIntelligenceAgent: analysis complete for %s", student_id)

        # Merge LLM-extracted skills with DB skills
        llm_skills = result.get("skills", [])
        merged_skills = list(set(all_skills + llm_skills))

        has_projects = result.get("has_projects", bool(resume_text and "project" in resume_text.lower()))
        project_summary = result.get("project_summary", "")

        return {
            "skills": merged_skills,
            "experience_level": result.get("experience_level", "junior"),
            "domains": result.get("domains", ["general"]),
            "has_projects": has_projects,
            "project_summary": project_summary,
        }
    except Exception as exc:
        logger.error("ProfileIntelligenceAgent LLM error: %s", exc)
        # Fallback: return DB data directly
        has_projects = bool(resume_text and "project" in resume_text.lower())
        return {
            "skills": all_skills,
            "experience_level": (
                "senior" if experience_years >= 5
                else "mid" if experience_years >= 2
                else "junior"
            ),
            "domains": ["general"],
            "has_projects": has_projects,
            "project_summary": "",
        }
