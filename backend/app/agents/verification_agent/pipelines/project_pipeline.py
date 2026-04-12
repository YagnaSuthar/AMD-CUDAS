"""
Project verification pipeline — Enhanced.
Orchestrates GitHub scraping, deep contributor analysis, validation, and AI-powered analysis.
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
    github_username: str | None = None,
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
    print(f"[Verification Agent] GitHub Username: {github_username or 'auto-detect'}")
    print(f"[Verification Agent] Description: {(project_description or 'N/A')[:60]}")
    print(f"[Verification Agent] Tech Stack: {tech_stack or 'N/A'}")

    extracted: dict[str, Any] = {
        "link": link,
        "project_description": project_description,
        "tech_stack": tech_stack,
        "github_username": github_username,
    }

    # Run GitHub verification + scraping + deep analysis
    project_res = await verify_github_project(
        link=link,
        project_description=project_description,
        tech_stack=tech_stack,
        github_username=github_username,
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
        # Deep analysis data
        "contributor_count": scraped_data.get("contributor_count", 0),
        "user_commits_count": scraped_data.get("user_commits_count", 0),
    })

    # Extract contribution analysis data
    contribution_data = project_res.get("contribution_data", {})
    if contribution_data:
        extracted["contribution_analysis"] = {
            "contribution_percentage": contribution_data.get("contribution_percentage", 0),
            "commit_count": contribution_data.get("commit_count", 0),
            "lines_added": contribution_data.get("lines_added", 0),
            "lines_deleted": contribution_data.get("lines_deleted", 0),
            "authenticity_score": contribution_data.get("contribution_authenticity_score", 0),
            "summary": contribution_data.get("contribution_summary", ""),
        }

    # Cross-profile consistency
    consistency_res = await validate_cross_profile_consistency(extracted=extracted, profile_data=profile_data)
    issues.extend(consistency_res["issues"])

    # ML placeholder score
    ml_res = await fraud_score_placeholder(input_type="project", extracted=extracted)

    # Build scores dict — now includes contribution_score
    contribution_score = contribution_data.get("contribution_authenticity_score", 0.5)

    scores = {
        "format_score": project_res["format_score"],
        "metadata_score": project_res["metadata_score"],
        "source_score": project_res["source_score"],
        "consistency_score": consistency_res["score"],
        "ml_score": ml_res["score"],
        "contribution_score": round(contribution_score, 4),
    }

    verified_fields.extend(project_res.get("verified_fields", []))
    recommendations.extend(project_res.get("recommendations", []))

    print(f"\n[Verification Agent] ═══ PROJECT PIPELINE COMPLETE ═══")
    print(f"[Verification Agent] Scores: {scores}")
    print(f"[Verification Agent] Issues: {len(issues)}")
    print(f"[Verification Agent] Verified: {verified_fields}")
    print(f"[Verification Agent] Contribution Score: {contribution_score:.2f}")

    return extracted, scores, issues, verified_fields, recommendations
