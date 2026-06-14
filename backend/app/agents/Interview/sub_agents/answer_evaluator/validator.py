from __future__ import annotations

from typing import Any, Dict, List


_DEFAULT_EVALUATION: Dict[str, Any] = {
    "is_factual": False,
    "correctness": 0,
    "completeness": 0,
    "concept_depth": 0,
    "communication": 0,
    "confidence": 0,
    "good_points": [],
    "mistakes": [],
    "missing_points": [],
    "misconceptions": [],
    "severity": "high",
    "final_feedback": "Unable to evaluate the answer reliably. Please provide a clearer, direct response addressing the question.",
}


def _clamp_int(value: Any, lo: int = 0, hi: int = 10, default: int = 0) -> int:
    try:
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return max(lo, min(hi, int(round(float(value)))))
        if isinstance(value, str) and value.strip() != "":
            return max(lo, min(hi, int(round(float(value.strip())))))
    except Exception:
        return default
    return default


def _as_limited_str_list(value: Any, max_items: int = 8, item_max_len: int = 180) -> List[str]:
    if not isinstance(value, list):
        return []

    out: List[str] = []
    for item in value:
        if len(out) >= max_items:
            break
        if item is None:
            continue
        s = str(item).strip()
        if not s:
            continue
        if len(s) > item_max_len:
            s = s[: item_max_len - 1].rstrip() + "…"
        if s not in out:
            out.append(s)
    return out


def _normalize_severity(sev: Any) -> str:
    s = str(sev).strip().lower() if sev is not None else ""
    if s in ("low", "medium", "high"):
        return s
    return "high"


def _compute_severity(correctness: int, misconceptions_count: int) -> str:
    if correctness <= 3 or misconceptions_count >= 2:
        return "high"
    if 4 <= correctness <= 6 or misconceptions_count == 1:
        return "medium"
    return "low"


def validate_evaluation(data: Any) -> Dict[str, Any]:
    """Validate and normalize evaluator output.

    Never raises. Always returns a dict with required keys.
    """
    if not isinstance(data, dict):
        return dict(_DEFAULT_EVALUATION)

    is_factual = bool(data.get("is_factual", False))
    correctness = _clamp_int(data.get("correctness"), default=_DEFAULT_EVALUATION["correctness"])
    completeness = _clamp_int(data.get("completeness"), default=_DEFAULT_EVALUATION["completeness"])
    concept_depth = _clamp_int(data.get("concept_depth"), default=_DEFAULT_EVALUATION["concept_depth"])
    communication = _clamp_int(data.get("communication"), default=_DEFAULT_EVALUATION["communication"])
    confidence = _clamp_int(data.get("confidence"), default=_DEFAULT_EVALUATION["confidence"])

    good_points = _as_limited_str_list(data.get("good_points"), max_items=8)
    mistakes = _as_limited_str_list(data.get("mistakes"), max_items=8)
    missing_points = _as_limited_str_list(data.get("missing_points"), max_items=8)
    misconceptions = _as_limited_str_list(data.get("misconceptions"), max_items=6)

    # 6. Consistency Constraints
    # Enforce:
    # If correctness <= 3
    # Then:
    # concept_depth <= 3
    # completeness <= 3
    # communication <= 5
    # confidence <= 5
    if correctness <= 3:
        concept_depth = min(concept_depth, 3)
        completeness = min(completeness, 3)
        communication = min(communication, 5)
        confidence = min(confidence, 5)

    # Deterministic constraint: confidence shouldn't exceed correctness too much.
    confidence = min(confidence, correctness + 2)

    # Severity: prefer deterministic calculation; allow provided value only if valid and consistent.
    computed_severity = _compute_severity(correctness, len(misconceptions))
    provided_severity = _normalize_severity(data.get("severity"))
    severity = computed_severity if provided_severity not in ("low", "medium", "high") else computed_severity

    final_feedback = data.get("final_feedback")
    if final_feedback is None:
        final_feedback = _DEFAULT_EVALUATION["final_feedback"]
    final_feedback = str(final_feedback).strip()
    if not final_feedback:
        final_feedback = _DEFAULT_EVALUATION["final_feedback"]
    if len(final_feedback) > 1200:
        final_feedback = final_feedback[:1200]

    return {
        "is_factual": is_factual,
        "correctness": correctness,
        "completeness": completeness,
        "concept_depth": concept_depth,
        "communication": communication,
        "confidence": confidence,
        "good_points": good_points,
        "mistakes": mistakes,
        "missing_points": missing_points,
        "misconceptions": misconceptions,
        "severity": severity,
        "final_feedback": final_feedback,
    }


def default_evaluation() -> Dict[str, Any]:
    return dict(_DEFAULT_EVALUATION)
