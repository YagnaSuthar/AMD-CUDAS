"""
CSV upload router — upload CSV of subordinate users, download template, download credentials.
"""

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import MessageResponse
from app.services.csv_service import get_csv_template, process_csv_upload

router = APIRouter(prefix="/csv", tags=["CSV Upload"])


# ── Download CSV Template ─────────────────────────────────────────────────


@router.get("/template")
async def download_template(target_role: str = Query(..., description="Target role for CSV")):
    template = get_csv_template(target_role)
    if not template:
        raise HTTPException(status_code=400, detail=f"No template for role: {target_role}")

    return StreamingResponse(
        io.BytesIO(template.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={target_role.lower()}_template.csv"},
    )


# ── Upload CSV ────────────────────────────────────────────────────────────


@router.post("/upload")
async def upload_csv(
    target_role: str = Query(..., description="Role to create from CSV"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    content = await file.read()
    file_content = content.decode("utf-8")

    success, message, credentials = await process_csv_upload(
        db=db,
        file_content=file_content,
        target_role=target_role,
        parent_user=current_user,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"message": message, "created_count": len(credentials), "credentials": credentials}


# ── Download Credentials ──────────────────────────────────────────────────


@router.post("/download-credentials")
async def download_credentials(
    credentials: list[dict],
):
    """Convert credentials list to a downloadable CSV."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["name", "email", "password"])
    writer.writeheader()
    for cred in credentials:
        writer.writerow(cred)

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=credentials.csv"},
    )
