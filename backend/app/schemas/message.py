"""Pydantic schemas for messaging and notifications."""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel


# ── Requests ───────────────────────────────────────────────────────────────


class SendMessageRequest(BaseModel):
    recipient_email: str
    subject: str
    body: str


class MarkNotificationReadRequest(BaseModel):
    notification_ids: list[UUID]


# ── Responses ──────────────────────────────────────────────────────────────


class MessageResponse(BaseModel):
    id: UUID
    sender_id: UUID
    recipient_id: UUID
    message_type: str
    subject: str
    body: str
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    notification_type: str
    title: str
    message: str
    is_read: bool
    read_at: Optional[datetime]
    meta_json: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int
