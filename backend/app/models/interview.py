"""
SQLAlchemy ORM models for the AI Interview System.
All tables use UUID primary keys and maintain proper relationships.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Index,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────

import enum


class UserRole(str, enum.Enum):
    STUDENT = "student"
    RECRUITER = "recruiter"
    ADMIN = "admin"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class QuestionType(str, enum.Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SITUATIONAL = "situational"
    CONCEPTUAL = "conceptual"


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class BehaviorFlag(str, enum.Enum):
    POLITE = "polite"
    ARROGANT = "arrogant"
    NEUTRAL = "neutral"


# ── Models ────────────────────────────────────────────────────────────────


class User(Base):
    """Application user (student, recruiter, or admin)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(
        SAEnum(UserRole, name="user_role_enum", create_constraint=True),
        nullable=False,
        default=UserRole.STUDENT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class StudentProfile(Base):
    """Extended profile for a student user."""

    __tablename__ = "student_profiles"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    resume_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    portfolio_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    has_projects: Mapped[bool] = mapped_column(Boolean, default=False)
    project_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships (no back_populates to AuthUser — separate model)
    skills: Mapped[List["Skill"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Skill(Base):
    """Individual skill entry for a student profile."""

    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    skill_level: Mapped[str] = mapped_column(String(50), nullable=False)  # beginner/intermediate/advanced

    # Relationships
    profile: Mapped["StudentProfile"] = relationship(back_populates="skills")


class InterviewSession(Base):
    """A single interview session for a student."""

    __tablename__ = "interview_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_role: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False, default="basic")
    status: Mapped[str] = mapped_column(
        SAEnum(SessionStatus, name="session_status_enum", create_constraint=True),
        nullable=False,
        default=SessionStatus.ACTIVE,
    )
    current_difficulty: Mapped[str] = mapped_column(
        SAEnum(Difficulty, name="difficulty_enum", create_constraint=True),
        nullable=False,
        default=Difficulty.MEDIUM,
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    communication_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_turn_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Relationships (student_id references auth_users, no ORM back_populates)
    questions: Mapped[List["Question"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    answers: Mapped[List["Answer"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    memory: Mapped[Optional["InterviewMemory"]] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    report: Mapped[Optional["InterviewReport"]] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    violations: Mapped[List["ProctoringViolation"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    turns: Mapped[List["InterviewTurn"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewTurn.timestamp",
    )


class Question(Base):
    """A question asked during an interview session."""

    __tablename__ = "questions"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_order: Mapped[int] = mapped_column(Integer, default=0)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    difficulty: Mapped[str] = mapped_column(
        SAEnum(Difficulty, name="difficulty_enum", create_constraint=True),
        nullable=False,
    )
    question_type: Mapped[str] = mapped_column(
        SAEnum(QuestionType, name="question_type_enum", create_constraint=True),
        nullable=False,
        default=QuestionType.TECHNICAL,
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(back_populates="questions")
    answers: Mapped[List["Answer"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class Answer(Base):
    """A student's answer to a question."""

    __tablename__ = "answers"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        nullable=False,
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    audio_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="answers")
    score: Mapped[Optional["AnswerScore"]] = relationship(
        back_populates="answer", uselist=False, cascade="all, delete-orphan"
    )


class AnswerScore(Base):
    """Evaluation scores for a student answer."""

    __tablename__ = "answer_scores"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("answers.answer_id", ondelete="CASCADE"),
        primary_key=True,
    )
    clarity: Mapped[int] = mapped_column(Integer, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    technical_score: Mapped[int] = mapped_column(Integer, default=5)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    behavior_flag: Mapped[str] = mapped_column(
        SAEnum(BehaviorFlag, name="behavior_flag_enum", create_constraint=True),
        nullable=False,
        default=BehaviorFlag.NEUTRAL,
    )

    # Relationships
    answer: Mapped["Answer"] = relationship(back_populates="score")


class InterviewMemory(Base):
    """Running memory / context for an interview session."""

    __tablename__ = "interview_memory"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.session_id", ondelete="CASCADE"),
        primary_key=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    weak_areas: Mapped[list] = mapped_column(ARRAY(String), default=list)
    strong_areas: Mapped[list] = mapped_column(ARRAY(String), default=list)
    last_behavior_state: Mapped[str] = mapped_column(Text, default="neutral")
    token_usage: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    session: Mapped["InterviewSession"] = relationship(back_populates="memory")


class InterviewReport(Base):
    """Final report generated at the end of an interview session."""

    __tablename__ = "interview_reports"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.session_id", ondelete="CASCADE"),
        primary_key=True,
    )
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    strengths: Mapped[list] = mapped_column(ARRAY(String), default=list)
    weaknesses: Mapped[list] = mapped_column(ARRAY(String), default=list)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    session: Mapped["InterviewSession"] = relationship(back_populates="report")


class InterviewTurn(Base):
    """A single interview turn: question + answer + evaluation + metadata."""

    __tablename__ = "interview_turns"

    __table_args__ = (
        Index("idx_turn_session_answer", "session_id", "answer"),
        Index("idx_turn_session_timestamp", "session_id", "timestamp"),
    )

    turn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    answer_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evaluation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)
    # Optional metadata for context
    phase: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relationships
    session: Mapped["InterviewSession"] = relationship(back_populates="turns")


class ProctoringViolation(Base):
    """A proctoring violation detected during an interview session."""

    __tablename__ = "proctoring_violations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    violation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="warning"
    )  # warning, critical
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        Text, nullable=True
    )  # stored as JSON text
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(back_populates="violations")
