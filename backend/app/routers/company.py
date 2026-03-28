"""
Company router — register company + company_admin, manage recruiters.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import RoleChecker, get_current_user, hash_password
from app.models.auth import AuthUser, AuthUserRole, Company
from app.schemas.auth import (
    MessageResponse,
    RegisterCompanyRequest,
    UserResponse,
)
from app.services.email_service import send_verification_email
from app.services.user_service import get_children

router = APIRouter(prefix="/company", tags=["Company Management"])

company_admin_only = RoleChecker(["COMPANY_ADMIN"])


# ── Register Company ──────────────────────────────────────────────────────


@router.post("/register", response_model=MessageResponse)
async def register_company(
    body: RegisterCompanyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Check email uniqueness
    existing = await db.execute(select(AuthUser).where(AuthUser.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    admin_user = AuthUser(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=AuthUserRole.COMPANY_ADMIN,
        is_verified=False,
        phone_number=body.phone_number,
    )
    db.add(admin_user)
    await db.flush()

    company = Company(
        name=body.company_name,
        company_admin_id=admin_user.id,
    )
    db.add(company)

    return MessageResponse(message="Company registered! Please login to verify your email.")


# ── List Recruiters ───────────────────────────────────────────────────────


@router.get("/recruiters", response_model=list[UserResponse])
async def list_recruiters(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(company_admin_only),
):
    children = await get_children(db, current_user.id)
    return [
        UserResponse(
            id=str(u.id),
            name=u.name,
            email=u.email,
            role=u.role,
            is_verified=u.is_verified,
            parent_id=str(u.parent_id) if u.parent_id else None,
        )
        for u in children
    ]
