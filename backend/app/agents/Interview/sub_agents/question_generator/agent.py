"""
Dynamic Question Generator Agent.
Generates contextually-relevant interview questions at a specified difficulty.
"""

import logging
from typing import Any, Dict

from app.agents.Interview.prompts import QUESTION_GENERATION_PROMPT
from app.agents.Interview.utils import parse_json_response

logger = logging.getLogger(__name__)


async def generate_question(
    context: str,
    difficulty: str,
    llm: Any,
) -> Dict[str, str]:
    """
    Generate a single interview question based on session context and
    requested difficulty level.

    Returns
    -------
    dict   {"question": str, "topic": str, "difficulty": str}
    """
    logger.info("QuestionGeneratorAgent: generating %s question", difficulty)

    prompt = QUESTION_GENERATION_PROMPT.format(
        context=context,
        difficulty=difficulty,
    )

    try:
        response = await llm.ainvoke(prompt)
        content: str = getattr(response, "content", str(response))
        result = parse_json_response(content)
        logger.info("QuestionGeneratorAgent: generated question on topic '%s'", result.get("topic"))
        return {
            "question": result.get("question", ""),
            "topic": result.get("topic", "general"),
            "difficulty": result.get("difficulty", difficulty),
        }
    except Exception as exc:
        logger.error("QuestionGeneratorAgent LLM error: %s", exc)
        raise exc
