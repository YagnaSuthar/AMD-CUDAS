"""
Messaging and notifications router.
Supports: Recruiter→Student, Principal/HOD/Faculty→Student/Faculty/HOD/Principal.
"""

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import RoleChecker, get_current_user
from app.models.auth import AuthUser
from app.models.message import Message, Notification, MessageType, NotificationType
from app.schemas.message import (
    SendMessageRequest,
    ComposeMessageRequest,
    MarkNotificationReadRequest,
    ToggleStarRequest,
    MessageResponse,
    SentMessageResponse,
    NotificationListResponse,
    NotificationResponse,
    RecipientListResponse,
    RecipientItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["Messaging"])

recruiter_only = RoleChecker(["RECRUITER"])
student_only = RoleChecker(["STUDENT"])
college_roles = RoleChecker(["COLLEGE_PRINCIPAL", "HOD", "FACULTY"])
any_authenticated = RoleChecker(["COLLEGE_PRINCIPAL", "HOD", "FACULTY", "STUDENT", "RECRUITER"])


# ── Helper: resolve message type ─────────────────────────────────────────

def _resolve_message_type(sender_role: str, receiver_role: str) -> str:
    if sender_role == "RECRUITER":
        return MessageType.RECRUITER_TO_STUDENT
    mapping = {
        "STUDENT": MessageType.COLLEGE_TO_STUDENT,
        "FACULTY": MessageType.COLLEGE_TO_FACULTY,
        "HOD": MessageType.COLLEGE_TO_HOD,
        "COLLEGE_PRINCIPAL": MessageType.COLLEGE_TO_PRINCIPAL,
    }
    return mapping.get(receiver_role, MessageType.INTERNAL)


def _resolve_notification_type(sender_role: str) -> str:
    if sender_role == "RECRUITER":
        return NotificationType.MESSAGE
    return NotificationType.COLLEGE_MESSAGE


# ── Legacy: Recruiter send to single student ─────────────────────────────

@router.post("/send", response_model=MessageResponse)
async def send_message(
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    """Recruiter sends a message to a student."""
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
            sender_role="RECRUITER",
            receiver_role="STUDENT",
            receiver_ids=[str(recipient.id)],
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
            sender_role="RECRUITER",
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

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error sending message: {exc}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc))


# ── New: Compose message (role-based, bulk targeting) ────────────────────

@router.post("/compose")
async def compose_message(
    body: ComposeMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(college_roles),
):
    """Principal/HOD/Faculty composes and sends a message with role-based targeting."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot send messages")

    sender_role = current_user.role
    if isinstance(sender_role, str):
        pass
    else:
        sender_role = sender_role.value if hasattr(sender_role, 'value') else str(sender_role)

    logger.info(f"Compose message from {current_user.email} ({sender_role}) to role={body.recipient_role}")

    # Validate recipient_role
    valid_roles = ["STUDENT", "FACULTY", "HOD", "COLLEGE_PRINCIPAL"]
    if body.recipient_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid recipient role. Must be one of: {valid_roles}")

    # Validate subject/body
    if not body.subject or not body.subject.strip():
        raise HTTPException(status_code=400, detail="Subject is required")
    if not body.body or not body.body.strip():
        raise HTTPException(status_code=400, detail="Message body is required")

    # ── Resolve recipients ──
    recipient_users = []

    if body.recipient_ids and len(body.recipient_ids) > 0:
        # Specific recipients selected
        recipient_uuids = []
        for rid in body.recipient_ids:
            try:
                recipient_uuids.append(uuid.UUID(rid))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid recipient ID: {rid}")

        result = await db.execute(
            select(AuthUser).where(AuthUser.id.in_(recipient_uuids))
        )
        recipient_users = list(result.scalars().all())

        if len(recipient_users) == 0:
            raise HTTPException(status_code=400, detail="No valid recipients found")

    elif body.recipient_role == "STUDENT":
        # Semester-based targeting
        if not body.semester:
            raise HTTPException(status_code=400, detail="Semester is required when sending to all students")

        query = select(AuthUser).where(
            AuthUser.role == "STUDENT",
            AuthUser.semester == body.semester,
        )

        # Faculty can only send to students under their hierarchy
        if sender_role == "FACULTY" and current_user.department:
            query = query.where(AuthUser.department == current_user.department)
        elif sender_role == "HOD" and current_user.department:
            query = query.where(AuthUser.department == current_user.department)

        result = await db.execute(query)
        recipient_users = list(result.scalars().all())

        if len(recipient_users) == 0:
            raise HTTPException(status_code=404, detail=f"No students found for semester {body.semester}")

    elif body.recipient_role == "FACULTY":
        query = select(AuthUser).where(AuthUser.role == "FACULTY")
        if sender_role == "HOD" and current_user.department:
            query = query.where(AuthUser.department == current_user.department)
        result = await db.execute(query)
        recipient_users = list(result.scalars().all())

    elif body.recipient_role == "HOD":
        query = select(AuthUser).where(AuthUser.role == "HOD")
        result = await db.execute(query)
        recipient_users = list(result.scalars().all())

    elif body.recipient_role == "COLLEGE_PRINCIPAL":
        result = await db.execute(
            select(AuthUser).where(AuthUser.role == "COLLEGE_PRINCIPAL")
        )
        recipient_users = list(result.scalars().all())

    if len(recipient_users) == 0:
        raise HTTPException(status_code=400, detail="At least one recipient is required")

    # ── Create the message record ──
    receiver_id_strings = [str(u.id) for u in recipient_users]
    msg_type = _resolve_message_type(sender_role, body.recipient_role)

    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_users[0].id if len(recipient_users) == 1 else None,
        message_type=msg_type,
        sender_role=sender_role,
        receiver_role=body.recipient_role,
        receiver_ids=receiver_id_strings,
        semester_id=body.semester,
        cc_ids=[str(cid) for cid in (body.cc_ids or [])],
        subject=body.subject.strip(),
        body=body.body.strip(),
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(message)
    await db.flush()

    # ── Create notification for each recipient ──
    notif_type = _resolve_notification_type(sender_role)
    sender_display = current_user.name or current_user.email
    role_label = {
        "COLLEGE_PRINCIPAL": "Principal",
        "HOD": "HOD",
        "FACULTY": "Faculty",
    }.get(sender_role, sender_role)

    for recipient in recipient_users:
        notification = Notification(
            user_id=recipient.id,
            notification_type=notif_type,
            title=f"Message from {role_label}: {sender_display}",
            message=body.subject.strip(),
            sender_role=sender_role,
            meta_json={
                "sender_id": str(current_user.id),
                "sender_name": sender_display,
                "sender_role": sender_role,
                "message_id": str(message.id),
                "body_preview": body.body.strip()[:200],
            },
            is_read=False,
            is_starred=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(notification)

    await db.commit()

    logger.info(f"Message composed and sent to {len(recipient_users)} recipient(s)")
    return {
        "detail": f"Message sent to {len(recipient_users)} recipient(s)",
        "message_id": str(message.id),
        "recipient_count": len(recipient_users),
    }


# ── Recipients lookup ────────────────────────────────────────────────────

@router.get("/recipients", response_model=RecipientListResponse)
async def get_recipients(
    role: str = Query(..., description="Target role: STUDENT, FACULTY, HOD, COLLEGE_PRINCIPAL"),
    semester: int | None = Query(None, description="Semester filter (for students)"),
    search: str | None = Query(None, description="Search by name or email"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(college_roles),
):
    """Fetch potential recipients filtered by role, semester, and search term."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot fetch recipients")

    sender_role = current_user.role
    if hasattr(sender_role, 'value'):
        sender_role = sender_role.value

    valid_roles = ["STUDENT", "FACULTY", "HOD", "COLLEGE_PRINCIPAL"]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    query = select(AuthUser).where(AuthUser.role == role)

    # Semester filter for students
    if role == "STUDENT" and semester:
        query = query.where(AuthUser.semester == semester)

    # Department scoping for Faculty/HOD
    if role == "STUDENT" and sender_role in ("FACULTY", "HOD") and current_user.department:
        query = query.where(AuthUser.department == current_user.department)
    if role == "FACULTY" and sender_role == "HOD" and current_user.department:
        query = query.where(AuthUser.department == current_user.department)

    # Search filter
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        query = query.where(
            (AuthUser.name.ilike(search_term)) | (AuthUser.email.ilike(search_term))
        )

    query = query.order_by(AuthUser.name)
    result = await db.execute(query)
    users = list(result.scalars().all())

    recipients = [
        RecipientItem(
            id=str(u.id),
            name=u.name,
            email=u.email,
            department=u.department,
            semester=u.semester,
            enrollment_number=u.enrollment_number,
        )
        for u in users
    ]

    return RecipientListResponse(recipients=recipients, total=len(recipients))


# ── Sent messages (for college roles) ────────────────────────────────────

@router.get("/sent")
async def list_sent_messages_college(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(college_roles),
):
    """Principal/HOD/Faculty lists messages they have sent."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot list messages")

    result = await db.execute(
        select(Message)
        .where(Message.sender_id == current_user.id)
        .order_by(Message.created_at.desc())
        .limit(100)
    )
    messages = list(result.scalars().all())

    response = []
    for msg in messages:
        receiver_ids = msg.receiver_ids or []
        # Count how many recipients read it
        read_count = 0
        if receiver_ids:
            read_result = await db.execute(
                select(func.count(Notification.id)).where(
                    Notification.meta_json["message_id"].as_string() == str(msg.id),
                    Notification.is_read == True,
                )
            )
            read_count = read_result.scalar() or 0

        response.append(SentMessageResponse(
            id=msg.id,
            sender_id=msg.sender_id,
            sender_name=current_user.name,
            sender_role=msg.sender_role,
            receiver_role=msg.receiver_role,
            recipient_count=len(receiver_ids),
            subject=msg.subject,
            body=msg.body,
            semester_id=msg.semester_id,
            created_at=msg.created_at,
            read_count=read_count,
        ))

    return response


# ── Legacy: Recruiter sent messages ──────────────────────────────────────

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


# ── Notifications (expanded to all roles) ────────────────────────────────

@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(any_authenticated),
):
    """Any authenticated user fetches their notifications with unread count."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot view notifications")

    # Fetch notifications
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
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


# ── Mark notifications read (batch) ─────────────────────────────────────

@router.post("/notifications/mark-read")
async def mark_notifications_read(
    body: MarkNotificationReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(any_authenticated),
):
    """Mark notifications as read."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot mark notifications")

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


# ── Mark single notification read ────────────────────────────────────────

@router.put("/notifications/{notification_id}/read")
async def mark_single_notification_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(any_authenticated),
):
    """Mark a single notification as read."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot mark notifications")

    await db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"detail": "Notification marked as read"}


# ── Mark notification unread ─────────────────────────────────────────────

@router.put("/notifications/{notification_id}/unread")
async def mark_notification_unread(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(any_authenticated),
):
    """Mark a notification as unread."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot mark notifications")

    await db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .values(is_read=False, read_at=None)
    )
    await db.commit()
    return {"detail": "Notification marked as unread"}


# ── Toggle star ──────────────────────────────────────────────────────────

@router.put("/notifications/{notification_id}/star")
async def toggle_star(
    notification_id: uuid.UUID,
    body: ToggleStarRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(any_authenticated),
):
    """Toggle star status on a notification."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot star notifications")

    await db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .values(is_starred=body.is_starred)
    )
    await db.commit()
    return {"detail": "Star toggled", "is_starred": body.is_starred}


# ── Delete notification ──────────────────────────────────────────────────

@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(any_authenticated),
):
    """Delete a notification."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot delete notifications")

    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(notification)
    await db.commit()
    return {"detail": "Notification deleted"}
