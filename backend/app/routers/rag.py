"""
RAG & Agent API Router.

Provides endpoints for document upload, embedding generation,
career guidance queries, and roadmap generation.

All responses wrapped in { success: true/false, data/error } format.
"""

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.rag import (
    CareerGuidanceRequest,
    DocumentUploadRequest,
    EmbeddingGenerateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG & Agents"])


# ── Document Upload ───────────────────────────────────────────────────────────


@router.post("/upload-document")
async def upload_document(
    body: DocumentUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a document: chunk it, embed it, and store in pgvector."""
    from app.services.chunking_service import ChunkingService
    from app.services.embedding_service import EmbeddingService
    from app.services.vector_store_service import VectorStoreService

    user_id = current_user.id if not isinstance(current_user, dict) else None
    if user_id is None:
        return {"success": False, "error": "Admin cannot upload documents"}

    logger.info("Document upload started for user_id: %s, title: '%s'", user_id, body.title)

    try:
        # 1) Chunk the content
        chunker = ChunkingService()
        if body.content_type == "application/pdf":
            import base64
            pdf_bytes = base64.b64decode(body.content)
            raw_text = chunker.extract_text_from_pdf(pdf_bytes)
            logger.info("PDF text extracted: %d chars", len(raw_text))
        else:
            raw_text = body.content

        chunks = chunker.chunk_text(raw_text)
        logger.info("Created %d chunks from document", len(chunks))

        if not chunks:
            return {"success": False, "error": "No content could be extracted from the document"}

        # 2) Generate embeddings
        embedder = EmbeddingService()
        vectors = embedder.embed_batch(chunks)
        logger.info("Generated embeddings for %d chunks", len(vectors))

        # 3) Store everything
        store = VectorStoreService(db)
        doc_id = await store.store_document_with_embeddings(
            user_id=user_id,
            title=body.title,
            raw_content=raw_text,
            chunks=chunks,
            vectors=vectors,
            content_type=body.content_type,
            agent_type=body.agent_type,
        )
        logger.info("Stored embeddings in vector DB. Document ID: %s", doc_id)

        return {
            "success": True,
            "data": {
                "id": str(doc_id),
                "title": body.title,
                "content_type": body.content_type,
                "agent_type": body.agent_type,
                "chunk_count": len(chunks),
            }
        }

    except Exception as e:
        logger.error("Document upload failed: %s", e)
        return {"success": False, "error": str(e)}


# ── Generate Embeddings (for existing document) ──────────────────────────────


@router.post("/generate-embeddings")
async def generate_embeddings(
    body: EmbeddingGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """(Re-)generate embeddings for an existing document's chunks."""
    from sqlalchemy import select
    from app.models.rag import Chunk, ChunkEmbedding, Document
    from app.services.embedding_service import EmbeddingService

    try:
        doc_id = uuid.UUID(body.document_id)
        result = await db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return {"success": False, "error": "Document not found"}

        chunk_result = await db.execute(
            select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.chunk_index)
        )
        chunks = chunk_result.scalars().all()
        if not chunks:
            return {"success": False, "error": "No chunks found for document"}

        embedder = EmbeddingService()
        texts = [c.content for c in chunks]
        vectors = embedder.embed_batch(texts)
        logger.info("Generated embeddings for %d chunks of doc %s", len(vectors), doc_id)

        count = 0
        for chunk, vector in zip(chunks, vectors):
            existing = await db.execute(
                select(ChunkEmbedding).where(ChunkEmbedding.chunk_id == chunk.id)
            )
            emb = existing.scalar_one_or_none()
            if emb:
                emb.vector = vector
            else:
                db.add(ChunkEmbedding(
                    chunk_id=chunk.id,
                    vector=vector,
                    metadata_={"agent_type": doc.agent_type},
                ))
            count += 1

        await db.flush()
        logger.info("Stored embeddings in vector DB for %d chunks", count)

        return {
            "success": True,
            "data": {
                "document_id": str(doc_id),
                "chunks_embedded": count,
                "message": f"Successfully embedded {count} chunks",
            }
        }

    except Exception as e:
        logger.error("Embedding generation failed: %s", e)
        return {"success": False, "error": str(e)}


# ── Career Guidance Query ────────────────────────────────────────────────────


@router.post("/query-career-guidance")
async def query_career_guidance(
    body: CareerGuidanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Query the Career Guidance Agent with a career-related question."""
    from app.agents.career_guidance.agent import CareerGuidanceAgent

    user_id = current_user.id if not isinstance(current_user, dict) else None
    if user_id is None:
        return {"success": False, "error": "Admin cannot use career guidance"}

    logger.info("Career guidance query from user %s: '%s'", user_id, body.query[:80])

    try:
        agent = CareerGuidanceAgent(db)
        result = await agent.handle_query(user_id=user_id, query=body.query)
        logger.info("Career guidance response generated (intent=%s, rag=%s, sources=%s)",
                     result.get("intent"), result.get("used_rag"), result.get("data_sources"))

        # Persist career advisory query + response to DB
        try:
            from app.models.career_advisory import CareerAdvisoryLog
            log_entry = CareerAdvisoryLog(
                user_id=user_id,
                query=body.query,
                response=result.get("response", ""),
                intent=result.get("intent"),
                used_rag=result.get("used_rag", False),
            )
            db.add(log_entry)
            await db.flush()
            logger.info("Career advisory log saved: id=%s", log_entry.id)
        except Exception as log_err:
            logger.warning("Career advisory log save failed (non-fatal): %s", log_err)

        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error("Career guidance error: %s", e)
        return {"success": False, "error": f"Career guidance failed: {str(e)}"}


# ── Sync User Data to Vector DB ──────────────────────────────────────────────


@router.post("/sync-user-data")
async def sync_user_data(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Manually trigger embedding of user profile data into pgvector.
    This indexes resume, skills, certificates, projects, interviews, and academics.
    """
    user_id = current_user.id if not isinstance(current_user, dict) else None
    if user_id is None:
        return {"success": False, "error": "Admin cannot sync user data"}

    logger.info("Manual user data sync requested by user %s", user_id)

    try:
        from app.services.user_data_embedder import UserDataEmbedder

        embedder = UserDataEmbedder(db)
        summary = await embedder.ensure_user_data_indexed(
            user_id=user_id,
            force_reindex=True,
        )

        return {
            "success": True,
            "data": summary,
        }
    except Exception as e:
        logger.error("User data sync failed: %s", e)
        return {"success": False, "error": f"Sync failed: {str(e)}"}


# ── Roadmap Generation ───────────────────────────────────────────────────────


class GenerateRoadmapRequest(BaseModel):
    force_regenerate: bool = False


@router.get("/my-roadmap")
async def get_my_roadmap(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Load existing saved roadmap from DB (steps + weekly branch plans)."""
    from app.models.roadmap import RoadmapStep, RoadmapBranch, BranchStep

    user_id = current_user.id if not isinstance(current_user, dict) else None
    if user_id is None:
        return {"success": False, "error": "Admin cannot view roadmaps"}

    user = current_user
    goal_text = user.goal if hasattr(user, 'goal') and user.goal else None
    if not goal_text:
        return {"success": True, "data": None}

    # Load saved steps
    saved_res = await db.execute(
        select(RoadmapStep)
        .where(
            RoadmapStep.user_id == user_id,
            RoadmapStep.goal_title == goal_text,
        )
        .order_by(RoadmapStep.created_at.asc())
    )
    saved_steps = list(saved_res.scalars().all())

    if not saved_steps:
        return {"success": True, "data": None}

    # Build steps response with branch data
    steps_list = []
    phase_branches = {}

    for idx, s in enumerate(saved_steps, 1):
        step_data = {
            "id": str(s.id),
            "title": s.phase,
            "description": s.description or "",
            "skills": s.skills or [],
            "resources": [],
            "timeline": s.duration or "",
            "status": s.status or "pending",
        }
        steps_list.append(step_data)

        # Load branch (weekly plan) for this step
        branch_res = await db.execute(
            select(RoadmapBranch)
            .where(RoadmapBranch.parent_phase_id == s.id)
            .order_by(RoadmapBranch.created_at.desc())
            .limit(1)
        )
        branch = branch_res.scalar_one_or_none()

        if branch:
            # Load branch steps (weeks)
            bs_res = await db.execute(
                select(BranchStep)
                .where(BranchStep.branch_id == branch.id)
                .order_by(BranchStep.week.asc())
            )
            branch_steps = list(bs_res.scalars().all())

            if branch_steps:
                weeks = []
                for bs in branch_steps:
                    weeks.append({
                        "id": str(bs.id),
                        "week": bs.week,
                        "topics": bs.topics or [],
                        "tasks": bs.tasks or [],
                        "resources": bs.resources or [],
                        "deliverable": bs.deliverable or "",
                        "submission_required": bs.submission_required,
                        "submission_type": bs.submission_type or "none",
                        "status": bs.status or "pending",
                    })
                phase_branches[str(s.id)] = {
                    "steps": weeks,
                }

    return {
        "success": True,
        "data": {
            "goal": goal_text,
            "steps": steps_list,
            "phase_branches": phase_branches,
        }
    }


@router.post("/generate-roadmap")
async def generate_roadmap(
    req: GenerateRoadmapRequest = GenerateRoadmapRequest(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate a structured JSON career roadmap for the current user."""
    from app.agents.career_roadmap.agent import CareerRoadmapAgent
    from app.models.roadmap import RoadmapStep

    user_id = current_user.id if not isinstance(current_user, dict) else None
    if user_id is None:
        return {"success": False, "error": "Admin cannot generate roadmaps"}

    logger.info("=" * 50)
    logger.info("Roadmap generation requested by user: %s, force=%s", user_id, req.force_regenerate)
    logger.info("=" * 50)

    # If not forcing regeneration, check for existing data first
    if not req.force_regenerate:
        user = current_user
        goal_text = user.goal if hasattr(user, 'goal') and user.goal else None
        if goal_text:
            saved_res = await db.execute(
                select(RoadmapStep)
                .where(
                    RoadmapStep.user_id == user_id,
                    RoadmapStep.goal_title == goal_text,
                )
                .order_by(RoadmapStep.created_at.asc())
            )
            saved_steps = list(saved_res.scalars().all())

            if saved_steps:
                logger.info("Returning existing roadmap (%d steps) from DB", len(saved_steps))
                legacy_steps = []
                for s in saved_steps:
                    legacy_steps.append({
                        "id": str(s.id),
                        "title": s.phase,
                        "description": s.description or "",
                        "skills": s.skills or [],
                        "resources": [],
                        "timeline": s.duration or "",
                        "status": s.status or "pending",
                    })
                return {
                    "success": True,
                    "data": {
                        "goal": goal_text,
                        "steps": legacy_steps,
                    }
                }

    try:
        agent = CareerRoadmapAgent(db)
        roadmap = await agent.generate_roadmap(user_id=user_id)

        logger.info("Roadmap API response: success=True, title='%s', steps=%d",
                     roadmap.get("title", ""), len(roadmap.get("steps", [])))

        return {
            "success": True,
            "data": roadmap
        }
    except Exception as e:
        logger.error("Roadmap generation error: %s", e, exc_info=True)
        return {"success": False, "error": f"Roadmap generation failed: {str(e)}"}


class PhaseDetailedRequest(BaseModel):
    phase_id: str
    force_regenerate: bool = False


@router.post("/generate-phase-detailed-roadmap")
async def generate_phase_detailed_roadmap(
    req: PhaseDetailedRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate a weekly detailed breakdown for a specific roadmap phase."""
    from app.agents.career_roadmap.agent import CareerRoadmapAgent
    import uuid as _uuid

    user_id = current_user.id if not isinstance(current_user, dict) else None
    if user_id is None:
        return {"success": False, "error": "Admin cannot generate phase roadmaps"}

    try:
        phase_uuid = _uuid.UUID(req.phase_id)
    except (ValueError, AttributeError):
        return {"success": False, "error": f"Invalid phase_id: {req.phase_id}"}

    logger.info("Phase detailed roadmap requested: user=%s, phase=%s, force=%s",
                user_id, phase_uuid, req.force_regenerate)

    try:
        agent = CareerRoadmapAgent(db)
        result = await agent.generate_phase_detailed_roadmap(
            user_id=user_id,
            phase_id=phase_uuid,
            force_regenerate=req.force_regenerate,
        )

        # Map weekly_plan to the format the frontend expects (steps array)
        weekly_plan = result.get("weekly_plan", [])
        steps = []
        for w in weekly_plan:
            steps.append({
                "id": w.get("id", ""),
                "week": w.get("week", 0),
                "topics": w.get("topics", []),
                "tasks": w.get("tasks", []),
                "resources": w.get("resources", []),
                "deliverable": w.get("deliverable", ""),
                "submission_required": w.get("submission_required", False),
                "submission_type": w.get("submission_type", "none"),
                "submission_link": w.get("submission_link", ""),
                "status": w.get("status", "pending"),
            })

        return {
            "success": True,
            "data": {
                "branch_id": result.get("branch_id"),
                "parent_phase_id": result.get("parent_phase_id"),
                "phase": result.get("phase"),
                "steps": steps,
            }
        }
    except Exception as e:
        logger.error("Phase detailed roadmap error: %s", e, exc_info=True)
        return {"success": False, "error": f"Phase roadmap generation failed: {str(e)}"}


class MarkStepCompleteRequest(BaseModel):
    step_id: str


@router.post("/mark-step-complete")
async def mark_step_complete(
    req: MarkStepCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Mark a roadmap step as completed."""
    from app.models.roadmap import RoadmapStep
    from sqlalchemy import select
    import uuid as _uuid

    user_id = current_user.id if not isinstance(current_user, dict) else None
    if user_id is None:
        return {"success": False, "error": "Admin cannot mark steps complete"}

    try:
        step_uuid = _uuid.UUID(req.step_id)
    except (ValueError, AttributeError):
        return {"success": False, "error": f"Invalid step_id: {req.step_id}"}

    result = await db.execute(
        select(RoadmapStep).where(
            RoadmapStep.id == step_uuid,
            RoadmapStep.user_id == user_id,
        )
    )
    step = result.scalar_one_or_none()
    if step is None:
        return {"success": False, "error": "Step not found"}

    step.status = "completed"
    await db.commit()

    logger.info("Step %s marked as completed by user %s", step_uuid, user_id)
    return {"success": True, "data": {"step_id": str(step_uuid), "status": "completed"}}
