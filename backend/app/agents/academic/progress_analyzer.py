"""Progress analysis for adaptive academic coaching.

Pure logic; no framework imports.
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def analyze_progress(
    daily_available_hours: int,
    completed_hours: int,
    topics_completed: List[str],
    subjects: List[Dict],
) -> Dict:
    """
    Analyze student progress and categorize subjects.

    Parameters
    ----------
    daily_available_hours : int
    completed_hours : int
    topics_completed : list[str]
        Subject names completed in the latest session.
    subjects : list[dict]
        Each dict must include marks and a subject/name field.

    Returns
    -------
    dict
        {
            "completion_ratio": float,
            "missed_subjects": list[str],
            "strong_subjects": list[str],
            "weak_subjects": list[str],
        }
    """
    # Completion ratio with clamping
    completion_ratio = completed_hours / daily_available_hours if daily_available_hours > 0 else 0.0
    completion_ratio = max(0.0, min(1.0, completion_ratio))
    logger.debug("Completion ratio: %.2f", completion_ratio)

    # Categorize subjects
    weak_subjects = []
    strong_subjects = []
    for s in subjects:
        subject_name = s.get("subject") or s.get("name")
        marks = s.get("marks", 0)
        if marks < 60:
            weak_subjects.append(subject_name)
        elif marks >= 75:
            strong_subjects.append(subject_name)

    # Missed subjects: those not in topics_completed
    all_subject_names = {s.get("subject") or s.get("name") for s in subjects}
    missed_subjects = sorted(list(all_subject_names - set(topics_completed)))

    return {
        "completion_ratio": completion_ratio,
        "missed_subjects": missed_subjects,
        "strong_subjects": strong_subjects,
        "weak_subjects": weak_subjects,
    }
