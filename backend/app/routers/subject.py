import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, hod_only
from app.models.auth import SubjectAssignment, AuthUser
from app.schemas.auth import (
    SubjectAssignmentCreate, 
    SubjectAssignmentUpdate, 
    SubjectAssignmentResponse,
    MessageResponse
)

router = APIRouter(prefix="/subject", tags=["Subject Assignment"])


@router.post("/assign", response_model=MessageResponse)
async def assign_subject(
    body: SubjectAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """Assign a subject to a faculty member for a specific semester."""
    faculty_id = uuid.UUID(body.faculty_id)

    # Verify faculty is in HOD's hierarchy
    res = await db.execute(
        select(AuthUser).where(AuthUser.id == faculty_id, AuthUser.parent_id == current_user.id)
    )
    faculty = res.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=403, detail="Faculty not found in your department.")

    # Check for duplicate subjectCode + semester
    res = await db.execute(
        select(SubjectAssignment).where(
            SubjectAssignment.subject_code == body.subject_code,
            SubjectAssignment.semester == body.semester,
            SubjectAssignment.department == (current_user.department or "Unknown")
        )
    )
    if res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This subject is already assigned for this semester.")

    new_assignment = SubjectAssignment(
        faculty_id=faculty_id,
        semester=body.semester,
        subject_name=body.subject_name,
        subject_code=body.subject_code,
        department=current_user.department or "Unknown",
        assigned_by=current_user.id
    )
    db.add(new_assignment)
    await db.commit()
    return MessageResponse(message=f"Subject '{body.subject_name}' assigned to {faculty.name}.")


@router.get("/all", response_model=list[SubjectAssignmentResponse])
async def list_all_assignments(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """List all subject assignments for the HOD's department."""
    res = await db.execute(
        select(SubjectAssignment, AuthUser.name)
        .join(AuthUser, SubjectAssignment.faculty_id == AuthUser.id)
        .where(SubjectAssignment.department == (current_user.department or "Unknown"))
        .order_by(SubjectAssignment.semester, SubjectAssignment.subject_name)
    )
    rows = res.all()
    return [
        SubjectAssignmentResponse(
            id=str(m.id),
            faculty_id=str(m.faculty_id),
            faculty_name=name,
            semester=m.semester,
            subject_name=m.subject_name,
            subject_code=m.subject_code,
            department=m.department,
            created_at=str(m.created_at)
        )
        for m, name in rows
    ]


@router.delete("/{assignment_id}", response_model=MessageResponse)
async def delete_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """Remove a subject assignment."""
    res = await db.execute(
        select(SubjectAssignment).where(
            SubjectAssignment.id == assignment_id,
            SubjectAssignment.department == (current_user.department or "Unknown")
        )
    )
    assignment = res.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    await db.delete(assignment)
    await db.commit()
    return MessageResponse(message="Subject assignment removed.")


@router.put("/{assignment_id}", response_model=MessageResponse)
async def update_assignment(
    assignment_id: uuid.UUID,
    body: SubjectAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """Update a subject assignment."""
    res = await db.execute(
        select(SubjectAssignment).where(
            SubjectAssignment.id == assignment_id,
            SubjectAssignment.department == (current_user.department or "Unknown")
        )
    )
    assignment = res.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    if body.faculty_id:
        assignment.faculty_id = uuid.UUID(body.faculty_id)
    if body.semester:
        assignment.semester = body.semester
    if body.subject_name:
        assignment.subject_name = body.subject_name
    if body.subject_code:
        assignment.subject_code = body.subject_code

    await db.commit()
    return MessageResponse(message="Subject assignment updated.")


@router.get("/faculty/{faculty_id}", response_model=list[SubjectAssignmentResponse])
async def get_faculty_subjects(
    faculty_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all subjects assigned to a specific faculty member."""
    res = await db.execute(
        select(SubjectAssignment)
        .where(SubjectAssignment.faculty_id == faculty_id)
        .order_by(SubjectAssignment.semester)
    )
    assignments = res.scalars().all()
    return [
        SubjectAssignmentResponse(
            id=str(m.id),
            faculty_id=str(m.faculty_id),
            semester=m.semester,
            subject_name=m.subject_name,
            subject_code=m.subject_code,
            department=m.department,
            created_at=str(m.created_at)
        )
        for m in assignments
    ]
