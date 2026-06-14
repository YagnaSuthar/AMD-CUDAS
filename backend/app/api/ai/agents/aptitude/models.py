import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AptitudeQuestion(Base):
    __tablename__ = "aptitude_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list] = mapped_column(JSONB, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="curated", index=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Production-grade extensions
    domain: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Enhanced properties
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    expected_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    normalized_question_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Usage statistics
    times_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    times_wrong: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Statistics helper methods
    def increment_usage(self) -> None:
        self.times_used = (self.times_used or 0) + 1

    def increment_correct(self) -> None:
        self.times_correct = (self.times_correct or 0) + 1

    def increment_wrong(self) -> None:
        self.times_wrong = (self.times_wrong or 0) + 1


class QuestionImportJob(Base):
    __tablename__ = "question_import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # JSON, CSV, XLSX, PDF
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending, completed, failed, imported
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_log: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QuestionImportItem(Base):
    __tablename__ = "question_import_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("question_import_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    parsed_question: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_errors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending, valid, invalid, imported


class AptitudeSession(Base):
    __tablename__ = "aptitude_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    current_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used_question_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    question_sequence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AptitudeAttempt(Base):
    __tablename__ = "aptitude_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("aptitude_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("aptitude_questions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    selected_option: Mapped[str] = mapped_column(String(255), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_taken: Mapped[int | None] = mapped_column(Integer, nullable=True)


Index("uq_aptitude_attempts_session_question", AptitudeAttempt.session_id, AptitudeAttempt.question_id, unique=True)

