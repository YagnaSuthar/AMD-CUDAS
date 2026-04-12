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
<<<<<<< HEAD
from typing import Any, Optional

=======

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import delete, func, select
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import get_llm
from app.agents.career_guidance.profile_builder import build_user_profile
<<<<<<< HEAD
from app.agents.career_roadmap.prompts import ROADMAP_SYSTEM_PROMPT
=======
from app.agents.career_roadmap.prompts import PHASE_DETAILED_SYSTEM_PROMPT, ROADMAP_SYSTEM_PROMPT
from app.models.auth import AuthUser, Certificate
from app.models.interview import InterviewReport, InterviewSession
from app.models.roadmap import BranchStep, RoadmapBranch, RoadmapStep
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
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


<<<<<<< HEAD
=======
def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """Extract a JSON array from LLM output that may contain fences or surrounding text."""
    text = (text or "").strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                parsed = json.loads(part)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                continue

    start = text.find("[")
    end = text.rfind("]") + 1
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start:end])
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    logger.error("Could not extract valid JSON array from LLM response: %s", text[:300])
    raise ValueError(f"Could not extract valid JSON array from LLM response: {text[:200]}...")


>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
class CareerRoadmapAgent:
    """
    Generates career roadmaps in strict JSON format using LLM + optional RAG.
    """

    AGENT_TYPE = "career_roadmap"

    def __init__(self, db: AsyncSession):
        self.db = db
        self._retrieval = RetrievalService(db)
        logger.info("CareerRoadmapAgent initialized")

<<<<<<< HEAD
=======
    async def _multi_source_retrieve(
        self,
        *,
        user_id: uuid.UUID,
        goal: str,
        skills: list[str],
        top_k: int = 6,
    ) -> dict[str, list[dict[str, Any]]]:
        """Run multiple semantic searches (agent_type used as an index proxy)."""

        skill_summary = ", ".join(skills[:20]) if skills else ""
        queries: dict[str, str] = {
            "resume_index": f"resume experience projects for goal {goal}. skills: {skill_summary}",
            "skills_index": f"skills assessment for goal {goal}. current skills: {skill_summary}",
            "certification_index": f"certifications completed relevant to goal {goal}. skills: {skill_summary}",
            "interview_index": f"interview feedback weak areas missing skills for goal {goal}. skills: {skill_summary}",
        }

        # Map these indexes onto existing Document.agent_type. If your ingestion uses
        # different values, we still fall back to agent_type=None (global user docs).
        agent_type_map: dict[str, Optional[str]] = {
            "resume_index": "career_roadmap",
            "skills_index": "career_roadmap",
            "certification_index": "career_roadmap",
            "interview_index": "career_roadmap",
        }

        out: dict[str, list[dict[str, Any]]] = {}
        for key, q in queries.items():
            try:
                out[key] = await self._retrieval.search(
                    query=q,
                    user_id=user_id,
                    agent_type=agent_type_map.get(key),
                    top_k=top_k,
                )
            except Exception as e:
                logger.warning("RAG retrieval failed for %s (non-fatal): %s", key, e)
                out[key] = []

        return out

    @staticmethod
    def _infer_level(*, skills: list[str], semester: int | None, interview_avg_score: float | None) -> str:
        """Heuristic level estimation. Avoid defaulting to beginner without evidence."""

        score = 0
        if skills:
            score += min(len(skills), 30)
        if semester is not None:
            if semester >= 6:
                score += 20
            elif semester >= 3:
                score += 10
        if interview_avg_score is not None:
            # InterviewReport.final_score appears to be 0-10 (legacy), normalize gently
            if interview_avg_score >= 7:
                score += 25
            elif interview_avg_score >= 5:
                score += 12

        if score >= 45:
            return "advanced"
        if score >= 20:
            return "intermediate"
        return "beginner"

    async def _get_interview_performance(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Compute average score and weak areas from recent interview reports."""

        stmt = (
            select(InterviewReport, InterviewSession)
            .join(InterviewSession, InterviewReport.session_id == InterviewSession.session_id)
            .where(InterviewSession.student_id == user_id)
            .order_by(InterviewSession.start_time.desc())
            .limit(10)
        )
        res = await self.db.execute(stmt)
        rows = res.all()

        scores: list[float] = []
        weak: set[str] = set()
        for rpt, _sess in rows:
            if rpt and rpt.final_score is not None:
                scores.append(float(rpt.final_score))
            if rpt and rpt.weaknesses:
                for w in (rpt.weaknesses or []):
                    if w:
                        weak.add(str(w))

        avg = sum(scores) / len(scores) if scores else None
        return {
            "average_score": round(avg, 3) if avg is not None else None,
            "weak_areas": sorted(list(weak))[:12],
        }

    async def _get_completed_steps(self, user_id: uuid.UUID, goal_title: str) -> list[str]:
        res = await self.db.execute(
            select(RoadmapStep)
            .where(
                RoadmapStep.user_id == user_id,
                RoadmapStep.goal_title == goal_title,
                RoadmapStep.status == "completed",
            )
            .order_by(RoadmapStep.created_at.asc())
        )
        steps = list(res.scalars().all())
        return [s.phase for s in steps if s.phase]

    async def _persist_new_steps(
        self, user_id: uuid.UUID, goal_title: str, steps: list[dict[str, Any]]
    ) -> None:
        for step in steps:
            self.db.add(
                RoadmapStep(
                    user_id=user_id,
                    phase=str(step.get("phase", "")),
                    goal_title=goal_title,
                    description=str(step.get("description", "")),
                    skills=step.get("skills", []) if isinstance(step.get("skills"), list) else [],
                    duration=str(step.get("duration", "")),
                    status=str(step.get("status", "pending")),
                )
            )
        await self.db.flush()

>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
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

<<<<<<< HEAD
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
=======
        # ── Step 1: Load base user + profile ──────────────────────────────
        result = await self.db.execute(select(AuthUser).where(AuthUser.id == user_id))
        user = result.scalar_one_or_none()

        profile: dict[str, Any]
        if student_data:
            profile = student_data
        else:
            profile = await build_user_profile(user_id, self.db)

        goal_text = (
            profile.get("goal")
            or ", ".join(profile.get("goals", []))
            or (user.goal if user is not None else None)
            or "career development"
        )
        skills = profile.get("skills") or (user.skills if user is not None and user.skills else []) or []
        semester = None
        try:
            semester = int(profile.get("semester")) if profile.get("semester") is not None else None
        except Exception:
            semester = None
        if semester is None and isinstance(profile.get("education"), dict):
            try:
                semester = int(profile["education"].get("semester")) if profile["education"].get("semester") is not None else None
            except Exception:
                semester = None

        # ── Step 2: Completed roadmap steps (to avoid repetition) ─────────
        completed_steps = await self._get_completed_steps(user_id, goal_title=goal_text)

        # ── Step 3: Interview performance summary ────────────────────────
        interview_perf = await self._get_interview_performance(user_id)

        # ── Step 4: Certifications completed ─────────────────────────────
        cert_res = await self.db.execute(select(Certificate).where(Certificate.student_id == user_id))
        certs = list(cert_res.scalars().all())
        cert_titles = [c.title for c in certs if getattr(c, "title", None)]

        # ── Step 5: Multi-source semantic retrieval ──────────────────────
        rag_hits = await self._multi_source_retrieve(user_id=user_id, goal=goal_text, skills=list(skills), top_k=6)

        # ── Step 6: Resume summary (best-effort from retrieved chunks) ────
        resume_chunks = rag_hits.get("resume_index", [])
        resume_summary = " ".join([c.get("content", "") for c in resume_chunks[:2] if c.get("content")]).strip()
        if len(resume_summary) > 800:
            resume_summary = resume_summary[:800]

        # ── Step 7: Level estimation ─────────────────────────────────────
        current_level = self._infer_level(
            skills=list(skills),
            semester=semester,
            interview_avg_score=interview_perf.get("average_score"),
        )

        context_payload = {
            "goal": goal_text,
            "current_skills": list(skills)[:50],
            "resume_summary": resume_summary,
            "certifications_completed": cert_titles[:20],
            "interview_performance": interview_perf,
            "completed_roadmap_steps": completed_steps,
            "current_level_estimation": current_level,
            "rag_sources": {
                k: [
                    {
                        "document_title": h.get("document_title"),
                        "score": h.get("score"),
                        "content": h.get("content"),
                    }
                    for h in (v or [])[:5]
                ]
                for k, v in rag_hits.items()
            },
        }

        # Required debugging prints
        print("===== RAG CONTEXT =====")
        print(json.dumps(context_payload, indent=2, ensure_ascii=False))

        # ── Step 8: Build prompt ─────────────────────────────────────────
        system_content = ROADMAP_SYSTEM_PROMPT.format(
            context_payload=json.dumps(context_payload, ensure_ascii=False),
        )

        print("===== FINAL PROMPT =====")
        print(system_content)
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=system_content),
<<<<<<< HEAD
            HumanMessage(content="Generate my career roadmap based on the profile above."),
        ]

        # ── Step 4: LLM call with retry ────────────────────────────────────
=======
            HumanMessage(content="Generate the roadmap JSON now."),
        ]

        # ── Step 9: LLM call with retry ───────────────────────────────────
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
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

<<<<<<< HEAD
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
=======
                # ── Step 10: Parse JSON array ─────────────────────────────
                phases = _extract_json_array(content)

                if not phases:
                    raise ValueError("Roadmap output must be a non-empty JSON array")

                # Filter out completed steps (defensive)
                completed_set = {s.strip().lower() for s in completed_steps if s}
                normalized: list[dict[str, Any]] = []
                for p in phases:
                    if not isinstance(p, dict):
                        continue
                    phase_name = str(p.get("phase", "")).strip() or "Untitled Phase"
                    if phase_name.strip().lower() in completed_set:
                        continue
                    normalized.append(
                        {
                            "phase": phase_name,
                            "description": str(p.get("description", "")) if p.get("description") is not None else "",
                            "skills": p.get("skills") if isinstance(p.get("skills"), list) else [],
                            "duration": str(p.get("duration", "")) if p.get("duration") is not None else "",
                            "status": "pending",
                        }
                    )

                if not normalized:
                    raise ValueError("After removing completed steps, there are no new phases to add")

                # Safety cap: maximum 12 phases
                if len(normalized) > 12:
                    normalized = normalized[:12]

                # Delete ALL old steps for this user/goal before persisting new ones
                # (completed phases were already captured above and excluded from LLM output)
                await self.db.execute(
                    delete(RoadmapStep).where(
                        RoadmapStep.user_id == user_id,
                        RoadmapStep.goal_title == goal_text,
                    )
                )
                await self.db.flush()

                # Persist new steps
                await self._persist_new_steps(user_id, goal_title=goal_text, steps=normalized)
                await self.db.commit()

                # Reload from DB to get real UUIDs
                saved_res = await self.db.execute(
                    select(RoadmapStep)
                    .where(
                        RoadmapStep.user_id == user_id,
                        RoadmapStep.goal_title == goal_text,
                    )
                    .order_by(RoadmapStep.created_at.asc())
                )
                saved_steps = list(saved_res.scalars().all())

                # Return legacy-compatible structure with real UUIDs
                legacy_steps = []
                for idx, s in enumerate(saved_steps, 1):
                    legacy_steps.append(
                        {
                            "id": str(s.id),
                            "title": s.phase,
                            "description": s.description or "",
                            "skills": s.skills or [],
                            "resources": [],
                            "timeline": s.duration or "",
                            "status": s.status or "pending",
                        }
                    )

                return {
                    "title": goal_text,
                    "summary": f"Personalized roadmap ({current_level})",
                    "steps": legacy_steps,
                }

>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a

            except Exception as exc:
                last_error = exc
                logger.warning("Roadmap generation attempt %d failed: %s", attempt, exc)
                await asyncio.sleep(0.5 * attempt)

        logger.error("All 3 roadmap generation attempts failed. Last error: %s", last_error)
        raise RuntimeError(f"Failed to generate valid roadmap JSON after 3 attempts: {last_error}")

<<<<<<< HEAD
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
=======

    async def generate_phase_detailed_roadmap(
        self,
        user_id: uuid.UUID,
        phase_id: uuid.UUID,
        force_regenerate: bool = False,
    ) -> dict[str, Any]:
        phase_res = await self.db.execute(
            select(RoadmapStep).where(RoadmapStep.id == phase_id, RoadmapStep.user_id == user_id)
        )
        phase = phase_res.scalar_one_or_none()
        if phase is None:
            raise ValueError("Phase not found")

        user_res = await self.db.execute(select(AuthUser).where(AuthUser.id == user_id))
        user = user_res.scalar_one_or_none()
        goal_text = (getattr(user, "goal", None) or "").strip()
        if not goal_text:
            goal_text = (getattr(phase, "goal_title", "") or "").strip()

        existing_branch_res = await self.db.execute(
            select(RoadmapBranch).where(
                RoadmapBranch.user_id == user_id,
                RoadmapBranch.parent_phase_id == phase_id,
                RoadmapBranch.branch_type == "detailed",
            )
        )
        existing_branch = existing_branch_res.scalar_one_or_none()
        if existing_branch is not None and not force_regenerate:
            steps_res = await self.db.execute(
                select(BranchStep)
                .where(BranchStep.branch_id == existing_branch.id)
                .order_by(BranchStep.week.asc(), BranchStep.created_at.asc())
            )
            existing_steps = list(steps_res.scalars().all())
            return {
                "branch_id": str(existing_branch.id),
                "parent_phase_id": str(phase_id),
                "phase": phase.phase,
                "weekly_plan": [
                    {
                        "id": str(s.id),
                        "week": s.week,
                        "topics": list(s.topics or []),
                        "tasks": list(s.tasks or []),
                        "resources": list(s.resources or []),
                        "deliverable": s.deliverable or "",
                        "submission_required": bool(s.submission_required),
                        "submission_type": s.submission_type,
                        "submission_link": s.submission_link or "",
                        "status": s.status,
                    }
                    for s in existing_steps
                ],
            }

        if existing_branch is not None and force_regenerate:
            await self.db.execute(delete(BranchStep).where(BranchStep.branch_id == existing_branch.id))
            await self.db.execute(delete(RoadmapBranch).where(RoadmapBranch.id == existing_branch.id))
            await self.db.commit()

        profile = await build_user_profile(user_id, self.db)
        skills = profile.get("skills") or (user.skills if user is not None and user.skills else []) or []

        completed_steps = await self._get_completed_steps(user_id, goal_title=goal_text)
        interview_perf = await self._get_interview_performance(user_id)
        cert_res = await self.db.execute(select(Certificate).where(Certificate.student_id == user_id))
        certs = list(cert_res.scalars().all())
        cert_titles = [c.title for c in certs if getattr(c, "title", None)]

        rag_goal = f"{goal_text} | {phase.phase}"
        rag_hits = await self._multi_source_retrieve(
            user_id=user_id, goal=rag_goal, skills=list(skills), top_k=6
        )
        resume_chunks = rag_hits.get("resume_index", [])
        resume_summary = " ".join([c.get("content", "") for c in resume_chunks[:2] if c.get("content")]).strip()
        if len(resume_summary) > 800:
            resume_summary = resume_summary[:800]

        semester = None
        try:
            semester = int(profile.get("semester")) if profile.get("semester") is not None else None
        except Exception:
            semester = None
        if semester is None and isinstance(profile.get("education"), dict):
            try:
                semester = int(profile["education"].get("semester")) if profile["education"].get("semester") is not None else None
            except Exception:
                semester = None

        current_level = self._infer_level(
            skills=list(skills),
            semester=semester,
            interview_avg_score=interview_perf.get("average_score"),
        )

        context_payload = {
            "main_goal": goal_text,
            "phase_goal": phase.phase,
            "user_current_state": {
                "semester": semester,
            },
            "skills": list(skills)[:50],
            "resume": resume_summary,
            "certifications": cert_titles[:20],
            "interview_performance": interview_perf,
            "completed_steps": completed_steps,
            "current_level": current_level,
            "phase_duration": phase.duration or "",
        }

        print("===== PHASE CONTEXT =====")
        print(json.dumps(context_payload, indent=2, ensure_ascii=False))

        system_content = PHASE_DETAILED_SYSTEM_PROMPT.format(
            context_payload=json.dumps(context_payload, ensure_ascii=False),
        )

        print("===== PHASE PROMPT =====")
        print(system_content)

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(
                content=(
                    "Generate the detailed weekly roadmap JSON now. "
                    "Return ONLY the JSON object exactly matching the specified schema."
                )
            ),
        ]

        llm = get_llm()
        llm.max_tokens = 2048

        last_error: Exception | None = None
        parsed: dict[str, Any] | None = None
        for attempt in range(1, 4):
            try:
                response = await asyncio.to_thread(llm.invoke, messages)
                content = response.content if hasattr(response, "content") else str(response)
                parsed = _extract_json(content)
                break
            except Exception as exc:
                last_error = exc
                messages.append(
                    HumanMessage(
                        content=(
                            "Your previous response was invalid. "
                            "Return ONLY a valid JSON object (no prose, no markdown) with keys: "
                            "phase, weekly_plan[]."
                        )
                    )
                )
                await asyncio.sleep(0.4 * attempt)

        if parsed is None:
            raise ValueError(f"Could not extract valid JSON from LLM response: {last_error}")

        weekly_plan = parsed.get("weekly_plan") if isinstance(parsed, dict) else None
        if not isinstance(weekly_plan, list) or not weekly_plan:
            raise ValueError("Detailed roadmap output must include a non-empty weekly_plan")

        branch = RoadmapBranch(user_id=user_id, parent_phase_id=phase_id, branch_type="detailed")
        self.db.add(branch)
        await self.db.flush()

        for w in weekly_plan:
            if not isinstance(w, dict):
                continue
            week_num = w.get("week")
            try:
                week_num_int = int(week_num)
            except Exception:
                continue

            resources = w.get("resources") if isinstance(w.get("resources"), list) else []
            self.db.add(
                BranchStep(
                    branch_id=branch.id,
                    week=week_num_int,
                    topics=w.get("topics") if isinstance(w.get("topics"), list) else [],
                    tasks=w.get("tasks") if isinstance(w.get("tasks"), list) else [],
                    resources=resources,
                    deliverable=str(w.get("deliverable", "")) if w.get("deliverable") is not None else "",
                    submission_required=bool(w.get("submission_required", False)),
                    submission_type=str(w.get("submission_type", "none")) if w.get("submission_type") is not None else "none",
                    status="pending",
                )
            )

        await self.db.commit()

        steps_res = await self.db.execute(
            select(BranchStep)
            .where(BranchStep.branch_id == branch.id)
            .order_by(BranchStep.week.asc(), BranchStep.created_at.asc())
        )
        saved_steps = list(steps_res.scalars().all())
        return {
            "branch_id": str(branch.id),
            "parent_phase_id": str(phase_id),
            "phase": phase.phase,
            "weekly_plan": [
                {
                    "id": str(s.id),
                    "week": s.week,
                    "topics": list(s.topics or []),
                    "tasks": list(s.tasks or []),
                    "resources": list(s.resources or []),
                    "deliverable": s.deliverable or "",
                    "submission_required": bool(s.submission_required),
                    "submission_type": s.submission_type,
                    "submission_link": s.submission_link or "",
                    "status": s.status,
                }
                for s in saved_steps
            ],
        }

    # NOTE: legacy _format_* helpers removed; prompt now uses structured context_payload.
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
