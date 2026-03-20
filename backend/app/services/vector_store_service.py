"""
Vector Store Service.

Handles CRUD operations for pgvector-backed embeddings, including
batch insertion and deletion by document.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag import Chunk, ChunkEmbedding, Document

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Manage pgvector embeddings in the database."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def store_document_with_embeddings(
        self,
        user_id: uuid.UUID,
        title: str,
        raw_content: str,
        chunks: list[str],
        vectors: list[list[float]],
        content_type: str = "text/plain",
        agent_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> uuid.UUID:
        """
        Store a complete document: raw content, chunks, and their embeddings.

        Returns the document ID.
        """
        doc = Document(
            user_id=user_id,
            title=title,
            raw_content=raw_content,
            content_type=content_type,
            agent_type=agent_type,
        )
        self.db.add(doc)
        await self.db.flush()  # populate doc.id

        for idx, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            chunk = Chunk(
                document_id=doc.id,
                content=chunk_text,
                chunk_index=idx,
            )
            self.db.add(chunk)
            await self.db.flush()

            emb = ChunkEmbedding(
                chunk_id=chunk.id,
                vector=vector,
                metadata_=metadata or {"agent_type": agent_type},
            )
            self.db.add(emb)

        await self.db.flush()
        logger.info(
            "Stored document '%s' (%s) with %d chunks for user %s",
            title, doc.id, len(chunks), user_id,
        )
        return doc.id

    async def delete_by_document(self, document_id: uuid.UUID) -> None:
        """Delete a document and all its chunks/embeddings (cascade)."""
        await self.db.execute(
            delete(Document).where(Document.id == document_id)
        )
        await self.db.flush()
        logger.info("Deleted document %s and related chunks/embeddings", document_id)

    async def get_documents_for_user(self, user_id: uuid.UUID) -> list[Document]:
        """List all documents belonging to a user."""
        result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())
