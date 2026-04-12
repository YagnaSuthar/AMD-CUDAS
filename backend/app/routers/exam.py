"""
Exam router — exam timetable CSV template, upload, and bulk creation.
"""

import csv
import io
import datetime
import logging
from typing import List

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, update

from app.core.database import get_db
from app.core.security import hod_only
from app.models.auth import Timetable
from app.services.csv_service import decode_csv_content

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exam", tags=["Exam"])


class ExamEntry(BaseModel):
    semester: str
    subject: str
    date: str
    time: str


class ExamBulkCreate(BaseModel):
    exams: List[ExamEntry]


@router.get("/template")
async def download_template():
    """Download an example exam timetable CSV template."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["semester", "subject", "date", "time"])
    writer.writeheader()
    writer.writerow({
        "semester": "1",
        "subject": "Mathematics I",
        "date": "2024-05-20",
        "time": "10:30"
    })

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=exam_timetable_template.csv"},
    )


@router.post("/upload-exam-csv")
async def upload_exam_csv(
    file: UploadFile = File(...),
    current_user=Depends(hod_only),
):
    """
    Upload an exam timetable CSV for validation.
    Returns parsed rows with per-row validation status.
    Requires HOD authentication.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Use shared decoder for multi-encoding support
    file_content = decode_csv_content(raw_bytes)

    reader = csv.DictReader(io.StringIO(file_content))

    # Check if headers exist
    expected_fields = {"semester", "subject", "date", "time"}
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or missing headers.")

    actual_fields = {f.strip().lower() for f in reader.fieldnames if f}
    missing = expected_fields - actual_fields
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required headers: {', '.join(missing)}"
        )

    results = []

    for row in reader:
        # Get values safely, stripping whitespace
        row_data = {
            "semester": str(row.get("semester", "")).strip(),
            "subject": str(row.get("subject", "")).strip(),
            "date": str(row.get("date", "")).strip(),
            "time": str(row.get("time", "")).strip()
        }

        valid = True
        error_msg = None

        # Skip completely empty rows
        if not any(row_data.values()):
            continue

        # Check required fields
        if not all(row_data.values()):
            valid = False
            error_msg = "All fields (semester, subject, date, time) are required."
        else:
            # Flexible Date Parsing (try multiple formats)
            date_formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"]
            parsed_date = None

            for fmt in date_formats:
                try:
                    parsed_date = datetime.datetime.strptime(row_data["date"], fmt)
                    # Normalize to YYYY-MM-DD
                    row_data["date"] = parsed_date.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

            if not parsed_date:
                valid = False
                error_msg = "Invalid date. Use YYYY-MM-DD or DD-MM-YYYY."

            # Validate Time (HH:MM)
            if valid:
                try:
                    datetime.datetime.strptime(row_data["time"], "%H:%M")
                except ValueError:
                    valid = False
                    error_msg = "Invalid time format. Expected HH:MM."

        results.append({
            "row": row_data,
            "valid": valid,
            "error": error_msg
        })

    _logger.info(
        "Exam CSV uploaded by %s: %d rows parsed",
        getattr(current_user, "email", "unknown"),
        len(results),
    )

    return {
        "filename": file.filename,
        "status": "success",
        "data": results
    }


@router.post("/bulk-create-exams")
async def bulk_create_exams(
    data: ExamBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only)
):
    """Bulk-create exam timetable entries from validated data."""
    try:
        dept = current_user.department or "Unknown"
        from datetime import date
        today = date.today().isoformat()

        # Archive past exams for this department
        await db.execute(
            update(Timetable)
            .where(Timetable.department == dept, Timetable.status == "active", Timetable.exam_date < today)
            .values(status="archived")
        )

        exam_objects = []
        for entry in data.exams:
            try:
                datetime.datetime.strptime(entry.date, "%Y-%m-%d")
                datetime.datetime.strptime(entry.time, "%H:%M")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid format in data: {str(e)}")

            exam_objects.append({
                "department": dept,
                "semester": int(entry.semester),
                "subject_name": entry.subject,
                "exam_date": entry.date,
                "exam_time": entry.time,
                "created_by": current_user.id,
                "status": "active"
            })

        if not exam_objects:
            return {"message": "No valid records to insert", "inserted_count": 0}

        await db.execute(insert(Timetable), exam_objects)
        await db.commit()

        return {
            "status": "success",
            "message": f"Successfully inserted {len(exam_objects)} exam records.",
            "inserted_count": len(exam_objects)
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        _logger.error("Bulk exam creation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
