"""
Career Guidance Agent.

Hybrid agent that uses direct LLM for general queries and
RAG-enhanced responses for personalized/skill-gap/career-switch/
project-recommendation/job-matching queries.

Automatically ensures user data is indexed in pgvector before retrieval.
"""

import asyncio
import logging
import uuid
from typing import Any, AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import get_llm
from app.agents.career_guidance.intent_classifier import IntentType, classify_intent
from app.agents.career_guidance.profile_builder import build_user_profile
from app.agents.career_guidance import prompts
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class CareerGuidanceAgent:
    """
    Hybrid Career Guidance Agent.

    - GENERAL_QUERY → direct LLM call (no retrieval)
    - All other intents → RAG pipeline with user data auto-indexing
    """

    AGENT_TYPE = "career_guidance"

    def __init__(self, db: AsyncSession):
        self.db = db
        self._retrieval = RetrievalService(db)

    # Short answers are much faster to generate and easier to read.
    MAX_ANSWER_TOKENS = 900

    async def prepare(
        self,
        user_id: uuid.UUID,
        query: str,
    ) -> tuple[list, dict[str, Any]]:
        """
        Classify the query, gather profile/RAG context and build the LLM messages.

        Returns ``(messages, meta)`` where meta has 'intent', 'used_rag', 'data_sources'.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        # 1) Classify intent
        intent = classify_intent(query)
        logger.info("CareerGuidanceAgent: user=%s intent=%s query='%s…'",
                     user_id, intent.value, query[:60])

        if intent == IntentType.GENERAL_QUERY:
            messages = [
                SystemMessage(content=prompts.GENERAL_QUERY_SYSTEM + prompts.BREVITY_RULES),
                HumanMessage(content=query),
            ]
            return messages, {"intent": intent.value, "used_rag": False, "data_sources": []}

        # 2) Profile + make sure the user's data is indexed (same DB session,
        #    so these run sequentially)
        profile = await build_user_profile(user_id, self.db)
        data_sources = await self._ensure_data_indexed(user_id)

        # 3) Retrieve relevant context (search ALL user documents)
        retrieved = await self._retrieval.search(
            query=query,
            user_id=user_id,
            agent_type=None,
            top_k=6,
        )

        system_content = self._get_prompt_for_intent(intent).format(
            profile=self._format_profile(profile),
            context=self._format_context(retrieved),
        ) + prompts.BREVITY_RULES

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=query),
        ]
        return messages, {"intent": intent.value, "used_rag": True, "data_sources": data_sources}

    async def handle_query(
        self,
        user_id: uuid.UUID,
        query: str,
    ) -> dict[str, Any]:
        """
        Main entry point (non-streaming).

        Returns a dict with keys 'response', 'intent', 'used_rag', 'data_sources'.
        """
        messages, meta = await self.prepare(user_id, query)
        llm = get_llm(max_tokens=self.MAX_ANSWER_TOKENS)
        response = await llm.ainvoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        return {"response": content, **meta}

    async def stream_answer(self, messages: list) -> AsyncIterator[str]:
        """Yield the answer text chunk by chunk as the LLM generates it."""
        llm = get_llm(max_tokens=self.MAX_ANSWER_TOKENS)
        async for chunk in llm.astream(messages):
            text = chunk.content if hasattr(chunk, "content") else str(chunk)
            if text:
                yield text

    # ── Private methods ─────────────────────────────────────────────────────

    async def _ensure_data_indexed(self, user_id: uuid.UUID) -> list[str]:
        """
        Ensure user's profile data is embedded in pgvector.
        Returns the list of data sources that were indexed or already existed.
        """
        try:
            from app.services.user_data_embedder import UserDataEmbedder

            embedder = UserDataEmbedder(self.db)
            summary = await embedder.ensure_user_data_indexed(
                user_id=user_id,
                force_reindex=False,
            )

            # Combine indexed and skipped (skipped means already indexed)
            sources = summary.get("indexed", []) + summary.get("skipped", [])
            # Clean up "(empty)" / "(no chunks)" suffixes for display
            clean_sources = [
                s.split(" (")[0] for s in sources
                if "(empty)" not in s and "(no chunks)" not in s
            ]

            logger.info(
                "Data indexing for user %s: indexed=%s, skipped=%s",
                user_id, summary.get("indexed"), summary.get("skipped"),
            )
            return clean_sources

        except Exception as e:
            logger.warning(
                "User data indexing failed (non-fatal): %s", e
            )
            return []

    def _get_prompt_for_intent(self, intent: IntentType) -> str:
        """Return the system prompt template for the given intent."""
        mapping = {
            IntentType.PERSONALIZED_GUIDANCE: prompts.PERSONALIZED_GUIDANCE_SYSTEM,
            IntentType.SKILL_GAP_ANALYSIS: prompts.SKILL_GAP_SYSTEM,
            IntentType.CAREER_SWITCH: prompts.CAREER_SWITCH_SYSTEM,
            IntentType.PROJECT_RECOMMENDATION: prompts.PROJECT_RECOMMENDATION_SYSTEM,
            IntentType.JOB_ROLE_MATCHING: prompts.JOB_ROLE_MATCHING_SYSTEM,
        }
        return mapping.get(intent, prompts.PERSONALIZED_GUIDANCE_SYSTEM)

    @staticmethod
    def _format_context(retrieved: list[dict]) -> str:
        """Format retrieved chunks into a context string."""
        if not retrieved:
            return "No relevant documents found for this user."
        parts = []
        for i, chunk in enumerate(retrieved, 1):
            parts.append(f"[Source {i}: {chunk['document_title']}]\n{chunk['content']}")
        return "\n\n".join(parts)

    @staticmethod
    def _format_profile(profile: dict[str, Any]) -> str:
        """Format a user profile dict into a readable string."""
        lines = []

        # Skills
        skills = profile.get("skills", [])
        lines.append(f"Skills: {', '.join(skills) if skills else 'None specified'}")
        lines.append(f"Experience Level: {profile.get('experience_level', 'unknown')}")

        # Education
        edu = profile.get("education", {})
        lines.append(f"Department: {edu.get('department', 'N/A')}")
        lines.append(f"Semester: {edu.get('semester', 'N/A')}")
        lines.append(f"Average Percentage: {edu.get('average_percentage', 0)}%")

        # Goals
        goals = profile.get("goals", [])
        lines.append(f"Career Goals: {', '.join(goals) if goals else 'Not set'}")

        # Certifications
        certs = profile.get("certifications", [])
        if certs:
            cert_entries = []
            for c in certs:
                title = c.get("title", "Unknown")
                verified = " ✓" if c.get("is_verified") else ""
                cert_entries.append(f"{title}{verified}")
            lines.append(f"Certifications: {', '.join(cert_entries)}")
        else:
            lines.append("Certifications: None")

        # Projects
        projects = profile.get("projects", [])
        if projects:
            lines.append(f"Projects ({len(projects)}):")
            for p in projects:
                status = p.get("verification_status", "pending")
                tech = p.get("tech_stack", "")
                lines.append(f"  - {p.get('name', 'Unnamed')}: {tech} [{status}]")
        else:
            lines.append("Projects: None")

        # Interview history
        interviews = profile.get("interview_history", [])
        if interviews:
            scores = [i.get("score") for i in interviews if i.get("score") is not None]
            avg = round(sum(scores) / len(scores), 1) if scores else "N/A"
            lines.append(f"Interview History: {len(interviews)} interviews, avg score: {avg}")
            # Include latest strengths/weaknesses
            latest = interviews[-1] if interviews else {}
            if latest.get("strengths"):
                lines.append(f"  Latest Strengths: {latest['strengths']}")
            if latest.get("weaknesses"):
                lines.append(f"  Latest Weaknesses: {latest['weaknesses']}")
        else:
            lines.append("Interview History: No interviews yet")

        # Resume summary
        resume_summary = profile.get("resume_summary")
        if resume_summary:
            lines.append(f"Resume Summary: {resume_summary[:300]}...")

        return "\n".join(lines)
