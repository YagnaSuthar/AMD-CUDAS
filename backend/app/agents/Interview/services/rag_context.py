"""
RAG Context Service for Interview Agent.

Retrieves relevant CV/document chunks from pgvector for use
during question generation and follow-up intelligence.
Reuses the existing RetrievalService and EmbeddingService.
"""

import logging
import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


async def get_interview_context(
    student_id: uuid.UUID,
    query: str,
    db: AsyncSession,
    top_k: int = 5,
) -> str:
    """
    Retrieve top-k relevant CV/document chunks for a student
    based on a query (e.g., skill name, topic, job role).

    Returns a formatted context string — NOT the full CV.
    """
    retrieval = RetrievalService(db)
    results = await retrieval.search(
        query=query,
        user_id=student_id,
        top_k=top_k,
    )

    if not results:
        logger.info("RAG: No relevant chunks found for student %s, query='%s'", student_id, query[:50])
        return ""

    # Format the chunks for LLM consumption
    context_parts: List[str] = []
    for i, r in enumerate(results, 1):
        score = r.get("score", 0)
        content = r.get("content", "").strip()
        if content and score > 0.2:  # Only include reasonably relevant chunks
            context_parts.append(f"[Chunk {i}] (relevance: {score:.2f})\n{content}")

    context = "\n\n".join(context_parts)
    logger.info(
        "RAG: Retrieved %d relevant chunks for student %s (query='%s...')",
        len(context_parts), student_id, query[:50],
    )
    return context


async def get_followup_context(
    student_id: uuid.UUID,
    answer_text: str,
    db: AsyncSession,
    top_k: int = 3,
) -> str:
    """
    After a candidate answers, retrieve related concepts from their
    CV/documents for intelligent follow-up questions.

    Example: If candidate says 'I used React hooks', retrieve chunks
    about useEffect, useState, lifecycle, React projects, etc.
    """
    if not answer_text or len(answer_text.strip()) < 10:
        return ""

    retrieval = RetrievalService(db)
    results = await retrieval.search(
        query=answer_text,
        user_id=student_id,
        top_k=top_k,
    )

    if not results:
        return ""

    # Format for follow-up intelligence
    parts: List[str] = []
    for r in results:
        score = r.get("score", 0)
        content = r.get("content", "").strip()
        if content and score > 0.15:
            parts.append(content)

    context = "\n---\n".join(parts)
    logger.info(
        "RAG follow-up: Retrieved %d related chunks for student %s",
        len(parts), student_id,
    )
    return context


async def get_cv_sections(
    student_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """
    Retrieve categorized CV sections (skills, projects, experience, education)
    from the student's stored documents via semantic search.

    Returns a dict with section keys and their content.
    """
    sections = {}
    queries = {
        "skills": "technical skills programming languages frameworks tools",
        "projects": "projects built developed implemented created",
        "experience": "work experience internship job role responsibilities",
        "education": "education degree university college academic",
    }

    retrieval = RetrievalService(db)
    for section_name, query in queries.items():
        results = await retrieval.search(
            query=query,
            user_id=student_id,
            top_k=2,
        )
        if results:
            content = "\n".join(r["content"] for r in results if r.get("score", 0) > 0.15)
            if content.strip():
                sections[section_name] = content.strip()

    logger.info(
        "RAG CV sections: Found %d sections for student %s: %s",
        len(sections), student_id, list(sections.keys()),
    )
    return sections
