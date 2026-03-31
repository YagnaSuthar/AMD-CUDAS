"""
Pydantic schemas for the interview system.
Covers all route request/response contracts and internal agent I/O types.
Updated with greeting handshake flow, resume-awareness, and interview history.
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
    """POST /interview/start — student_id extracted from JWT."""
    job_role: str = Field(..., min_length=1, max_length=255)


class StartInterviewResponse(BaseModel):
    """Returns only the greeting — no LLM call at this stage."""
    session_id: uuid.UUID
    status: str
    student_name: str
    greeting: str


# ── Greeting Handshake ────────────────────────────────────────────────────

class GreetingRequest(BaseModel):
    """POST /interview/greet — student responds Yes/No."""
    session_id: uuid.UUID
    answer: str = Field(..., description="'yes' or 'no'")


class GreetingResponse(BaseModel):
    agent_message: str
    next_step: str  # "confirm_start" | "session_closed" | "first_question"
    session_id: uuid.UUID
    first_question: Optional[QuestionOutput] = None
    profile: Optional[ProfileOutput] = None


# ── Questions & Answers ───────────────────────────────────────────────────

class NextQuestionRequest(BaseModel):
    """POST /interview/next"""
    session_id: uuid.UUID


class NextQuestionResponse(BaseModel):
    question: QuestionOutput
    difficulty: str
    question_number: int


class SubmitAnswerRequest(BaseModel):
    """POST /interview/answer"""
    session_id: uuid.UUID
    question_id: uuid.UUID
    answer_text: str = Field(..., min_length=1)
    audio_path: Optional[str] = None


class SubmitAnswerResponse(BaseModel):
    evaluation: EvaluationOutput
    memory: MemoryOutput
    agent_response: str = ""
    behavior_flag: str = "neutral"
    next_action: str  # "ask_question" | "end"
    next_difficulty: str
    next_question: Optional[QuestionOutput] = None
    running_avg_score: float = 0.0


class EndInterviewRequest(BaseModel):
    """POST /interview/end"""
    session_id: uuid.UUID
    ended_reason: str = "normal"


class EndInterviewResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    report: FeedbackOutput


class InterviewReportResponse(BaseModel):
    """GET /interview/report/{session_id}"""
    session_id: uuid.UUID
    final_score: float
    communication_score: float = 0.0
    strengths: List[str]
    weaknesses: List[str]
    behavior_summary: str = ""
    recommendation: str


class InterviewConfigResponse(BaseModel):
    """GET /interview/config — returns client-side config."""
    max_questions: int
    answer_timeout: int
    silence_timeout: int


# ── Interview History ─────────────────────────────────────────────────────

class InterviewHistoryItem(BaseModel):
    session_id: uuid.UUID
    job_role: str
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    total_questions: int = 0
    overall_score: Optional[float] = None
    recommendation: Optional[str] = None


class InterviewHistoryResponse(BaseModel):
    sessions: List[InterviewHistoryItem]


class SessionQuestionAnswer(BaseModel):
    question_order: int
    question_text: str
    topic: str
    difficulty: str
    answer_text: Optional[str] = None
    score: Optional[float] = None


class SessionDetailResponse(BaseModel):
    session_id: uuid.UUID
    job_role: str
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    total_questions: int = 0
    overall_score: Optional[float] = None
    recommendation: Optional[str] = None
    questions: List[SessionQuestionAnswer]


# ── Proctoring / Detector Agent ───────────────────────────────────────────

class ProctoringViolationRequest(BaseModel):
    """POST /interview/violation — report a proctoring violation."""
    session_id: uuid.UUID
    violation_type: str = Field(..., description="NO_FACE, PHONE_DETECTED, MULTIPLE_PEOPLE, etc.")
    message: str = Field(..., description="Human-readable violation message")
    severity: str = Field(default="warning", description="warning or critical")


class ProctoringViolationResponse(BaseModel):
    logged: bool
    should_end: bool
    reason: str = ""
    warning_count: int = 0
    violation_count: int = 0


class ProctoringSessionSummary(BaseModel):
    total_violations: int = 0
    violation_breakdown: dict = {}
    integrity_score: float = 1.0
    flags: List[str] = []
    summary: str = ""


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
    has_projects: bool = False
    project_summary: str = ""


class QuestionOutput(BaseModel):
    question_id: Optional[uuid.UUID] = None
    question: str
    topic: str
    difficulty: str


class EvaluationOutput(BaseModel):
    model_config = {"extra": "ignore"}

    clarity: float = Field(ge=0, le=10)
    depth: float = Field(ge=0, le=10)
    confidence: float = Field(ge=0, le=10)
    technical_score: float = Field(ge=0, le=10, default=5)
    behavior_flag: str = "neutral"
    next_difficulty: str = "medium"
    # Weighted 0-1 scores from the upgraded evaluator
    answer_type: str = "VALID"
    communication_score: float = Field(ge=0.0, le=1.0, default=0.5)
    behavior_score: float = Field(ge=0.0, le=1.0, default=0.5)
    weighted_score: float = Field(ge=0.0, le=1.0, default=0.5)


class MemoryOutput(BaseModel):
    summary: str = ""
    weak_areas: List[str] = []
    strong_areas: List[str] = []
    last_behavior_state: str = "neutral"
    token_usage: int = 0


class STTOutput(BaseModel):
    transcript: str
    confidence: float = Field(ge=0.0, le=1.0)


class TTSOutput(BaseModel):
    audio_path: str


class FeedbackOutput(BaseModel):
    model_config = {"extra": "ignore"}

    final_score: float = Field(ge=0.0, le=10.0)
    communication_score: float = Field(ge=0.0, le=10.0, default=0.0)
    behavior_score: float = Field(ge=0.0, le=1.0, default=0.0)
    strengths: List[str] = []
    weaknesses: List[str] = []
    behavior_summary: str = ""
    recommendation: str = ""
    # Detailed report sections
    student_report: Optional[dict] = None
    recruiter_report: Optional[dict] = None
    # Proctoring integrity data from DetectorAgent
    proctoring_summary: Optional[dict] = None


# ── Rebuild forward refs so nested models resolve ────────────────────────
StartInterviewResponse.model_rebuild()
GreetingResponse.model_rebuild()
SubmitAnswerResponse.model_rebuild()
EndInterviewResponse.model_rebuild()
