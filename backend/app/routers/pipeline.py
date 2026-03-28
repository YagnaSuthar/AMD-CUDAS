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
from app.models.message import Notification, NotificationType
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
async def list_recruiter_pipeline(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    import logging
    logger = logging.getLogger(__name__)

    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot view pipeline")

    result = await db.execute(
        select(InterviewPipeline)
        .where(InterviewPipeline.recruiter_id == current_user.id)
        .order_by(InterviewPipeline.updated_at.desc())
    )
    pipelines = list(result.scalars().all())

    if not pipelines:
        return []

    job_ids = list({p.job_id for p in pipelines})
    company_ids = list({p.company_id for p in pipelines})

    jobs_res = await db.execute(select(Job.id, Job.title).where(Job.id.in_(job_ids)))
    jobs = {jid: title for jid, title in jobs_res.all()}
    companies_res = await db.execute(select(Company.id, Company.name).where(Company.id.in_(company_ids)))
    companies = {cid: name for cid, name in companies_res.all()}

    # Safeguard: if pipeline has ai_session_id, check session status; if COMPLETED, force AI_COMPLETED
    session_ids = [p.ai_session_id for p in pipelines if p.ai_session_id]
    session_status_map = {}
    if session_ids:
        from app.models import InterviewSession, SessionStatus
        sess_res = await db.execute(
            select(InterviewSession.session_id, InterviewSession.status)
            .where(InterviewSession.session_id.in_(session_ids))
        )
        session_status_map = {sid: status for sid, status in sess_res.all()}

    out: list[dict] = []
    for p in pipelines:
        effective_status = p.status.value if hasattr(p.status, "value") else str(p.status)
        if p.ai_session_id and session_status_map.get(p.ai_session_id) == SessionStatus.COMPLETED:
            effective_status = PipelineStatus.AI_COMPLETED.value
            logger.info("pipeline/my: pipeline id=%s forcing AI_COMPLETED because session id=%s is COMPLETED", p.id, p.ai_session_id)

        out.append(
            {
                "id": p.id,
                "job_id": p.job_id,
                "company_id": p.company_id,
                "recruiter_id": p.recruiter_id,
                "student_id": p.student_id,
                "ai_session_id": p.ai_session_id,
                "status": effective_status,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "round2_link": p.round2_link,
                "hired_company_name": p.hired_company_name,
                "job_title": jobs.get(p.job_id),
                "company_name": companies.get(p.company_id),
                "round2_scheduled_at": getattr(p, "round2_scheduled_at", None),
            }
        )

    return out


@router.get("/student", response_model=list[PipelineResponse])
async def list_student_pipeline(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(student_only),
):
    import logging
    logger = logging.getLogger(__name__)

    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot view pipeline")

    result = await db.execute(
        select(InterviewPipeline)
        .where(InterviewPipeline.student_id == current_user.id)
        .order_by(InterviewPipeline.updated_at.desc())
    )
    pipelines = list(result.scalars().all())

    if not pipelines:
        return []

    job_ids = list({p.job_id for p in pipelines})
    company_ids = list({p.company_id for p in pipelines})

    jobs_res = await db.execute(select(Job.id, Job.title).where(Job.id.in_(job_ids)))
    jobs = {jid: title for jid, title in jobs_res.all()}
    companies_res = await db.execute(select(Company.id, Company.name).where(Company.id.in_(company_ids)))
    companies = {cid: name for cid, name in companies_res.all()}

    # Safeguard: if pipeline has ai_session_id, check session status; if COMPLETED, force AI_COMPLETED
    session_ids = [p.ai_session_id for p in pipelines if p.ai_session_id]
    session_status_map = {}
    if session_ids:
        from app.models import InterviewSession, SessionStatus
        sess_res = await db.execute(
            select(InterviewSession.session_id, InterviewSession.status)
            .where(InterviewSession.session_id.in_(session_ids))
        )
        session_status_map = {sid: status for sid, status in sess_res.all()}

    out: list[dict] = []
    for p in pipelines:
        effective_status = p.status.value if hasattr(p.status, "value") else str(p.status)
        if p.ai_session_id and session_status_map.get(p.ai_session_id) == SessionStatus.COMPLETED:
            effective_status = PipelineStatus.AI_COMPLETED.value
            logger.info("pipeline/student: pipeline id=%s forcing AI_COMPLETED because session id=%s is COMPLETED", p.id, p.ai_session_id)

        out.append(
            {
                "id": p.id,
                "job_id": p.job_id,
                "company_id": p.company_id,
                "recruiter_id": p.recruiter_id,
                "student_id": p.student_id,
                "ai_session_id": p.ai_session_id,
                "status": effective_status,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "round2_link": p.round2_link,
                "hired_company_name": p.hired_company_name,
                "job_title": jobs.get(p.job_id),
                "company_name": companies.get(p.company_id),
                "round2_scheduled_at": getattr(p, "round2_scheduled_at", None),
            }
        )

    return out


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
    pipeline.round2_scheduled_at = body.scheduled_at
    pipeline.status = PipelineStatus.ROUND2_INVITED

    job_result = await db.execute(select(Job).where(Job.id == pipeline.job_id))
    job = job_result.scalar_one_or_none()
    company_result = await db.execute(select(Company).where(Company.id == pipeline.company_id))
    company = company_result.scalar_one_or_none()

    db.add(
        Notification(
            user_id=pipeline.student_id,
            notification_type=NotificationType.ROUND2_INVITED,
            title="Round 2 Interview Invitation",
            message=(
                f"You have been invited for Round 2 interview"
                f"{f' for {job.title}' if job else ''}"
                f"{f' at {company.name}' if company else ''}."
            ),
            meta_json={
                "pipeline_id": str(pipeline.id),
                "job_id": str(pipeline.job_id),
                "job_title": job.title if job else None,
                "company_id": str(pipeline.company_id),
                "company_name": company.name if company else None,
                "round2_link": pipeline.round2_link,
                "round2_scheduled_at": pipeline.round2_scheduled_at.isoformat() if pipeline.round2_scheduled_at else None,
            },
            is_read=False,
        )
    )

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
    import logging
    logger = logging.getLogger(__name__)
    logger.info("router.mark_pipeline_ai_completed: called for session_id=%s", session_id)

    result = await db.execute(
        select(InterviewPipeline).where(InterviewPipeline.ai_session_id == session_id)
    )
    pipeline = result.scalar_one_or_none()
    if pipeline is None:
        logger.warning("router.mark_pipeline_ai_completed: no pipeline found for session_id=%s", session_id)
        return

    logger.info("router.mark_pipeline_ai_completed: found pipeline id=%s, current status=%s", pipeline.id, pipeline.status)
    pipeline.status = PipelineStatus.AI_COMPLETED
    logger.info("router.mark_pipeline_ai_completed: updated pipeline id=%s to AI_COMPLETED", pipeline.id)
    await db.flush()
    await db.commit()
    logger.info("router.mark_pipeline_ai_completed: committed pipeline id=%s status=AI_COMPLETED", pipeline.id)


async def attach_session_to_pipeline(db: AsyncSession, student_id: uuid.UUID, session_id: uuid.UUID) -> None:
    """Attach the latest AI session to the most recent AI_ASSIGNED pipeline for a student."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("attach_session_to_pipeline: called for student_id=%s, session_id=%s", student_id, session_id)

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
        logger.warning("attach_session_to_pipeline: no AI_ASSIGNED pipeline found for student_id=%s", student_id)
        return
    logger.info("attach_session_to_pipeline: attaching session_id=%s to pipeline id=%s", session_id, pipeline.id)
    pipeline.ai_session_id = session_id
    await db.flush()
    await db.commit()
    logger.info("attach_session_to_pipeline: committed attachment for pipeline id=%s", pipeline.id)
