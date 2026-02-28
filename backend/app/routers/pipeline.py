import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import RoleChecker
from app.models.auth import AuthUser, Company
from app.models.interview import InterviewSession, SessionStatus
from app.models.job import Job
from app.models.pipeline import InterviewPipeline, PipelineStatus
from app.schemas.pipeline import (
    AssignAiInterviewRequest,
    InviteRound2Request,
    MarkHiredRequest,
    PipelineResponse,
)

router = APIRouter(prefix="/pipeline", tags=["Interview Pipeline"])

recruiter_only = RoleChecker(["RECRUITER"])
student_only = RoleChecker(["STUDENT"])


async def _get_recruiter_company(db: AsyncSession, recruiter: AuthUser) -> Company:
    if recruiter.parent_id is None:
        raise HTTPException(status_code=400, detail="Recruiter has no company admin parent")
    result = await db.execute(select(Company).where(Company.company_admin_id == recruiter.parent_id))
    company = result.scalar_one_or_none()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found for recruiter")
    return company


@router.post("/assign-ai", response_model=PipelineResponse)
async def assign_ai_interview(
    body: AssignAiInterviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot assign interviews")

    company = await _get_recruiter_company(db, current_user)

    job_result = await db.execute(select(Job).where(Job.id == body.job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.company_id != company.id:
        raise HTTPException(status_code=403, detail="Job does not belong to your company")

    student_result = await db.execute(select(AuthUser).where(AuthUser.id == body.student_id))
    student = student_result.scalar_one_or_none()
    if student is None or student.role != "STUDENT":
        raise HTTPException(status_code=404, detail="Student not found")

    # Create a pipeline row (unique per job+student)
    pipeline = InterviewPipeline(
        job_id=job.id,
        company_id=company.id,
        recruiter_id=current_user.id,
        student_id=student.id,
        status=PipelineStatus.AI_ASSIGNED,
    )
    db.add(pipeline)

    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        # Likely unique constraint violation
        raise HTTPException(status_code=409, detail="Pipeline already exists for this job and student") from e

    await db.refresh(pipeline)
    return pipeline


@router.get("/my", response_model=list[PipelineResponse])
async def list_my_pipeline(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot view pipeline")

    result = await db.execute(
        select(InterviewPipeline)
        .where(InterviewPipeline.recruiter_id == current_user.id)
        .order_by(InterviewPipeline.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/student", response_model=list[PipelineResponse])
async def list_student_pipeline(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(student_only),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot view pipeline")

    result = await db.execute(
        select(InterviewPipeline)
        .where(InterviewPipeline.student_id == current_user.id)
        .order_by(InterviewPipeline.updated_at.desc())
    )
    return list(result.scalars().all())


@router.put("/invite-round2", response_model=PipelineResponse)
async def invite_round2(
    body: InviteRound2Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot update pipeline")

    result = await db.execute(select(InterviewPipeline).where(InterviewPipeline.id == body.pipeline_id))
    pipeline = result.scalar_one_or_none()
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    if pipeline.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    pipeline.round2_link = body.round2_link
    pipeline.status = PipelineStatus.ROUND2_INVITED

    await db.commit()
    await db.refresh(pipeline)
    return pipeline


@router.put("/mark-hired", response_model=PipelineResponse)
async def mark_hired(
    body: MarkHiredRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot update pipeline")

    result = await db.execute(select(InterviewPipeline).where(InterviewPipeline.id == body.pipeline_id))
    pipeline = result.scalar_one_or_none()
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    if pipeline.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    pipeline.hired_company_name = body.hired_company_name
    pipeline.status = PipelineStatus.HIRED

    await db.commit()
    await db.refresh(pipeline)
    return pipeline


async def mark_pipeline_ai_completed(db: AsyncSession, session_id: uuid.UUID) -> None:
    """Called when an AI interview session completes."""
    result = await db.execute(
        select(InterviewPipeline).where(InterviewPipeline.ai_session_id == session_id)
    )
    pipeline = result.scalar_one_or_none()
    if pipeline is None:
        return

    pipeline.status = PipelineStatus.AI_COMPLETED
    await db.flush()


async def attach_session_to_pipeline(db: AsyncSession, student_id: uuid.UUID, session_id: uuid.UUID) -> None:
    """Attach the latest AI session to the most recent AI_ASSIGNED pipeline for a student."""
    result = await db.execute(
        select(InterviewPipeline)
        .where(
            InterviewPipeline.student_id == student_id,
            InterviewPipeline.status == PipelineStatus.AI_ASSIGNED,
            InterviewPipeline.ai_session_id.is_(None),
        )
        .order_by(InterviewPipeline.created_at.desc())
    )
    pipeline = result.scalar_one_or_none()
    if pipeline is None:
        return
    pipeline.ai_session_id = session_id
    await db.flush()
