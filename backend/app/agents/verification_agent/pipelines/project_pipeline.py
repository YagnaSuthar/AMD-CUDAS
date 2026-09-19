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
        "file_count": (scraped_data.get("repo_tree") or {}).get("total_files", 0),
        "branch": scraped_data.get("branch"),
        "analyzed_folder": scraped_data.get("sub_path"),
        "is_fork": scraped_data.get("is_fork", False),
        "fork_parent": scraped_data.get("fork_parent"),
        # Full folder-tree analysis (saved to projects.project_structure)
        "repo_tree": scraped_data.get("repo_tree"),
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
    if project_res.get("structure_score") is not None:
        scores["structure_score"] = project_res["structure_score"]
    if scraped_data.get("description_match_score") is not None:
        scores["description_match_score"] = scraped_data["description_match_score"]

    # GitHub could not be read at all — report "pending", do not judge the student
    if project_res.get("verification_unavailable"):
        scores["verification_unavailable"] = True
        verified_fields.extend(project_res.get("verified_fields", []))
        recommendations.extend(project_res.get("recommendations", []))
        return extracted, scores, issues, verified_fields, recommendations

    # ── Authorship gate ───────────────────────────────────────────────────
    # A polished repository proves nothing if the student never contributed to
    # it. Without commits (and without owning the repo) it cannot be "verified".
    contributors = scraped_data.get("contributors") or []
    user_found = bool((contribution_data.get("details") or {}).get("user_found"))
    user_commits = scraped_data.get("user_commits_count", 0) or len(scraped_data.get("user_commits_detail") or [])
    repo_owner = (scraped_data.get("repo_name") or "/").split("/")[0].lower()
    owns_repo = bool(github_username) and repo_owner == github_username.lower()

    if contributors and not user_found and not user_commits and not owns_repo:
        issues.append(
            f"No commits by '{github_username}' in this repository — "
            "the student does not appear to have contributed to it"
        )
        recommendations.append(
            "Submit a repository you contributed to, or set the GitHub username on your profile "
            "to the account you commit with"
        )
        scores["confidence_cap"] = 0.40
    elif not contributors and not user_commits and not owns_repo:
        issues.append(f"Could not confirm any commits by '{github_username}' in this repository")
        scores["confidence_cap"] = 0.54  # cannot reach "verified" without proof of authorship

    # Hard ceiling: without real, reachable source code a project can't be "verified"
    tree = scraped_data.get("repo_tree") or {}
    if (not scraped_data.get("exists")
            or not tree.get("scope_found", True)
            or tree.get("code_files", 1) == 0
            or tree.get("looks_like_template")):
        scores["confidence_cap"] = 0.45

    verified_fields.extend(project_res.get("verified_fields", []))
    recommendations.extend(project_res.get("recommendations", []))

    print(f"\n[Verification Agent] ═══ PROJECT PIPELINE COMPLETE ═══")
    print(f"[Verification Agent] Scores: {scores}")
    print(f"[Verification Agent] Issues: {len(issues)}")
    print(f"[Verification Agent] Verified: {verified_fields}")
    print(f"[Verification Agent] Contribution Score: {contribution_score:.2f}")

    return extracted, scores, issues, verified_fields, recommendations
