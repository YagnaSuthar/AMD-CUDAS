from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


async def run_profile_pipeline(
    *,
    db: AsyncSession,
    user_id: uuid.UUID | None,
    profile_data: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str], list[str]]:
    from app.agents.verification_agent.validators.profile_validator import validate_profile_data
    from app.agents.verification_agent.ml_models.placeholder_fraud import fraud_score_placeholder

    issues: list[str] = []
    verified_fields: list[str] = []
    recommendations: list[str] = []

    extracted = profile_data or {}

    profile_res = await validate_profile_data(profile_data=profile_data)
    issues.extend(profile_res["issues"])
    verified_fields.extend(profile_res.get("verified_fields", []))

    ml_res = await fraud_score_placeholder(input_type="profile", extracted=extracted)

    scores = {
        "format_score": profile_res["format_score"],
        "metadata_score": profile_res["metadata_score"],
        "source_score": profile_res["source_score"],
        "consistency_score": profile_res["consistency_score"],
        "ml_score": ml_res["score"],
    }

    recommendations.extend(profile_res.get("recommendations", []))

    return extracted, scores, issues, verified_fields, recommendations
