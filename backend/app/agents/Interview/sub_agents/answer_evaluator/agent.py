"""
Answer Evaluation Agent.
Evaluates a candidate's answer on clarity, depth, confidence, technical accuracy,
and classifies behavioral tone (polite/arrogant/neutral).
"""

import logging
from typing import Any, Dict

from app.agents.Interview.prompts import ANSWER_EVALUATION_PROMPT
from app.agents.Interview.utils import parse_json_response

logger = logging.getLogger(__name__)


async def evaluate_answer(
    question: str,
    answer: str,
    llm: Any,
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
    )

    try:
        response = await llm.ainvoke(prompt)
        content: str = getattr(response, "content", str(response))
        result = parse_json_response(content)

        clarity = int(result.get("clarity", 5))
        depth = int(result.get("depth", 5))
        confidence = int(result.get("confidence", 5))
        technical_score = int(result.get("technical_score", 5))
        behavior_flag = result.get("behavior_flag", "neutral")
        next_difficulty = result.get("next_difficulty", "medium")

        # Validate behavior_flag
        if behavior_flag not in ("polite", "arrogant", "neutral"):
            behavior_flag = "neutral"

        logger.info(
            "AnswerEvaluatorAgent: c=%s d=%s conf=%s tech=%s behavior=%s",
            clarity, depth, confidence, technical_score, behavior_flag,
        )

        return {
            "clarity": clarity,
            "depth": depth,
            "confidence": confidence,
            "technical_score": technical_score,
            "behavior_flag": behavior_flag,
            "next_difficulty": next_difficulty,
        }
    except Exception as exc:
        logger.error("AnswerEvaluatorAgent LLM error: %s", exc)
        raise exc
