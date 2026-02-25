"""Adaptive priority adjustments for academic study planner.

Pure deterministic logic; no FastAPI/DB imports.
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def adjust_priorities(
    subjects: List[Dict],
    progress_data: Dict,
) -> List[Dict]:
    """
    Adjust subject priorities based on progress and urgency.

    Parameters
    ----------
    subjects : list[dict]
        Each dict must include: priority, credit, marks, days_left, and subject/name.
    progress_data : dict
        Expected keys: completion_ratio, weak_subjects, strong_subjects, missed_subjects.

    Returns
    -------
    list[dict]
        Updated subjects with modified 'priority' field only.
    """
    completion_ratio = progress_data.get("completion_ratio", 0.0)
    topics_completed = progress_data.get("topics_completed", [])
    daily_available_hours = progress_data.get("daily_available_hours", 1)

    # Determine global urgency multiplier
    days_left_values = [s.get("days_left", 999) for s in subjects]
    min_days_left = min(days_left_values) if days_left_values else 999
    urgency_multiplier = 1.25 if min_days_left < 5 else 1.0
    logger.debug("Urgency multiplier: %.2f (days_left=%d)", urgency_multiplier, min_days_left)

    adjusted = []
    for s in subjects:
        subject_name = s.get("subject") or s.get("name")
        base_priority = s.get("priority", 0.0)
        new_priority = base_priority

        # Rule: weak subjects (completion_ratio < 0.6) get +20%
        if completion_ratio < 0.6:
            new_priority *= 1.20

        # Rule: skipped subjects get +15%
        if subject_name not in topics_completed:
            new_priority *= 1.15

        # Rule: high completion (>90%) get -10%
        if completion_ratio > 0.9:
            new_priority *= 0.90

        # Apply global urgency multiplier
        new_priority *= urgency_multiplier

        # Defensive: never allow negative priority
        new_priority = max(0.0, new_priority)

        # Preserve other fields
        updated = dict(s)
        updated["priority"] = new_priority
        adjusted.append(updated)

    return adjusted
