"""
CSV upload router — upload CSV of subordinate users, download template,
download credentials.

Provides structured error responses and role-based authorization.
"""

import csv
import io
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.csv_service import (
    EXPECTED_COLUMNS,
    MAX_CSV_SIZE_BYTES,
    get_csv_template,
    process_csv_upload,
)
from app.services.user_service import can_create_role

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/csv", tags=["CSV Upload"])


# ── Download CSV Template ─────────────────────────────────────────────────


@router.get("/template")
async def download_template(
    target_role: str = Query(..., description="Target role for CSV template"),
):
    """Download an example CSV template for the given target role."""
    target_role = target_role.strip().upper()
    template = get_csv_template(target_role)
    if not template:
        valid_roles = ", ".join(EXPECTED_COLUMNS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"No template for role: '{target_role}'. Valid roles: {valid_roles}",
        )

    return StreamingResponse(
        io.BytesIO(template.encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={target_role.lower()}_template.csv"
        },
    )


# ── Upload CSV ────────────────────────────────────────────────────────────


@router.post("/upload")
async def upload_csv(
    target_role: str = Query(..., description="Role to create from CSV"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Upload a CSV file to bulk-create subordinate user accounts.

    Returns structured response with created credentials or detailed
    per-row validation errors.
    """
    target_role = target_role.strip().upper()

    # ── File Extension Check ──────────────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a file with .csv extension",
        )

    # ── Role Authorization Check ──────────────────────────────────────────
    user_role = (
        current_user.role
        if hasattr(current_user, "role")
        else current_user.get("role")
    )
    if not can_create_role(user_role, target_role):
        raise HTTPException(
            status_code=403,
            detail=f"Your role ({user_role}) cannot create {target_role} accounts via CSV",
        )

    # ── Read & Size Check ─────────────────────────────────────────────────
    raw_bytes = await file.read()
    if len(raw_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(raw_bytes) > MAX_CSV_SIZE_BYTES:
        size_mb = round(len(raw_bytes) / (1024 * 1024), 2)
        limit_mb = MAX_CSV_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb} MB). Maximum allowed: {limit_mb} MB",
        )

    _logger.info(
        "CSV upload: user=%s role=%s target=%s file=%s size=%d",
        getattr(current_user, "email", "admin"),
        user_role,
        target_role,
        file.filename,
        len(raw_bytes),
    )

    # ── Process ───────────────────────────────────────────────────────────
    result = await process_csv_upload(
        db=db,
        raw_bytes=raw_bytes,
        target_role=target_role,
        parent_user=current_user,
    )

    if not result.success:
        # Return structured validation errors
        error_response = {
            "success": False,
            "message": result.message,
        }
        if result.errors:
            error_response["errors"] = [
                {"row": e.row, "field": e.field, "message": e.message}
                for e in result.errors
            ]
        raise HTTPException(status_code=400, detail=error_response)

    return {
        "success": True,
        "message": result.message,
        "created_count": result.created_count,
        "skipped_count": result.skipped_count,
        "credentials": result.credentials,
    }


# ── Download Credentials ──────────────────────────────────────────────────


@router.post("/download-credentials")
async def download_credentials(
    credentials: list[dict],
):
    """Convert credentials list to a downloadable CSV file."""
    if not credentials:
        raise HTTPException(status_code=400, detail="No credentials to download")

    output = io.StringIO()
    fieldnames = ["name", "email", "role", "action"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for cred in credentials:
        writer.writerow(cred)

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=credentials.csv"},
    )
