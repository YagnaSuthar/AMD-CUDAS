"""
Admin router — CUDAS admin endpoints for college verification and analytics.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import RoleChecker
from app.models.auth import AuthUser, College, ApprovalStatus, Company
from app.schemas.auth import AnalyticsResponse, CollegeResponse, MessageResponse, CompanyResponse

router = APIRouter(prefix="/admin", tags=["CUDAS Admin"])

admin_only = RoleChecker(["CUDAS_ADMIN"])


# ── List Colleges ─────────────────────────────────────────────────────────


@router.get("/colleges", response_model=list[CollegeResponse])
async def list_colleges(
    db: AsyncSession = Depends(get_db),
    _=Depends(admin_only),
):
    result = await db.execute(
        select(College, AuthUser).join(AuthUser, College.principal_id == AuthUser.id)
    )
    colleges = []
    for college, principal in result.all():
        colleges.append(
            CollegeResponse(
                id=str(college.id),
                name=college.name,
                principal_name=principal.name,
                principal_email=principal.email,
                status=college.status,
                created_at=str(college.created_at),
            )
        )
    return colleges


# ── Verify (Approve) College ──────────────────────────────────────────────


@router.put("/verify-college/{college_id}", response_model=MessageResponse)
async def verify_college(
    college_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(admin_only),
):
    result = await db.execute(select(College).where(College.id == college_id))
    college = result.scalar_one_or_none()

    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    college.status = ApprovalStatus.APPROVED
    return MessageResponse(message=f"College '{college.name}' has been approved.")


# ── Reject College ────────────────────────────────────────────────────────


@router.put("/reject-college/{college_id}", response_model=MessageResponse)
async def reject_college(
    college_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(admin_only),
):
    result = await db.execute(select(College).where(College.id == college_id))
    college = result.scalar_one_or_none()

    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    college.status = ApprovalStatus.REJECTED
    return MessageResponse(message=f"College '{college.name}' has been rejected.")


# ── List Companies ────────────────────────────────────────────────────────


@router.get("/companies", response_model=list[CompanyResponse])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    _=Depends(admin_only),
):
    result = await db.execute(
        select(Company, AuthUser).join(AuthUser, Company.company_admin_id == AuthUser.id)
    )
    companies = []
    for company, admin in result.all():
        companies.append(
            CompanyResponse(
                id=str(company.id),
                name=company.name,
                admin_name=admin.name,
                admin_email=admin.email,
                status=company.status,
                created_at=str(company.created_at),
            )
        )
    return companies


# ── Verify (Approve) Company ──────────────────────────────────────────────


@router.put("/verify-company/{company_id}", response_model=MessageResponse)
async def verify_company(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(admin_only),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.status = ApprovalStatus.APPROVED
    return MessageResponse(message=f"Company '{company.name}' has been approved.")


# ── Reject Company ────────────────────────────────────────────────────────


@router.put("/reject-company/{company_id}", response_model=MessageResponse)
async def reject_company(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(admin_only),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.status = ApprovalStatus.REJECTED
    return MessageResponse(message=f"Company '{company.name}' has been rejected.")


# ── System Analytics ──────────────────────────────────────────────────────


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    _=Depends(admin_only),
):
    # College counts
    total_colleges = await db.scalar(select(func.count(College.id)))

    # Company counts
    total_companies = await db.scalar(select(func.count(Company.id)))

    # User counts
    total_users = await db.scalar(select(func.count(AuthUser.id)))

    # Pending approvals (both)
    pending_colleges = await db.scalar(
        select(func.count(College.id)).where(College.status == ApprovalStatus.PENDING)
    )
    pending_companies = await db.scalar(
        select(func.count(Company.id)).where(Company.status == ApprovalStatus.PENDING)
    )
    pending_approvals = (pending_colleges or 0) + (pending_companies or 0)

    role_counts_result = await db.execute(
        select(AuthUser.role, func.count(AuthUser.id)).group_by(AuthUser.role)
    )
    users_by_role = {row[0]: row[1] for row in role_counts_result.all()}

    return AnalyticsResponse(
        total_colleges=total_colleges or 0,
        total_companies=total_companies or 0,
        total_users=total_users or 0,
        pending_approvals=pending_approvals,
        users_by_role=users_by_role,
    )
