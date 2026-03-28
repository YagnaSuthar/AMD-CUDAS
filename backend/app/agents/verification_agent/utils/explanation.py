from __future__ import annotations

import asyncio
from typing import Any


async def generate_explanation(
    *,
    input_type: str,
    extracted_data: dict[str, Any],
    scores: dict[str, Any],
    issues: list[str],
    status: str,
    confidence_score: float,
) -> dict[str, Any]:
    risk_level = "low" if status == "verified" else ("medium" if status == "suspicious" else "high")

    llm_payload = {
        "input_type": input_type,
        "status": status,
        "risk_level": risk_level,
        "confidence_score": confidence_score,
        "scores": scores,
        "issues": issues,
        "extracted_data": extracted_data,
    }

    try:
        from app.core.llm import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        system = (
            "You are a strict digital auditor. Produce a compact JSON with keys: "
            "summary (string), reasons (string[]), suggested_actions (string[]), evidence (object). "
            "Do not include markdown."
        )

        messages = [
            SystemMessage(content=system),
            HumanMessage(content=f"Verification context: {llm_payload}"),
        ]

        llm = get_llm()
        resp = await asyncio.to_thread(llm.invoke, messages)
        text = resp.content if hasattr(resp, "content") else str(resp)

        import json

        parsed = json.loads(text)
        parsed.setdefault("risk_level", risk_level)
        return parsed
    except Exception:
        return {
            "summary": f"Result: {status} (confidence={round(confidence_score, 2)}).",
            "risk_level": risk_level,
            "reasons": issues[:8],
            "suggested_actions": [
                "Provide clearer source proof (issuer link, certificate ID lookup)" if input_type == "certificate" else "Provide additional evidence",
            ],
            "evidence": {"scores": scores},
        }
