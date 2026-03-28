"""Cognitive load balancing for schedule adjustments.

Pure deterministic logic; no framework imports.
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def balance_schedule(
    allocations: List[Dict],
) -> List[Dict]:
    """
    Adjust allocations to avoid cognitive overload.

    Parameters
    ----------
    allocations : list[dict]
        Each dict includes 'allocated_hours', 'priority', and 'subject'.

    Returns
    -------
    list[dict]
        Adjusted allocations with modified 'allocated_hours' only.
    """
    # Defensive: if allocations empty, return as-is
    if not allocations:
        logger.warning("balance_schedule called with empty allocations")
        return allocations

    # Identify heavy subjects (>2.0 hours)
    heavy = [a for a in allocations if a.get("allocated_hours", 0) > 2.0]

    # Rule: no more than 2 heavy subjects per day
    if len(heavy) <= 2:
        logger.debug("No cognitive load adjustment needed (heavy subjects=%d)", len(heavy))
        return allocations

    # Find the lowest-priority heavy subject
    lowest_heavy = min(heavy, key=lambda a: a.get("priority", 0))
    subject_to_reduce = lowest_heavy.get("subject")

    # Reduce its allocation by 10%
    adjusted: list[dict] = []
    removed_hours = 0.0
    for a in allocations:
        updated = dict(a)
        if updated.get("subject") == subject_to_reduce:
            original = float(updated.get("allocated_hours", 0) or 0.0)
            reduced = round(original * 0.90, 2)
            reduced = max(0.0, reduced)
            removed_hours = max(0.0, round(original - reduced, 2))
            updated["allocated_hours"] = reduced
            logger.debug(
                "Reduced allocation for %s: %.2f -> %.2f (removed=%.2f)",
                subject_to_reduce,
                original,
                reduced,
                removed_hours,
            )
        adjusted.append(updated)

    # Redistribute removed hours proportionally to lighter subjects (<= 2.0 hours)
    if removed_hours > 0:
        light_indices: list[int] = [
            i
            for i, a in enumerate(adjusted)
            if (a.get("subject") != subject_to_reduce)
            and float(a.get("allocated_hours", 0) or 0.0) <= 2.0
        ]

        if light_indices:
            light_total = sum(float(adjusted[i].get("allocated_hours", 0) or 0.0) for i in light_indices)
            if light_total <= 0:
                # Fallback: split evenly if all light allocations are 0
                per = round(removed_hours / len(light_indices), 2)
                remainder = round(removed_hours - (per * len(light_indices)), 2)
                for j, i in enumerate(light_indices):
                    inc = per + (remainder if j == 0 else 0.0)
                    adjusted[i]["allocated_hours"] = round(
                        float(adjusted[i].get("allocated_hours", 0) or 0.0) + inc,
                        2,
                    )
            else:
                # Proportional redistribution with rounding; push remainder into first light subject
                increments: list[float] = []
                for i in light_indices:
                    base = float(adjusted[i].get("allocated_hours", 0) or 0.0)
                    inc = round(removed_hours * (base / light_total), 2)
                    increments.append(inc)

                distributed = round(sum(increments), 2)
                remainder = round(removed_hours - distributed, 2)
                if remainder != 0 and increments:
                    increments[0] = round(increments[0] + remainder, 2)

                for inc, i in zip(increments, light_indices):
                    adjusted[i]["allocated_hours"] = round(
                        float(adjusted[i].get("allocated_hours", 0) or 0.0) + inc,
                        2,
                    )
        else:
            logger.debug("No light subjects available for redistribution; total hours may decrease")

    # Rule: ensure no subject appears 3 consecutive days (assume 7-day plan)
    # Since we only have allocations per subject, we cannot enforce day-level constraints here.
    # This rule would require daily plan data; we leave it for the scheduler layer.

    return adjusted
