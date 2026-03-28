from __future__ import annotations

from typing import Any


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def compute_final_score(scores: dict[str, Any]) -> dict[str, Any]:
    format_score = _clamp01(scores.get("format_score", 0.0))
    metadata_score = _clamp01(scores.get("metadata_score", 0.0))
    source_score = _clamp01(scores.get("source_score", 0.0))
    consistency_score = _clamp01(scores.get("consistency_score", 0.0))
    ml_score = _clamp01(scores.get("ml_score", 0.5))

    confidence = (
        format_score * 0.20
        + metadata_score * 0.15
        + source_score * 0.30
        + consistency_score * 0.20
        + ml_score * 0.15
    )

    confidence = _clamp01(confidence)

    if confidence >= 0.75:
        status = "verified"
    elif confidence >= 0.45:
        status = "suspicious"
    else:
        status = "failed"

    return {
        "confidence_score": round(confidence, 4),
        "trust_score": int(round(confidence * 100)),
        "status": status,
    }
