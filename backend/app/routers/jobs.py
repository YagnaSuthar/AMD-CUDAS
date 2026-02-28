import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import RoleChecker, get_current_user
from app.models.auth import AuthUser, Company
from app.models.job import Job
from app.schemas.jobs import JobCreateRequest, JobResponse, JobUpdateRequest

router = APIRouter(prefix="/jobs", tags=["Jobs"])

recruiter_only = RoleChecker(["RECRUITER"])
student_only = RoleChecker(["STUDENT"])


async def _get_recruiter_company_id(db: AsyncSession, recruiter: AuthUser) -> uuid.UUID:
    if recruiter.parent_id is None:
        raise HTTPException(status_code=400, detail="Recruiter has no company admin parent")

    result = await db.execute(select(Company).where(Company.company_admin_id == recruiter.parent_id))
    company = result.scalar_one_or_none()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found for recruiter")
    return company.id


@router.post("/", response_model=JobResponse)
async def create_job(
    body: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot create jobs")

    company_id = await _get_recruiter_company_id(db, current_user)

    job = Job(
        company_id=company_id,
        recruiter_id=current_user.id,
        title=body.title,
        description=body.description,
        package_lpa=body.package_lpa,
        bond=body.bond,
        location=body.location,
        status="ACTIVE",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/my", response_model=list[JobResponse])
async def list_my_jobs(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot list jobs")

    result = await db.execute(select(Job).where(Job.recruiter_id == current_user.id).order_by(Job.created_at.desc()))
    return list(result.scalars().all())


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: uuid.UUID,
    body: JobUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot update jobs")

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to modify this job")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(job, field, value)

    await db.commit()
    await db.refresh(job)
    return job


@router.get("/", response_model=list[JobResponse])
async def list_jobs_for_students(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot list jobs")

    if current_user.role not in ("STUDENT", "RECRUITER", "COMPANY_ADMIN"):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(select(Job).where(Job.status == "ACTIVE").order_by(Job.created_at.desc()))
    return list(result.scalars().all())
