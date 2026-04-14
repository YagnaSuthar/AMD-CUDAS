"""
Message and Notification models for role-based messaging.
Supports: Recruiter→Student, Principal/HOD/Faculty→Student/Faculty/HOD/Principal.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Text,
    Boolean,
    Integer,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────


class MessageType(str, enum.Enum):
    RECRUITER_TO_STUDENT = "RECRUITER_TO_STUDENT"
    COLLEGE_TO_STUDENT = "COLLEGE_TO_STUDENT"
    COLLEGE_TO_FACULTY = "COLLEGE_TO_FACULTY"
    COLLEGE_TO_HOD = "COLLEGE_TO_HOD"
    COLLEGE_TO_PRINCIPAL = "COLLEGE_TO_PRINCIPAL"
    INTERNAL = "INTERNAL"


class NotificationType(str, enum.Enum):
    MESSAGE = "MESSAGE"
    AI_ASSIGNED = "AI_ASSIGNED"
    ROUND2_INVITED = "ROUND2_INVITED"
    HIRED = "HIRED"
    COLLEGE_MESSAGE = "COLLEGE_MESSAGE"


# ── Message ───────────────────────────────────────────────────────────────


class Message(Base):
    """A message sent between roles."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Legacy single recipient (kept for backward compat with recruiter messages)
    recipient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=True,
    )
    message_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MessageType.RECRUITER_TO_STUDENT,
    )

    # ── New role-based fields ──
    sender_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    receiver_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    receiver_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    semester_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cc_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    sender = relationship("AuthUser", foreign_keys=[sender_id])
    recipient = relationship("AuthUser", foreign_keys=[recipient_id])


# ── Notification ───────────────────────────────────────────────────────────


class Notification(Base):
    """A notification for any user (messages, pipeline updates, etc.)."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    sender_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    meta_json: Mapped[dict | None] = mapped_column(
        # e.g. {"message_id": "...", "pipeline_id": "..."} for quick navigation
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationship
    user = relationship("AuthUser", foreign_keys=[user_id])
