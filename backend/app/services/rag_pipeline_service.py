"""
RAG Pipeline Service.

End-to-end pipeline: Query → Embed → Retrieve → Context Injection → LLM → Response.
"""

import logging
import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.llm import get_llm
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

# ── Context injection prompt ────────────────────────────────────────────────

_RAG_SYSTEM_TEMPLATE = """\
You are an expert AI assistant for the CUDAS education platform.
Use ONLY the provided context to answer the user's question.
If the context does not contain enough information, say so honestly.
Do NOT hallucinate or fabricate information beyond the context.

CONTEXT:
{context}

USER PROFILE:
{profile}
"""


class RAGPipeline:
    """Orchestrates the full RAG flow: retrieve → build context → LLM."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._retrieval = RetrievalService(db)

    async def generate(
        self,
        query: str,
        user_context: Optional[dict[str, Any]] = None,
        user_id: Optional[uuid.UUID] = None,
        agent_type: Optional[str] = None,
        top_k: Optional[int] = None,
        system_prompt_override: Optional[str] = None,
    ) -> str:
        """
        Run the full RAG pipeline and return the LLM response.

        Parameters
        ----------
        query : str
            The user's natural-language question.
        user_context : dict, optional
            Structured user profile / extra context to inject.
        user_id : uuid, optional
            Filter retrieval to this user's documents.
        agent_type : str, optional
            Filter retrieval by agent type.
        top_k : int, optional
            Number of chunks to retrieve.
        system_prompt_override : str, optional
            Custom system prompt (replaces the default template).

        Returns
        -------
        str
            The LLM-generated response text.
        """
        # 1) Retrieve relevant chunks
        retrieved = await self._retrieval.search(
            query=query,
            user_id=user_id,
            agent_type=agent_type,
            top_k=top_k,
        )

        # 2) Build context string from retrieved chunks
        context_parts: list[str] = []
        for i, chunk in enumerate(retrieved, 1):
            context_parts.append(
                f"[Source {i}: {chunk['document_title']}]\n{chunk['content']}"
            )
        context_str = "\n\n".join(context_parts) if context_parts else "No relevant context found."

        # 3) Profile string
        profile_str = ""
        if user_context:
            profile_parts = []
            for key, value in user_context.items():
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                profile_parts.append(f"- {key}: {value}")
            profile_str = "\n".join(profile_parts)

        # 4) Build messages
        if system_prompt_override:
            system_content = system_prompt_override.format(
                context=context_str,
                profile=profile_str,
            )
        else:
            system_content = _RAG_SYSTEM_TEMPLATE.format(
                context=context_str,
                profile=profile_str,
            )

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=query),
        ]

        # 5) Call LLM
        llm = get_llm()
        import asyncio
        response = await asyncio.to_thread(llm.invoke, messages)
        answer = response.content if hasattr(response, "content") else str(response)

        logger.info(
            "RAG pipeline: query='%s…' → %d chunks retrieved, response length=%d",
            query[:50], len(retrieved), len(answer),
        )
        return answer
