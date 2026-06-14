import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, distinct, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import RoleChecker, get_current_user
from app.api.ai.agents.aptitude.models import AptitudeQuestion, QuestionImportJob, QuestionImportItem
from app.repositories.aptitude_repository import AptitudeRepository
from app.services.aptitude_import_service import AptitudeImportService
from app.services.aptitude_validator import validate_aptitude_question
from app.schemas.aptitude_admin import (
    AptitudeQuestionCreate,
    AptitudeQuestionUpdate,
    AptitudeQuestionResponse,
    AptitudeQuestionListResponse,
    QuestionImportJobResponse,
    QuestionImportJobDetailResponse,
    TaxonomyHierarchyResponse,
)

# ── Router Initialization ──────────────────────────────────────────────────

admin_only = RoleChecker(["CUDAS_ADMIN"])

# Main Admin Router (protected)
admin_router = APIRouter(
    prefix="/admin/aptitude",
    tags=["Aptitude Admin Management"],
    dependencies=[Depends(admin_only)],
)

# Public Taxonomy Router (not globally protected, but authenticates)
public_taxonomy_router = APIRouter(tags=["Aptitude Taxonomy"])


# ── Admin CRUD Endpoints ──────────────────────────────────────────────────


@admin_router.get("/questions", response_model=AptitudeQuestionListResponse)
async def list_questions(
    db: AsyncSession = Depends(get_db),
    domain: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    is_active: Optional[bool] = Query(None),
    include_deleted: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List questions with advanced pagination and filtering."""
    questions, total = await AptitudeRepository.search_questions(
        db=db,
        domain=domain,
        category=category,
        subcategory=subcategory,
        difficulty=difficulty,
        status=status,
        source=source,
        tags=tags,
        is_active=is_active,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
    )
    return {
        "questions": questions,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@admin_router.get("/questions/{question_id}", response_model=AptitudeQuestionResponse)
async def get_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details of a specific question by UUID."""
    res = await db.execute(
        select(AptitudeQuestion).where(
            AptitudeQuestion.id == question_id,
            AptitudeQuestion.is_deleted == False
        )
    )
    q = res.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Aptitude question not found")
    return q


@admin_router.post("/questions", response_model=AptitudeQuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    body: AptitudeQuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(admin_only),
):
    """Manually create a new aptitude question."""
    # Check validator
    errors = await validate_aptitude_question(
        question=body.question,
        options=body.options,
        correct_answer=body.correct_answer,
        domain=body.domain,
        category=body.category,
        difficulty=body.difficulty,
        status=body.status,
        source=body.source,
        expected_time_seconds=body.expected_time_seconds,
        db=db,
    )
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Validation failed", "errors": errors},
        )

    # Resolve created_by UUID
    user_id = current_user.id if hasattr(current_user, "id") else None

    q = await AptitudeRepository.create_question(
        db=db,
        question=body.question,
        options=body.options,
        correct_answer=body.correct_answer,
        category=body.category,
        difficulty=body.difficulty,
        domain=body.domain,
        subcategory=body.subcategory,
        status=body.status or "draft",
        source=body.source or "admin",
        explanation=body.explanation,
        tags=body.tags,
        expected_time_seconds=body.expected_time_seconds,
        created_by=user_id,
    )
    await db.commit()
    await db.refresh(q)
    return q


@admin_router.put("/questions/{question_id}", response_model=AptitudeQuestionResponse)
async def update_question(
    question_id: uuid.UUID,
    body: AptitudeQuestionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Manually update an existing aptitude question."""
    # Fetch existing
    res = await db.execute(
        select(AptitudeQuestion).where(
            AptitudeQuestion.id == question_id,
            AptitudeQuestion.is_deleted == False
        )
    )
    existing = res.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Aptitude question not found")

    # Merge updates for validation
    body_dict = body.model_dump(exclude_unset=True)
    val_q = body_dict.get("question", existing.question)
    val_opts = body_dict.get("options", existing.options)
    val_ans = body_dict.get("correct_answer", existing.correct_answer)
    val_dom = body_dict.get("domain", existing.domain)
    val_cat = body_dict.get("category", existing.category)
    val_diff = body_dict.get("difficulty", existing.difficulty)
    val_status = body_dict.get("status", existing.status)
    val_time = body_dict.get("expected_time_seconds", existing.expected_time_seconds)

    # Validate
    errors = await validate_aptitude_question(
        question=val_q,
        options=val_opts,
        correct_answer=val_ans,
        domain=val_dom,
        category=val_cat,
        difficulty=val_diff,
        status=val_status,
        expected_time_seconds=val_time,
        db=db,
        exclude_question_id=question_id,
    )
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Validation failed", "errors": errors},
        )

    updated = await AptitudeRepository.update_question(
        db=db,
        question_id=question_id,
        **body_dict,
    )
    await db.commit()
    await db.refresh(updated)
    return updated


@admin_router.delete("/questions/{question_id}")
async def delete_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete an aptitude question."""
    success = await AptitudeRepository.soft_delete_question(db, question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Aptitude question not found or already deleted")
    await db.commit()
    return {"message": "Question soft deleted successfully", "id": question_id}


@admin_router.patch("/questions/{question_id}/approve", response_model=AptitudeQuestionResponse)
async def approve_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(admin_only),
):
    """Approve an aptitude question, enabling it for candidate testing."""
    user_id = current_user.id if hasattr(current_user, "id") else None
    q = await AptitudeRepository.approve_question(db, question_id, approved_by=user_id)
    if not q:
        raise HTTPException(status_code=404, detail="Aptitude question not found")
    await db.commit()
    await db.refresh(q)
    return q


@admin_router.patch("/questions/{question_id}/archive", response_model=AptitudeQuestionResponse)
async def archive_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Archive a question, removing it from active selection lists."""
    q = await AptitudeRepository.archive_question(db, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Aptitude question not found")
    await db.commit()
    await db.refresh(q)
    return q


@admin_router.patch("/questions/{question_id}/restore", response_model=AptitudeQuestionResponse)
async def restore_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted or archived question back to draft status."""
    q = await AptitudeRepository.restore_question(db, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Aptitude question not found")
    await db.commit()
    await db.refresh(q)
    return q


# ── Statistics Endpoint ───────────────────────────────────────────────────


@admin_router.get("/statistics")
async def get_statistics(
    db: AsyncSession = Depends(get_db),
):
    """
    Return aggregated question statistics:
    totals (total, approved, draft, archived),
    breakdowns by domain, difficulty, and source.
    """
    base_filter = AptitudeQuestion.is_deleted == False

    # ── Totals ──
    total = await db.scalar(
        select(func.count(AptitudeQuestion.id)).where(base_filter)
    ) or 0
    approved = await db.scalar(
        select(func.count(AptitudeQuestion.id)).where(
            base_filter, AptitudeQuestion.status == "approved"
        )
    ) or 0
    draft = await db.scalar(
        select(func.count(AptitudeQuestion.id)).where(
            base_filter, AptitudeQuestion.status == "draft"
        )
    ) or 0
    archived = await db.scalar(
        select(func.count(AptitudeQuestion.id)).where(
            base_filter, AptitudeQuestion.status == "archived"
        )
    ) or 0

    # ── By Domain ──
    domain_rows = (
        await db.execute(
            select(AptitudeQuestion.domain, func.count(AptitudeQuestion.id))
            .where(base_filter, AptitudeQuestion.domain.isnot(None))
            .group_by(AptitudeQuestion.domain)
        )
    ).all()
    by_domain: Dict[str, int] = {row[0]: row[1] for row in domain_rows}

    # ── By Difficulty ──
    diff_rows = (
        await db.execute(
            select(AptitudeQuestion.difficulty, func.count(AptitudeQuestion.id))
            .where(base_filter, AptitudeQuestion.difficulty.isnot(None))
            .group_by(AptitudeQuestion.difficulty)
        )
    ).all()
    by_difficulty: Dict[str, int] = {row[0]: row[1] for row in diff_rows}

    # ── By Source ──
    source_rows = (
        await db.execute(
            select(AptitudeQuestion.source, func.count(AptitudeQuestion.id))
            .where(base_filter, AptitudeQuestion.source.isnot(None))
            .group_by(AptitudeQuestion.source)
        )
    ).all()
    by_source: Dict[str, int] = {row[0]: row[1] for row in source_rows}

    return {
        "totals": {
            "total_questions": total,
            "approved": approved,
            "draft": draft,
            "archived": archived,
        },
        "by_domain": by_domain,
        "by_difficulty": by_difficulty,
        "by_source": by_source,
    }


# ── Bulk Import Endpoints ─────────────────────────────────────────────────


@admin_router.post("/import/upload", response_model=QuestionImportJobResponse)
async def upload_import_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a file (JSON, CSV, XLSX, PDF) to create an import job preview.
    Runs validator in non-destructive dry-run, saving preview rows.
    """
    filename = file.filename or "unknown_file"
    ext = filename.split(".")[-1].lower()

    if ext not in ["json", "csv", "xlsx", "pdf"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '.{ext}'. Supported extensions: .json, .csv, .xlsx, .pdf",
        )

    # Map ext to source_type
    source_type = ext.upper()

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Create job
    job = await AptitudeImportService.create_import_job(db=db, filename=filename, source_type=source_type)
    await db.commit()

    # Process and Validate (background/sync processing within route)
    job = await AptitudeImportService.process_import_job(db=db, job_id=job.id, file_bytes=file_bytes)
    await db.commit()

    return job


@admin_router.get("/import/jobs", response_model=None)
async def list_import_jobs(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all import jobs with pagination, ordered by creation date descending."""
    total = await db.scalar(
        select(func.count(QuestionImportJob.id))
    ) or 0

    result = await db.execute(
        select(QuestionImportJob)
        .order_by(QuestionImportJob.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    jobs = result.scalars().all()

    return {
        "jobs": [
            {
                "id": str(job.id),
                "filename": job.filename,
                "source_type": job.source_type,
                "status": job.status,
                "total_questions": job.total_questions,
                "valid_questions": job.valid_questions,
                "invalid_questions": job.invalid_questions,
                "error_log": job.error_log,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
            for job in jobs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@admin_router.get("/import/jobs/{job_id}", response_model=QuestionImportJobDetailResponse)
async def get_import_job_preview(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details and item previews for an import job."""
    # Fetch job
    job_res = await db.execute(select(QuestionImportJob).where(QuestionImportJob.id == job_id))
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    # Fetch items
    items_res = await db.execute(
        select(QuestionImportItem).where(QuestionImportItem.job_id == job_id).order_by(QuestionImportItem.id)
    )
    items = items_res.scalars().all()

    return {
        "job": job,
        "items": items,
    }


@admin_router.post("/import/jobs/{job_id}/confirm")
async def confirm_import_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(admin_only),
):
    """
    Confirm and insert validated questions from import job into AptitudeQuestion table.
    """
    user_id = current_user.id if hasattr(current_user, "id") else None

    try:
        inserted, skipped = await AptitudeImportService.confirm_import(
            db=db, job_id=job_id, confirmed_by=user_id
        )
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Import confirmation failed: {str(e)}")

    return {
        "message": "Import confirmed successfully",
        "job_id": job_id,
        "inserted_questions": inserted,
        "skipped_duplicates": skipped,
    }


# ── Admin Taxonomy Endpoint ───────────────────────────────────────────────


@admin_router.get("/taxonomy", response_model=TaxonomyHierarchyResponse)
async def get_taxonomy_tree(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve structured domains, categories, and subcategories tree hierarchy."""
    stmt = select(
        AptitudeQuestion.domain,
        AptitudeQuestion.category,
        AptitudeQuestion.subcategory
    ).where(AptitudeQuestion.is_deleted == False).distinct()

    result = await db.execute(stmt)
    rows = result.all()

    hierarchy = {}
    for dom, cat, sub in rows:
        # Default fallback if domain is not provided
        dom_name = str(dom or "quantitative").strip().lower()
        if not cat:
            continue
        cat_name = str(cat).strip().lower()

        dom_entry = hierarchy.setdefault(dom_name, {})
        cat_entry = dom_entry.setdefault(cat_name, [])

        if sub:
            sub_name = str(sub).strip().lower()
            if sub_name not in cat_entry:
                cat_entry.append(sub_name)

    return {"hierarchy": hierarchy}


# ── Public Taxonomy Endpoints ─────────────────────────────────────────────


@public_taxonomy_router.get("/domains", response_model=List[str])
async def list_domains(db: AsyncSession = Depends(get_db)):
    """List all unique active question domains."""
    res = await db.execute(
        select(distinct(AptitudeQuestion.domain)).where(
            AptitudeQuestion.is_deleted == False,
            AptitudeQuestion.domain.isnot(None),
        )
    )
    return list(res.scalars().all())


@public_taxonomy_router.get("/categories", response_model=List[str])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """List all unique active question categories."""
    res = await db.execute(
        select(distinct(AptitudeQuestion.category)).where(
            AptitudeQuestion.is_deleted == False,
            AptitudeQuestion.category.isnot(None),
        )
    )
    return list(res.scalars().all())


@public_taxonomy_router.get("/subcategories", response_model=List[str])
async def list_subcategories(db: AsyncSession = Depends(get_db)):
    """List all unique active question subcategories."""
    res = await db.execute(
        select(distinct(AptitudeQuestion.subcategory)).where(
            AptitudeQuestion.is_deleted == False,
            AptitudeQuestion.subcategory.isnot(None),
        )
    )
    return list(res.scalars().all())
