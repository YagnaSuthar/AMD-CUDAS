"""
RAG-related ORM models: Document, Chunk, Embedding.

These support the full RAG pipeline by storing chunked document content
and their pgvector embeddings for semantic retrieval.
"""

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.config import settings
from app.core.database import Base


class Document(Base):
    """A user-uploaded document (resume, notes, PDF, etc.)."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    content_type = Column(String(100), nullable=False, default="text/plain")
    agent_type = Column(String(100), nullable=True, index=True)
    raw_content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """A text chunk extracted from a Document."""

    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)

    document = relationship("Document", back_populates="chunks")
    embedding = relationship("ChunkEmbedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan")


class ChunkEmbedding(Base):
    """A pgvector embedding for a single Chunk."""

    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, unique=True)
    vector = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)

    chunk = relationship("Chunk", back_populates="embedding")

    __table_args__ = (
        Index(
            "ix_embeddings_vector_cosine",
            vector,
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"vector": "vector_cosine_ops"},
        ),
    )
