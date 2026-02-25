"""
Profile Intelligence Agent.
Analyses a student's profile (resume, skills, portfolio) and produces
a structured profile summary for the interviewer and question generator.
"""

import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.Interview.prompts import PROFILE_ANALYSIS_PROMPT
from app.agents.Interview.utils import parse_json_response
from app.models.interview import Skill, StudentProfile

logger = logging.getLogger(__name__)


async def analyze_profile(
    student_id: UUID,
    db: AsyncSession,
    llm: Any,
) -> Dict[str, Any]:
    """
    Fetch the student's profile + skills from the DB, then invoke the LLM
    to produce a structured profile analysis.

    Returns
    -------
    dict   {"skills": [...], "experience_level": str, "domains": [...]}
    """
    logger.info("ProfileIntelligenceAgent: analysing student %s", student_id)

    # ── Fetch profile from DB ────────────────────────────────────────────
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.student_id == student_id)
    )
    profile: StudentProfile | None = profile_result.scalar_one_or_none()

    if profile is None:
        logger.warning("No profile found for student %s — returning defaults", student_id)
        return {
            "skills": [],
            "experience_level": "junior",
            "domains": ["general"],
        }

    # ── Fetch skills ─────────────────────────────────────────────────────
    skills_result = await db.execute(
        select(Skill).where(Skill.student_id == student_id)
    )
    skills: List[Skill] = list(skills_result.scalars().all())
    skills_str = ", ".join(f"{s.skill_name} ({s.skill_level})" for s in skills)

    # ── Build prompt & call LLM ──────────────────────────────────────────
    prompt = PROFILE_ANALYSIS_PROMPT.format(
        resume_text=profile.resume_text or "Not provided",
        portfolio_text=profile.portfolio_text or "Not provided",
        experience_years=profile.experience_years,
        skills=skills_str or "None listed",
    )

    try:
        response = await llm.ainvoke(prompt)
        content: str = getattr(response, "content", str(response))
        result = parse_json_response(content)
        logger.info("ProfileIntelligenceAgent: analysis complete for %s", student_id)
        return {
            "skills": result.get("skills", []),
            "experience_level": result.get("experience_level", "junior"),
            "domains": result.get("domains", ["general"]),
        }
    except Exception as exc:
        logger.error("ProfileIntelligenceAgent LLM error: %s", exc)
        return {
            "skills": [s.skill_name for s in skills],
            "experience_level": (
                "senior" if profile.experience_years >= 5
                else "mid" if profile.experience_years >= 2
                else "junior"
            ),
            "domains": ["general"],
        }
