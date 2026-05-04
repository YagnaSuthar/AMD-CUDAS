import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(
        UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    project_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    github_url = Column(String(512), nullable=False)
    tech_stack = Column(String(512), nullable=True)

    verification_status = Column(String(50), default="pending")  # pending, verified, suspicious, failed
    verification_run_id = Column(
        UUID(as_uuid=True), ForeignKey("verification_runs.id", ondelete="SET NULL"), nullable=True
    )
    project_structure = Column(JSONB, nullable=True)  # Full recursive repo tree from GitHub

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    student = relationship("AuthUser", backref="project_records")
    verification_run = relationship("VerificationRun", foreign_keys=[verification_run_id])
