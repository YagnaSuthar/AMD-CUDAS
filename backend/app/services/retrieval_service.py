"""
Retrieval Service.

Performs semantic similarity search against pgvector embeddings
with optional user/agent/document-type filters.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.rag import Chunk, ChunkEmbedding, Document
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class RetrievalService:
    """Semantic search over stored embeddings."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._embedding_service = EmbeddingService()

    async def search(
        self,
        query: str,
        user_id: Optional[uuid.UUID] = None,
        agent_type: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> list[dict]:
        """
        Embed *query* and return the top-K most similar chunks.

        Parameters
        ----------
        query : str
            Natural-language search query.
        user_id : uuid, optional
            Filter results to a specific user's documents.
        agent_type : str, optional
            Filter by agent type (e.g. 'career_guidance').
        top_k : int, optional
            Number of results (defaults to settings.RAG_TOP_K).

        Returns
        -------
        list[dict]
            Each dict has 'content', 'chunk_index', 'document_id',
            'document_title', and 'score'.
        """
        k = top_k or settings.RAG_TOP_K
        query_vector = self._embedding_service.embed_text(query)

        # Build the query: join Embedding → Chunk → Document
        stmt = (
            select(
                Chunk.content,
                Chunk.chunk_index,
                Chunk.document_id,
                Document.title.label("document_title"),
                ChunkEmbedding.vector.cosine_distance(query_vector).label("distance"),
            )
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id)
            .join(Document, Document.id == Chunk.document_id)
        )

        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        if agent_type is not None:
            stmt = stmt.where(Document.agent_type == agent_type)

        stmt = stmt.order_by("distance").limit(k)

        result = await self.db.execute(stmt)
        rows = result.all()

        results = []
        for row in rows:
            results.append({
                "content": row.content,
                "chunk_index": row.chunk_index,
                "document_id": str(row.document_id),
                "document_title": row.document_title,
                "score": round(1.0 - float(row.distance), 4),  # cosine similarity
            })

        logger.info(
            "Retrieval: query='%s…' user=%s agent=%s → %d results",
            query[:50], user_id, agent_type, len(results),
        )
        return results
