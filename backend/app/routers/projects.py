"""
Project CRUD & Verification Routes.
Students can upload/list their projects. Uploading triggers the verification agent.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project
from app.models.verification import VerificationRun

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ProjectCreateRequest(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    github_url: str = Field(..., min_length=1, max_length=512)
    tech_stack: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    project_name: str
    description: Optional[str] = None
    github_url: str
    tech_stack: Optional[str] = None
    verification_status: str = "pending"
    verification_score: Optional[float] = None
    verification_result: Optional[dict] = None
    created_at: Optional[str] = None


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=ProjectListResponse)
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all projects for the current student."""
    user_id = current_user.id if hasattr(current_user, "id") else current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=403, detail="No user ID found")

    result = await db.execute(
        select(Project)
        .where(Project.student_id == user_id)
        .order_by(Project.created_at.desc())
    )
    projects = list(result.scalars().all())

    response_list = []
    for p in projects:
        # Fetch verification score if run exists
        v_score = None
        v_result = None
        if p.verification_run_id:
            vr = await db.execute(
                select(VerificationRun).where(VerificationRun.id == p.verification_run_id)
            )
            run = vr.scalar_one_or_none()
            if run:
                v_score = run.confidence_score
                v_result = run.result

        response_list.append(ProjectResponse(
            id=str(p.id),
            project_name=p.project_name,
            description=p.description,
            github_url=p.github_url,
            tech_stack=p.tech_stack,
            verification_status=p.verification_status or "pending",
            verification_score=v_score,
            verification_result=v_result,
            created_at=p.created_at.isoformat() if p.created_at else None,
        ))

    return ProjectListResponse(projects=response_list)


@router.post("", response_model=ProjectResponse)
async def create_project(
    body: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a new project and trigger verification."""
    user_id = current_user.id if hasattr(current_user, "id") else current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=403, detail="No user ID found")

    logger.info("[PROJECTS] Creating project: %s for user=%s", body.project_name, user_id)

    project = Project(
        student_id=user_id,
        project_name=body.project_name,
        description=body.description,
        github_url=body.github_url,
        tech_stack=body.tech_stack,
        verification_status="pending",
    )
    db.add(project)
    await db.flush()

    # Trigger verification agent
    v_score = None
    v_result = None
    try:
        from app.agents.verification_agent.controller import VerificationController
        controller = VerificationController(db=db)
        verification = await controller.verify(
            user_id=user_id,
            file=None,
            link=body.github_url,
            profile_data=None,
            project_description=body.description,
            tech_stack=body.tech_stack,
        )
        # Update project with verification result
        project.verification_status = verification.status
        project.verification_run_id = uuid.UUID(verification.run_id)
        v_score = verification.confidence_score

        # Fetch the full result
        vr = await db.execute(
            select(VerificationRun).where(VerificationRun.id == uuid.UUID(verification.run_id))
        )
        run = vr.scalar_one_or_none()
        if run:
            v_result = run.result

        logger.info(
            "[PROJECTS] Verification complete: status=%s score=%.2f",
            verification.status, verification.confidence_score,
        )
    except Exception as exc:
        logger.error("[PROJECTS] Verification failed (non-fatal): %s", exc)
        project.verification_status = "failed"

    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        id=str(project.id),
        project_name=project.project_name,
        description=project.description,
        github_url=project.github_url,
        tech_stack=project.tech_stack,
        verification_status=project.verification_status or "pending",
        verification_score=v_score,
        verification_result=v_result,
        created_at=project.created_at.isoformat() if project.created_at else None,
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a project."""
    user_id = current_user.id if hasattr(current_user, "id") else current_user.get("id")
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    result = await db.execute(
        select(Project).where(Project.id == pid, Project.student_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()
    return {"message": "Project deleted successfully"}
