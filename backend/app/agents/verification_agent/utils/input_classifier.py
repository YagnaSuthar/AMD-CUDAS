from __future__ import annotations

import logging
from fastapi import UploadFile
from typing import Any, Dict

logger = logging.getLogger(__name__)

async def classify_input(
    file: Any = None, link: str | None = None, profile_data: dict[str, Any] | None = None
) -> str:
    """Classify input type (certificate, project, profile)."""
    logger.info("[VERIFICATION] Classifying input type - file=%s, link=%s, profile_data=%s", 
                file.filename if file else None, link, bool(profile_data))
    
    if file:
        content_type = getattr(file, "content_type", None) or ""
        filename = getattr(file, "filename", "") or ""
        logger.info("[VERIFICATION] File detected - content_type=%s, filename=%s", content_type, filename)
        if "pdf" in content_type or filename.lower().endswith(".pdf") or "image" in content_type:
            logger.info("[VERIFICATION] Input classified as: certificate (file)")
            return "certificate"
        else:
            logger.warning("[VERIFICATION] Unknown file type: %s / %s", content_type, filename)
            return "certificate"  # Default assumption
    elif link:
        logger.info("[VERIFICATION] Link detected: %s", link)
        if "github" in link.lower():
            logger.info("[VERIFICATION] Input classified as: project (GitHub link)")
            return "project"
        else:
            logger.info("[VERIFICATION] Input classified as: certificate (non-GitHub link)")
            return "certificate"
    elif profile_data:
        logger.info("[VERIFICATION] Profile data detected - classifying as: profile")
        return "profile"
    else:
        logger.warning("[VERIFICATION] No recognizable input - defaulting to certificate")
        return "certificate"
