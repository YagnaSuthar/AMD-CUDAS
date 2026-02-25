from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class StudyPlanRequest(BaseModel):
    student_id: str
    daily_available_hours: int


class StudyProgressUpdate(BaseModel):
    student_id: str
    completed_hours: int
    topics_completed: list[str]


class StudyPlanDay(BaseModel):
    day: int
    date: date
    tasks: list[str]


class StudyPlanResponse(BaseModel):
    student_id: str
    daily_plan: list[StudyPlanDay]
    motivation_note: Optional[str] = None
