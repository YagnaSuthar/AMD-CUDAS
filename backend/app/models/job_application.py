import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ApplicationStatus(str, enum.Enum):
    PENDING = "PENDING"
    AI_ASSIGNED = "AI_ASSIGNED"
    AI_COMPLETED = "AI_COMPLETED"
    ROUND2_INVITED = "ROUND2_INVITED"
    HIRED = "HIRED"
    REJECTED = "REJECTED"


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (
        UniqueConstraint("job_id", "student_id", name="uq_application_job_student"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Status tracks the application through the pipeline
    status: Mapped[str] = mapped_column(
        SAEnum(ApplicationStatus, name="application_status_enum", create_constraint=True),
        nullable=False,
        default=ApplicationStatus.PENDING,
    )

    # AI interview score (denormalized for quick access)
    ai_score: Mapped[int | None] = mapped_column(nullable=True)

    # Cover letter or notes from student
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
