"""
RAG Context Service for Interview Agent.

Retrieves relevant CV/document chunks from pgvector for use
during question generation and follow-up intelligence.
Reuses the existing RetrievalService and EmbeddingService.
"""

import logging
import uuid
from typing import List, Optional

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval_service import RetrievalService
from app.agents.Interview.utils import InterviewTracer

logger = logging.getLogger(__name__)


def clean_chunks(chunks):
    cleaned = []

    for c in chunks:
        text = (c or "").strip()

        if not text:
            continue

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        # remove broken OCR-like text
        if len(text) < 60:
            continue

        # remove useless metadata
        if any(x in text.lower() for x in [
            "linkedin", "student name", "department",
            "semester", "career goal"
        ]):
            continue

        # remove contact info / headers / footers
        if re.search(r"\b(email|e-mail|phone|mobile|address|github)\b", text, re.IGNORECASE):
            continue
        if re.search(r"\b\+?\d[\d\s().-]{7,}\b", text):
            continue
        if re.search(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", text, re.IGNORECASE):
            continue

        # remove common section headings when they are mostly standalone
        if re.fullmatch(r"(projects?|experience|education|skills?|summary|objective)\s*:?", text.strip(), re.IGNORECASE):
            continue

        # remove spaced text (OCR issue)
        if " " in text and all(len(word) == 1 for word in text.split()[:10]):
            continue

        # Prefer chunks that look like project/skill descriptions
        projecty = any(k in text.lower() for k in [
            "built", "developed", "implemented", "designed", "deployed",
            "project", "api", "frontend", "backend", "database", "pipeline",
            "react", "flask", "django", "fastapi", "node", "postgres", "mysql",
            "mongodb", "redis", "docker", "kubernetes", "aws", "azure", "gcp",
            "cuda", "ml", "model", "inference", "training",
        ])

        if not projecty:
            continue

        cleaned.append(text)

    # De-duplicate while preserving order
    seen = set()
    uniq = []
    for t in cleaned:
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(t)

    return uniq[:3]


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
        InterviewTracer.log_rag(query, top_k, [])
        return ""

    InterviewTracer.log_rag(query, top_k, results)

    raw_chunks = [r.get("content", "") for r in results if r.get("score", 0) > 0.2]
    rag_chunks = clean_chunks(raw_chunks)
    context = "\n\n".join(rag_chunks)

    logger.info(
        "RAG: Retrieved %d relevant chunks for student %s (query='%s...')",
        len(rag_chunks), student_id, query[:50],
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
        InterviewTracer.log_rag(f"Followup: {answer_text[:50]}", top_k, [])
        return ""

    InterviewTracer.log_rag(f"Followup: {answer_text[:50]}", top_k, results)

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
