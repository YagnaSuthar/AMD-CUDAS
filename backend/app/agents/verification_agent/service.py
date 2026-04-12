import asyncio
import logging
import uuid
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verification import VerificationFeedback, VerificationRun
from app.schemas.verification import VerificationResponse

logger = logging.getLogger(__name__)


class VerificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_verification(
        self,
        *,
        user_id: uuid.UUID | None,
        file: UploadFile | None,
        link: str | None,
        profile_data: dict[str, Any] | None,
    ) -> VerificationResponse:
        logger.info("[VERIFICATION] Starting verification run - user_id=%s", user_id)
        
        from app.agents.verification_agent.utils.input_classifier import classify_input
        from app.agents.verification_agent.pipelines.certificate_pipeline import run_certificate_pipeline
        from app.agents.verification_agent.pipelines.project_pipeline import run_project_pipeline
        from app.agents.verification_agent.pipelines.profile_pipeline import run_profile_pipeline
        from app.agents.verification_agent.scorers.weighted_scorer import compute_final_score
        from app.agents.verification_agent.utils.explanation import generate_explanation

        if file is None and not link and not profile_data:
            raise HTTPException(status_code=400, detail="Provide at least one of: file, link, profile_data")

        input_type = await classify_input(file=file, link=link, profile_data=profile_data)
        logger.info("[VERIFICATION] Input classified as: %s", input_type)

        # Run appropriate pipeline
        if input_type == "certificate":
            logger.info("[VERIFICATION] Running certificate pipeline")
            extracted, scores, issues, verified_fields, recommendations = await run_certificate_pipeline(
                db=self.db,
                user_id=user_id,
                file=file,
                profile_data=profile_data,
            )
        elif input_type == "project":
            logger.info("[VERIFICATION] Running project pipeline")
            extracted, scores, issues, verified_fields, recommendations = await run_project_pipeline(
                db=self.db,
                user_id=user_id,
                link=link,
                profile_data=profile_data,
            )
        else:  # profile
            logger.info("[VERIFICATION] Running profile pipeline")
            extracted, scores, issues, verified_fields, recommendations = await run_profile_pipeline(
                db=self.db,
                user_id=user_id,
                profile_data=profile_data,
            )

        logger.info("[VERIFICATION] Pipeline completed - extracted fields: %s", list(extracted.keys()))
        logger.debug("[VERIFICATION] Scores: %s", scores)
        logger.debug("[VERIFICATION] Issues: %s", issues)
        logger.debug("[VERIFICATION] Verified fields: %s", verified_fields)
        logger.debug("[VERIFICATION] Recommendations: %s", recommendations)

        # Compute final score and status
        scoring = compute_final_score(scores)
        confidence = float(scoring["confidence_score"])
        status = scoring["status"]
        logger.info("[VERIFICATION] Final scoring - score=%.2f, status=%s", confidence, status)

        # Generate explanation
        logger.info("[VERIFICATION] Generating explanation")
        explanation = await generate_explanation(
            input_type=input_type,
            extracted_data=extracted,
            scores=scores,
            issues=issues,
            status=status,
            confidence_score=confidence,
        )
        logger.info("[VERIFICATION] Explanation generated")

        # Store verification run
        run = VerificationRun(
            user_id=user_id,
            input_type=input_type,
            input_link=link,
            input_file_name=(file.filename if file else None),
            input_file_hash=extracted.get("file_hash"),
            extracted_data=extracted,
            scores=scores,
            result={
                "status": status,
                "confidence_score": confidence,
                "verified_fields": verified_fields,
                "issues": issues,
                "trust_score": int(scoring["trust_score"]),
                "recommendations": recommendations,
                "explanation": explanation,
            },
            status=status,
            confidence_score=confidence,
        )
        self.db.add(run)
        await self.db.flush()
        run_id_str = str(run.id)
        logger.info("[VERIFICATION] Verification run stored with ID: %s", run_id_str)

        try:
            from app.services.chunking_service import ChunkingService
            from app.services.embedding_service import EmbeddingService
            from app.services.vector_store_service import VectorStoreService

            raw = {
                "input_type": input_type,
                "link": link,
                "extracted": extracted,
                "scores": scores,
                "status": status,
                "confidence": confidence,
                "issues": issues,
            }
            raw_text = str(raw)

            chunker = ChunkingService()
            chunks = chunker.chunk_text(raw_text)
            if chunks and user_id is not None:
                embedder = EmbeddingService()
                vectors = embedder.embed_batch(chunks)
                store = VectorStoreService(self.db)
                await store.store_document_with_embeddings(
                    user_id=user_id,
                    title=f"VerificationRun {run.id}",
                    raw_content=raw_text,
                    chunks=chunks,
                    vectors=vectors,
                    content_type="text/plain",
                    agent_type="verification_agent",
                )
        except Exception as e:
            logger.warning("Verification vector indexing failed (non-fatal): %s", e)

        return VerificationResponse(
            **result_payload,
            input_type=input_type,
            run_id=str(run.id),
        )

    async def store_feedback(
        self,
        *,
        run_id: uuid.UUID,
        user_id: uuid.UUID | None,
        is_correct: bool,
        notes: str | None,
    ) -> None:
        res = await self.db.execute(select(VerificationRun).where(VerificationRun.id == run_id))
        run = res.scalar_one_or_none()
        if run is None:
            raise HTTPException(status_code=404, detail="Verification run not found")

        fb = VerificationFeedback(run_id=run_id, is_correct=is_correct, notes=notes)
        self.db.add(fb)
        await self.db.flush()

        logger.info("Verification feedback stored: run=%s correct=%s user=%s", run_id, is_correct, user_id)
