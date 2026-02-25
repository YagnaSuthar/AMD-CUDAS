"""
User service — CRUD operations for auth users with hierarchy enforcement.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import AuthUser, AuthUserRole


# Which roles can create which child roles
HIERARCHY_MAP = {
    "CUDAS_ADMIN": [],  # admin doesn't create users via this service
    "COLLEGE_PRINCIPAL": ["HOD"],
    "HOD": ["FACULTY"],
    "FACULTY": ["STUDENT"],
    "COMPANY_ADMIN": ["RECRUITER"],
    "RECRUITER": [],
    "STUDENT": [],
}


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[AuthUser]:
    result = await db.execute(select(AuthUser).where(AuthUser.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[AuthUser]:
    result = await db.execute(select(AuthUser).where(AuthUser.id == user_id))
    return result.scalar_one_or_none()


async def get_children(db: AsyncSession, parent_id: UUID) -> list[AuthUser]:
    result = await db.execute(
        select(AuthUser).where(AuthUser.parent_id == parent_id)
    )
    return list(result.scalars().all())


async def get_users_by_role(db: AsyncSession, role: str) -> list[AuthUser]:
    result = await db.execute(
        select(AuthUser).where(AuthUser.role == role)
    )
    return list(result.scalars().all())


async def count_users_by_role(db: AsyncSession) -> dict:
    result = await db.execute(
        select(AuthUser.role, func.count(AuthUser.id)).group_by(AuthUser.role)
    )
    return {row[0]: row[1] for row in result.all()}


def can_create_role(parent_role: str, child_role: str) -> bool:
    """Check if a parent role is allowed to create the given child role."""
    return child_role in HIERARCHY_MAP.get(parent_role, [])
