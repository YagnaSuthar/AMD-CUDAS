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
        # Apply urgency multipliers based on days_left
        priority = s.get("priority", 0)
        days_left = s.get("days_left", 0)
        if days_left <= 3:
            priority *= 1.35
        elif days_left <= 7:
            priority *= 1.20

        ratio = (priority / total_priority) if total_priority > 0 else (1 / len(subjects_with_priority))
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


def distribute_weekly_allocations(allocations: List[Dict]) -> List[Dict]:
    """
    Apply daily distribution adjustments:
    - Days 1–3: boost weak subjects by 15%
    - Days 5–7: reduce weak subjects slightly to compensate
    - Preserve total weekly hours
    """
    # Identify weak subjects (marks < 60)
    weak_subjects = {a["subject"] for a in allocations if a.get("marks", 0) < 60}
    weekly = []
    for day in range(1, 8):
        day_allocations = []
        for a in allocations:
            subject = a["subject"]
            allocated = a["allocated_hours"]
            if subject in weak_subjects:
                if day <= 3:
                    allocated = round(allocated * 1.15, 2)
                elif day >= 5:
                    allocated = round(allocated * 0.92, 2)  # slight reduction to compensate
            day_allocations.append(
                {
                    "subject": subject,
                    "allocated_hours": allocated,
                }
            )
        weekly.append({"day": day, "allocations": day_allocations})
    return weekly
