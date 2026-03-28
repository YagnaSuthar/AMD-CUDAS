from __future__ import annotations

import re
from typing import Any

from fastapi import UploadFile


async def extract_certificate_structured(*, file: UploadFile, file_bytes: bytes) -> dict[str, Any]:
    from app.agents.verification_agent.utils.text_extraction import extract_text_from_certificate

    text = await extract_text_from_certificate(file=file, file_bytes=file_bytes)

    data: dict[str, Any] = {
        "raw_text": text,
        "name": _extract_name(text),
        "course": _extract_course(text),
        "issuer": _extract_issuer(text),
        "date": _extract_date(text),
        "certificate_id": _extract_certificate_id(text),
    }
    return data


def _extract_name(text: str) -> str | None:
    patterns = [
        r"\bawarded to\b\s*[:\-]?\s*(?P<v>[A-Z][A-Za-z .]{2,80})",
        r"\bthis is to certify that\b\s*(?P<v>[A-Z][A-Za-z .]{2,80})",
        r"\bcertifies that\b\s*(?P<v>[A-Z][A-Za-z .]{2,80})",
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            return m.group("v").strip()
    return None


def _extract_course(text: str) -> str | None:
    m = re.search(r"\b(course|program|training)\b\s*[:\-]?\s*(?P<v>[A-Za-z0-9 ,./\-]{3,120})", text, flags=re.IGNORECASE)
    return m.group("v").strip() if m else None


def _extract_issuer(text: str) -> str | None:
    m = re.search(r"\b(issued by|issuer|organization|institution)\b\s*[:\-]?\s*(?P<v>[A-Za-z0-9 &.,/\-]{3,120})", text, flags=re.IGNORECASE)
    return m.group("v").strip() if m else None


def _extract_date(text: str) -> str | None:
    m = re.search(r"\b(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})\b", text)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{4}[\-/]\d{1,2}[\-/]\d{1,2})\b", text)
    return m.group(1) if m else None


def _extract_certificate_id(text: str) -> str | None:
    m = re.search(r"\b(cert(ificate)?\s*(id|no|number)\b\s*[:\-#]?\s*(?P<v>[A-Za-z0-9\-_/]{4,64}))", text, flags=re.IGNORECASE)
    return m.group("v").strip() if m else None
