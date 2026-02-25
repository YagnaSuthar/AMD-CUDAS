from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai.agents.academic.schema import (
    StudyPlanRequest,
    StudyPlanResponse,
    StudyProgressUpdate,
)
from app.api.ai.agents.academic.service import (
    generate_study_plan_service,
    update_study_progress_service,
    get_study_plan_service,
)
from app.core.database import get_db

router = APIRouter()

@router.get("/")
async def test_academic():
    return {"message":"Academic agent working"}

@router.post(
    "/plan",
    response_model=StudyPlanResponse,
)
async def create_plan(
    request: StudyPlanRequest,
    db: AsyncSession = Depends(get_db),
) -> StudyPlanResponse:
    return await generate_study_plan_service(
        student_id=request.student_id,
        daily_available_hours=request.daily_available_hours,
        db=db,
    )


@router.patch(
    "/progress",
    response_model=StudyPlanResponse,
)
async def update_progress(
    update: StudyProgressUpdate,
    db: AsyncSession = Depends(get_db),
) -> StudyPlanResponse:
    return await update_study_progress_service(
        student_id=update.student_id,
        completed_hours=update.completed_hours,
        topics_completed=update.topics_completed,
        db=db,
    )


@router.get(
    "/plan/{student_id}",
    response_model=StudyPlanResponse,
)
async def get_plan(
    student_id: str,
    db: AsyncSession = Depends(get_db),
) -> StudyPlanResponse:
    return await get_study_plan_service(student_id=student_id, db=db)