"""
Calibrated Deterministic Report Builder.
Derives human-like insights strictly from InterviewTurn evaluation data.
NO LLM usage. Production-ready consistency.

Enhanced with presentation-layer derived fields:
- executive_summary, communication_analysis, improvement_roadmap,
  hiring_readiness, interviewer_remarks, verdict_label,
  and enriched per-question entries.
"""

from __future__ import annotations

import math
import re
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


def _clean_leakage(text: str) -> str:
    """Sanitize evaluator-internal reasoning from candidate-facing output."""
    if not text or not isinstance(text, str):
        return ""
    cleaned = text.strip()
    # Reject placeholder / null values
    if cleaned.lower() in {"none found", "n/a", "none", "nil", "evaluation incomplete",
                           "empty placeholders", "not applicable", "—", "-"}:
        return ""
    # Strip evaluator-reasoning prefixes
    prefixes = [
        r"^did not demonstrate a thorough understanding of\s*",
        r"^did not demonstrate an? understanding of\s*",
        r"^did not demonstrate\s*",
        r"^did not mention how\s*",
        r"^did not mention\s*",
        r"^failed to mention\s*",
        r"^failed to explain\s*",
        r"^importance of\s*",
        r"^candidate did not\s*",
        r"^the candidate did not\s*",
        r"^candidate failed to\s*",
        r"^the candidate failed to\s*",
        r"^lacks understanding of\s*",
        r"^no\s+\w+\s+found\s*",
    ]
    for p in prefixes:
        cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE).strip()
    # Trailing punctuation cleanup
    cleaned = cleaned.rstrip(".,:; ")
    if not cleaned:
        return ""
    # Short residual → title-case as a topic label
    if len(cleaned.split()) <= 6:
        return cleaned.title()
    return cleaned[:1].upper() + cleaned[1:]


# _build_better_answer_direction removed — Change 2: evaluator-internal coaching
# is no longer shown on candidate-facing reports.


def _build_improvement_areas(
    valid_evals: List[Dict[str, Any]],
    all_missing: List[str],
    all_misconceptions: List[str],
) -> List[str]:
    """
    Generate 3-5 concrete, topic-specific improvement bullets.
    Avoids generic words like 'Technical', 'Domain', 'Fundamentals' unless
    attached to a specific subject.
    """
    bullets: List[str] = []
    seen: set = set()

    # 1. Weak topics — use actual topic names from questions scored <= 5
    weak_topics = list(dict.fromkeys(
        ev["topic"] for ev in valid_evals
        if ev.get("correctness", 10) <= 5 and ev.get("topic")
        and ev["topic"].lower() not in {"technical", "general", "n/a", "domain"}
    ))[:3]
    for wt in weak_topics:
        label = wt.replace("_", " ").title()
        bullets.append(label)
        seen.add(label.lower())

    # 2. Concrete missing concepts from evaluations
    for item in (all_missing + all_misconceptions):
        cl = _clean_leakage(item)
        if not cl or cl.lower() in seen:
            continue
        # Skip generic single-word fillers
        if cl.lower() in {"technical", "domain", "fundamentals", "concepts",
                          "general", "details", "implementation", "understanding"}:
            continue
        seen.add(cl.lower())
        bullets.append(cl)
        if len(bullets) >= 5:
            break

    # 3. Structure/communication if scores are weak
    avg_depth = _compute_average([ev.get("concept_depth", 5) for ev in valid_evals])
    avg_comm = _compute_average([ev.get("communication", 5) for ev in valid_evals])
    if avg_depth < 6 and len(bullets) < 5:
        bullets.append("Deeper implementation-level explanations")
    if avg_comm < 6 and len(bullets) < 5:
        bullets.append("Structured answer delivery (definition → mechanism → example)")

    # Fallbacks with concrete guidance
    if len(bullets) < 2:
        bullets.append("Practice explaining concepts with real-world examples")

    return _dedupe_limit(bullets, limit=5)


def _build_overall_strength_bullets(
    valid_evals: List[Dict[str, Any]],
    raw_strengths: List[str],
) -> List[str]:
    """
    Generate 3-5 high-level strength pattern bullets observed across the interview.
    """
    bullets: List[str] = []

    avg_corr  = _compute_average([ev.get("correctness",    0) for ev in valid_evals])
    avg_comm  = _compute_average([ev.get("communication",  0) for ev in valid_evals])
    avg_conf  = _compute_average([ev.get("confidence",     0) for ev in valid_evals])
    avg_depth = _compute_average([ev.get("concept_depth",  0) for ev in valid_evals])

    strong_topics = list(dict.fromkeys(
        ev["topic"] for ev in valid_evals
        if ev.get("correctness", 0) >= 7 and ev.get("topic")
    ))[:2]
    if strong_topics:
        bullets.append(f"Strong understanding demonstrated in {', '.join(strong_topics)}")

    if avg_comm >= 6.5:
        bullets.append("Clear and structured communication throughout the interview")
    if avg_conf >= 6.5:
        bullets.append("Confident delivery and engagement with technical questions")
    if avg_depth >= 6.5:
        bullets.append("Good technical depth demonstrated in explanations")
    if avg_corr >= 7.0 and len(bullets) < 5:
        bullets.append("Strong overall technical accuracy across the interview")

    # Supplement from raw good_points
    for s in raw_strengths:
        cl = _clean_leakage(s)
        if cl and cl not in bullets:
            bullets.append(cl)
        if len(bullets) >= 5:
            break

    if not bullets:
        bullets.append("Demonstrated willingness to engage with technical challenges")

    return _dedupe_limit(bullets, limit=5)


# ---------------------------------------------------------------------------
# NEW: Presentation-layer helpers (no scoring logic changes)
# ---------------------------------------------------------------------------

_SPEECH_ARTIFACTS_RE = re.compile(
    r"\b(uh|um|umm|uhh|hmm|hm|hello|hi there|can you hear me|so basically|you know|like basically|basically)\b",
    re.IGNORECASE,
)
_LEADING_FILLER_RE = re.compile(
    r"^\s*(?:(?:uh|um|umm|uhh|hmm|hm|hello|hi there|hi|hey|so|okay|ok|right|well|yeah|yes|no|alright)[\s,.:;!?]*)+",
    re.IGNORECASE,
)
_TRAILING_FILLER_RE = re.compile(
    r"(?:[\s,.:;!?]*(?:uh|um|umm|uhh|hmm|hm|so yeah|you know|right|okay|ok))+\s*$",
    re.IGNORECASE,
)
_MULTI_SPACE_RE = re.compile(r"\s{2,}")


def _clean_answer(text: str) -> str:
    """Remove common speech artifacts from a transcribed answer."""
    if not text or not isinstance(text, str):
        return text or ""
    cleaned = _LEADING_FILLER_RE.sub("", text)
    cleaned = _TRAILING_FILLER_RE.sub("", cleaned)
    cleaned = _SPEECH_ARTIFACTS_RE.sub("", cleaned)
    cleaned = _MULTI_SPACE_RE.sub(" ", cleaned).strip()
    return cleaned if cleaned else text.strip()


def _build_executive_summary(
    avg_corr: float,
    avg_depth: float,
    avg_comm: float,
    avg_conf: float,
    overall_score: float,
    valid_evals: List[Dict[str, Any]] | None = None,
) -> str:
    """Generate a concise, personalized 3-4 sentence executive summary using actual topics."""
    evals = valid_evals or []

    # Collect actual strong/weak topic names
    strong_topics = list(dict.fromkeys(
        ev["topic"].replace("_", " ").title()
        for ev in evals
        if ev.get("correctness", 0) >= 7 and ev.get("topic")
        and ev["topic"].lower() not in {"technical", "general", "n/a"}
    ))[:2]
    weak_topics = list(dict.fromkeys(
        ev["topic"].replace("_", " ").title()
        for ev in evals
        if ev.get("correctness", 10) <= 4 and ev.get("topic")
        and ev["topic"].lower() not in {"technical", "general", "n/a"}
    ))[:2]

    # Sentence 1: Overall performance
    if overall_score >= 7.5:
        s1 = f"The candidate scored {overall_score:.1f}/10, demonstrating strong technical competence."
    elif overall_score >= 5.0:
        s1 = f"The candidate scored {overall_score:.1f}/10, showing a solid foundation with room for growth."
    elif overall_score >= 3.0:
        s1 = f"The candidate scored {overall_score:.1f}/10, indicating early-stage preparation."
    else:
        s1 = f"The candidate scored {overall_score:.1f}/10, suggesting significant preparation is needed."

    # Sentence 2: Strengths (personalized with actual topics)
    if strong_topics:
        s2 = f"Strongest performance was in {' and '.join(strong_topics)}."
    elif avg_corr >= 5:
        s2 = "Responses showed adequate understanding across topics covered."
    else:
        s2 = "No individual topic stood out as a clear strength."

    # Sentence 3: Weaknesses (personalized with actual topics)
    if weak_topics:
        s3 = f"{' and '.join(weak_topics)} need{'s' if len(weak_topics) == 1 else ''} focused improvement."
    elif avg_corr >= 7:
        s3 = "No major weaknesses were identified."
    else:
        s3 = "Deeper technical explanations would strengthen overall performance."

    # Sentence 4: Communication
    if avg_comm >= 7:
        s4 = "Communication was clear and well-structured throughout."
    elif avg_comm >= 5:
        s4 = "Communication was adequate but could be more structured."
    else:
        s4 = "Answer structure and clarity need improvement."

    return f"{s1} {s2} {s3} {s4}"


def _build_communication_analysis(
    avg_corr: float,
    avg_depth: float,
    avg_comm: float,
    avg_conf: float,
) -> Dict[str, Any]:
    """Derive communication analysis metrics from existing per-turn averages."""
    technical_vocabulary = round((avg_corr + avg_depth) / 2, 2)
    answer_structure = round((avg_comm + avg_depth) / 2, 2)
    conciseness = round(avg_comm * 0.8 + avg_conf * 0.2, 2)

    # Deterministic analysis text
    parts: List[str] = []
    if avg_comm >= 7:
        parts.append("The candidate communicates technical ideas clearly and concisely.")
    elif avg_comm >= 5:
        parts.append("The candidate communicates adequately, with room for clearer articulation.")
    else:
        parts.append("Communication clarity needs improvement; responses lacked structure.")

    if technical_vocabulary >= 6:
        parts.append("Technical vocabulary usage is appropriate and precise.")
    elif technical_vocabulary >= 4:
        parts.append("Technical terminology is used but sometimes imprecisely.")
    else:
        parts.append("Technical vocabulary is limited and should be expanded.")

    if avg_conf >= 7:
        parts.append("The candidate projects strong confidence in their responses.")
    elif avg_conf >= 5:
        parts.append("Confidence level is moderate; could benefit from more assertive delivery.")
    else:
        parts.append("Low confidence was evident; practice and preparation would help.")

    return {
        "clarity": avg_comm,
        "confidence": avg_conf,
        "technical_vocabulary": technical_vocabulary,
        "answer_structure": answer_structure,
        "conciseness": conciseness,
        "analysis_text": " ".join(parts),
    }


def _build_improvement_roadmap(
    missing_points: List[str],
    misconceptions: List[str],
) -> List[Dict[str, str]]:
    """Convert flat improvement data into a structured, compact roadmap (max 3 items)."""
    roadmap: List[Dict[str, str]] = []
    priority = 1

    # Misconceptions first — higher priority
    for mc in misconceptions:
        if priority > 3:
            break
        topic = _clean_leakage(mc)
        if not topic:
            continue
        roadmap.append({
            "priority": priority,
            "topic": topic,
            "reason": f"A misconception about {topic} can lead to fundamental errors in practice.",
            "practice_plan": f"Review authoritative references on {topic}, build a small project exercising the concept, and re-test understanding.",
            "estimated_effort": "4–6 Hours",
        })
        priority += 1

    for mp in missing_points:
        if priority > 3:
            break
        topic = _clean_leakage(mp)
        if not topic:
            continue
        roadmap.append({
            "priority": priority,
            "topic": topic,
            "reason": f"This area was not fully addressed during the interview. Understanding {topic} is critical for this role.",
            "practice_plan": f"Study {topic} through official documentation, implement a hands-on exercise, and practice explaining it aloud.",
            "estimated_effort": "2–4 Hours",
        })
        priority += 1

    # Fallback if nothing meaningful was generated
    if not roadmap:
        roadmap.append({
            "priority": 1,
            "topic": "Technical Communication",
            "reason": "Clear, structured communication is as important as technical accuracy in interviews.",
            "practice_plan": "Practice explaining complex concepts using the STAR method and conduct regular mock interviews.",
            "estimated_effort": "Ongoing",
        })

    return roadmap[:3]


def _build_hiring_readiness(overall_score: float) -> Dict[str, Any]:
    """Determine hiring readiness level from overall score."""
    if overall_score >= 8.5:
        tier = "Strong Hire"
        reason = "Demonstrates strong technical competence and interview readiness."
        next_milestone = "Ready for senior technical interviews."
    elif overall_score >= 7.0:
        tier = "Placement Ready"
        reason = "Capable of performing well in most campus recruitment processes."
        next_milestone = "Refine advanced concepts and communication to reach Strong Hire level."
    elif overall_score >= 5.0:
        tier = "Internship Ready"
        reason = "Demonstrates sufficient understanding for internship-level opportunities."
        next_milestone = "Deepen technical implementation knowledge to reach Placement Ready level."
    elif overall_score >= 3.0:
        tier = "Developing"
        reason = "Foundational understanding exists but significant improvement is required."
        next_milestone = "Improve core architecture knowledge to reach Internship Ready level."
    else:
        tier = "Needs Significant Improvement"
        reason = "Fundamental concepts require strengthening before interview readiness."
        next_milestone = "Master core fundamentals through a structured study plan."

    return {
        "tier": tier,
        "reason": reason,
        "next_milestone": next_milestone,
        # Legacy fields to prevent breaking UI
        "level": tier,
        "readiness_pct": None,
        "recommendation_text": reason,
    }


def _build_interviewer_remarks(
    overall_score: float,
    valid_evals: List[Dict[str, Any]] | None = None,
) -> str:
    """Return concise, personalized, professional interviewer remarks (4-5 lines max)."""
    evals = valid_evals or []
    n_questions = len(evals)

    # Find actual strong/weak topics for personalization
    strong = [ev["topic"].replace("_", " ").title() for ev in evals
              if ev.get("correctness", 0) >= 7 and ev.get("topic")
              and ev["topic"].lower() not in {"technical", "general", "n/a"}]
    weak = [ev["topic"].replace("_", " ").title() for ev in evals
            if ev.get("correctness", 10) <= 4 and ev.get("topic")
            and ev["topic"].lower() not in {"technical", "general", "n/a"}]
    strong_u = list(dict.fromkeys(strong))[:2]
    weak_u = list(dict.fromkeys(weak))[:2]

    if overall_score >= 8.5:
        core = f"Scored {overall_score:.1f}/10 across {n_questions} questions."
        detail = f"Strong performance in {', '.join(strong_u)}." if strong_u else "Consistently strong across all topics."
        closing = "Recommended for technical roles."
    elif overall_score >= 7.0:
        core = f"Scored {overall_score:.1f}/10 across {n_questions} questions."
        detail = f"Good command of {', '.join(strong_u)}." if strong_u else "Showed solid technical awareness."
        gap = f"Could improve in {', '.join(weak_u)}." if weak_u else "Minor depth improvements would elevate performance."
        closing = gap
    elif overall_score >= 5.0:
        core = f"Scored {overall_score:.1f}/10 across {n_questions} questions."
        detail = f"Adequate understanding of {', '.join(strong_u)}." if strong_u else "Foundational knowledge is present."
        gap = f"Needs focused work on {', '.join(weak_u)}." if weak_u else "Needs deeper technical explanations."
        closing = gap
    elif overall_score >= 3.0:
        core = f"Scored {overall_score:.1f}/10 across {n_questions} questions."
        detail = "Early-stage preparation is evident."
        gap = f"Significant gaps in {', '.join(weak_u)}." if weak_u else "Core concepts need strengthening."
        closing = f"{gap} Hands-on practice recommended before next assessment."
    else:
        core = f"Scored {overall_score:.1f}/10 across {n_questions} questions."
        detail = "Fundamental concepts require strengthening."
        closing = "A structured study plan and hands-on projects are recommended."

    return f"{core} {detail} {closing}"


def _build_verdict_label(verdict: str, overall_score: float) -> str:
    """Map internal verdict to a user-facing label."""
    if verdict == "Strong Hire":
        return "Excellent"
    if verdict == "Consider":
        return "Good" if overall_score >= 6.5 else "Developing"
    return "Needs Improvement"



def build_report(
    turns: List[Dict[str, Any]],
    proctoring_violations: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Build a human-like, fair deterministic report.
    - Strengths logic: correctness >= 7 (Strong), >= 5 (Developing)
    - Weakness logic: mistakes/missing if correctness <= 5
    - Includes confidence gap detection
    - Comprehensive per-question feedback fallbacks
    """
    proctoring_violations = proctoring_violations or []

    # Convert any SQLAlchemy model instances of ProctoringViolation to dictionaries
    mapped_violations = []
    for v in proctoring_violations:
        if isinstance(v, dict):
            mapped_violations.append(v)
        elif hasattr(v, "violation_type"):
            ts = ""
            if hasattr(v, "detected_at") and v.detected_at:
                ts = v.detected_at.strftime("%H:%M:%S")
            mapped_violations.append({
                "type": v.violation_type,
                "timestamp": ts,
                "count": 1,
                "message": getattr(v, "message", ""),
            })
        else:
            mapped_violations.append(v)
    proctoring_violations = mapped_violations

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
            "improvement_plan": [],
            # --- New presentation fields ---
            "executive_summary": "No interview data available to generate an executive summary.",
            "communication_analysis": {
                "clarity": 0.0,
                "confidence": 0.0,
                "technical_vocabulary": 0.0,
                "answer_structure": 0.0,
                "conciseness": 0.0,
                "analysis_text": "No data available.",
            },
            "improvement_roadmap": [],
            "hiring_readiness": {
                "level": "Needs Significant Improvement",
                "readiness_pct": 0,
                "recommendation_text": "No interview data to assess readiness.",
            },
            "interviewer_remarks": "No interview data available.",
            "verdict_label": "Needs Improvement",
            "proctoring_violations": proctoring_violations,
        }

    valid_evals = []
    q_analysis = []
    
    for t in turns:
        ev = t.get("evaluation") or {}
        qm = ev.get("question_meta", {}) if isinstance(ev, dict) else {}
        
        turn_data = {
            "question": t.get("question", "N/A"),
            "answer": t.get("answer", "No answer provided."),
            "topic": t.get("topic") or qm.get("topic") or qm.get("concept") or "Technical",
            "correctness": _safe_int(ev.get("correctness")),
            "concept_depth": _safe_int(ev.get("concept_depth")),
            "communication": _safe_int(ev.get("communication")),
            "confidence": _safe_int(ev.get("confidence")),
            "good_points": ev.get("good_points", []) if isinstance(ev.get("good_points"), list) else [],
            "mistakes": ev.get("mistakes", []) if isinstance(ev.get("mistakes"), list) else [],
            "missing_points": ev.get("missing_points", []) if isinstance(ev.get("missing_points"), list) else [],
            "misconceptions": ev.get("misconceptions", []) if isinstance(ev.get("misconceptions"), list) else [],
            "severity": (ev.get("severity") or "low").lower(),
            "final_feedback": (ev.get("final_feedback") or "Improve clarity and provide more detailed explanation.").strip(),
            "difficulty": t.get("difficulty") or qm.get("difficulty") or (ev.get("difficulty") or "medium"),
        }
        
        valid_evals.append(turn_data)

        # Sanitize and derive per-question fields
        how_to_improve: List[str] = []
        for mistake in turn_data["mistakes"]:
            cl = _clean_leakage(mistake)
            if cl:
                how_to_improve.append(cl)
        for mp in turn_data["missing_points"]:
            cl = _clean_leakage(mp)
            if cl and cl not in how_to_improve:
                how_to_improve.append(cl)

        good_pts: List[str] = []
        for gp in turn_data["good_points"]:
            cl = _clean_leakage(gp)
            if cl:
                good_pts.append(cl)

        # What was missing — up to 2 clean items joined as single string
        missing_clean = _dedupe_limit(how_to_improve, limit=2)
        what_was_missing_str = "; ".join(missing_clean) if missing_clean else ""

        q_analysis.append({
            "question": turn_data["question"],
            "answer": turn_data["answer"],
            "correctness": turn_data["correctness"],
            "concept_depth": turn_data["concept_depth"],
            "communication": turn_data["communication"],
            "feedback": turn_data["final_feedback"],
            "difficulty": turn_data["difficulty"],
            # --- Per-question feedback: ✓ Correct / ⚠ Missing only ---
            "key_strength":            good_pts[0] if good_pts else "",
            "improvement_opportunity": what_was_missing_str,
            "what_was_missing":        what_was_missing_str,
            "better_answer_direction": "",  # Removed — no longer shown
            "cleaned_answer":          _clean_answer(turn_data["answer"]),
            # Legacy nulls — kept for schema stability
            "what_went_well": None,
            "how_to_improve": None,
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

    # Merge raw good_points then derive high-level pattern bullets
    raw_strengths_list = _dedupe_limit(strong_strengths + developing_strengths, limit=10)
    strengths = _build_overall_strength_bullets(valid_evals, raw_strengths_list)
    if not strengths:
        strengths = ["Demonstrated willingness to engage with technical challenges."]

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

    # Improvement areas replaces the old roadmap + recommendation system
    improvement_plan = _build_improvement_areas(valid_evals, all_missing, all_misconceptions)

    # --- Presentation-layer fields ---
    executive_summary = _build_executive_summary(
        avg_corr, avg_depth, avg_comm, avg_conf, overall_score,
        valid_evals=valid_evals,
    )
    communication_analysis = _build_communication_analysis(
        avg_corr, avg_depth, avg_comm, avg_conf
    )
    # Proctoring violations are included via critical_issues
    hiring_readiness = _build_hiring_readiness(overall_score)
    interviewer_remarks = _build_interviewer_remarks(
        overall_score, valid_evals=valid_evals,
    )
    verdict_label = _build_verdict_label(verdict, overall_score)

    return {
    "summary": summary,
    "final_score": float(overall_score),
    "strengths": strengths,
    "weaknesses": weaknesses,
    "critical_issues": critical_issues,
    "weakness_patterns": patterns,
    "questions": q_analysis,
    "improvement_plan": improvement_plan,

    "executive_summary": executive_summary,
    "communication_analysis": communication_analysis,
    "hiring_readiness": hiring_readiness,
    "interviewer_remarks": interviewer_remarks,
    "verdict_label": verdict_label,

    # Final violations list
    "proctoring_violations": proctoring_violations,
}