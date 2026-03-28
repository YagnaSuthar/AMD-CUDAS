from __future__ import annotations

from datetime import datetime
from typing import Any


async def validate_certificate_metadata(extracted: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    verified_fields: list[str] = []

    fields = ["name", "course", "issuer", "date", "certificate_id"]
    present = [f for f in fields if extracted.get(f)]

    base_score = len(present) / len(fields)

    date_ok = True
    if extracted.get("date"):
        date_ok = _date_sane(str(extracted["date"]))
        if not date_ok:
            issues.append("Certificate date looks invalid or far in the future")

    if extracted.get("certificate_id") and len(str(extracted["certificate_id"])) < 5:
        issues.append("Certificate ID is too short")

    if base_score >= 0.6:
        verified_fields.extend(present)
    else:
        issues.append("Too few structured fields could be extracted")

    score = base_score * (1.0 if date_ok else 0.7)
    return {"score": round(score, 4), "issues": issues, "verified_fields": verified_fields}


def _date_sane(date_str: str) -> bool:
    now = datetime.utcnow()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%y", "%d/%m/%y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.year > now.year + 1:
                return False
            if dt.year < 1990:
                return False
            return True
        except Exception:
            continue
    return True
