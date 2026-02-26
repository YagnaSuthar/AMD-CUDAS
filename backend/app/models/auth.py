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
from sqlalchemy.dialects.postgresql import UUID
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
