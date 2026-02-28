import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline import InterviewPipeline, PipelineStatus


async def attach_session_to_pipeline(
    db: AsyncSession,
    student_id: uuid.UUID,
    session_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(InterviewPipeline)
        .where(
            InterviewPipeline.student_id == student_id,
            InterviewPipeline.status == PipelineStatus.AI_ASSIGNED,
            InterviewPipeline.ai_session_id.is_(None),
        )
        .order_by(InterviewPipeline.created_at.desc())
    )
    pipeline = result.scalar_one_or_none()
    if pipeline is None:
        return

    pipeline.ai_session_id = session_id
    await db.flush()


async def mark_pipeline_ai_completed(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(InterviewPipeline).where(InterviewPipeline.ai_session_id == session_id)
    )
    pipeline = result.scalar_one_or_none()
    if pipeline is None:
        return

    pipeline.status = PipelineStatus.AI_COMPLETED
    await db.flush()
