"""
<<<<<<< HEAD
Answer Evaluation Agent.
Evaluates a candidate's answer on clarity, depth, confidence, technical accuracy,
and classifies behavioral tone (polite/arrogant/neutral).
"""

import logging
from typing import Any, Dict

from app.agents.Interview.prompts import ANSWER_EVALUATION_PROMPT
=======
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
from typing import Any, Dict

from app.agents.Interview.prompts import WEIGHTED_EVALUATION_PROMPT
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
from app.agents.Interview.utils import parse_json_response

logger = logging.getLogger(__name__)

<<<<<<< HEAD
=======
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
]

_SKIP_RE = re.compile("|".join(SKIP_PATTERNS), re.IGNORECASE)


def classify_answer_type(answer: str) -> str:
    """Classify the answer into one of: VALID, SKIPPED, REFUSAL, IRRELEVANT.

    Currently detects SKIPPED via keyword patterns.
    Short answers (< 8 words) that match skip patterns are classified as SKIPPED.
    Very short answers (< 3 words) without skip patterns are IRRELEVANT.
    """
    text = answer.strip()

    if not text:
        return "SKIPPED"

    word_count = len(text.split())

    # Check for skip/refusal phrases
    if _SKIP_RE.search(text):
        # Short answers with skip keywords → SKIPPED
        if word_count < 25:
            return "SKIPPED"
        # Longer answers that happen to contain a skip word but also have
        # real content should still be evaluated by the LLM.

    # Very short answers with no real content
    if word_count < 3:
        return "IRRELEVANT"

    return "VALID"


# ── Hardcoded scores for non-valid answers ────────────────────────────────

_OVERRIDE_SCORES: Dict[str, Dict[str, Any]] = {
    "SKIPPED": {
        "technical_score": 0.0,
        "communication_score": 0.2,
        "behavior_score": 0.2,
        "weighted_score": 0.0 * 0.5 + 0.2 * 0.3 + 0.2 * 0.2,  # 0.10
        "behavior_flag": "neutral",
        "next_difficulty": "easy",
        "clarity": 2,
        "depth": 0,
        "confidence": 2,
        "technical_score_int": 0,
    },
    "REFUSAL": {
        "technical_score": 0.0,
        "communication_score": 0.2,
        "behavior_score": 0.2,
        "weighted_score": 0.10,
        "behavior_flag": "neutral",
        "next_difficulty": "easy",
        "clarity": 2,
        "depth": 0,
        "confidence": 2,
        "technical_score_int": 0,
    },
    "IRRELEVANT": {
        "technical_score": 0.0,
        "communication_score": 0.1,
        "behavior_score": 0.3,
        "weighted_score": 0.0 * 0.5 + 0.1 * 0.3 + 0.3 * 0.2,  # 0.09
        "behavior_flag": "neutral",
        "next_difficulty": "easy",
        "clarity": 1,
        "depth": 0,
        "confidence": 3,
        "technical_score_int": 0,
    },
}

>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a

async def evaluate_answer(
    question: str,
    answer: str,
    llm: Any,
<<<<<<< HEAD
) -> Dict[str, Any]:
    """
    Evaluate the candidate's answer for clarity, depth, confidence,
    technical accuracy, and behavioral tone.

    Returns
    -------
    dict   {"clarity": int, "depth": int, "confidence": int,
            "technical_score": int, "behavior_flag": str, "next_difficulty": str}
    """
    logger.info("AnswerEvaluatorAgent: evaluating answer")

    prompt = ANSWER_EVALUATION_PROMPT.format(
        question=question,
        answer=answer,
=======
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
    answer_type = classify_answer_type(answer)
    logger.info("AnswerEvaluatorAgent: answer_type=%s", answer_type)

    # ── Short-circuit for non-valid answers ────────────────────────────────
    if answer_type in _OVERRIDE_SCORES:
        result = dict(_OVERRIDE_SCORES[answer_type])
        result["answer_type"] = answer_type
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

    prompt = WEIGHTED_EVALUATION_PROMPT.format(
        question=question,
        answer=answer,
        difficulty=difficulty,
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
    )

    try:
        response = await llm.ainvoke(prompt)
        content: str = getattr(response, "content", str(response))
        result = parse_json_response(content)

<<<<<<< HEAD
        clarity = int(result.get("clarity", 5))
        depth = int(result.get("depth", 5))
        confidence = int(result.get("confidence", 5))
        technical_score = int(result.get("technical_score", 5))
        behavior_flag = result.get("behavior_flag", "neutral")
        next_difficulty = result.get("next_difficulty", "medium")

=======
        # Extract 0-1 scores
        tech = float(result.get("technical_score", 0.5))
        comm = float(result.get("communication_score", 0.5))
        behav = float(result.get("behavior_score", 0.5))
        behavior_flag = result.get("behavior_flag", "neutral")
        next_difficulty = result.get("next_difficulty", "medium")

        # Clamp to 0-1
        tech = max(0.0, min(1.0, tech))
        comm = max(0.0, min(1.0, comm))
        behav = max(0.0, min(1.0, behav))

        # Compute weighted score
        weighted = 0.5 * tech + 0.3 * comm + 0.2 * behav

>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
        # Validate behavior_flag
        if behavior_flag not in ("polite", "arrogant", "neutral"):
            behavior_flag = "neutral"

<<<<<<< HEAD
        logger.info(
            "AnswerEvaluatorAgent: c=%s d=%s conf=%s tech=%s behavior=%s",
            clarity, depth, confidence, technical_score, behavior_flag,
        )

        return {
            "clarity": clarity,
            "depth": depth,
            "confidence": confidence,
            "technical_score": technical_score,
=======
        # Convert to integer scores for backward compatibility (0-10 scale)
        clarity_int = int(round(comm * 10))
        depth_int = int(round(tech * 10))
        confidence_int = int(round(behav * 10))
        technical_int = int(round(tech * 10))

        logger.info(
            "AnswerEvaluatorAgent: tech=%.2f comm=%.2f behav=%.2f weighted=%.2f behavior=%s",
            tech, comm, behav, weighted, behavior_flag,
        )

        return {
            "answer_type": "VALID",
            # New weighted scores (0-1)
            "technical_score": tech,
            "communication_score": comm,
            "behavior_score": behav,
            "weighted_score": round(weighted, 4),
            # Legacy integer scores (0-10) for backward compat
            "clarity": clarity_int,
            "depth": depth_int,
            "confidence": confidence_int,
            "technical_score_int": technical_int,
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
            "behavior_flag": behavior_flag,
            "next_difficulty": next_difficulty,
        }
    except Exception as exc:
        logger.error("AnswerEvaluatorAgent LLM error: %s", exc)
        raise exc
