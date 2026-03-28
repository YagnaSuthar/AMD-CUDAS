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
    await db.commit()


async def mark_pipeline_ai_completed(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> None:
    from app.models import InterviewReport, JobApplication, ApplicationStatus
    import logging

    logger = logging.getLogger(__name__)
    logger.info("mark_pipeline_ai_completed: called for session_id=%s", session_id)

    result = await db.execute(
        select(InterviewPipeline).where(InterviewPipeline.ai_session_id == session_id)
    )
    pipeline = result.scalar_one_or_none()
    if pipeline is None:
        logger.warning("mark_pipeline_ai_completed: no pipeline found for session_id=%s", session_id)
        return

    logger.info("mark_pipeline_ai_completed: found pipeline id=%s, current status=%s", pipeline.id, pipeline.status)
    pipeline.status = PipelineStatus.AI_COMPLETED
    logger.info("mark_pipeline_ai_completed: updated pipeline id=%s to AI_COMPLETED", pipeline.id)

    # Get the AI score from the interview report
    report_result = await db.execute(
        select(InterviewReport).where(InterviewReport.session_id == session_id)
    )
    report = report_result.scalar_one_or_none()
    ai_score = report.final_score if report else None

    # Update the job application status and score
    app_result = await db.execute(
        select(JobApplication).where(
            JobApplication.job_id == pipeline.job_id,
            JobApplication.student_id == pipeline.student_id,
        )
    )
    application = app_result.scalar_one_or_none()
    if application:
        application.status = ApplicationStatus.AI_COMPLETED
        application.ai_score = int(ai_score) if ai_score else None

    await db.flush()
    await db.commit()
    logger.info("mark_pipeline_ai_completed: committed pipeline id=%s status=AI_COMPLETED", pipeline.id)
