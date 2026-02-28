"""
Dynamic Question Generator Agent.
Generates context-aware, resume-aware interview questions based on student
skills, previous answer, behavior, and memory — token efficient.
"""

import logging
from typing import Any, Dict

from app.agents.Interview.prompts import (
    QUESTION_GENERATION_PROMPT,
    RESUME_PROJECT_QUESTION_PROMPT,
    RESUME_NO_PROJECT_QUESTION_PROMPT,
)
from app.agents.Interview.utils import parse_json_response

logger = logging.getLogger(__name__)


async def generate_question(
    context: str = "",
    difficulty: str = "medium",
    llm: Any = None,
    *,
    last_question: str = "",
    last_answer_summary: str = "",
    behavior: str = "neutral",
    skill_summary: str = "",
    resume_has_projects: bool = False,
    resume_project_summary: str = "",
    is_first_question: bool = False,
    job_description: str = "",
) -> Dict[str, str]:
    """
    Generate a single interview question based on dynamic context.

    For the FIRST question:
      - If resume has projects → use project-specific prompt
      - If no projects → use "no projects" prompt

    For follow-up questions:
      - Use context-aware prompt with last Q/A + behavior + resume context

    Only sends minimal data to the LLM for token efficiency.

    Parameters
    ----------
    context : str
        Legacy context string (used as skill_summary fallback).
    difficulty : str
        Target difficulty level.
    llm : Any
        LangChain LLM instance.
    last_question : str
        The previous question text.
    last_answer_summary : str
        Summarized version of the last answer.
    behavior : str
        Current behavioral classification.
    skill_summary : str
        Comma-separated student skills.
    resume_has_projects : bool
        Whether the student's resume includes project details.
    resume_project_summary : str
        Brief summary of the student's projects.
    is_first_question : bool
        Whether this is the first question of the interview.

    Returns
    -------
    dict   {"question": str, "topic": str, "difficulty": str}
    """
    logger.info("QuestionGeneratorAgent: generating %s question (first=%s)", difficulty, is_first_question)

    # Use skill_summary if provided, fall back to legacy context
    effective_skills = skill_summary or context

    # ── Choose the right prompt ──────────────────────────────────────────
    if is_first_question:
        if resume_has_projects and resume_project_summary:
            prompt = RESUME_PROJECT_QUESTION_PROMPT.format(
                job_description=job_description or "Not specified",
                skill_summary=effective_skills,
                project_summary=resume_project_summary,
                difficulty=difficulty,
            )
        else:
            prompt = RESUME_NO_PROJECT_QUESTION_PROMPT.format(
                job_description=job_description or "Not specified",
                skill_summary=effective_skills,
                difficulty=difficulty,
            )
    else:
        # Follow-up question: context-aware
        resume_context = ""
        if resume_has_projects and resume_project_summary:
            resume_context = f"Student has projects: {resume_project_summary}"
        elif not resume_has_projects:
            resume_context = "Student has no project experience."

        prompt = QUESTION_GENERATION_PROMPT.format(
            job_description=job_description or "Not specified",
            skill_summary=effective_skills,
            last_question=last_question or "None (first question)",
            last_answer_summary=last_answer_summary or "None (first question)",
            behavior=behavior,
            difficulty=difficulty,
            resume_context=resume_context,
        )

    try:
        response = await llm.ainvoke(prompt)
        content: str = getattr(response, "content", str(response))
        result = parse_json_response(content)
        logger.info(
            "QuestionGeneratorAgent: generated question on topic '%s'",
            result.get("topic"),
        )
        return {
            "question": result.get("question", ""),
            "topic": result.get("topic", "general"),
            "difficulty": result.get("difficulty", difficulty),
        }
    except Exception as exc:
        logger.error("QuestionGeneratorAgent LLM error: %s", exc)
        raise exc
