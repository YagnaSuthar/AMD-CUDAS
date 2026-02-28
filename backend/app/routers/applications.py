"""
Job Applications API

Endpoints for students to apply to jobs and recruiters to manage applications.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import RoleChecker
from app.models import AuthUser, JobApplication, ApplicationStatus, InterviewPipeline, PipelineStatus, Notification, NotificationType

router = APIRouter(prefix="/applications", tags=["applications"])

recruiter_only = RoleChecker(["RECRUITER"])
student_only = RoleChecker(["STUDENT"])

@router.get("/debug")
async def debug_applications(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    """Debug endpoint to check recruiter applications."""
    from app.models import Job, JobApplication
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Debug: User {current_user.id}, role: {current_user.role}")

        # Get jobs by this recruiter
        job_result = await db.execute(select(Job).where(Job.recruiter_id == current_user.id))
        jobs = job_result.scalars().all()
        logger.info(f"Debug: Found {len(jobs)} jobs for recruiter")

        # Get applications
        app_result = await db.execute(select(JobApplication))
        apps = app_result.scalars().all()
        logger.info(f"Debug: Found {len(apps)} total applications")

        return {
            "user_id": str(current_user.id),
            "user_role": current_user.role,
            "jobs_count": len(jobs),
            "applications_count": len(apps),
            "jobs": [{"id": str(j.id), "title": j.title} for j in jobs[:5]],  # First 5 jobs
        }
    except Exception as exc:
        logger.error(f"Debug error: {exc}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc))


class ApplyRequest(BaseModel):
    job_id: uuid.UUID
    cover_letter: Optional[str] = None


@router.post("/apply", status_code=status.HTTP_201_CREATED)
async def apply_to_job(
    request: ApplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(student_only),
):
    """Student applies to a job."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Invalid user")

    # Check if already applied
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.job_id == request.job_id,
            JobApplication.student_id == current_user.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied to this job",
        )

    application = JobApplication(
        job_id=request.job_id,
        student_id=current_user.id,
        cover_letter=request.cover_letter,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.flush()
    await db.refresh(application)
    return {
        "id": str(application.id),
        "job_id": str(application.job_id),
        "status": application.status.value,
        "created_at": application.created_at.isoformat() if application.created_at else None,
    }


@router.get("/my")
async def get_my_applications(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(student_only),
):
    """Get all applications submitted by the current student."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Invalid user")

    result = await db.execute(
        select(JobApplication).where(
            JobApplication.student_id == current_user.id
        ).order_by(JobApplication.created_at.desc())
    )
    applications = result.scalars().all()

    return [
        {
            "id": str(app.id),
            "job_id": str(app.job_id),
            "status": app.status.value,
            "ai_score": app.ai_score,
            "cover_letter": app.cover_letter,
            "applied_at": app.created_at.isoformat() if app.created_at else None,
        }
        for app in applications
    ]


@router.get("/recruiter")
async def get_recruiter_applications(
    job_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    """Get all applications for jobs posted by the recruiter."""
    from app.models import Job
    import traceback
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"get_recruiter_applications called by user {current_user.id if hasattr(current_user, 'id') else 'unknown'}")
        
        if isinstance(current_user, dict):
            raise HTTPException(status_code=403, detail="Invalid user")

        # Get jobs by this recruiter
        logger.info(f"Querying jobs for recruiter {current_user.id}")
        job_ids_query = select(Job.id).where(Job.recruiter_id == current_user.id)
        if job_id:
            job_ids_query = job_ids_query.where(Job.id == job_id)

        job_ids_result = await db.execute(job_ids_query)
        job_ids = job_ids_result.scalars().all()
        logger.info(f"Found {len(job_ids)} jobs for recruiter")
        if not job_ids:
            return []

        # Get applications for these jobs with student info
        apps_result = await db.execute(
            select(JobApplication).where(
                JobApplication.job_id.in_(job_ids)
            ).order_by(JobApplication.created_at.desc())
        )
        applications = apps_result.scalars().all()

        result = []
        for app in applications:
            job_result = await db.execute(select(Job).where(Job.id == app.job_id))
            job = job_result.scalar_one_or_none()
            
            student_result = await db.execute(select(AuthUser).where(AuthUser.id == app.student_id))
            student = student_result.scalar_one_or_none()

            # Get AI score from pipeline if available
            pipeline_result = await db.execute(
                select(InterviewPipeline).where(
                    InterviewPipeline.job_id == app.job_id,
                    InterviewPipeline.student_id == app.student_id,
                )
            )
            pipeline = pipeline_result.scalar_one_or_none()

            # Get score from report if AI completed
            ai_score = app.ai_score
            if pipeline and pipeline.status == PipelineStatus.AI_COMPLETED:
                from app.models import InterviewReport
                report_result = await db.execute(
                    select(InterviewReport).where(
                        InterviewReport.session_id == pipeline.ai_session_id
                    )
                )
                report = report_result.scalar_one_or_none()
                if report:
                    ai_score = report.final_score

            result.append({
                "id": str(app.id),
                "job_id": str(app.job_id),
                "job_title": job.title if job else "Unknown",
                "job_location": job.location if job else "Unknown",
                "student_id": str(app.student_id),
                "student_name": student.name if student else "Unknown",
                "student_email": student.email if student else "Unknown",
                "status": app.status.value,
                "ai_score": ai_score,
                "cover_letter": app.cover_letter,
                "applied_at": app.created_at.isoformat() if app.created_at else None,
            })

        return result
    except Exception as exc:
        logger.error(f"Error in get_recruiter_applications: {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{application_id}/invite-ai")
async def invite_to_ai_interview(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    """Invite an applicant to AI interview (creates pipeline entry)."""
    from app.models import Job

    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Invalid user")

    app_result = await db.execute(
        select(JobApplication).where(JobApplication.id == application_id)
    )
    application = app_result.scalar_one_or_none()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    # Verify job belongs to this recruiter
    job_result = await db.execute(select(Job).where(Job.id == application.job_id))
    job = job_result.scalar_one_or_none()
    if not job or job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage this application",
        )

    # Check if pipeline entry already exists
    pipeline_result = await db.execute(
        select(InterviewPipeline).where(
            InterviewPipeline.job_id == application.job_id,
            InterviewPipeline.student_id == application.student_id,
        )
    )
    existing_pipeline = pipeline_result.scalar_one_or_none()

    if existing_pipeline:
        # Update existing pipeline
        existing_pipeline.status = PipelineStatus.AI_ASSIGNED
    else:
        # Create new pipeline entry
        from app.models import Company
        company_result = await db.execute(select(Company).where(Company.id == job.company_id))
        company = company_result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        pipeline = InterviewPipeline(
            job_id=application.job_id,
            company_id=company.id,
            recruiter_id=current_user.id,
            student_id=application.student_id,
            status=PipelineStatus.AI_ASSIGNED,
        )
        db.add(pipeline)

    # Update application status
    application.status = ApplicationStatus.AI_ASSIGNED

    # Create notification for student
    notification = Notification(
        user_id=application.student_id,
        type=NotificationType.AI_ASSIGNED,
        title="AI Interview Invitation",
        message=f"You have been invited to an AI interview for {job.title}",
        data={
            "job_id": str(job.id),
            "job_title": job.title,
            "recruiter_id": str(current_user.id),
        },
    )
    db.add(notification)

    await db.flush()

    return {
        "message": "Student invited to AI interview",
        "application_id": str(application_id),
        "status": ApplicationStatus.AI_ASSIGNED.value,
    }


@router.get("/jobs/{job_id}/applicants")
async def get_job_applicants(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    """Get all applicants for a specific job."""
    from app.models import Job

    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Invalid user")

    # Verify job belongs to this recruiter
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job or job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this job's applicants",
        )

    apps_result = await db.execute(
        select(JobApplication).where(
            JobApplication.job_id == job_id
        ).order_by(JobApplication.created_at.desc())
    )
    applications = apps_result.scalars().all()

    result = []
    for app in applications:
        student_result = await db.execute(select(AuthUser).where(AuthUser.id == app.student_id))
        student = student_result.scalar_one_or_none()
        result.append({
            "id": str(app.id),
            "student_id": str(app.student_id),
            "student_name": student.name if student else "Unknown",
            "student_email": student.email if student else "Unknown",
            "status": app.status.value,
            "applied_at": app.created_at.isoformat() if app.created_at else None,
        })

    return result
