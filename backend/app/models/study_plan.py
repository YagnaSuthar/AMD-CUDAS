import uuid
from datetime import datetime, date

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generated_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")

    days: Mapped[list["StudyPlanDay"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class StudyPlanDay(Base):
    __tablename__ = "study_plan_days"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("study_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(nullable=False)
    tasks: Mapped[dict] = mapped_column(JSONB, nullable=False)

    plan: Mapped[StudyPlan] = relationship(back_populates="days")
