from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai.agents.performance.schema import (
    PerformanceAnalysisResponse,
    PerformanceAnalysisRequest,
    PerformanceCategoryQueryResponse,
    PerformanceCategoryStudent,
)
from app.api.ai.agents.performance.service import prepare_dataframe , classify_students
from app.core.database import get_db
from app.core.security import RoleChecker
from app.models.auth import AuthUser, StudentPerformanceCategory

router = APIRouter()

faculty_only = RoleChecker(["FACULTY"])

@router.get("/")
async def test_performance():
    return {"message":"performance agent working"}

@router.post("/analyze",response_model=PerformanceAnalysisResponse)
def analyze_performance(request:PerformanceAnalysisRequest):
    df = prepare_dataframe(request.marks_data)
    
    top,weak,dropout,avg = classify_students(df)

    return PerformanceAnalysisResponse(
        top_students=top.to_dict("records"),
        weak_students=weak.to_dict("records"),
        average_performance=round(avg,2),
        dropout_rist_students=dropout.to_dict("records")
    )


@router.get("/categories", response_model=PerformanceCategoryQueryResponse)
async def get_performance_categories(
    semester: int | None = None,
    subject_name: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(faculty_only),
):
    q = (
        select(StudentPerformanceCategory, AuthUser.name)
        .join(AuthUser, StudentPerformanceCategory.student_id == AuthUser.id)
        .where(StudentPerformanceCategory.computed_by == current_user.id)
        .order_by(StudentPerformanceCategory.semester, StudentPerformanceCategory.subject_name)
    )

    if semester is not None:
        q = q.where(StudentPerformanceCategory.semester == semester)
    if subject_name is not None:
        q = q.where(StudentPerformanceCategory.subject_name == subject_name)
    if category is not None:
        q = q.where(StudentPerformanceCategory.category == category)

    res = await db.execute(q)
    rows = res.all()
    return PerformanceCategoryQueryResponse(
        results=[
            PerformanceCategoryStudent(
                student_id=str(r.student_id),
                student_name=name,
                semester=r.semester,
                subject_name=r.subject_name,
                average_percentage=float(r.average_percentage),
                category=str(r.category),
            )
            for r, name in rows
        ]
    )

