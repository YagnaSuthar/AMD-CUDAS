"""
RAG & Agent API Router.

Provides endpoints for document upload, embedding generation,
career guidance queries, and roadmap generation.

All responses wrapped in { success: true/false, data/error } format.
"""

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
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
        logger.info("Career guidance response generated (intent=%s, rag=%s)",
                     result.get("intent"), result.get("used_rag"))
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error("Career guidance error: %s", e)
        return {"success": False, "error": f"Career guidance failed: {str(e)}"}


# ── Roadmap Generation ───────────────────────────────────────────────────────


@router.post("/generate-roadmap")
async def generate_roadmap(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate a structured JSON career roadmap for the current user."""
    from app.agents.career_roadmap.agent import CareerRoadmapAgent

    user_id = current_user.id if not isinstance(current_user, dict) else None
    if user_id is None:
        return {"success": False, "error": "Admin cannot generate roadmaps"}

    logger.info("=" * 50)
    logger.info("Roadmap generation requested by user: %s", user_id)
    logger.info("=" * 50)

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
