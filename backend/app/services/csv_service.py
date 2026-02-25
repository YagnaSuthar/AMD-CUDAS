"""
CSV service — parse uploaded CSV, validate structure, bulk-create users,
generate random passwords, and return downloadable credential data.
"""

import csv
import io
import secrets
import string
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.auth import AuthUser
from app.services.email_service import send_credentials_email
from app.services.user_service import can_create_role, get_user_by_email


# Expected CSV columns per target role
EXPECTED_COLUMNS = {
    "HOD": ["name", "email", "department"],
    "FACULTY": ["name", "email", "department"],
    "STUDENT": ["name", "email", "semester", "roll_number"],
    "RECRUITER": ["name", "email"],
}


def generate_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(chars) for _ in range(length))


def get_csv_template(target_role: str) -> Optional[str]:
    """Return a CSV header string for the given target role."""
    cols = EXPECTED_COLUMNS.get(target_role)
    if not cols:
        return None
    return ",".join(cols) + "\n"


def validate_csv_structure(file_content: str, target_role: str) -> tuple[bool, str, list[dict]]:
    """
    Validate CSV structure against expected columns.
    Returns (is_valid, error_message, parsed_rows).
    """
    cols = EXPECTED_COLUMNS.get(target_role)
    if not cols:
        return False, f"No CSV template defined for role {target_role}", []

    reader = csv.DictReader(io.StringIO(file_content))
    if reader.fieldnames is None:
        return False, "CSV file is empty or has no header", []

    # normalise header
    headers = [h.strip().lower() for h in reader.fieldnames]
    missing = [c for c in cols if c not in headers]
    if missing:
        return False, f"Missing columns: {', '.join(missing)}", []

    rows = []
    for i, row in enumerate(reader, start=2):
        cleaned = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        if not cleaned.get("name") or not cleaned.get("email"):
            return False, f"Row {i}: name and email are required", []
        rows.append(cleaned)

    if not rows:
        return False, "CSV has no data rows", []

    return True, "", rows


async def process_csv_upload(
    db: AsyncSession,
    file_content: str,
    target_role: str,
    parent_user,
    base_url: str = "http://localhost:5173",
) -> tuple[bool, str, list[dict]]:
    """
    Process a CSV upload: validate, create accounts, send emails.
    Returns (success, message, credentials_list).
    """
    parent_role = parent_user.role if hasattr(parent_user, "role") else parent_user.get("role")
    parent_id = parent_user.id if hasattr(parent_user, "id") else parent_user.get("id")

    if not can_create_role(parent_role, target_role):
        return False, f"Role {parent_role} cannot create {target_role} accounts", []

    is_valid, error, rows = validate_csv_structure(file_content, target_role)
    if not is_valid:
        return False, error, []

    credentials = []
    created_count = 0

    for row in rows:
        # Skip if email already exists
        existing = await get_user_by_email(db, row["email"])
        if existing:
            continue

        password = generate_password()
        new_user = AuthUser(
            name=row["name"],
            email=row["email"],
            hashed_password=hash_password(password),
            role=target_role,
            parent_id=parent_id,
            is_verified=True,  # auto-verified when created by parent
            department=row.get("department"),
            semester=int(row["semester"]) if row.get("semester") else None,
            roll_number=row.get("roll_number"),
        )
        db.add(new_user)
        created_count += 1

        credentials.append({
            "name": row["name"],
            "email": row["email"],
            "password": password,
        })

        # Send credentials email
        send_credentials_email(row["email"], row["name"], password, target_role)

    await db.flush()

    return True, f"Successfully created {created_count} {target_role} accounts", credentials
