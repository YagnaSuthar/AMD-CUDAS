"""Priority calculation for academic study planning.

Pure function: no FastAPI/DB imports.
"""

from typing import List, Dict


def compute_priorities(subjects: List[Dict]) -> List[Dict]:
    """
    Compute priority for each subject using:
        priority = (credit * 2) + ((100 - marks)/10) + (30/days_left)

    Parameters
    ----------
    subjects : list of dict
        Each dict must contain: credit, marks, days_left

    Returns
    -------
    list of dict
        Each dict includes original fields plus 'priority'.
    """
    enriched = []
    for s in subjects:
        credit = int(s.get("credit", 0))
        marks = int(s.get("marks", 0))
        days_left = max(int(s.get("days_left", 1)), 1)
        priority = (credit * 2) + ((100 - marks) / 10) + (30 / days_left)
        enriched.append({**s, "priority": priority})
    return enriched
