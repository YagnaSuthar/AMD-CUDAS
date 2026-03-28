"""
SQLAlchemy ORM models for the Career Roadmap System.
Tables: roadmap_steps, roadmap_branches, branch_steps.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RoadmapStep(Base):
    """A high-level phase/step in the user's career roadmap."""

    __tablename__ = "roadmap_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    goal_title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    phase: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skills = Column(JSON, default=list)
    duration: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    branches: Mapped[List["RoadmapBranch"]] = relationship(
        back_populates="parent_phase", cascade="all, delete-orphan"
    )


class RoadmapBranch(Base):
    """A detailed sub-branch of a roadmap phase (e.g. weekly breakdown)."""

    __tablename__ = "roadmap_branches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_phase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmap_steps.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="detailed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    parent_phase: Mapped["RoadmapStep"] = relationship(back_populates="branches")
    steps: Mapped[List["BranchStep"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )


class BranchStep(Base):
    """An individual step within a roadmap branch (weekly plan item)."""

    __tablename__ = "branch_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmap_branches.id", ondelete="CASCADE"),
        nullable=False,
    )
    week: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    topics = Column(JSON, default=list)
    tasks = Column(JSON, default=list)
    resources = Column(JSON, default=list)
    deliverable: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submission_required: Mapped[bool] = mapped_column(Boolean, default=False)
    submission_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default="none"
    )
    submission_link: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, default=""
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    branch: Mapped["RoadmapBranch"] = relationship(back_populates="steps")

