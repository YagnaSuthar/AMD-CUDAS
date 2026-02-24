"""
Pydantic schemas for the interview system.
Covers all route request/response contracts and internal agent I/O types.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════
#  Route-level Request / Response Schemas
# ═══════════════════════════════════════════════════════════════════════════


class StartInterviewRequest(BaseModel):
    """POST /interview/start"""
    student_id: uuid.UUID
    job_role: str = Field(..., min_length=1, max_length=255)


class StartInterviewResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    profile: ProfileOutput
    first_question: QuestionOutput


class NextQuestionRequest(BaseModel):
    """POST /interview/next"""
    student_id: uuid.UUID
    session_id: uuid.UUID


class NextQuestionResponse(BaseModel):
    question: QuestionOutput
    difficulty: str
    question_number: int


class SubmitAnswerRequest(BaseModel):
    """POST /interview/answer"""
    student_id: uuid.UUID
    session_id: uuid.UUID
    question_id: uuid.UUID
    answer_text: str = Field(..., min_length=1)
    audio_path: Optional[str] = None


class SubmitAnswerResponse(BaseModel):
    evaluation: EvaluationOutput
    memory: MemoryOutput
    next_action: str  # "ask_question" | "end"
    next_difficulty: str
    next_question: Optional[QuestionOutput] = None


class EndInterviewRequest(BaseModel):
    """POST /interview/end"""
    student_id: uuid.UUID
    session_id: uuid.UUID


class EndInterviewResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    report: FeedbackOutput


class InterviewReportResponse(BaseModel):
    """GET /interview/report/{session_id}"""
    session_id: uuid.UUID
    final_score: float
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str


# ═══════════════════════════════════════════════════════════════════════════
#  Orchestrator I/O
# ═══════════════════════════════════════════════════════════════════════════


class OrchestratorInput(BaseModel):
    student_id: uuid.UUID
    session_id: uuid.UUID
    last_answer: str = ""


class OrchestratorOutput(BaseModel):
    next_agent: str
    difficulty: str
    action: str  # "ask_question" | "evaluate" | "end"


# ═══════════════════════════════════════════════════════════════════════════
#  Agent-level Output Schemas
# ═══════════════════════════════════════════════════════════════════════════


class ProfileOutput(BaseModel):
    skills: List[str] = []
    experience_level: str = "junior"
    domains: List[str] = ["general"]


class QuestionOutput(BaseModel):
    question_id: Optional[uuid.UUID] = None
    question: str
    topic: str
    difficulty: str


class EvaluationOutput(BaseModel):
    clarity: int = Field(ge=1, le=10)
    depth: int = Field(ge=1, le=10)
    confidence: int = Field(ge=1, le=10)
    next_difficulty: str = "medium"


class MemoryOutput(BaseModel):
    summary: str = ""
    weak_areas: List[str] = []
    strong_areas: List[str] = []


class STTOutput(BaseModel):
    transcript: str
    confidence: float = Field(ge=0.0, le=1.0)


class TTSOutput(BaseModel):
    audio_path: str


class FeedbackOutput(BaseModel):
    final_score: float = Field(ge=0.0, le=10.0)
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendation: str = ""


# ── Rebuild forward refs so nested models resolve ────────────────────────
StartInterviewResponse.model_rebuild()
SubmitAnswerResponse.model_rebuild()
EndInterviewResponse.model_rebuild()
