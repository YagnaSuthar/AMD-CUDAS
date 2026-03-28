"""Academic agent business logic module."""

from .adaptive_engine import adjust_priorities
from .cognitive_load import balance_schedule
from .orchestrator import generate_study_plan
from .priority_engine import compute_priorities
from .planner import allocate_hours
from .prompts import STUDY_PLAN_SYSTEM_PROMPT, STUDY_PLAN_USER_PROMPT, build_llm_messages
from .progress_analyzer import analyze_progress
from .validators import _validate_plan_schema, _validate_subjects_and_hours

__all__ = [
    "adjust_priorities",
    "balance_schedule",
    "generate_study_plan",
    "compute_priorities",
    "allocate_hours",
    "STUDY_PLAN_SYSTEM_PROMPT",
    "STUDY_PLAN_USER_PROMPT",
    "build_llm_messages",
    "analyze_progress",
    "_validate_plan_schema",
    "_validate_subjects_and_hours",
]
