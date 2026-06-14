"""
Answer Evaluation Agent (Upgraded).
Evaluates answers with weighted scoring on 0-1 scale:
  - technical_score (0-1)
  - communication_score (0-1)
  - behavior_score (0-1)
  - final_score = 0.5 * technical + 0.3 * communication + 0.2 * behavior

Also maintains backward compatibility with the existing integer-based scoring.

Includes answer-type classification to detect skipped/refusal answers and
override scores accordingly.
"""

import logging
import re
import json
from json import JSONDecodeError
from typing import Any, Dict

from .prompt import build_evaluator_prompt
from .validator import default_evaluation, validate_evaluation

logger = logging.getLogger(__name__)

# ── Skip / Refusal Detection ─────────────────────────────────────────────

SKIP_PATTERNS = [
    r"\bskip\b",
    r"\bskip\s+this\b",
    r"\bpass\b",
    r"\bnext\s+question\b",
    r"\bdon'?t\s+(?:want\s+to\s+)?answer\b",
    r"\bno\s+idea\b",
    r"\bi\s+don'?t\s+know\b",
    r"\bcan'?t\s+answer\b",
    r"\bnot\s+sure\b",
    r"\bno\s+comment\b",
    r"\bi\s+have\s+no\s+(?:clue|idea)\b",
    r"\blet'?s\s+move\s+on\b",
    r"\bmove\s+(?:on|to\s+next)\b",
    r"\bi'?ll\s+skip\b",
    r"\bmaybe\b",
    r"\bi\s+think\b",
]

_SKIP_RE = re.compile("|".join(SKIP_PATTERNS), re.IGNORECASE)


def _normalize_stt_answer(answer: str) -> str:
    text = (answer or "").strip()
    if not text:
        return text

    lowered = text.lower()

    if re.search(r"\b(oop|o\.o\.p)\b", lowered):
        text = re.sub(r"\b(oop|o\.o\.p)\b", "object oriented programming", text, flags=re.IGNORECASE)

    if re.search(r"\b(big\s*o|order)\b", lowered) or re.search(r"\bn\s*square\b", lowered):
        text = re.sub(
            r"\b(?:big\s*o\s*(?:of\s*)?|order\s*)n\s*(?:square|squared|two)\b",
            "O(n^2)",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\bn\s*(?:square|squared)\b", "O(n^2)", text, flags=re.IGNORECASE)
        text = re.sub(
            r"\b(?:big\s*o\s*(?:of\s*)?|order\s*)n\s*log\s*n\b",
            "O(n log n)",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\bn\s*log\s*n\b", "O(n log n)", text, flags=re.IGNORECASE)
        text = re.sub(
            r"\b(?:big\s*o\s*(?:of\s*)?|order\s*)n\b",
            "O(n)",
            text,
            flags=re.IGNORECASE,
        )

    if re.search(r"\b(makes\s+searching\s+faster|search\s+faster)\b", lowered):
        text = re.sub(
            r"\b(makes\s+searching\s+faster|search\s+faster)\b",
            "improves lookup time",
            text,
            flags=re.IGNORECASE,
        )

    return text


def classify_answer_type(answer: str) -> str:
    """Classify the answer into one of: VALID, skip, no_knowledge, IRRELEVANT."""
    text = answer.strip()

    if not text:
        return "skip"

    # Step 1: Remove known skip/refusal phrases
    cleaned_text = _SKIP_RE.sub("", text).strip()
    cleaned_text_no_punct = re.sub(r'[^\w\s]', '', cleaned_text).strip()

    # Step 2: Analyze remaining content
    if not cleaned_text_no_punct:
        return "no_knowledge"

    return "VALID"


# ── Hardcoded scores for non-valid answers ────────────────────────────────

_OVERRIDE_SCORES: Dict[str, Dict[str, Any]] = {
    "skip": {
        "correctness": 0,
        "concept_depth": 0,
        "communication": 1,
        "confidence": 1,
        "overall_score": 0.0,
        "mistakes": ["No answer provided."],
        "missing_points": ["Did not address the question."],
        "misconceptions": [],
        "severity": "high",
        "final_feedback": "You skipped this question. In a real interview, even a partial attempt or stating what you know about the topic is better than skipping.",
        "technical_score": 0.0,
        "communication_score": 0.0,
        "behavior_score": 0.0,
        "weighted_score": 0.0,
        "behavior_flag": "neutral",
        "next_difficulty": "easy",
        "clarity": 0,
        "depth": 0,
        "technical_score_int": 0,
    },
    "no_knowledge": {
        "correctness": 0,
        "concept_depth": 0,
        "communication": 1,
        "confidence": 1,
        "overall_score": 0.25,
        "mistakes": ["Refused to answer or indicated no knowledge."],
        "missing_points": ["No attempt was made to address the question."],
        "misconceptions": [],
        "severity": "high",
        "final_feedback": "You indicated no knowledge. In interviews, share what you know, outline an approach, and ask clarifying questions if needed.",
        "technical_score": 0.0,
        "communication_score": 0.1,
        "behavior_score": 0.1,
        "weighted_score": 0.05,
        "behavior_flag": "neutral",
        "next_difficulty": "easy",
        "clarity": 1,
        "depth": 0,
        "technical_score_int": 0,
    },
    "IRRELEVANT": {
        "correctness": 1,
        "concept_depth": 1,
        "communication": 2,
        "confidence": 2,
        "overall_score": 1.25, # (1*0.5 + 1*0.25 + 2*0.15 + 2*0.10)
        "mistakes": ["Answer was too short or not evaluable."],
        "missing_points": ["No substantive explanation provided."],
        "misconceptions": [],
        "severity": "medium",
        "final_feedback": "Your response is too brief or irrelevant to assess. Provide a direct answer plus a short explanation of why.",
        "technical_score": 0.1,
        "communication_score": 0.2,
        "behavior_score": 0.2,
        "weighted_score": 0.15,
        "behavior_flag": "neutral",
        "next_difficulty": "easy",
        "clarity": 2,
        "depth": 1,
        "technical_score_int": 1,
    },
}


def _safe_parse_json(content: str) -> Dict[str, Any]:
    """Best-effort JSON extraction.

    Requirements:
    - Never raise
    - If parsing fails, return {}
    """
    try:
        text = (content or "").strip()

        # Remove markdown fences if present.
        if "```" in text:
            m = re.search(r"```(?:\w*)\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
            if m:
                text = m.group(1).strip()

        # Try direct parse.
        try:
            obj = json.loads(text)
            return obj if isinstance(obj, dict) else {}
        except JSONDecodeError:
            pass

        # Attempt to find the first JSON object by braces.
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            obj = json.loads(text[first : last + 1])
            return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}
    return {}


async def evaluate_answer(
    question: str,
    answer: str,
    llm: Any,
    difficulty: str = "medium",
) -> Dict[str, Any]:
    """
    Evaluate the candidate's answer with weighted scoring.

    First classifies the answer type. If the answer is SKIPPED, REFUSAL, or
    IRRELEVANT, hardcoded low scores are returned immediately without calling
    the LLM — preventing the model from hallucinating high scores for empty
    or skip answers.

    Returns
    -------
    dict with:
      - answer_type (str): VALID, SKIPPED, REFUSAL, IRRELEVANT
      - technical_score (float 0-1)
      - communication_score (float 0-1)
      - behavior_score (float 0-1)
      - weighted_score (float 0-1)
      - behavior_flag (str)
      - next_difficulty (str)
      - clarity, depth, confidence, technical_score_int (int 0-10) for backward compat
    """
    logger.info("[DEBUG] Evaluated Answer Length: %d", len(answer))
    answer = _normalize_stt_answer(answer)
    answer_type = classify_answer_type(answer)
    logger.info("AnswerEvaluatorAgent: answer_type=%s", answer_type)

    # ── Short-circuit for non-valid answers ────────────────────────────────
    if answer_type in _OVERRIDE_SCORES:
        result = dict(_OVERRIDE_SCORES[answer_type])
        result["answer_classification"] = answer_type if answer_type in ["skip", "no_knowledge"] else "no_knowledge"
        
        # Force truly blank/no-response answers to be 0 across metrics.
        if not answer.strip():
            result["communication"] = 0
            result["communication_score"] = 0.0
            result["clarity"] = 0
            result["confidence"] = 0
            result["behavior_score"] = 0.0
            result["overall_score"] = 0.0
            result["weighted_score"] = 0.0
        
        logger.info(
            "AnswerEvaluatorAgent: overriding scores for %s answer — tech=%.2f comm=%.2f behav=%.2f",
            answer_type,
            result["technical_score"],
            result["communication_score"],
            result["behavior_score"],
        )
        return result

    # ── Normal LLM evaluation for VALID answers ───────────────────────────
    logger.info("AnswerEvaluatorAgent: evaluating answer (weighted scoring)")

    # NOTE: We cannot change orchestrator/question_generator interfaces.
    # phase/job_role are not currently provided here, so we keep safe defaults.
    prompt = build_evaluator_prompt(
        question=question,
        answer=answer,
        phase="core_technical",
        difficulty=difficulty,
        keywords=None,  # Placeholder for future keyword support
    )

    try:
        response = await llm.ainvoke(prompt)
        content: str = getattr(response, "content", str(response))
        raw = _safe_parse_json(content)
        evaluation = validate_evaluation(raw)

        # Map new structured evaluation to legacy weighted scoring.
        tech = evaluation["correctness"] / 10.0
        comm = evaluation["communication"] / 10.0
        behav = evaluation["confidence"] / 10.0
        weighted = 0.5 * tech + 0.3 * comm + 0.2 * behav

        # Calculate calibrated overall_score (0-10) for UI/Recruiter consumption
        # 50% correctness, 25% depth, 15% communication, 10% confidence
        overall = (
            evaluation["correctness"] * 0.50 +
            evaluation["concept_depth"] * 0.25 +
            evaluation["communication"] * 0.15 +
            evaluation["confidence"] * 0.10
        )

        logger.info(
            "AnswerEvaluatorAgent: correctness=%d depth=%d comm=%d conf=%d severity=%s overall=%.2f",
            evaluation["correctness"],
            evaluation["concept_depth"],
            evaluation["communication"],
            evaluation["confidence"],
            evaluation["severity"],
            overall,
        )

        # Map to requested classifications based on correctness
        ans_class = "strong"
        if evaluation["correctness"] < 4:
            ans_class = "no_knowledge"
        elif 4 <= evaluation["correctness"] <= 6:
            ans_class = "partial"

        return {
            "answer_type": "VALID",
            "answer_classification": ans_class,
            # New structured output
            **evaluation,
            "overall_score": round(overall, 2),
            # Legacy weighted scores (0-1)
            "technical_score": round(tech, 4),
            "communication_score": round(comm, 4),
            "behavior_score": round(behav, 4),
            "weighted_score": round(weighted, 4),
            # Legacy integer scores (0-10) for backward compat
            "clarity": evaluation["communication"],
            "depth": evaluation["concept_depth"],
            "confidence": evaluation["confidence"],
            "technical_score_int": evaluation["correctness"],
            # Keep legacy keys expected by other modules
            "behavior_flag": "neutral",
            "next_difficulty": difficulty,
        }
    except Exception as exc:
        logger.error("AnswerEvaluatorAgent LLM/parse error (returning default evaluation): %s", exc)
        evaluation = default_evaluation()

        tech = evaluation["correctness"] / 10.0
        comm = evaluation["communication"] / 10.0
        behav = evaluation["confidence"] / 10.0
        weighted = 0.5 * tech + 0.3 * comm + 0.2 * behav

        # Map to requested classifications natively
        ans_class = "strong"
        if evaluation["correctness"] < 4:
            ans_class = "no_knowledge"
        elif 4 <= evaluation["correctness"] <= 6:
            ans_class = "partial"

        return {
            "answer_type": "VALID",
            "answer_classification": ans_class,
            **evaluation,
            "technical_score": round(tech, 4),
            "communication_score": round(comm, 4),
            "behavior_score": round(behav, 4),
            "weighted_score": round(weighted, 4),
            "clarity": evaluation["communication"],
            "depth": evaluation["concept_depth"],
            "confidence": evaluation["confidence"],
            "technical_score_int": evaluation["correctness"],
            "behavior_flag": "neutral",
            "next_difficulty": difficulty,
        }
