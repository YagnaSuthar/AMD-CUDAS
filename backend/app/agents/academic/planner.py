"""Hour allocation planner for academic study planning.

Pure function: no FastAPI/DB imports.
"""

from typing import List, Dict


def allocate_hours(subjects_with_priority: List[Dict], daily_available_hours: int) -> List[Dict]:
    """
    Allocate daily hours proportionally to subject priorities.

    Parameters
    ----------
    subjects_with_priority : list of dict
        Each dict must contain 'priority' and original subject fields.
    daily_available_hours : int

    Returns
    -------
    list of dict
        Each dict includes allocation details:
        - subject
        - allocated_hours (rounded to 2 decimals)
        - priority
        - credit
        - marks
        - days_left
    """
    total_priority = sum(s.get("priority", 0) for s in subjects_with_priority)
    allocations = []
    for s in subjects_with_priority:
        ratio = (s.get("priority", 0) / total_priority) if total_priority > 0 else (1 / len(subjects_with_priority))
        allocated = round(daily_available_hours * ratio, 2)
        allocations.append(
            {
                "subject": s.get("subject") or s.get("name"),
                "allocated_hours": allocated,
                "priority": round(s.get("priority", 0), 4),
                "credit": s.get("credit"),
                "marks": s.get("marks"),
                "days_left": s.get("days_left"),
            }
        )
    return allocations
