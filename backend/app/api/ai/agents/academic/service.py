from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.academic.orchestrator import generate_study_plan as generate_academic_plan
from app.agents.academic.llm_provider import get_llm
from app.api.ai.agents.academic.schema import (
    StudyPlanDay,
    StudyPlanRequest,
    StudyPlanResponse,
    StudyProgressUpdate,
)


_PLANS_BY_STUDENT: dict[str, StudyPlanResponse] = {}

_STUDY_PROGRESS: dict[str, dict] = {}


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
        from sqlalchemy import select
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

    # 2) Mock subjects (you can replace with real later)
    subjects = [
        {"name": "Mathematics", "credit": 4, "marks": 62, "days_left": 12},
        {"name": "Operating Systems", "credit": 3, "marks": 55, "days_left": 12},
        {"name": "DBMS", "credit": 3, "marks": 70, "days_left": 12},
    ]

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
    _STUDY_PROGRESS[student_id] = {
        "completed_hours": completed_hours,
        "topics_completed": topics_completed,
    }
    progress_data = {
        "daily_available_hours": 1,  # fallback; can be enhanced later
        "completed_hours": completed_hours,
        "topics_completed": topics_completed,
    }
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
