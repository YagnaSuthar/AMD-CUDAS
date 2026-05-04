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
    llm: Any,  # Kept for signature compatibility but not used
) -> Dict[str, Any]:
    """
    Fetch stored profile intelligence from AuthUser.
    NO LLM call during interview.
    Returns deterministic, cached data extracted during resume upload.

    Returns
    -------
    dict   {"skills": [...], "experience_level": str, "domains": [...],
            "has_projects": bool, "project_summary": str}
    """
    logger.info("ProfileIntelligenceAgent: fetching stored profile for student %s", student_id)

    # ── Fetch from AuthUser (primary source for all profile data) ──────────
    auth_result = await db.execute(
        select(AuthUser).where(AuthUser.id == student_id)
    )
    auth_user: AuthUser | None = auth_result.scalar_one_or_none()

    if not auth_user:
        logger.warning("AuthUser not found for student %s — returning defaults", student_id)
        return {
            "skills": [],
            "projects": [],
            "experience_level": "junior",
            "domains": ["general"],
            "has_projects": False,
            "project_summary": "",
        }

    # Extract stored intelligence from AuthUser
    skills = auth_user.skills or []
    projects = auth_user.projects or []
    project_summary = auth_user.project_summary or ""
    resume_text = auth_user.resume_text or ""

    # Determine experience level from resume text (simple heuristic)
    experience_years = 0
    if resume_text:
        import re
        # Look for patterns like "5 years", "3+ years", etc.
        year_matches = re.findall(r'(\d+)\+?\s*years?', resume_text.lower())
        if year_matches:
            try:
                experience_years = max(int(m) for m in year_matches)
            except ValueError:
                pass

    experience_level = (
        "senior" if experience_years >= 5
        else "mid" if experience_years >= 2
        else "junior"
    )

    # Determine domains from skills (simple mapping)
    domains = set(["general"])
    skill_lower = " ".join(skills).lower()
    if any(k in skill_lower for k in ["python", "java", "javascript", "react", "node", "angular"]):
        domains.add("software")
    if any(k in skill_lower for k in ["ml", "machine learning", "tensorflow", "pytorch", "ai"]):
        domains.add("ai/ml")
    if any(k in skill_lower for k in ["aws", "azure", "gcp", "docker", "kubernetes"]):
        domains.add("cloud")
    if any(k in skill_lower for k in ["sql", "mongodb", "postgresql", "mysql"]):
        domains.add("data")

    has_projects = bool(projects) or bool(project_summary)

    logger.info(
        "ProfileIntelligenceAgent: retrieved stored profile for %s — %d skills, %d projects, level=%s",
        student_id, len(skills), len(projects), experience_level
    )

    return {
        "skills": skills,
        "projects": projects,
        "experience_level": experience_level,
        "domains": list(domains),
        "has_projects": has_projects,
        "project_summary": project_summary,
    }
