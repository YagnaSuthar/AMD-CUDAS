"""
College router — endpoints for principals to manage their college hierarchy.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import RoleChecker, get_current_user
from app.models.auth import AuthUser
from app.schemas.auth import UserResponse
from app.services.user_service import get_children

router = APIRouter(prefix="/college", tags=["College Management"])

principal_or_above = RoleChecker(["CUDAS_ADMIN", "COLLEGE_PRINCIPAL", "HOD", "FACULTY"])


# ── List subordinate users ────────────────────────────────────────────────


@router.get("/users", response_model=list[UserResponse])
async def list_my_users(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List users created by the current user (direct children)."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="CUDAS admin uses /admin routes")

    children = await get_children(db, current_user.id)
    return [
        UserResponse(
            id=str(u.id),
            name=u.name,
            email=u.email,
            role=u.role,
            is_verified=u.is_verified,
            department=u.department,
            semester=u.semester,
            roll_number=u.roll_number,
            parent_id=str(u.parent_id) if u.parent_id else None,
        )
        for u in children
    ]


# ── Get all users under hierarchy (recursive) ────────────────────────────


@router.get("/all-users", response_model=list[UserResponse])
async def list_all_hierarchy_users(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(principal_or_above),
):
    """Recursively list all users under the current user's hierarchy."""
    if isinstance(current_user, dict):
        # CUDAS admin — return all users
        result = await db.execute(select(AuthUser))
        users = result.scalars().all()
    else:
        users = await _get_all_descendants(db, current_user.id)

    return [
        UserResponse(
            id=str(u.id),
            name=u.name,
            email=u.email,
            role=u.role,
            is_verified=u.is_verified,
            department=u.department,
            semester=u.semester,
            roll_number=u.roll_number,
            parent_id=str(u.parent_id) if u.parent_id else None,
        )
        for u in users
    ]


async def _get_all_descendants(db: AsyncSession, parent_id) -> list:
    """BFS to get all descendants."""
    all_users = []
    queue = [parent_id]
    while queue:
        pid = queue.pop(0)
        children = await get_children(db, pid)
        for child in children:
            all_users.append(child)
            queue.append(child.id)
    return all_users
