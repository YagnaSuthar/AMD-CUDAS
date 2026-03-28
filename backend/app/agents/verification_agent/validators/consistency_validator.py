from __future__ import annotations

from typing import Any


async def validate_cross_profile_consistency(
    *,
    extracted: dict[str, Any],
    profile_data: dict[str, Any] | None,
) -> dict[str, Any]:
    issues: list[str] = []

    if not profile_data:
        return {"score": 0.5, "issues": ["No profile data provided for cross-check"], "verified_fields": []}

    score = 1.0

    extracted_name = (extracted.get("name") or "").strip().lower()
    profile_name = (profile_data.get("name") or profile_data.get("full_name") or "").strip().lower()

    if extracted_name and profile_name and extracted_name not in profile_name and profile_name not in extracted_name:
        issues.append("Name mismatch between certificate/project and profile data")
        score -= 0.5

    return {"score": round(max(0.0, score), 4), "issues": issues, "verified_fields": []}
