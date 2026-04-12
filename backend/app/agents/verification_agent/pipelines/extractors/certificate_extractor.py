from __future__ import annotations

import re
from typing import Any

from fastapi import UploadFile


async def extract_certificate_structured(*, file: UploadFile, file_bytes: bytes) -> dict[str, Any]:
    from app.agents.verification_agent.utils.text_extraction import extract_text_from_certificate
<<<<<<< HEAD

=======
    from app.core.llm import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage
    import json
    import asyncio
    import logging

    logger = logging.getLogger(__name__)
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
    text = await extract_text_from_certificate(file=file, file_bytes=file_bytes)

    data: dict[str, Any] = {
        "raw_text": text,
<<<<<<< HEAD
        "name": _extract_name(text),
        "course": _extract_course(text),
        "issuer": _extract_issuer(text),
        "date": _extract_date(text),
        "certificate_id": _extract_certificate_id(text),
    }
=======
        "name": None,
        "course": None,
        "issuer": None,
        "date": None,
        "certificate_id": None,
    }

    if text.strip():
        try:
            llm = get_llm()
            prompt = f"""
Extract the following information from the given certificate OCR text.
Return ONLY valid JSON with these keys: name, course, issuer, date, certificate_id.
If a field is not found, set its value to null.

Text:
\"\"\"
{text}
\"\"\"
"""
            response = await asyncio.to_thread(llm.invoke, [HumanMessage(content=prompt)])
            content = response.content if hasattr(response, "content") else str(response)
            
            # Extract JSON block if surrounded by markdown
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                parsed = json.loads(content[start:end])
                data["name"] = parsed.get("name") or _extract_name(text)
                data["course"] = parsed.get("course") or _extract_course(text)
                data["issuer"] = parsed.get("issuer") or _extract_issuer(text)
                data["date"] = parsed.get("date") or _extract_date(text)
                data["certificate_id"] = parsed.get("certificate_id") or _extract_certificate_id(text)
                return data
        except Exception as e:
            logger.warning("LLM certificate extraction failed, falling back to regex: %s", e)

    # Fallback to regex
    data["name"] = _extract_name(text)
    data["course"] = _extract_course(text)
    data["issuer"] = _extract_issuer(text)
    data["date"] = _extract_date(text)
    data["certificate_id"] = _extract_certificate_id(text)
    
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
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
