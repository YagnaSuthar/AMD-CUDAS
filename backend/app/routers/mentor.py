import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.auth import MentorAssignment, AuthUser
from app.schemas.auth import MentorAssignmentResponse

router = APIRouter(prefix="/mentor", tags=["Mentor Assignment"])


@router.get("/faculty/{faculty_id}", response_model=list[MentorAssignmentResponse])
async def get_faculty_mentors(
    faculty_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all mentor assignments for a specific faculty member."""
    # Note: Anyone authenticated can view these assignments (usually HOD/Faculty/Principal)
    res = await db.execute(
        select(MentorAssignment, AuthUser.name)
        .join(AuthUser, MentorAssignment.faculty_id == AuthUser.id)
        .where(MentorAssignment.faculty_id == faculty_id)
        .order_by(MentorAssignment.semester)
    )
    rows = res.all()
    return [
        MentorAssignmentResponse(
            id=str(m.id),
            faculty_id=str(m.faculty_id),
            faculty_name=name,
            semester=m.semester,
            department=m.department,
            created_at=str(m.created_at)
        )
        for m, name in rows
    ]
