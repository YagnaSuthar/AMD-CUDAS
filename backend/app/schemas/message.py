"""Pydantic schemas for messaging and notifications."""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel


# ── Requests ───────────────────────────────────────────────────────────────


class SendMessageRequest(BaseModel):
    """Legacy: recruiter sends to a single student by email."""
    recipient_email: str
    subject: str
    body: str


class ComposeMessageRequest(BaseModel):
    """New: role-based compose message with bulk targeting."""
    recipient_role: str                        # STUDENT | FACULTY | HOD | COLLEGE_PRINCIPAL
    semester: Optional[int] = None             # required when recipient_role=STUDENT and send_to_all
    recipient_ids: Optional[list[str]] = None  # specific user UUIDs (strings)
    cc_ids: Optional[list[str]] = None         # CC user UUIDs (strings)
    subject: str
    body: str


class MarkNotificationReadRequest(BaseModel):
    notification_ids: list[UUID]


class ToggleStarRequest(BaseModel):
    is_starred: bool


# ── Responses ──────────────────────────────────────────────────────────────


class MessageResponse(BaseModel):
    id: UUID
    sender_id: UUID
    recipient_id: Optional[UUID] = None
    message_type: str
    subject: str
    body: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    sender_role: Optional[str] = None
    receiver_role: Optional[str] = None
    receiver_ids: Optional[list] = None
    semester_id: Optional[int] = None

    class Config:
        from_attributes = True


class SentMessageResponse(BaseModel):
    id: UUID
    sender_id: UUID
    sender_name: Optional[str] = None
    sender_role: Optional[str] = None
    receiver_role: Optional[str] = None
    recipient_count: int = 0
    subject: str
    body: str
    semester_id: Optional[int] = None
    created_at: datetime
    read_count: int = 0

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    notification_type: str
    title: str
    message: str
    is_read: bool
    is_starred: bool = False
    sender_role: Optional[str] = None
    read_at: Optional[datetime] = None
    meta_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int


class RecipientItem(BaseModel):
    id: str
    name: str
    email: str
    department: Optional[str] = None
    semester: Optional[int] = None
    enrollment_number: Optional[str] = None


class RecipientListResponse(BaseModel):
    recipients: list[RecipientItem]
    total: int
