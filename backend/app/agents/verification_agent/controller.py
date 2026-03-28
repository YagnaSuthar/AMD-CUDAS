"""
Verification Agent Controller.
Entry point for verification operations, delegates to VerificationService.
"""

import logging
import uuid
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.verification_agent.service import VerificationService
from app.schemas.verification import VerificationResponse

logger = logging.getLogger(__name__)


class VerificationController:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = VerificationService(db=self.db)

    async def verify(
        self,
        *,
        user_id: uuid.UUID | None,
        file: UploadFile | None,
        link: str | None,
        profile_data: dict[str, Any] | None,
        project_description: str | None = None,
        tech_stack: str | None = None,
    ) -> VerificationResponse:
        logger.info("[VERIFICATION] Controller.verify called - user_id=%s", user_id)
        try:
            return await self.service.run_verification(
                user_id=user_id,
                file=file,
                link=link,
                profile_data=profile_data,
                project_description=project_description,
                tech_stack=tech_stack,
            )
        except Exception as e:
            logger.error("[VERIFICATION] Controller.verify failed: %s", e, exc_info=True)
            raise

    async def submit_feedback(
        self,
        *,
        run_id: uuid.UUID,
        user_id: uuid.UUID | None,
        is_correct: bool,
        notes: str | None,
    ) -> None:
        logger.info("[VERIFICATION] Controller.submit_feedback called - run_id=%s", run_id)
        try:
            await self.service.store_feedback(
                run_id=run_id,
                user_id=user_id,
                is_correct=is_correct,
                notes=notes,
            )
        except Exception as e:
            logger.error("[VERIFICATION] Controller.submit_feedback failed: %s", e, exc_info=True)
            raise
