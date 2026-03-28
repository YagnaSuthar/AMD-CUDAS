import json
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.verification_agent.controller import VerificationController
from app.core.security import get_current_user
from app.db.base import get_db
from app.schemas.verification import VerificationResponse, VerificationFeedbackRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Verification"])


@router.post("/verify", response_model=VerificationResponse)
async def verify(
    file: UploadFile | None = File(None),
    link: str | None = Form(None),
    profile_data: str | None = Form(None),
    project_description: str | None = Form(None),
    tech_stack: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    logger.info("[VERIFICATION] /verify endpoint called - user=%s, file=%s, link=%s", 
                current_user.id, file.filename if file else None, link)
    
    # Parse profile_data JSON string if provided
    parsed_profile = None
    if profile_data:
        try:
            parsed_profile = json.loads(profile_data)
        except Exception as e:
            logger.error("[VERIFICATION] Failed to parse profile_data JSON: %s", e)
            raise HTTPException(status_code=400, detail="Invalid profile_data JSON")

    controller = VerificationController(db=db)

    user_id = current_user.id if hasattr(current_user, "id") else None

    result = await controller.verify(
        user_id=user_id,
        file=file,
        link=link,
        profile_data=parsed_profile,
        project_description=project_description,
        tech_stack=tech_stack,
    )
    logger.info("[VERIFICATION] /verify endpoint completed - run_id=%s, score=%.2f, status=%s", 
                result.run_id, result.confidence_score, result.status)
    return result


@router.post("/verify/{run_id}/feedback")
async def submit_verification_feedback(
    run_id: str,
    body: VerificationFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    logger.info("[VERIFICATION] /verify/%s/feedback endpoint called - user=%s", run_id, current_user.id)
    
    controller = VerificationController(db=db)

    try:
        run_uuid = uuid.UUID(run_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run_id")

    user_id = current_user.id if hasattr(current_user, "id") else None

    await controller.submit_feedback(
        run_id=run_uuid,
        user_id=user_id,
        is_correct=body.is_correct,
        notes=body.notes,
    )

    return {"success": True}
