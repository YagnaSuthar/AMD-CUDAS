"""
Pydantic schemas for RAG endpoints and agent responses.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Document & Embedding Schemas ──────────────────────────────────────────────


class DocumentUploadRequest(BaseModel):
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Raw text content or base64 PDF")
    content_type: str = Field("text/plain", description="MIME type")
    agent_type: Optional[str] = Field(None, description="Target agent (e.g. career_guidance)")


class DocumentResponse(BaseModel):
    id: str
    title: str
    content_type: str
    agent_type: Optional[str] = None
    chunk_count: int = 0
    created_at: Optional[str] = None


class EmbeddingGenerateRequest(BaseModel):
    document_id: str = Field(..., description="Document UUID to generate embeddings for")


class EmbeddingResponse(BaseModel):
    document_id: str
    chunks_embedded: int
    message: str


# ── Career Guidance Schemas ───────────────────────────────────────────────────


class CareerGuidanceRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Career guidance question")


class CareerGuidanceResponse(BaseModel):
    response: str
    intent: str
    used_rag: bool


# ── Career Roadmap Schemas ────────────────────────────────────────────────────


class RoadmapStepSchema(BaseModel):
    title: str
    description: str
    skills: list[str] = []
    resources: list[str] = []
    timeline: str = ""


class RoadmapResponse(BaseModel):
    title: str
    summary: str = ""
    steps: list[RoadmapStepSchema]


# ── Generic Agent Query ──────────────────────────────────────────────────────


class AgentQueryRequest(BaseModel):
    agent_type: str = Field(..., description="Agent to query (career_guidance, career_roadmap)")
    query: str = Field(..., description="User query")
    options: Optional[dict[str, Any]] = Field(None, description="Extra options")


class AgentQueryResponse(BaseModel):
    agent_type: str
    response: Any
    metadata: Optional[dict[str, Any]] = None
