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
    adjusted = []
    for a in allocations:
        updated = dict(a)
        if updated.get("subject") == subject_to_reduce:
            original = updated.get("allocated_hours", 0)
            updated["allocated_hours"] = round(original * 0.90, 2)
            # Defensive: ensure non-negative
            updated["allocated_hours"] = max(0.0, updated["allocated_hours"])
            logger.debug(
                "Reduced allocation for %s: %.2f -> %.2f",
                subject_to_reduce,
                original,
                updated["allocated_hours"],
            )
        adjusted.append(updated)

    # Rule: ensure no subject appears 3 consecutive days (assume 7-day plan)
    # Since we only have allocations per subject, we cannot enforce day-level constraints here.
    # This rule would require daily plan data; we leave it for the scheduler layer.

    return adjusted
