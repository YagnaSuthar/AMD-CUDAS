"""
Career Guidance Agent.

Hybrid agent that uses direct LLM for general queries and
RAG-enhanced responses for personalized/skill-gap/career-switch queries.
"""

import asyncio
import logging
import uuid
from typing import Any, Optional

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
    - PERSONALIZED_GUIDANCE / SKILL_GAP / CAREER_SWITCH → RAG pipeline
    """

    AGENT_TYPE = "career_guidance"

    def __init__(self, db: AsyncSession):
        self.db = db
        self._retrieval = RetrievalService(db)

    async def handle_query(
        self,
        user_id: uuid.UUID,
        query: str,
    ) -> dict[str, Any]:
        """
        Main entry point.

        Parameters
        ----------
        user_id : uuid.UUID
            The authenticated user's ID.
        query : str
            The user's natural-language question.

        Returns
        -------
        dict with keys 'response', 'intent', 'used_rag'.
        """
        # 1) Classify intent
        intent = classify_intent(query)
        logger.info("CareerGuidanceAgent: user=%s intent=%s query='%s…'",
                     user_id, intent.value, query[:60])

        # 2) Build user profile (needed for all personalized intents)
        profile = await build_user_profile(user_id, self.db)

        # 3) Route by intent
        if intent == IntentType.GENERAL_QUERY:
            response = await self._handle_general(query)
            return {"response": response, "intent": intent.value, "used_rag": False}

        # For all personalized intents, use RAG
        response = await self._handle_with_rag(query, profile, intent, user_id)
        return {"response": response, "intent": intent.value, "used_rag": True}

    # ── Private methods ─────────────────────────────────────────────────────

    async def _handle_general(self, query: str) -> str:
        """Handle a general career query with direct LLM call."""
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=prompts.GENERAL_QUERY_SYSTEM),
            HumanMessage(content=query),
        ]
        llm = get_llm()
        response = await asyncio.to_thread(llm.invoke, messages)
        return response.content if hasattr(response, "content") else str(response)

    async def _handle_with_rag(
        self,
        query: str,
        profile: dict[str, Any],
        intent: IntentType,
        user_id: uuid.UUID,
    ) -> str:
        """Handle queries that benefit from RAG-enhanced context."""
        from langchain_core.messages import HumanMessage, SystemMessage

        # 1) Retrieve relevant context (search ALL user documents)
        retrieved = await self._retrieval.search(
            query=query,
            user_id=user_id,
            agent_type=None,
            top_k=5,
        )

        # 2) Format context and profile
        context_str = self._format_context(retrieved)
        profile_str = self._format_profile(profile)

        # 3) Select prompt template based on intent
        system_template = self._get_prompt_for_intent(intent)
        system_content = system_template.format(
            profile=profile_str,
            context=context_str,
        )

        # 4) Call LLM
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=query),
        ]
        llm = get_llm()
        response = await asyncio.to_thread(llm.invoke, messages)
        return response.content if hasattr(response, "content") else str(response)

    def _get_prompt_for_intent(self, intent: IntentType) -> str:
        """Return the system prompt template for the given intent."""
        mapping = {
            IntentType.PERSONALIZED_GUIDANCE: prompts.PERSONALIZED_GUIDANCE_SYSTEM,
            IntentType.SKILL_GAP_ANALYSIS: prompts.SKILL_GAP_SYSTEM,
            IntentType.CAREER_SWITCH: prompts.CAREER_SWITCH_SYSTEM,
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
        skills = profile.get("skills", [])
        lines.append(f"Skills: {', '.join(skills) if skills else 'None specified'}")
        lines.append(f"Experience Level: {profile.get('experience_level', 'unknown')}")

        edu = profile.get("education", {})
        lines.append(f"Department: {edu.get('department', 'N/A')}")
        lines.append(f"Semester: {edu.get('semester', 'N/A')}")
        lines.append(f"Average Percentage: {edu.get('average_percentage', 0)}%")

        goals = profile.get("goals", [])
        lines.append(f"Career Goals: {', '.join(goals) if goals else 'Not set'}")

        certs = profile.get("certifications", [])
        if certs:
            cert_titles = [c.get("title", "Unknown") for c in certs]
            lines.append(f"Certifications: {', '.join(cert_titles)}")
        else:
            lines.append("Certifications: None")

        return "\n".join(lines)
