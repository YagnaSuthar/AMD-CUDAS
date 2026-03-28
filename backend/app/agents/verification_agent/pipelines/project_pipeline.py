"""
Project verification pipeline.
Orchestrates GitHub scraping, validation, and AI-powered analysis.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


async def run_project_pipeline(
    *,
    db: AsyncSession,
    user_id: uuid.UUID | None,
    link: str | None,
    profile_data: dict[str, Any] | None,
    project_description: str | None = None,
    tech_stack: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str], list[str]]:
    from app.agents.verification_agent.validators.project_validator import verify_github_project
    from app.agents.verification_agent.validators.consistency_validator import validate_cross_profile_consistency
    from app.agents.verification_agent.ml_models.placeholder_fraud import fraud_score_placeholder

    issues: list[str] = []
    verified_fields: list[str] = []
    recommendations: list[str] = []

    print(f"\n[Verification Agent] ═══ PROJECT PIPELINE START ═══")
    print(f"[Verification Agent] User: {user_id}")
    print(f"[Verification Agent] Link: {link}")
    print(f"[Verification Agent] Description: {(project_description or 'N/A')[:60]}")
    print(f"[Verification Agent] Tech Stack: {tech_stack or 'N/A'}")

    extracted: dict[str, Any] = {
        "link": link,
        "project_description": project_description,
        "tech_stack": tech_stack,
    }

    # Run GitHub verification + scraping + AI analysis
    project_res = await verify_github_project(
        link=link,
        project_description=project_description,
        tech_stack=tech_stack,
    )
    issues.extend(project_res["issues"])

    # Merge scraped data into extracted
    scraped_data = project_res.get("scraped_data", {})
    extracted.update({
        "repo_name": scraped_data.get("repo_name"),
        "repo_description": scraped_data.get("description"),
        "readme_length": len(scraped_data.get("readme_content", "")),
        "languages": scraped_data.get("languages", []),
        "topics": scraped_data.get("topics", []),
        "stars": scraped_data.get("stars", 0),
        "forks": scraped_data.get("forks", 0),
        "file_count": len(scraped_data.get("file_names", [])),
        "complexity_level": scraped_data.get("complexity_level"),
        "internal_feedback": scraped_data.get("internal_feedback"),
        "student_feedback": scraped_data.get("student_feedback"),
        "description_match_score": scraped_data.get("description_match_score"),
        "tech_stack_match_score": scraped_data.get("tech_stack_match_score"),
    })

    # Cross-profile consistency
    consistency_res = await validate_cross_profile_consistency(extracted=extracted, profile_data=profile_data)
    issues.extend(consistency_res["issues"])

    # ML placeholder score
    ml_res = await fraud_score_placeholder(input_type="project", extracted=extracted)

    scores = {
        "format_score": project_res["format_score"],
        "metadata_score": project_res["metadata_score"],
        "source_score": project_res["source_score"],
        "consistency_score": consistency_res["score"],
        "ml_score": ml_res["score"],
    }

    verified_fields.extend(project_res.get("verified_fields", []))
    recommendations.extend(project_res.get("recommendations", []))

    print(f"\n[Verification Agent] ═══ PROJECT PIPELINE COMPLETE ═══")
    print(f"[Verification Agent] Scores: {scores}")
    print(f"[Verification Agent] Issues: {len(issues)}")
    print(f"[Verification Agent] Verified: {verified_fields}")

    return extracted, scores, issues, verified_fields, recommendations
