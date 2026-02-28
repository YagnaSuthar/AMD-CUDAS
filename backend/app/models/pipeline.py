import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PipelineStatus(str, enum.Enum):
    AI_ASSIGNED = "AI_ASSIGNED"
    AI_COMPLETED = "AI_COMPLETED"
    ROUND2_INVITED = "ROUND2_INVITED"
    ROUND2_COMPLETED = "ROUND2_COMPLETED"
    HIRED = "HIRED"


class InterviewPipeline(Base):
    __tablename__ = "interview_pipelines"
    __table_args__ = (
        UniqueConstraint("job_id", "student_id", name="uq_pipeline_job_student"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )

    ai_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.session_id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        SAEnum(PipelineStatus, name="pipeline_status_enum", create_constraint=True),
        nullable=False,
        default=PipelineStatus.AI_ASSIGNED,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    round2_link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    hired_company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
