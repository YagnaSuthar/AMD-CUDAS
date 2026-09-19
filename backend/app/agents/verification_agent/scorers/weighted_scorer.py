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
    contribution_score = scores.get("contribution_score")
    description_match_score = scores.get("description_match_score")
    structure_score = scores.get("structure_score")

    if structure_score is not None:
        # Project verification with folder-tree analysis. Weights are
        # renormalised over the signals that are actually available.
        weights = {
            "format": (0.05, format_score),
            "metadata": (0.05, metadata_score),
            "structure": (0.20, _clamp01(structure_score)),
            "source": (0.10, source_score),
            "consistency": (0.10, consistency_score),
            "ml": (0.05, ml_score),
        }
        if contribution_score is not None:
            weights["contribution"] = (0.30, _clamp01(contribution_score))
        if description_match_score is not None:
            weights["description"] = (0.15, _clamp01(description_match_score))
        total_w = sum(w for w, _ in weights.values())
        confidence = sum(w * v for w, v in weights.values()) / total_w
    elif contribution_score is not None:
        # Enhanced scoring with contribution analysis
        contribution_score = _clamp01(contribution_score)
        
        # Include description match if available
        desc_weight = 0.15 if description_match_score is not None else 0.0
        contrib_weight = 0.30 if description_match_score is not None else 0.35
        source_weight = 0.15 if description_match_score is not None else 0.20
        ml_w = 0.05 if description_match_score is not None else 0.10
        
        desc_score = _clamp01(description_match_score) if description_match_score is not None else 0.0
        
        confidence = (
            format_score * 0.10
            + metadata_score * 0.10
            + source_score * source_weight
            + consistency_score * 0.15
            + ml_score * ml_w
            + contribution_score * contrib_weight
            + desc_score * desc_weight
        )
    else:
        # Fallback: original scoring without contribution data
        desc_weight = 0.15 if description_match_score is not None else 0.0
        source_weight = 0.25 if description_match_score is not None else 0.30
        ml_w = 0.05 if description_match_score is not None else 0.15
        
        desc_score = _clamp01(description_match_score) if description_match_score is not None else 0.0
        
        confidence = (
            format_score * 0.20
            + metadata_score * 0.15
            + source_score * source_weight
            + consistency_score * 0.20
            + ml_score * ml_w
            + desc_score * desc_weight
        )

    confidence = _clamp01(confidence)
    cap = scores.get("confidence_cap")
    if cap is not None:
        confidence = min(confidence, float(cap))

    if confidence >= 0.55:
        status = "verified"
    elif confidence >= 0.35:
        status = "suspicious"
    else:
        status = "failed"

    return {
        "confidence_score": round(confidence, 4),
        "trust_score": int(round(confidence * 100)),
        "status": status,
    }
