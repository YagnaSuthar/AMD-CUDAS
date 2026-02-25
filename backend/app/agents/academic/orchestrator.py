"""Academic study plan orchestrator.

Orchestrates priority → planner → prompt → LLM → validation.
No FastAPI/DB imports.
"""

import asyncio
import logging
from typing import Any, Callable, Dict

from app.agents.Interview.utils import parse_json_response

from .adaptive_engine import adjust_priorities
from .cognitive_load import balance_schedule
from .planner import allocate_hours
from .priority_engine import compute_priorities
from .progress_analyzer import analyze_progress
from .validators import _validate_plan_schema, _validate_subjects_and_hours

logger = logging.getLogger(__name__)


def _format_hours_minutes(hours_float: float) -> str:
    total_minutes = int(round(float(hours_float) * 60))
    h = total_minutes // 60
    m = total_minutes % 60
    if h > 0 and m == 0:
        return f"{h} hours"
    if h == 0:
        return f"{m} minutes"
    return f"{h} hours {m} minutes"


def _apply_display_formatting(plan: dict, structured_data: dict) -> None:
    allocations = structured_data.get("allocations")
    if not isinstance(allocations, list) or not allocations:
        return

    expected: dict[str, str] = {}
    display: dict[str, str] = {}
    for a in allocations:
        if not isinstance(a, dict):
            continue
        subject = a.get("subject")
        allocated = a.get("allocated_hours")
        if not isinstance(subject, str) or not isinstance(allocated, (int, float)):
            continue
        hours_str = f"{float(allocated):.2f}"
        expected[subject] = hours_str
        display[subject] = _format_hours_minutes(float(allocated))

    for day in plan.get("daily_plan", []):
        tasks = day.get("tasks")
        if not isinstance(tasks, list):
            continue
        new_tasks: list[str] = []
        for t in tasks:
            if not isinstance(t, str):
                new_tasks.append(t)
                continue
            updated_t = t
            for subject, hours_str in expected.items():
                needle = f"{subject}: {hours_str}"
                if needle in updated_t:
                    updated_t = updated_t.replace(
                        needle,
                        f"{subject} – {display.get(subject, hours_str)}",
                    )
            new_tasks.append(updated_t)
        day["tasks"] = new_tasks


async def generate_study_plan(
    student_data: dict,
    daily_available_hours: int,
    subjects: list[dict],
    llm_callable: Callable[[list[dict]], Any],
    progress_data: dict | None = None,
) -> dict:
    """
    Orchestrates the full study plan generation flow.

    Parameters
    ----------
    student_data : dict
        Student information (id, name, email).
    daily_available_hours : int
    subjects : list of dict
        Each dict: subject, credit, marks, days_left.
    llm_callable : async callable
        Expects list of LangChain messages.
    progress_data : dict | None
        If provided, triggers adaptive adjustments.

    Returns
    -------
    dict
        Validated study plan JSON.
    """
    # 1) Compute base priorities
    enriched = compute_priorities(subjects)

    # 2) Adaptive adjustments if progress_data provided
    if progress_data is not None:
        logger.info("Adaptive mode triggered for student %s", student_data.get("student_id"))
        analysis = analyze_progress(
            daily_available_hours=progress_data.get("daily_available_hours", daily_available_hours),
            completed_hours=progress_data.get("completed_hours", 0),
            topics_completed=progress_data.get("topics_completed", []),
            subjects=enriched,
        )
        enriched = adjust_priorities(enriched, analysis)
    else:
        logger.info("Baseline mode for student %s", student_data.get("student_id"))
        analysis = {}

    # 3) Allocate hours
    allocations = allocate_hours(enriched, daily_available_hours)

    # Defensive: ensure allocations not empty
    if not allocations:
        raise ValueError("Allocation produced empty list; cannot proceed to LLM.")

    # 4) Apply cognitive load balancing
    allocations = balance_schedule(allocations)

    structured_data = {
        "student": student_data,
        "daily_available_hours": daily_available_hours,
        "allocations": allocations,
        "performance_summary": analysis,
    }

    # 5) Build prompts
    from .prompts import build_llm_messages
    messages = build_llm_messages(structured_data)

    # 6) Call LLM with retry
    last_err: Exception | None = None
    for attempt in range(1, 4):
        try:
            resp = await asyncio.to_thread(llm_callable, messages)
            content = getattr(resp, "content", "")
            data: dict[str, Any] = parse_json_response(content)
            if not isinstance(data, dict):
                raise ValueError("LLM response is not a JSON object")

            _validate_plan_schema(data)
            _validate_subjects_and_hours(data, structured_data)
            _apply_display_formatting(data, structured_data)
            return data
        except Exception as exc:
            last_err = exc
            await asyncio.sleep(0.6 * attempt)

    raise RuntimeError(f"Failed to generate valid JSON study plan after retries: {last_err}")
