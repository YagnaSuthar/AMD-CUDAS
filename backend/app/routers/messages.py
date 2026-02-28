"""
Messaging and notifications router.
Recruiter can send messages to students; students can fetch notifications.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import RoleChecker, get_current_user
from app.models.auth import AuthUser
from app.models.message import Message, Notification, MessageType, NotificationType
from app.schemas.message import (
    SendMessageRequest,
    MarkNotificationReadRequest,
    MessageResponse,
    NotificationListResponse,
)

router = APIRouter(prefix="/messages", tags=["Messaging"])

recruiter_only = RoleChecker(["RECRUITER"])
student_only = RoleChecker(["STUDENT"])


@router.post("/send", response_model=MessageResponse)
async def send_message(
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    """Recruiter sends a message to a student."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Attempting to send message from {current_user.email} to {body.recipient_email}")
        
        if isinstance(current_user, dict):
            raise HTTPException(status_code=403, detail="Admin cannot send messages")

        # Verify recipient is a student by email
        recipient_result = await db.execute(
            select(AuthUser).where(AuthUser.email == body.recipient_email)
        )
        recipient = recipient_result.scalar_one_or_none()
        if not recipient:
            logger.error(f"Student not found with email: {body.recipient_email}")
            raise HTTPException(status_code=404, detail="Student not found with this email")
        if recipient.role != "STUDENT":
            logger.error(f"Recipient {body.recipient_email} is not a student, role: {recipient.role}")
            raise HTTPException(status_code=400, detail="Recipient must be a student")

        logger.info(f"Found student: {recipient.name} ({recipient.id})")

        # Create message
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            message_type=MessageType.RECRUITER_TO_STUDENT,
            subject=body.subject,
            body=body.body,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(message)

        # Create notification for student
        notification = Notification(
            user_id=recipient.id,
            notification_type=NotificationType.MESSAGE,
            title=f"New message from {current_user.name}",
            message=body.subject,
            meta_json={
                "sender_id": str(current_user.id),
                "sender_name": current_user.name,
                "message_id": str(message.id),
            },
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(notification)

        await db.flush()
        await db.commit()
        await db.refresh(message)
        
        logger.info(f"Message sent successfully to {recipient.email}")
        return message
        
    except Exception as exc:
        logger.error(f"Error sending message: {exc}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_model=list[MessageResponse])
async def list_sent_messages(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    """Recruiter lists messages they have sent."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot list messages")

    result = await db.execute(
        select(Message)
        .where(Message.sender_id == current_user.id)
        .order_by(Message.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(student_only),
):
    """Student fetches their notifications with unread count."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot view notifications")

    # Fetch notifications
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifications = list(result.scalars().all())

    # Count unread
    unread_result = await db.execute(
        select(func.count(Notification.id))
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
    )
    unread_count = unread_result.scalar() or 0

    return NotificationListResponse(
        notifications=notifications,
        unread_count=unread_count,
    )


@router.post("/notifications/mark-read")
async def mark_notifications_read(
    body: MarkNotificationReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(student_only),
):
    """Student marks notifications as read."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot mark notifications")

    # Perform update
    await db.execute(
        update(Notification)
        .where(
            Notification.id.in_(body.notification_ids),
            Notification.user_id == current_user.id,
        )
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"detail": "Notifications marked as read"}
