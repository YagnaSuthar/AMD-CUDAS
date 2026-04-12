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
) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str], list[str]]:
    from app.agents.verification_agent.validators.project_validator import verify_github_project
    from app.agents.verification_agent.validators.consistency_validator import validate_cross_profile_consistency
    from app.agents.verification_agent.ml_models.placeholder_fraud import fraud_score_placeholder

    issues: list[str] = []
    verified_fields: list[str] = []
    recommendations: list[str] = []

    extracted: dict[str, Any] = {"link": link}

    project_res = await verify_github_project(link=link)
    issues.extend(project_res["issues"])

    consistency_res = await validate_cross_profile_consistency(extracted=extracted, profile_data=profile_data)
    issues.extend(consistency_res["issues"])

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

    return extracted, scores, issues, verified_fields, recommendations
