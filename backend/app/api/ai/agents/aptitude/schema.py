from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, conint


class StartAptitudeRequest(BaseModel):
    total_questions: conint(ge=1, le=50) = Field(default=10)
    category: Optional[str] = Field(default=None)


class AptitudeQuestionResponse(BaseModel):
    session_id: UUID
    question_id: UUID
    question: str
    options: List[str]
    category: str
    difficulty: str
    current_index: int
    total_questions: int


class SubmitAnswerRequest(BaseModel):
    session_id: UUID
    question_id: UUID
    selected_option: str
    time_taken: Optional[int] = None


class SubmitAnswerResponse(BaseModel):
    correct: bool
    correct_answer: str
    explanation: Optional[str] = None
    score: int
    current_index: int
    total_questions: int
    is_completed: bool


class AptitudeAttemptDetail(BaseModel):
    question: str
    your_answer: str
    correct_answer: str
    is_correct: bool
    explanation: Optional[str] = None


class AptitudeReportResponse(BaseModel):
    session_id: UUID
    total_questions: int
    attempted: int
    score: int
    accuracy_percent: float
    category_breakdown: Dict[str, Dict[str, Any]]

    # New detailed fields (backward compatible additions)
    total: int
    accuracy: float
    attempts: List[AptitudeAttemptDetail]
