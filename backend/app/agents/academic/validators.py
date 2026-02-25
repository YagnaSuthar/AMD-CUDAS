"""Validation helpers for academic study planner."""

import json
import re
from typing import Any, Dict


def _validate_plan_schema(plan: dict) -> None:
    allowed_top_keys = {"student_id", "daily_plan", "motivation_note"}
    extra = set(plan.keys()) - allowed_top_keys
    if extra:
        raise ValueError(f"Unexpected top-level keys: {sorted(extra)}")
    if "student_id" not in plan or "daily_plan" not in plan:
        raise ValueError("Missing required keys: student_id and/or daily_plan")
    if not isinstance(plan["student_id"], str) or not plan["student_id"].strip():
        raise ValueError("student_id must be a non-empty string")
    if not isinstance(plan["daily_plan"], list) or len(plan["daily_plan"]) == 0:
        raise ValueError("daily_plan must be a non-empty list")
    for item in plan["daily_plan"]:
        if not isinstance(item, dict):
            raise ValueError("daily_plan items must be objects")
        allowed_item_keys = {"day", "date", "tasks"}
        extra_item = set(item.keys()) - allowed_item_keys
        if extra_item:
            raise ValueError(f"Unexpected daily_plan item keys: {sorted(extra_item)}")
        if not isinstance(item.get("day"), int):
            raise ValueError("daily_plan.day must be int")
        if not isinstance(item.get("date"), str):
            raise ValueError("daily_plan.date must be string YYYY-MM-DD")
        if not isinstance(item.get("tasks"), list) or not all(
            isinstance(t, str) for t in item.get("tasks", [])
        ):
            raise ValueError("daily_plan.tasks must be list[str]")


def _validate_subjects_and_hours(plan: dict, structured_data: dict) -> None:
    allocations = structured_data.get("allocations")
    if not isinstance(allocations, list) or len(allocations) == 0:
        raise ValueError("structured_data.allocations must be a non-empty list")
    expected: dict[str, str] = {}
    for a in allocations:
        if not isinstance(a, dict):
            raise ValueError("allocation entries must be objects")
        subject = a.get("subject")
        allocated = a.get("allocated_hours")
        if not isinstance(subject, str) or subject.strip() == "":
            raise ValueError("allocation.subject must be string")
        if not isinstance(allocated, (int, float)):
            raise ValueError("allocation.allocated_hours must be number")
        expected[subject] = f"{float(allocated):.2f}"
    for day in plan["daily_plan"]:
        tasks_text = "\n".join(day.get("tasks", []))
        for subject, hours in expected.items():
            pattern = rf"\b{re.escape(subject)}\s*:\s*{re.escape(hours)}\b"
            if re.search(pattern, tasks_text) is None:
                raise ValueError(
                    f"Missing or changed allocation for subject '{subject}'. "
                    f"Expected to find '{subject}: {hours}' in tasks."
                )
