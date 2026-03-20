"""
Career Roadmap Agent.

Generates structured JSON career roadmaps using ChatGroq LLM,
optionally enhanced with RAG-retrieved context.
Full logging at every pipeline stage for observability.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import get_llm
from app.agents.career_guidance.profile_builder import build_user_profile
from app.agents.career_roadmap.prompts import ROADMAP_SYSTEM_PROMPT
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


# ── JSON extraction helper ──────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """
    Extract a JSON object from LLM output that may contain
    markdown fences or surrounding text.
    """
    text = text.strip()

    # 1) Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.debug("Direct JSON parse failed, trying fallback extraction")

    # 2) Strip markdown code fences
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                result = json.loads(part)
                logger.debug("Extracted JSON from markdown fences")
                return result
            except json.JSONDecodeError:
                continue

    # 3) Find JSON object boundaries
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            result = json.loads(text[start:end])
            logger.debug("Extracted JSON from object boundaries")
            return result
        except json.JSONDecodeError:
            pass

    logger.error("Could not extract valid JSON from LLM response: %s", text[:300])
    raise ValueError(f"Could not extract valid JSON from LLM response: {text[:200]}...")


class CareerRoadmapAgent:
    """
    Generates career roadmaps in strict JSON format using LLM + optional RAG.
    """

    AGENT_TYPE = "career_roadmap"

    def __init__(self, db: AsyncSession):
        self.db = db
        self._retrieval = RetrievalService(db)
        logger.info("CareerRoadmapAgent initialized")

    async def generate_roadmap(
        self,
        user_id: uuid.UUID,
        student_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Generate a structured career roadmap.

        Returns
        -------
        dict
            Roadmap JSON: {title, summary, steps: [{id, title, description, skills, resources, timeline}]}
        """
        logger.info("=" * 60)
        logger.info("Starting roadmap generation for user_id: %s", user_id)
        logger.info("=" * 60)

        # ── Step 1: Build profile ──────────────────────────────────────────
        if student_data:
            profile = student_data
            logger.info("Using pre-built student data: goal='%s', skills=%s",
                        profile.get("goal", "N/A"),
                        profile.get("skills", []))
        else:
            logger.info("Building user profile from database...")
            profile = await build_user_profile(user_id, self.db)
            logger.info("Profile built: goal='%s', skills=%s, education=%s",
                        profile.get("goals", []),
                        profile.get("skills", []),
                        profile.get("education", {}))

        # ── Step 2: RAG Retrieval ──────────────────────────────────────────
        goal_text = profile.get("goal") or ", ".join(profile.get("goals", ["career development"]))
        logger.info("Querying RAG for relevant context: '%s'", goal_text)

        try:
            retrieved = await self._retrieval.search(
                query=f"career roadmap skills education certifications for {goal_text}",
                user_id=user_id,
                agent_type=None,
                top_k=8,
            )
            logger.info("Retrieved %d relevant chunks from vector store", len(retrieved))
            for i, chunk in enumerate(retrieved):
                logger.debug("  Chunk %d: score=%.4f, doc='%s'",
                             i + 1, chunk.get("score", 0), chunk.get("document_title", ""))
        except Exception as e:
            logger.warning("RAG retrieval failed (proceeding without context): %s", e)
            retrieved = []

        context_str = self._format_context(retrieved)
        profile_str = self._format_profile(profile)

        # ── Step 3: Build LLM prompt ───────────────────────────────────────
        logger.info("Building LLM prompt with profile and %d context chunks", len(retrieved))
        system_content = ROADMAP_SYSTEM_PROMPT.format(
            profile=profile_str,
            context=context_str,
        )

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content="Generate my career roadmap based on the profile above."),
        ]

        # ── Step 4: LLM call with retry ────────────────────────────────────
        llm = get_llm()
        # Override max_tokens for roadmap — needs more output space
        llm.max_tokens = 2048
        last_error: Exception | None = None

        for attempt in range(1, 4):
            logger.info("LLM attempt %d/3 — generating career roadmap...", attempt)
            try:
                response = await asyncio.to_thread(llm.invoke, messages)
                content = response.content if hasattr(response, "content") else str(response)
                logger.info("LLM response received (length=%d chars)", len(content))
                logger.debug("Raw LLM output: %s", content[:500])

                # ── Step 5: Parse JSON ─────────────────────────────────────
                roadmap = _extract_json(content)
                logger.info("JSON parsed successfully")

                # ── Step 6: Validate schema ────────────────────────────────
                if "title" not in roadmap or "steps" not in roadmap:
                    raise ValueError("Roadmap JSON missing 'title' or 'steps'")
                if not isinstance(roadmap["steps"], list) or len(roadmap["steps"]) == 0:
                    raise ValueError("Roadmap 'steps' must be a non-empty list")

                # Normalize each step — ensure all required fields + id
                for idx, step in enumerate(roadmap["steps"]):
                    step["id"] = step.get("id", idx + 1)
                    step.setdefault("title", "Untitled Step")
                    step.setdefault("description", "")
                    step.setdefault("skills", [])
                    step.setdefault("resources", [])
                    step.setdefault("timeline", "")

                roadmap.setdefault("summary", "")

                logger.info("=" * 60)
                logger.info("Roadmap generated successfully!")
                logger.info("  Title: %s", roadmap["title"])
                logger.info("  Steps: %d", len(roadmap["steps"]))
                for s in roadmap["steps"]:
                    logger.info("    Step %d: %s (%s)", s["id"], s["title"], s["timeline"])
                logger.info("=" * 60)

                return roadmap

            except Exception as exc:
                last_error = exc
                logger.warning("Roadmap generation attempt %d failed: %s", attempt, exc)
                await asyncio.sleep(0.5 * attempt)

        logger.error("All 3 roadmap generation attempts failed. Last error: %s", last_error)
        raise RuntimeError(f"Failed to generate valid roadmap JSON after 3 attempts: {last_error}")

    @staticmethod
    def _format_context(retrieved: list[dict]) -> str:
        if not retrieved:
            return "No additional context available."
        parts = []
        for i, chunk in enumerate(retrieved, 1):
            parts.append(f"[Source {i}] {chunk['content']}")
        return "\n\n".join(parts)

    @staticmethod
    def _format_profile(profile: dict) -> str:
        lines = []
        goal = profile.get("goal") or ", ".join(profile.get("goals", []))
        lines.append(f"Career Goal: {goal or 'Not specified'}")

        if "department" in profile:
            lines.append(f"Department: {profile['department']}")
        elif "education" in profile:
            edu = profile["education"]
            lines.append(f"Department: {edu.get('department', 'N/A')}")
            lines.append(f"Semester: {edu.get('semester', 'N/A')}")
            lines.append(f"Average: {edu.get('average_percentage', 0)}%")

        skills = profile.get("skills", [])
        lines.append(f"Skills: {', '.join(skills) if skills else 'None specified'}")

        if "semester" in profile and "education" not in profile:
            lines.append(f"Semester: {profile.get('semester', 'N/A')}")
        if "average_percentage" in profile:
            lines.append(f"Average: {profile['average_percentage']}%")

        certs = profile.get("certifications", [])
        if certs:
            cert_strs = [c.get("title", str(c)) if isinstance(c, dict) else str(c) for c in certs]
            lines.append(f"Certifications: {', '.join(cert_strs)}")

        subjects = profile.get("subjects", [])
        if subjects:
            subj_strs = [f"{s['name']}: {s.get('percentage', 'N/A')}%" if isinstance(s, dict) else str(s) for s in subjects[:5]]
            lines.append(f"Subjects: {', '.join(subj_strs)}")

        return "\n".join(lines)
