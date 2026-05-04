"""
Calibrated Deterministic Report Builder.
Derives human-like insights strictly from InterviewTurn evaluation data.
NO LLM usage. Production-ready consistency.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Sequence


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(round(float(value)))
    except (ValueError, TypeError):
        return default


def _dedupe_limit(items: Sequence[str], limit: int = 5) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if not item or not isinstance(item, str):
            continue
        s = item.strip()
        if not s or s.lower() in seen:
            continue
        seen.add(s.lower())
        result.append(s)
        if len(result) >= limit:
            break
    return result


def _compute_average(scores: List[float]) -> float:
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 2)


def _compute_std_dev(scores: List[float]) -> float:
    if len(scores) < 2:
        return 0.0
    avg = sum(scores) / len(scores)
    variance = sum((x - avg) ** 2 for x in scores) / len(scores)
    return round(math.sqrt(variance), 2)


def _compute_overall_score(
    correctness: float, 
    concept_depth: float, 
    communication: float, 
    confidence: float
) -> float:
    """Weighted average: 50% correctness, 20% depth, 15% comms, 15% confidence."""
    score = (
        correctness * 0.50 +
        concept_depth * 0.20 +
        communication * 0.15 +
        confidence * 0.15
    )
    return round(score, 2)


def _get_verdict(overall_score: float) -> str:
    if overall_score >= 7.5:
        return "Strong Hire"
    elif overall_score >= 5.0:
        return "Consider"
    return "Needs Improvement"


def _extract_weakness_patterns(weaknesses: List[str]) -> List[str]:
    if not weaknesses:
        return []
    keyword_map = {
        "logic": "Logical Gaps",
        "syntax": "Syntax Errors",
        "optimization": "Sub-optimal Approaches",
        "definition": "Conceptual Definitions",
        "naming": "Poor Naming/Structure",
        "missing": "Incomplete Explanation",
        "confused": "Conceptual Confusion",
        "operation": "Process Errors",
    }
    patterns = []
    for item in weaknesses:
        found = False
        for kw, label in keyword_map.items():
            if kw in item.lower():
                patterns.append(label)
                found = True
        if not found:
            patterns.append("Specialized Technical Gap")
    counts = Counter(patterns)
    return [item for item, _ in counts.most_common(3)]


def _build_improvement_plan(missing_points: List[str], misconceptions: List[str]) -> List[str]:
    plan = []
    for point in missing_points[:3]:
        plan.append(f"Deepen knowledge in '{point}' by reviewing documentation and practical implementation.")
    for mc in misconceptions[:2]:
        plan.append(f"Correct fundamental mistake regarding '{mc}'; verify with technical reference.")
    if len(plan) < 3:
        plan.append("Practice explaining technical trade-offs more clearly using the STAR method.")
    return _dedupe_limit(plan, limit=5)


def build_report(turns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a human-like, fair deterministic report.
    - Strengths logic: correctness >= 7 (Strong), >= 5 (Developing)
    - Weakness logic: mistakes/missing if correctness <= 5
    - Includes confidence gap detection
    - Comprehensive per-question feedback fallbacks
    """
    if not turns:
        return {
            "summary": {
                "average_correctness": 0.0,
                "average_concept_depth": 0.0,
                "average_communication": 0.0,
                "average_confidence": 0.0,
                "overall_score": 0.0,
                "consistency": 0.0,
                "verdict": "Needs Improvement"
            },
            "final_score": 0.0,
            "strengths": ["Insufficient data to determine strong areas."],
            "weaknesses": [],
            "critical_issues": [],
            "weakness_patterns": [],
            "questions": [],
            "improvement_plan": []
        }

    valid_evals = []
    q_analysis = []
    
    for t in turns:
        ev = t.get("evaluation") or {}
        
        turn_data = {
            "question": t.get("question", "N/A"),
            "answer": t.get("answer", "No answer provided."),
            "topic": t.get("topic") or "Technical",
            "correctness": _safe_int(ev.get("correctness")),
            "concept_depth": _safe_int(ev.get("concept_depth")),
            "communication": _safe_int(ev.get("communication")),
            "confidence": _safe_int(ev.get("confidence")),
            "good_points": ev.get("good_points", []) if isinstance(ev.get("good_points"), list) else [],
            "mistakes": ev.get("mistakes", []) if isinstance(ev.get("mistakes"), list) else [],
            "missing_points": ev.get("missing_points", []) if isinstance(ev.get("missing_points"), list) else [],
            "misconceptions": ev.get("misconceptions", []) if isinstance(ev.get("misconceptions"), list) else [],
            "severity": (ev.get("severity") or "low").lower(),
            "final_feedback": (ev.get("final_feedback") or "Improve clarity and provide more detailed explanation.").strip()
        }
        
        valid_evals.append(turn_data)
        
        q_analysis.append({
            "question": turn_data["question"],
            "answer": turn_data["answer"],
            "correctness": turn_data["correctness"],
            "concept_depth": turn_data["concept_depth"],
            "communication": turn_data["communication"],
            "feedback": turn_data["final_feedback"]
        })

    # 1. Averages & Consistency
    correctness_scores = [e["correctness"] for e in valid_evals]
    avg_corr = _compute_average(correctness_scores)
    avg_depth = _compute_average([e["concept_depth"] for e in valid_evals])
    avg_comm = _compute_average([e["communication"] for e in valid_evals])
    avg_conf = _compute_average([e["confidence"] for e in valid_evals])
    
    consistency = _compute_std_dev(correctness_scores)
    overall_score = _compute_overall_score(avg_corr, avg_depth, avg_comm, avg_conf)
    verdict = _get_verdict(overall_score)

    # 2. Insight Extraction
    strong_strengths = []
    developing_strengths = []
    weaknesses_raw = []
    critical_raw = []
    all_missing = []
    all_misconceptions = []
    
    for ev in valid_evals:
        # Strengths: correctness >= 7 (Strong), >= 5 (Developing)
        if ev["correctness"] >= 7:
            strong_strengths.extend(ev["good_points"])
        elif ev["correctness"] >= 5:
            developing_strengths.extend(ev["good_points"])
        
        # Confidence Gap (Rule 3)
        if (ev["confidence"] - ev["correctness"]) >= 4:
            critical_raw.append(f"Overconfidence without correctness in answer to '{ev['question'][:40]}...'")
        
        # Weaknesses: only for correctness <= 5
        if ev["correctness"] <= 5:
            weaknesses_raw.extend(ev["mistakes"])
            weaknesses_raw.extend(ev["missing_points"])
        
        all_missing.extend(ev["missing_points"])
        all_misconceptions.extend(ev["misconceptions"])
            
        # Critical Issues from misconceptions (severity == high)
        if ev["severity"] == "high":
            critical_raw.extend(ev["misconceptions"])

    # Merge strengths with tiered priority
    strengths = _dedupe_limit(strong_strengths + developing_strengths, limit=5)
    if not strengths:
        strengths = ["No strong areas identified yet, but foundational understanding is present."]

    # 3. Final Formatting
    summary = {
        "average_correctness": avg_corr,
        "average_concept_depth": avg_depth,
        "average_communication": avg_comm,
        "average_confidence": avg_conf,
        "overall_score": overall_score,
        "consistency": consistency,
        "verdict": verdict
    }
    
    if consistency > 2.0:
        summary["performance_warning"] = "Inconsistent performance across questions"

    weaknesses = _dedupe_limit(weaknesses_raw, limit=5)
    critical_issues = _dedupe_limit(critical_raw, limit=8)
    
    patterns = _extract_weakness_patterns(weaknesses_raw)
    improvement_plan = _build_improvement_plan(all_missing, all_misconceptions)

    return {
        "summary": summary,
        "final_score": float(overall_score),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "critical_issues": critical_issues,
        "weakness_patterns": patterns,
        "questions": q_analysis,
        "improvement_plan": improvement_plan
    }
