"""
<<<<<<< HEAD
Dynamic Question Generator Agent.
Generates context-aware, resume-aware interview questions based on student
skills, previous answer, behavior, and memory — token efficient.
=======
Dynamic Question Generator Agent (RAG-Enhanced).
Generates context-aware, resume-aware interview questions using:
- RAG context from pgvector (relevant CV chunks)
- Follow-up intelligence (related concepts from answer)
- Adaptive difficulty
- Behavior-reactive logic
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
"""

import logging
from typing import Any, Dict

from app.agents.Interview.prompts import (
    QUESTION_GENERATION_PROMPT,
    RESUME_PROJECT_QUESTION_PROMPT,
    RESUME_NO_PROJECT_QUESTION_PROMPT,
<<<<<<< HEAD
=======
    RAG_QUESTION_GENERATION_PROMPT,
    RAG_FOLLOWUP_PROMPT,
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
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
<<<<<<< HEAD
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
=======
    rag_context: str = "",
    followup_context: str = "",
    last_answer: str = "",
) -> Dict[str, str]:
    """
    Generate a single interview question.

    Priority for context:
    1. If followup_context available → RAG follow-up prompt (related concepts)
    2. If rag_context available → RAG-enhanced prompt (CV chunks)
    3. If first question → resume-aware prompt
    4. Fallback → standard context-aware prompt

    Parameters
    ----------
    rag_context : str
        Retrieved CV chunks from pgvector for context.
    followup_context : str
        Related concepts retrieved after candidate's answer.
    last_answer : str
        Raw last answer text (for follow-up intelligence).
    """
    logger.info(
        "QuestionGeneratorAgent: generating %s question (first=%s, rag=%s, followup=%s)",
        difficulty, is_first_question, bool(rag_context), bool(followup_context),
    )

    effective_skills = skill_summary or context

    # ── Choose the right prompt ──────────────────────────────────────────

    if is_first_question:
        # First question — use resume-aware prompts
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
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
<<<<<<< HEAD
    else:
        # Follow-up question: context-aware
=======
    elif followup_context and last_answer:
        # Follow-up intelligence: use answer + related CV concepts
        prompt = RAG_FOLLOWUP_PROMPT.format(
            last_question=last_question or "None",
            last_answer=last_answer,
            difficulty=difficulty,
            followup_context=followup_context,
        )
    elif rag_context:
        # RAG-enhanced: use relevant CV chunks
        prompt = RAG_QUESTION_GENERATION_PROMPT.format(
            job_description=job_description or "Not specified",
            skill_summary=effective_skills,
            last_question=last_question or "None (first question)",
            last_answer_summary=last_answer_summary or "None (first question)",
            behavior=behavior,
            difficulty=difficulty,
            rag_context=rag_context,
        )
    else:
        # Standard context-aware prompt (fallback)
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
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
