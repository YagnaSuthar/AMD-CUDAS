from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


async def validate_certificate_source(*, db: AsyncSession, extracted: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    recommendations: list[str] = []

    issuer = extracted.get("issuer")
    cert_id = extracted.get("certificate_id")

    score = 0.4

    if not issuer:
        issues.append("Issuer not detected; cannot validate source")
        recommendations.append("Ensure issuer name is visible or provide issuer link")
        return {"score": 0.0, "issues": issues, "recommendations": recommendations}

    try:
        from app.services.retrieval_service import RetrievalService

        retrieval = RetrievalService(db)
        hits = await retrieval.search(query=str(issuer), agent_type=None, top_k=3)
        if hits:
            score += 0.35
        else:
            issues.append("Issuer not found in internal knowledge base (RAG)")
            recommendations.append("Upload issuer documentation or use a known issuer")
    except Exception:
        issues.append("Issuer trust check unavailable")

    if cert_id:
        score += 0.25
    else:
        issues.append("Certificate ID not detected; external lookup not possible")
        recommendations.append("Provide a certificate ID / credential URL for lookup")

    return {"score": round(min(1.0, score), 4), "issues": issues, "recommendations": recommendations}
