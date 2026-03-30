"""
User Data Embedder Service.

Automatically collects user profile data (resume, skills, certificates,
projects, interview results, academic marks) and embeds them into pgvector
for RAG-based career guidance retrieval.

Reuses existing: ChunkingService, EmbeddingService, VectorStoreService.
"""

import logging
import os
import uuid
from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import AuthUser, Certificate, InternalMarks
from app.models.rag import Document
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)

# Document title patterns for deduplication
_TITLE_PREFIX = "UserProfile"


def _doc_title(category: str, user_id: uuid.UUID) -> str:
    return f"{_TITLE_PREFIX}::{category}::{user_id}"


class UserDataEmbedder:
    """
    Collects user data from PostgreSQL and embeds it into pgvector
    so the RAG pipeline can retrieve personalized context.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._chunker = ChunkingService()
        self._embedder = EmbeddingService()
        self._store = VectorStoreService(db)

    async def ensure_user_data_indexed(
        self,
        user_id: uuid.UUID,
        force_reindex: bool = False,
    ) -> dict[str, Any]:
        """
        Ensure all user data categories are embedded in pgvector.

        If data already exists and force_reindex is False, skips that category.
        Returns a summary of what was indexed.

        Parameters
        ----------
        user_id : uuid.UUID
            The user to index data for.
        force_reindex : bool
            If True, delete existing embeddings and re-index everything.
        """
        summary: dict[str, Any] = {
            "user_id": str(user_id),
            "indexed": [],
            "skipped": [],
            "errors": [],
        }

        # Fetch the user
        result = await self.db.execute(
            select(AuthUser).where(AuthUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            summary["errors"].append("User not found")
            return summary

        # Define all data sources to index
        data_sources = [
            ("Skills", self._build_skills_text, user),
            ("Certificates", self._build_certificates_text, user_id),
            ("Projects", self._build_projects_text, user_id),
            ("Academics", self._build_academics_text, user_id),
            ("Interviews", self._build_interviews_text, user_id),
            ("Resume", self._build_resume_text, user),
        ]

        for category, builder, arg in data_sources:
            doc_title = _doc_title(category, user_id)
            try:
                # Check if already indexed
                if not force_reindex:
                    existing = await self.db.execute(
                        select(Document).where(
                            Document.user_id == user_id,
                            Document.title == doc_title,
                        )
                    )
                    if existing.scalar_one_or_none() is not None:
                        summary["skipped"].append(category)
                        continue

                # Delete existing if re-indexing
                if force_reindex:
                    existing = await self.db.execute(
                        select(Document).where(
                            Document.user_id == user_id,
                            Document.title == doc_title,
                        )
                    )
                    old_doc = existing.scalar_one_or_none()
                    if old_doc:
                        await self._store.delete_by_document(old_doc.id)

                # Build text content
                text = await builder(arg)
                if not text or not text.strip():
                    summary["skipped"].append(f"{category} (empty)")
                    continue

                # Chunk → Embed → Store
                chunks = self._chunker.chunk_text(text)
                if not chunks:
                    summary["skipped"].append(f"{category} (no chunks)")
                    continue

                vectors = self._embedder.embed_batch(chunks)

                await self._store.store_document_with_embeddings(
                    user_id=user_id,
                    title=doc_title,
                    raw_content=text,
                    chunks=chunks,
                    vectors=vectors,
                    content_type="text/plain",
                    agent_type="career_guidance",
                )

                summary["indexed"].append(category)
                logger.info(
                    "Indexed %s for user %s: %d chunks",
                    category, user_id, len(chunks),
                )

            except Exception as e:
                logger.error(
                    "Failed to index %s for user %s: %s",
                    category, user_id, e,
                )
                summary["errors"].append(f"{category}: {str(e)}")

        await self.db.flush()

        logger.info(
            "UserDataEmbedder summary for %s: indexed=%s, skipped=%s, errors=%s",
            user_id,
            summary["indexed"],
            summary["skipped"],
            summary["errors"],
        )
        return summary

    # ── Text builders ────────────────────────────────────────────────────

    async def _build_skills_text(self, user: AuthUser) -> str:
        """Build a text document from user's skills."""
        skills = user.skills or []
        if not skills:
            return ""

        lines = [
            "USER SKILLS PROFILE",
            f"Name: {user.name}",
            f"Department: {user.department or 'Not specified'}",
            f"Semester: {user.semester or 'N/A'}",
            f"Career Goal: {user.goal or 'Not specified'}",
            "",
            "Technical Skills:",
        ]
        for skill in skills:
            lines.append(f"  - {skill}")

        lines.append("")
        lines.append(
            f"Total skills: {len(skills)}. "
            f"Experience level: {'advanced' if len(skills) >= 8 else 'intermediate' if len(skills) >= 4 else 'beginner'}."
        )
        return "\n".join(lines)

    async def _build_certificates_text(self, user_id: uuid.UUID) -> str:
        """Build a text document from user's certificates."""
        result = await self.db.execute(
            select(Certificate).where(Certificate.student_id == user_id)
        )
        certs = result.scalars().all()
        if not certs:
            return ""

        lines = ["USER CERTIFICATES AND CERTIFICATIONS", ""]
        for i, cert in enumerate(certs, 1):
            lines.append(f"Certificate {i}:")
            lines.append(f"  Title: {cert.title}")
            if cert.description:
                lines.append(f"  Description: {cert.description}")
            issuer = getattr(cert, "issuer", None)
            if issuer:
                lines.append(f"  Issuer: {issuer}")
            lines.append(f"  Points: {cert.points}")
            lines.append(f"  Verified: {'Yes' if cert.is_verified else 'No'}")
            lines.append("")

        lines.append(f"Total certificates: {len(certs)}")
        total_points = sum(c.points for c in certs)
        lines.append(f"Total certification points: {total_points}")
        return "\n".join(lines)

    async def _build_projects_text(self, user_id: uuid.UUID) -> str:
        """Build a text document from user's projects."""
        from app.models.project import Project

        result = await self.db.execute(
            select(Project).where(Project.student_id == user_id)
        )
        projects = result.scalars().all()
        if not projects:
            return ""

        lines = ["USER PROJECTS PORTFOLIO", ""]
        for i, proj in enumerate(projects, 1):
            lines.append(f"Project {i}: {proj.project_name}")
            if proj.description:
                lines.append(f"  Description: {proj.description}")
            if proj.tech_stack:
                lines.append(f"  Tech Stack: {proj.tech_stack}")
            if proj.github_url:
                lines.append(f"  GitHub: {proj.github_url}")
            lines.append(f"  Verification Status: {proj.verification_status or 'pending'}")
            lines.append("")

        lines.append(f"Total projects: {len(projects)}")
        verified = sum(1 for p in projects if p.verification_status == "verified")
        lines.append(f"Verified projects: {verified}")
        return "\n".join(lines)

    async def _build_academics_text(self, user_id: uuid.UUID) -> str:
        """Build a text document from user's academic marks."""
        result = await self.db.execute(
            select(InternalMarks).where(InternalMarks.student_id == user_id)
        )
        marks = result.scalars().all()
        if not marks:
            return ""

        lines = ["USER ACADEMIC PERFORMANCE", ""]

        # Group by semester
        by_semester: dict[int, list] = {}
        for m in marks:
            by_semester.setdefault(m.semester, []).append(m)

        total_obtained = 0
        total_max = 0

        for sem in sorted(by_semester.keys()):
            lines.append(f"Semester {sem}:")
            for m in by_semester[sem]:
                pct = round(m.marks_obtained / m.max_marks * 100, 1) if m.max_marks else 0
                lines.append(
                    f"  - {m.subject_name}: {m.marks_obtained}/{m.max_marks} ({pct}%)"
                )
                total_obtained += m.marks_obtained
                total_max += m.max_marks
            lines.append("")

        avg_pct = round(total_obtained / total_max * 100, 1) if total_max else 0
        lines.append(f"Overall Average: {avg_pct}%")

        # Identify strengths and weaknesses
        subject_pcts = []
        for m in marks:
            pct = round(m.marks_obtained / m.max_marks * 100, 1) if m.max_marks else 0
            subject_pcts.append((m.subject_name, pct))

        subject_pcts.sort(key=lambda x: x[1], reverse=True)
        if subject_pcts:
            lines.append(f"Strongest subject: {subject_pcts[0][0]} ({subject_pcts[0][1]}%)")
            lines.append(f"Weakest subject: {subject_pcts[-1][0]} ({subject_pcts[-1][1]}%)")

        return "\n".join(lines)

    async def _build_interviews_text(self, user_id: uuid.UUID) -> str:
        """Build a text document from user's interview reports."""
        from app.models.interview import InterviewReport, InterviewSession

        try:
            # Get user's interview sessions
            sessions_result = await self.db.execute(
                select(InterviewSession).where(
                    InterviewSession.student_id == user_id
                )
            )
            sessions = sessions_result.scalars().all()
            if not sessions:
                return ""

            session_ids = [s.session_id for s in sessions]

            # Get reports for those sessions
            reports_result = await self.db.execute(
                select(InterviewReport).where(
                    InterviewReport.session_id.in_(session_ids)
                )
            )
            reports = reports_result.scalars().all()
            if not reports:
                return ""

            lines = ["USER INTERVIEW PERFORMANCE HISTORY", ""]

            for i, report in enumerate(reports, 1):
                lines.append(f"Interview {i}:")
                if report.final_score is not None:
                    lines.append(f"  Final Score: {report.final_score}%")
                if hasattr(report, "strengths") and report.strengths:
                    lines.append(f"  Strengths: {report.strengths}")
                if hasattr(report, "weaknesses") and report.weaknesses:
                    lines.append(f"  Weaknesses: {report.weaknesses}")
                if hasattr(report, "overall_feedback") and report.overall_feedback:
                    lines.append(f"  Feedback: {report.overall_feedback}")
                if hasattr(report, "recommendations") and report.recommendations:
                    lines.append(f"  Recommendations: {report.recommendations}")
                lines.append("")

            avg_score = sum(
                r.final_score for r in reports if r.final_score is not None
            ) / max(len([r for r in reports if r.final_score is not None]), 1)
            lines.append(f"Total interviews: {len(reports)}")
            lines.append(f"Average score: {round(avg_score, 1)}%")

            return "\n".join(lines)

        except Exception as e:
            logger.warning("Failed to build interview text for user %s: %s", user_id, e)
            return ""

    async def _build_resume_text(self, user: AuthUser) -> str:
        """Build a text document from user's resume file."""
        resume_url = getattr(user, "resume_url", None)
        if not resume_url:
            return ""

        try:
            # Try reading as a local file path
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            resume_path = os.path.join(base_dir, "resumes", os.path.basename(resume_url))

            if not os.path.exists(resume_path):
                # Try the URL as-is
                resume_path = resume_url

            if not os.path.exists(resume_path):
                logger.info("Resume file not found: %s", resume_path)
                return ""

            if resume_path.lower().endswith(".pdf"):
                with open(resume_path, "rb") as f:
                    pdf_bytes = f.read()
                text = self._chunker.extract_text_from_pdf(pdf_bytes)
            else:
                with open(resume_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

            if text:
                return f"USER RESUME / CV\n\n{text}"
            return ""

        except Exception as e:
            logger.warning("Failed to read resume for user %s: %s", user.id, e)
            return ""
