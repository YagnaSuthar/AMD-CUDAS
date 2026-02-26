"""
Memory / Context Agent.
Maintains a running summary, tracks weak/strong areas, behavioral state,
and approximate token usage across the interview.
"""

import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.Interview.prompts import MEMORY_UPDATE_PROMPT
from app.agents.Interview.utils import parse_json_response
from app.models.interview import InterviewMemory

logger = logging.getLogger(__name__)


async def update_memory(
    session_id: UUID,
    answer: str,
    db: AsyncSession,
    llm: Any,
    behavior: str = "neutral",
) -> Dict[str, Any]:
    """
    Fetch existing memory for the session, incorporate the latest answer
    and behavior, and persist the updated memory.

    Returns
    -------
    dict   {"summary": str, "weak_areas": [...], "strong_areas": [...],
            "last_behavior_state": str, "token_usage": int}
    """
    logger.info("MemoryAgent: updating memory for session %s", session_id)

    # ── Fetch or create memory record ────────────────────────────────────
    mem_result = await db.execute(
        select(InterviewMemory).where(InterviewMemory.session_id == session_id)
    )
    memory: InterviewMemory | None = mem_result.scalar_one_or_none()

    previous_summary = memory.summary if memory else ""
    weak_areas: List[str] = list(memory.weak_areas) if memory and memory.weak_areas else []
    strong_areas: List[str] = list(memory.strong_areas) if memory and memory.strong_areas else []
    current_token_usage = memory.token_usage if memory else 0

    # ── Build prompt & call LLM ──────────────────────────────────────────
    prompt = MEMORY_UPDATE_PROMPT.format(
        previous_summary=previous_summary or "No previous data.",
        weak_areas=", ".join(weak_areas) if weak_areas else "None yet",
        strong_areas=", ".join(strong_areas) if strong_areas else "None yet",
        answer=answer,
        behavior=behavior,
    )

    # Approximate token usage (rough: 1 token ≈ 4 chars)
    prompt_tokens = len(prompt) // 4

    try:
        response = await llm.ainvoke(prompt)
        content: str = getattr(response, "content", str(response))
        result = parse_json_response(content)

        updated_summary = result.get("summary", previous_summary)
        updated_weak = result.get("weak_areas", weak_areas)
        updated_strong = result.get("strong_areas", strong_areas)

        # Approximate completion tokens
        completion_tokens = len(content) // 4
        total_new_tokens = prompt_tokens + completion_tokens
    except Exception as exc:
        logger.error("MemoryAgent LLM error: %s", exc)
        raise exc

    # ── Persist to DB ────────────────────────────────────────────────────
    new_token_total = current_token_usage + total_new_tokens

    if memory is None:
        memory = InterviewMemory(
            session_id=session_id,
            summary=updated_summary,
            weak_areas=updated_weak,
            strong_areas=updated_strong,
            last_behavior_state=behavior,
            token_usage=new_token_total,
        )
        db.add(memory)
    else:
        memory.summary = updated_summary
        memory.weak_areas = updated_weak
        memory.strong_areas = updated_strong
        memory.last_behavior_state = behavior
        memory.token_usage = new_token_total

    await db.flush()

    logger.info("MemoryAgent: memory updated for session %s (tokens=%d)", session_id, new_token_total)
    return {
        "summary": updated_summary,
        "weak_areas": updated_weak,
        "strong_areas": updated_strong,
        "last_behavior_state": behavior,
        "token_usage": new_token_total,
    }
