import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True, index=True)

    input_type = Column(String(50), nullable=False)  # certificate|project|profile
    input_link = Column(Text, nullable=True)
    input_file_name = Column(String(512), nullable=True)
    input_file_hash = Column(String(64), nullable=True, index=True)

    extracted_data = Column(JSONB, nullable=True)
    scores = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)

    status = Column(String(30), nullable=False)  # verified|suspicious|failed
    confidence_score = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    feedback = relationship("VerificationFeedback", back_populates="run", cascade="all, delete-orphan")


class VerificationFeedback(Base):
    __tablename__ = "verification_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("verification_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    is_correct = Column(Boolean, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    run = relationship("VerificationRun", back_populates="feedback")
