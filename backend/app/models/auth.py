"""
Auth-system ORM models — separate from the AI agent User model.
Table: auth_users, colleges, companies
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

# ... (skipping some lines to replace the right section later, let's just do a clean replace)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────


class AuthUserRole(str, enum.Enum):
    CUDAS_ADMIN = "CUDAS_ADMIN"
    COLLEGE_PRINCIPAL = "COLLEGE_PRINCIPAL"
    HOD = "HOD"
    FACULTY = "FACULTY"
    STUDENT = "STUDENT"
    COMPANY_ADMIN = "COMPANY_ADMIN"
    RECRUITER = "RECRUITER"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class StudentPerformanceCategoryType(str, enum.Enum):
    TOP = "TOP"
    AVERAGE = "AVERAGE"
    WEAK = "WEAK"
    DROPOUT_RISK = "DROPOUT_RISK"


# ── AuthUser ──────────────────────────────────────────────────────────────


class AuthUser(Base):
    """Application user for the RBAC / hierarchy system."""

    __tablename__ = "auth_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    must_reset_password: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(
        SAEnum(AuthUserRole, name="auth_user_role_enum", create_constraint=True),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    verification_token_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reset_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reset_token_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Optional profile fields (populated via CSV or manual creation)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)
    roll_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    resume_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Self-referential relationship for hierarchy
    parent = relationship("AuthUser", remote_side="AuthUser.id", backref="children")


# ── College ───────────────────────────────────────────────────────────────


class College(Base):
    """A registered college, linked to its principal."""

    __tablename__ = "colleges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    principal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=ApprovalStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    principal = relationship("AuthUser", foreign_keys=[principal_id])


# ── Company ───────────────────────────────────────────────────────────────


class Company(Base):
    """A registered company, linked to its admin."""

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=ApprovalStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    admin = relationship("AuthUser", foreign_keys=[company_admin_id])


# ── Timetable ─────────────────────────────────────────────────────────────


class Timetable(Base):
    """Department exam timetable entry, managed by HOD."""

    __tablename__ = "timetables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_name: Mapped[str] = mapped_column(String(255), nullable=False)
    exam_date: Mapped[str] = mapped_column(String(50), nullable=False)
    exam_time: Mapped[str] = mapped_column(String(50), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    creator = relationship("AuthUser", foreign_keys=[created_by])


# ── InternalMarks ─────────────────────────────────────────────────────────


class InternalMarks(Base):
    """Internal marks uploaded by faculty, lockable by HOD."""

    __tablename__ = "internal_marks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_name: Mapped[str] = mapped_column(String(255), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    marks_obtained: Mapped[float] = mapped_column(nullable=False)
    max_marks: Mapped[float] = mapped_column(nullable=False, default=100.0)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    student = relationship("AuthUser", foreign_keys=[student_id])
    uploader = relationship("AuthUser", foreign_keys=[uploaded_by])


class StudentPerformanceCategory(Base):
    __tablename__ = "student_performance_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    computed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_name: Mapped[str] = mapped_column(String(255), nullable=False)
    average_percentage: Mapped[float] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(
        SAEnum(
            StudentPerformanceCategoryType,
            name="student_performance_category_type_enum",
            create_constraint=True,
        ),
        nullable=False,
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    student = relationship("AuthUser", foreign_keys=[student_id])
    computed_by_user = relationship("AuthUser", foreign_keys=[computed_by])


# ── Certificate ───────────────────────────────────────────────────────────


class Certificate(Base):
    """Student certificate/document, file stored in backend/certificate/."""

    __tablename__ = "certificates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    points: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    student = relationship("AuthUser", foreign_keys=[student_id])


# ── Department ────────────────────────────────────────────────────────────


class Department(Base):
    """Department names managed by the College Principal."""

    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    college_principal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    principal = relationship("AuthUser", foreign_keys=[college_principal_id])


# ── MentorAssignment ─────────────────────────────────────────────────────


class MentorAssignment(Base):
    """HOD assigns a faculty member as mentor for a semester."""

    __tablename__ = "mentor_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    faculty_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    faculty = relationship("AuthUser", foreign_keys=[faculty_id])
    assigner = relationship("AuthUser", foreign_keys=[assigned_by])
