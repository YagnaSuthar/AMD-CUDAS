"""
Answer Evaluation Agent.
Evaluates a candidate's answer against the question on multiple dimensions
and recommends the next difficulty level.
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
    Evaluate the candidate's answer for clarity, depth, and confidence.

    Returns
    -------
    dict   {"clarity": int, "depth": int, "confidence": int, "next_difficulty": str}
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
        logger.info("AnswerEvaluatorAgent: scores c=%s d=%s conf=%s",
                     result.get("clarity"), result.get("depth"), result.get("confidence"))
        return {
            "clarity": int(result.get("clarity", 5)),
            "depth": int(result.get("depth", 5)),
            "confidence": int(result.get("confidence", 5)),
            "next_difficulty": result.get("next_difficulty", "medium"),
        }
    except Exception as exc:
        logger.error("AnswerEvaluatorAgent LLM error: %s", exc)
        raise exc
