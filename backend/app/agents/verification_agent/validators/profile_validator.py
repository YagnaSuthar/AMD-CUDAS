from __future__ import annotations

from typing import Any


async def validate_profile_data(*, profile_data: dict[str, Any] | None) -> dict[str, Any]:
    if not profile_data:
        return {
            "format_score": 0.0,
            "metadata_score": 0.0,
            "source_score": 0.0,
            "consistency_score": 0.0,
            "issues": ["No profile_data provided"],
            "verified_fields": [],
            "recommendations": ["Send structured profile data"],
        }

    issues: list[str] = []
    verified_fields: list[str] = []

    required = ["name", "email"]
    present = [k for k in required if profile_data.get(k)]

    format_score = len(present) / len(required)
    if format_score < 1.0:
        issues.append("Missing basic profile fields")

    metadata_score = 0.6
    source_score = 0.4
    consistency_score = 0.6

    verified_fields.extend(present)

    return {
        "format_score": round(format_score, 4),
        "metadata_score": round(metadata_score, 4),
        "source_score": round(source_score, 4),
        "consistency_score": round(consistency_score, 4),
        "issues": issues,
        "verified_fields": verified_fields,
        "recommendations": ["Provide LinkedIn/GitHub URLs for cross verification"],
    }
