"""
Message and Notification models for recruiter-to-student messaging.
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
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────


class MessageType(str, enum.Enum):
    RECRUITER_TO_STUDENT = "RECRUITER_TO_STUDENT"


class NotificationType(str, enum.Enum):
    MESSAGE = "MESSAGE"
    AI_ASSIGNED = "AI_ASSIGNED"
    ROUND2_INVITED = "ROUND2_INVITED"
    HIRED = "HIRED"


# ── Message ───────────────────────────────────────────────────────────────


class Message(Base):
    """A message sent from a recruiter to a student."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_type: Mapped[str] = mapped_column(
        SAEnum(MessageType, name="message_type_enum", create_constraint=True),
        nullable=False,
        default=MessageType.RECRUITER_TO_STUDENT,
    )
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
    """A notification for a student (messages, pipeline updates, etc.)."""

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
        SAEnum(NotificationType, name="notification_type_enum", create_constraint=True),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
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
