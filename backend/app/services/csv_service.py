"""
CSV service — parse uploaded CSV, validate structure, bulk-create users,
generate random passwords, and return downloadable credential data.

Supports multi-encoding (UTF-8 / BOM / ISO-8859-1), per-row validation,
and structured error reporting.
"""

import csv
import io
import logging
import re
import secrets
import string
import uuid as uuid_pkg
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import hash_password
from app.models.auth import AuthUser, MentorAssignment
from app.services.email_service import send_credentials_email
from app.services.user_service import can_create_role, get_user_by_email

_logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────

MAX_CSV_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# Expected CSV columns per target role
EXPECTED_COLUMNS: dict[str, list[str]] = {
    "HOD": ["name", "email", "department"],
    "FACULTY": ["name", "email", "department"],
    "STUDENT": ["serial_number", "enrollment_number", "name", "email"],
    "RECRUITER": ["name", "email"],
}

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


# ── Data Classes ──────────────────────────────────────────────────────────


@dataclass
class RowError:
    """Describes a validation error for a single row."""
    row: int
    field: str
    message: str


@dataclass
class CSVValidationResult:
    """Result of CSV structure/content validation."""
    is_valid: bool
    message: str = ""
    rows: list[dict] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class CSVUploadResult:
    """Result of a full CSV upload + account creation."""
    success: bool
    message: str
    created_count: int = 0
    skipped_count: int = 0
    credentials: list[dict] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────


def generate_password(length: int = 12) -> str:
    """Generate a secure random password."""
    chars = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(chars) for _ in range(length))


def decode_csv_content(raw_bytes: bytes) -> str:
    """
    Decode raw CSV bytes trying UTF-8 (with BOM), then ISO-8859-1.
    Strips the BOM character if present.
    """
    # Try UTF-8 first (handles UTF-8-BOM too)
    try:
        text = raw_bytes.decode("utf-8-sig")  # strips BOM automatically
        return text
    except UnicodeDecodeError:
        pass

    # Fallback to ISO-8859-1 (never fails, but may mangle non-Latin chars)
    try:
        text = raw_bytes.decode("iso-8859-1")
        _logger.warning("CSV decoded with ISO-8859-1 fallback — non-Latin characters may be incorrect")
        return text
    except Exception:
        pass

    # Last resort: UTF-8 with replacement
    return raw_bytes.decode("utf-8", errors="replace")


def _validate_email(email: str) -> bool:
    """Check if a string looks like a valid email address."""
    return bool(_EMAIL_RE.match(email))


def get_csv_template(target_role: str) -> Optional[str]:
    """Return a CSV header string (+ example row) for the given target role."""
    cols = EXPECTED_COLUMNS.get(target_role)
    if not cols:
        return None

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=cols)
    writer.writeheader()

    # Add an example row so users know the expected format
    example: dict[str, str] = {"name": "John Doe", "email": "johndoe@example.com"}
    if "department" in cols:
        example["department"] = "Computer Science"
    if "serial_number" in cols:
        example["serial_number"] = "1"
    if "enrollment_number" in cols:
        example["enrollment_number"] = "CS2023001"
    writer.writerow(example)

    return output.getvalue()


# ── Validation ────────────────────────────────────────────────────────────


def validate_csv_structure(
    file_content: str,
    target_role: str,
) -> CSVValidationResult:
    """
    Validate CSV structure and per-row content against expected schema.
    Collects ALL errors instead of failing on the first one.
    Extra columns are silently ignored.
    """
    cols = EXPECTED_COLUMNS.get(target_role)
    if not cols:
        return CSVValidationResult(
            is_valid=False,
            message=f"No CSV template defined for role '{target_role}'",
        )

    reader = csv.DictReader(io.StringIO(file_content))

    if reader.fieldnames is None:
        return CSVValidationResult(
            is_valid=False,
            message="CSV file is empty or has no header row",
        )

    # Normalise headers
    headers = [h.strip().lower() for h in reader.fieldnames]
    missing = [c for c in cols if c not in headers]
    if missing:
        return CSVValidationResult(
            is_valid=False,
            message=f"Missing required columns: {', '.join(missing)}. Expected: {', '.join(cols)}",
        )

    # Detect extra columns (warning only)
    extra = [h for h in headers if h not in cols and h.strip()]
    warnings: list[str] = []
    if extra:
        warnings.append(f"Extra columns ignored: {', '.join(extra)}")

    # ── Per-row validation ────────────────────────────────────────────────
    rows: list[dict] = []
    errors: list[RowError] = []
    seen_emails: set[str] = set()

    for i, row in enumerate(reader, start=2):
        # Normalise keys and trim values
        cleaned = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items() if k}

        # Required fields: name + email
        if not cleaned.get("name"):
            errors.append(RowError(row=i, field="name", message="Name is required"))
        if not cleaned.get("email"):
            errors.append(RowError(row=i, field="email", message="Email is required"))
        elif not _validate_email(cleaned["email"]):
            errors.append(RowError(row=i, field="email", message=f"Invalid email format: '{cleaned['email']}'"))

        # Duplicate email within the same CSV
        email_lower = cleaned.get("email", "").lower()
        if email_lower and email_lower in seen_emails:
            errors.append(RowError(row=i, field="email", message=f"Duplicate email in CSV: '{cleaned['email']}'"))
        seen_emails.add(email_lower)

        # Role-specific validation
        if target_role == "STUDENT":
            if not cleaned.get("enrollment_number"):
                errors.append(RowError(row=i, field="enrollment_number", message="Enrollment number is required"))

        if target_role in ("HOD", "FACULTY"):
            if not cleaned.get("department"):
                errors.append(RowError(row=i, field="department", message="Department is required"))

        rows.append(cleaned)

    if not rows:
        return CSVValidationResult(
            is_valid=False,
            message="CSV has no data rows",
        )

    is_valid = len(errors) == 0
    message = "" if is_valid else f"Validation failed with {len(errors)} error(s)"

    return CSVValidationResult(
        is_valid=is_valid,
        message=message,
        rows=rows,
        errors=errors,
        warnings=warnings,
    )


# ── Processing ────────────────────────────────────────────────────────────


async def process_csv_upload(
    db: AsyncSession,
    raw_bytes: bytes,
    target_role: str,
    parent_user,
    base_url: str = "http://localhost:5173",
) -> CSVUploadResult:
    """
    Full CSV upload pipeline: decode → validate → create accounts → send emails.
    Returns structured result with credentials and any errors.
    """
    parent_role = parent_user.role if hasattr(parent_user, "role") else parent_user.get("role")
    parent_id = parent_user.id if hasattr(parent_user, "id") else parent_user.get("id")
    parent_dept = None
    if hasattr(parent_user, "department"):
        parent_dept = parent_user.department
    elif isinstance(parent_user, dict):
        parent_dept = parent_user.get("department")

    # ── Permission Check ──────────────────────────────────────────────────
    if not can_create_role(parent_role, target_role):
        return CSVUploadResult(
            success=False,
            message=f"Role '{parent_role}' cannot create '{target_role}' accounts",
        )

    # ── File Size Check ───────────────────────────────────────────────────
    if len(raw_bytes) > MAX_CSV_SIZE_BYTES:
        size_mb = round(len(raw_bytes) / (1024 * 1024), 2)
        return CSVUploadResult(
            success=False,
            message=f"File too large ({size_mb} MB). Maximum allowed is {MAX_CSV_SIZE_BYTES // (1024 * 1024)} MB",
        )

    # ── Decode ────────────────────────────────────────────────────────────
    file_content = decode_csv_content(raw_bytes)
    _logger.info("CSV decoded: %d characters, target_role=%s", len(file_content), target_role)

    # ── Validate ──────────────────────────────────────────────────────────
    validation = validate_csv_structure(file_content, target_role)
    if not validation.is_valid:
        return CSVUploadResult(
            success=False,
            message=validation.message,
            errors=validation.errors,
        )

    if validation.warnings:
        for w in validation.warnings:
            _logger.warning("CSV warning: %s", w)

    # ── Verify Mentor Assignment (STUDENT ONLY) ───────────────────────────
    student_semester = None
    if target_role == "STUDENT" and parent_role == "FACULTY":
        # Get assigned semester for this faculty
        q = await db.execute(select(MentorAssignment).where(MentorAssignment.faculty_id == parent_id))
        assignment = q.scalars().first()
        if not assignment:
            return CSVUploadResult(
                success=False,
                message="You must be assigned as a Mentor for a semester by the HOD before you can bulk upload students."
            )
        student_semester = assignment.semester

    # ── Create Accounts ───────────────────────────────────────────────────
    credentials: list[dict] = []
    created_count = 0
    skipped_count = 0

    for row in validation.rows:
        # Skip if email already exists in DB
        existing = await get_user_by_email(db, row["email"])
        if existing:
            skipped_count += 1
            _logger.info("Skipped existing email: %s", row["email"])
            continue

        # Skip if enrollment_number exists globally
        if target_role == "STUDENT" and row.get("enrollment_number"):
            exist_enroll = await db.execute(select(AuthUser).where(AuthUser.enrollment_number == row["enrollment_number"]))
            if exist_enroll.scalar_one_or_none():
                skipped_count += 1
                _logger.info("Skipped existing enrollment_number: %s", row["enrollment_number"])
                continue

        # Generate reset token for password-reset flow (consistent with add-user)
        reset_token = str(uuid_pkg.uuid4())
        expiry = datetime.now(timezone.utc) + timedelta(hours=24)

        # Determine department: use CSV value, or inherit from parent
        department = row.get("department") or parent_dept

        new_user = AuthUser(
            name=row["name"],
            email=row["email"],
            hashed_password=None,  # No password — user sets via reset link
            role=target_role,
            parent_id=parent_id,
            is_verified=True,  # Auto-verified when created by parent
            department=department,
            semester=student_semester if target_role == "STUDENT" else None,
            enrollment_number=row.get("enrollment_number") if target_role == "STUDENT" else None,
            must_reset_password=True,
            reset_token=reset_token,
            reset_token_expiry=expiry,
        )
        db.add(new_user)
        created_count += 1

        credentials.append({
            "name": row["name"],
            "email": row["email"],
            "role": target_role,
            "action": "Set password via email link",
        })

        # Send welcome email with password-reset link
        try:
            send_credentials_email(
                row["email"],
                row["name"],
                reset_token,
                target_role,
                base_url,
            )
        except Exception as e:
            _logger.error("Failed to send credentials email to %s: %s", row["email"], e)

    try:
        await db.flush()
        _logger.info(
            "CSV upload complete: %d created, %d skipped (already exist)",
            created_count,
            skipped_count,
        )
    except Exception as e:
        _logger.error("Database flush failed during CSV upload: %s", e)
        return CSVUploadResult(
            success=False,
            message=f"Database error while creating accounts: {str(e)}",
        )

    # Build result message
    parts = [f"Successfully created {created_count} {target_role} account(s)"]
    if skipped_count:
        parts.append(f"{skipped_count} skipped (email already exists)")
    message = ". ".join(parts) + "."

    return CSVUploadResult(
        success=True,
        message=message,
        created_count=created_count,
        skipped_count=skipped_count,
        credentials=credentials,
    )
