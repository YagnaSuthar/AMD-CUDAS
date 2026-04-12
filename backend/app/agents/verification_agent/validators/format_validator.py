from __future__ import annotations

from typing import Any


async def validate_certificate_format(extracted: dict[str, Any]) -> dict[str, Any]:
    text = (extracted.get("raw_text") or "").lower()
    issues: list[str] = []
    verified_fields: list[str] = []

<<<<<<< HEAD
    key_phrases = ["certificate", "certify", "issued", "completion"]
    hits = sum(1 for p in key_phrases if p in text)

    score = min(1.0, hits / 3.0) if text.strip() else 0.0

    if score < 0.4:
=======
    key_phrases = ["certificate", "certify", "issued", "completion", "achievement", "award", "program", "diploma", "degree", "verify"]
    hits = sum(1 for p in key_phrases if p in text)

    # 4 strong hits is enough for perfect format score
    score = min(1.0, hits / 4.0) if text.strip() else 0.0

    if score < 0.35:
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
        issues.append("Certificate text does not match common certificate phrasing")
    else:
        verified_fields.append("format")

    return {"score": round(score, 4), "issues": issues, "verified_fields": verified_fields}
