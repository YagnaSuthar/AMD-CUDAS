from __future__ import annotations

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.agents.academic.orchestrator import generate_study_plan as generate_academic_plan
from app.agents.academic.llm_provider import get_llm
from app.api.ai.agents.academic.schema import (
    StudyPlanDay,
    StudyPlanRequest,
    StudyPlanResponse,
    StudyProgressUpdate,
)
from app.models.academic import Subject, StudyProgress


_PLANS_BY_STUDENT: dict[str, StudyPlanResponse] = {}

_STUDY_PROGRESS: dict[str, dict] = {}


async def get_progress_summary(student_id: str, db: AsyncSession) -> dict:
    """Aggregate completed hours per subject for adaptive engine."""
    from uuid import UUID
    from sqlalchemy import func
    from sqlalchemy.orm import aliased
    student_uuid = UUID(student_id)
    # Aggregate completed_hours per subject name via join
    stmt = (
        select(
            Subject.name.label("subject_name"),
            func.coalesce(func.sum(StudyProgress.completed_hours), 0).label("total_completed_hours"),
        )
        .join(StudyProgress, Subject.id == StudyProgress.subject_id, isouter=True)
        .where(Subject.student_id == student_uuid)
        .group_by(Subject.name)
    )
    result = await db.execute(stmt)
    rows = result.all()
    # Build topics_completed list and total completed_hours
    topics_completed = [row.subject_name for row in rows if row.total_completed_hours > 0]
    completed_hours = int(sum(row.total_completed_hours for row in rows))
    return {
        "completed_hours": completed_hours,
        "topics_completed": topics_completed,
    }


async def get_subjects_by_student(student_id: str, db: AsyncSession) -> list[dict]:
    """Fetch subjects for a student and compute days_left dynamically."""
    from uuid import UUID
    student_uuid = UUID(student_id)
    result = await db.execute(select(Subject).where(Subject.student_id == student_uuid))
    subjects = result.scalars().all()
    if not subjects:
        raise HTTPException(status_code=404, detail="No subjects found for this student.")
    today = date.today()
    return [
        {
            "name": s.name,
            "credit": s.credit,
            "marks": s.marks,
            "days_left": max((s.exam_date - today).days, 1),
        }
        for s in subjects
    ]


async def generate_study_plan_service(
    student_id: str,
    daily_available_hours: int,
    db: AsyncSession,
    progress_data: dict | None = None,
) -> dict:
    # 1) Fetch student data (DB only)
    student_data: dict
    try:
        from uuid import UUID
        from app.models.interview import User
        student_uuid = UUID(student_id)
        result = await db.execute(select(User).where(User.id == student_uuid))
        user = result.scalar_one_or_none()
        student_data = {
            "student_id": student_id,
            "name": getattr(user, "name", None) if user else None,
            "email": getattr(user, "email", None) if user else None,
        }
    except Exception:
        student_data = {"student_id": student_id, "name": None, "email": None}

    # 2) Fetch subjects from DB
    subjects = await get_subjects_by_student(student_id, db)

    # 3) Call business layer
    llm_callable = get_llm()
    # Enforce temperature <= 0.4
    try:
        if hasattr(llm_callable, "temperature") and getattr(llm_callable, "temperature") is not None:
            llm_callable.temperature = min(float(llm_callable.temperature), 0.4)
    except Exception:
        pass

    result = await generate_academic_plan(
        student_data=student_data,
        daily_available_hours=daily_available_hours,
        subjects=subjects,
        llm_callable=llm_callable,
        progress_data=progress_data,
    )
    _PLANS_BY_STUDENT[student_id] = StudyPlanResponse.model_validate(result)
    return result


async def update_study_progress_service(
    student_id: str,
    completed_hours: int,
    topics_completed: list[str],
    db: AsyncSession,
) -> dict:
    # Fetch real progress summary for adaptive mode
    progress_data = await get_progress_summary(student_id, db)
    # Override with latest incremental update if desired (optional)
    # progress_data["completed_hours"] += completed_hours
    # progress_data["topics_completed"] = list(set(progress_data["topics_completed"] + topics_completed))
    # For now, use aggregated DB data only
    progress_data["daily_available_hours"] = 1  # fallback; can be enhanced later
    return await generate_study_plan_service(
        student_id=student_id,
        daily_available_hours=1,
        db=db,
        progress_data=progress_data,
    )


async def get_study_plan_service(
    student_id: str,
    db: AsyncSession,
) -> dict:
    plan = _PLANS_BY_STUDENT.get(student_id)
    if plan is None:
        return await generate_study_plan_service(
            student_id=student_id,
            daily_available_hours=1,
            db=db,
        )
    return plan.model_dump()
