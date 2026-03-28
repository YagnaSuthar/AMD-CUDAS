"""
Verification Agent Service.
Orchestrates the full verification workflow: classify → pipeline → score → explain → store → notify.
"""

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
        project_description: str | None = None,
        tech_stack: str | None = None,
    ) -> VerificationResponse:
        print(f"\n{'='*60}")
        print(f"[Verification Agent Started]")
        print(f"  User: {user_id}")
        print(f"  File: {file.filename if file else 'None'}")
        print(f"  Link: {link}")
        print(f"  Profile Data: {bool(profile_data)}")
        print(f"{'='*60}")

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
        print(f"\n[Verification] Input Type: {input_type}")
        logger.info("[VERIFICATION] Input classified as: %s", input_type)

        # Run appropriate pipeline
        if input_type == "certificate":
            print("[Verification] Running certificate pipeline...")
            extracted, scores, issues, verified_fields, recommendations = await run_certificate_pipeline(
                db=self.db,
                user_id=user_id,
                file=file,
                profile_data=profile_data,
            )
        elif input_type == "project":
            print("[Verification] Running project pipeline...")
            extracted, scores, issues, verified_fields, recommendations = await run_project_pipeline(
                db=self.db,
                user_id=user_id,
                link=link,
                profile_data=profile_data,
                project_description=project_description,
                tech_stack=tech_stack,
            )
        else:  # profile
            print("[Verification] Running profile pipeline...")
            extracted, scores, issues, verified_fields, recommendations = await run_profile_pipeline(
                db=self.db,
                user_id=user_id,
                profile_data=profile_data,
            )

        print(f"\n[Verification] Pipeline completed")
        print(f"  Extracted fields: {list(extracted.keys())}")
        print(f"  Scores: {scores}")
        logger.info("[VERIFICATION] Pipeline completed - extracted fields: %s", list(extracted.keys()))

        # Compute final score and status
        scoring = compute_final_score(scores)
        confidence = float(scoring["confidence_score"])
        status = scoring["status"]
        trust_score = int(scoring["trust_score"])

        print(f"\n[Verification] ── Result ──")
        print(f"  Status: {status}")
        print(f"  Confidence Score: {confidence:.2f}")
        print(f"  Trust Score: {trust_score}")
        logger.info("[VERIFICATION] Final scoring - score=%.2f, status=%s", confidence, status)

        # Generate explanation
        print("[Verification] Generating explanation...")
        explanation = await generate_explanation(
            input_type=input_type,
            extracted_data=extracted,
            scores=scores,
            issues=issues,
            status=status,
            confidence_score=confidence,
        )

        # Build result payload
        result_payload = {
            "status": status,
            "confidence_score": confidence,
            "verified_fields": verified_fields,
            "issues": issues,
            "trust_score": trust_score,
            "recommendations": recommendations,
            "explanation": explanation,
        }

        # Store verification run
        run = VerificationRun(
            user_id=user_id,
            input_type=input_type,
            input_link=link,
            input_file_name=(file.filename if file else None),
            input_file_hash=extracted.get("file_hash"),
            extracted_data=extracted,
            scores=scores,
            result=result_payload,
            status=status,
            confidence_score=confidence,
        )
        self.db.add(run)
        await self.db.flush()
        run_id_str = str(run.id)
        print(f"[Verification] Run stored: {run_id_str}")
        logger.info("[VERIFICATION] Verification run stored with ID: %s", run_id_str)

        # Update Project record if it was a project verification
        if input_type == "project" and user_id and link:
            try:
                from app.models.project import Project
                res_proj = await self.db.execute(
                    select(Project)
                    .where(Project.student_id == user_id)
                    .where(Project.github_url == link)
                    .order_by(Project.created_at.desc())
                    .limit(1)
                )
                proj = res_proj.scalar_one_or_none()
                if proj:
                    proj.verification_status = status
                    proj.verification_run_id = run.id
                    await self.db.commit()
            except Exception as e:
                logger.error("Failed to update Project verification status: %s", e)

        # --- Send notification to student ---
        if user_id:
            try:
                from app.models.message import Notification, NotificationType

                student_feedback = extracted.get("student_feedback") or ""
                if not student_feedback:
                    score_str = f"Score: {int(confidence * 100)}%"
                    pieces: list[str] = []
                    if status == "verified":
                        pieces.append(f"AI Verification complete! ({score_str})")
                    elif status == "suspicious":
                        pieces.append(f"Flagged as suspicious. ({score_str})")
                    else:
                        pieces.append(f"Verification failed. ({score_str})")
                    
                    if issues:
                        pieces.append(f"Found issues: {'; '.join(issues[:2])}.")
                    if recommendations:
                        pieces.append(f"Tip: {recommendations[0]}")
                        
                    student_feedback = " ".join(pieces)

                notification = Notification(
                    user_id=user_id,
                    notification_type=NotificationType.AI_ASSIGNED,
                    title=f"{'Project' if input_type == 'project' else 'Certificate'} Verification",
                    message=student_feedback,
                    meta_json={
                        "run_id": run_id_str,
                        "input_type": input_type,
                        "score": confidence,
                        "status": status,
                        "trust_score": trust_score,
                        "issues": issues,
                        "recommendations": recommendations,
                    },
                )
                self.db.add(notification)
                await self.db.flush()
                print(f"[Verification] ✔ Notification sent to user {user_id}")
            except Exception as notif_err:
                print(f"[Verification] ⚠ Notification failed (non-fatal): {notif_err}")
                logger.warning("Notification creation failed: %s", notif_err)

        # --- RAG indexing (existing behavior) ---
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

        print(f"\n{'='*60}")
        print(f"[Verification Agent Complete]")
        print(f"  Run ID: {run_id_str}")
        print(f"  Status: {status} | Score: {confidence:.2f}")
        print(f"{'='*60}\n")

        return VerificationResponse(
            **result_payload,
            input_type=input_type,
            run_id=run_id_str,
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
