"""
Interview Orchestrator — runtime module.
Implements the interview state machine with:
- Human conversational greeting
- Behavior-reactive responses
- Dynamic context-aware question generation
- Token-efficient memory usage

States: INIT → PROFILING → GREETING → QUESTIONING → EVALUATING → MEMORY_UPDATE → ENDED
"""

import enum
import logging
from typing import Any, Dict
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.interview import InterviewTurn, StudentProfile
from app.agents.Interview.utils import InterviewTracer

from app.agents.Interview.prompts import (
    BEHAVIOR_RESPONSES,
    GREETING_TEMPLATE,
)
from app.agents.Interview.sub_agents.profile_intelligence.agent import analyze_profile
from app.agents.Interview.sub_agents.question_generator.agent import generate_question
from app.agents.Interview.sub_agents.question_generator.agent_strict import generate_question_strict
from app.agents.Interview.planner.interview_planner import InterviewPlanner
from app.agents.Interview.sub_agents.question_generator.topic_selector import (
    select_concept,
    get_rag_query_for_selection,
)
from app.agents.Interview.sub_agents.answer_evaluator.agent import evaluate_answer
from app.agents.Interview.sub_agents.memory_agent.agent import update_memory
from app.agents.Interview.sub_agents.feedback_agent.agent import generate_report
from app.agents.Interview.services.rag_context import get_interview_context, get_followup_context
from app.core.config import settings
from app.core.modes import normalize_interview_mode

logger = logging.getLogger(__name__)


def _soft_summarize_for_processing(text: str, max_chars: int = 20000) -> str:
    if not text:
        return text
    if len(text) <= max_chars:
        return text
    head = text[:8000].rstrip()
    tail = text[-4000:].lstrip()
    return (head + "\n...\n" + tail).strip()


def _default_turn_evaluation() -> dict:
    return {
        "correctness": 0,
        "concept_depth": 0,
        "communication": 0,
        "confidence": 0,
        "mistakes": [],
        "missing_points": [],
        "misconceptions": [],
        "severity": "low",
        "final_feedback": "No evaluation available",
    }


def extract_projects(summary_text):
    lines = summary_text.split("\n")

    projects = []
    for line in lines:
        if any(k in line.lower() for k in ["project", "built", "developed"]):
            projects.append(line.strip())

    return projects[:3]


class InterviewState(str, enum.Enum):
    """States in the interview state machine."""
    INIT = "init"
    PROFILING = "profiling"
    GREETING = "greeting"
    QUESTIONING = "questioning"
    EVALUATING = "evaluating"
    MEMORY_UPDATE = "memory_update"
    ENDED = "ended"


class InterviewOrchestrator:
    """
    Stateful orchestrator that manages the flow of an interview session.

    Each call to ``step()`` determines the next agent to invoke and
    returns an action indicating what the caller should do next.
    Includes human-conversational greeting and behavior-reactive logic.
    """

    def __init__(
        self,
        student_id: UUID,
        session_id: UUID,
        db: AsyncSession,
        llm: Any,
        student_name: str = "Student",
        job_role: str = "",
        mode: str = "basic",
    ) -> None:
        self.student_id = student_id
        self.session_id = session_id
        self.db = db
        self.llm = llm
        self.student_name = student_name
        self._job_role: str = job_role or ""

        try:
            self._mode = normalize_interview_mode(mode)
        except Exception:
            # Backwards-compatible fallback only.
            self._mode = self._normalize_mode(job_role)
        # Mode-based termination control
        self._is_time_based = self._mode == "basic"
        self._max_questions = 20 if self._is_time_based else 15
        self.state: InterviewState = InterviewState.INIT
        self._profile_context: str = ""
        self._skill_summary: str = ""
        self._current_difficulty: str = "medium"
        self._last_question: str = ""
        self._last_answer_summary: str = ""
        self._last_behavior: str = "neutral"
        self._current_turn: InterviewTurn | None = None
        self._current_phase: str = "resume"
        self._questions_in_phase: int = 0
        self._phase_order: list = ["resume", "core", "problem_solving", "behavioral", "mixed"]
        self._previous_topics: list = []
        self._current_topic: str = "initial"
        self._topic_depth: int = 0
        self._last_evaluation: dict = _default_turn_evaluation()
        self._weak_answers_total: int = 0
        self._weak_answers_in_phase: int = 0
        self._strong_answers_in_phase: int = 0
        self._current_intent: str = "primary"
        self._has_projects: bool = False
        self._has_relevant_projects: bool = False
        self._project_summary: str = ""
        self._project_list: list = []
        self._question_count: int = 0
        self._weak_streak: int = 0
        self._asked_behavioral_fallback: bool = False
        self._force_behavioral_fallback: bool = False
        
        self._phase_topics = self._build_phase_topics(self._mode)

    def _normalize_mode(self, job_role: str) -> str:
        """Best-effort mapping from stored job_role to one of the supported modes."""
        jr = (job_role or "").strip().lower()
        if not jr:
            return "basic"
        if jr in {"basic", "frontend", "backend", "fullstack", "java", "python", "cybersecurity"}:
            return jr
        if "cyber" in jr or "security" in jr or "infosec" in jr:
            return "cybersecurity"
        if "front" in jr or "react" in jr or "ui" in jr:
            return "frontend"
        if "back" in jr or "api" in jr or "server" in jr:
            return "backend"
        if "full" in jr or "mern" in jr or "mean" in jr:
            return "fullstack"
        if "java" in jr:
            return "java"
        if "python" in jr:
            return "python"
        return "basic"

    def _build_phase_topics(self, mode: str) -> dict:
        """Mode-aware topic plan per phase. Phase order remains unchanged."""
        base = {
            "resume": [
                {"topic": "project_overview", "intent": "primary"},
                {"topic": "tech_stack", "intent": "primary"},
                {"topic": "architecture_decisions", "intent": "primary"},
            ],
            "behavioral": [
                {"topic": "teamwork_conflict", "intent": "primary"},
            ],
        }

        if mode == "frontend":
            base["core"] = [
                {"topic": "HTML", "intent": "primary"},
                {"topic": "CSS", "intent": "primary"},
                {"topic": "JavaScript", "intent": "primary"},
                {"topic": "React", "intent": "primary"},
                {"topic": "Browser_Rendering_DOM", "intent": "primary"},
            ]
            base["problem_solving"] = [
                {"topic": "arrays_strings", "intent": "primary"},
                {"topic": "async_event_loop", "intent": "primary"},
                {"topic": "ui_state_logic", "intent": "primary"},
            ]
            return base

        if mode == "backend":
            base["core"] = [
                {"topic": "DBMS", "intent": "primary"},
                {"topic": "APIs", "intent": "primary"},
                {"topic": "Caching", "intent": "primary"},
                {"topic": "Authentication", "intent": "primary"},
                {"topic": "System_Design_Basics", "intent": "primary"},
            ]
            base["problem_solving"] = [
                {"topic": "hashing_maps", "intent": "primary"},
                {"topic": "queues_streams", "intent": "primary"},
                {"topic": "data_flow_reasoning", "intent": "primary"},
            ]
            return base

        if mode == "fullstack":
            base["core"] = [
                {"topic": "React", "intent": "primary"},
                {"topic": "Node_APIs", "intent": "primary"},
                {"topic": "MongoDB", "intent": "primary"},
                {"topic": "Auth_Fullstack", "intent": "primary"},
            ]
            base["problem_solving"] = [
                {"topic": "api_data_flow", "intent": "primary"},
                {"topic": "logic_reasoning", "intent": "primary"},
                {"topic": "real_world_scenario", "intent": "primary"},
            ]
            return base

        if mode in {"java", "python"}:
            base["core"] = [
                {"topic": f"{mode}_language_concepts", "intent": "primary"},
                {"topic": "OOP", "intent": "primary"},
                {"topic": "memory_runtime", "intent": "primary"},
            ]
            base["problem_solving"] = [
                {"topic": "language_specific_dsa", "intent": "primary"},
                {"topic": "logic_reasoning", "intent": "primary"},
                {"topic": "real_world_scenario", "intent": "primary"},
            ]
            return base

        if mode == "cybersecurity":
            base["core"] = [
                {"topic": "network_security", "intent": "primary"},
                {"topic": "auth_sessions", "intent": "primary"},
                {"topic": "encryption_basics", "intent": "primary"},
                {"topic": "web_security", "intent": "primary"},
            ]
            base["problem_solving"] = [
                {"topic": "threat_modeling_scenarios", "intent": "primary"},
                {"topic": "logic_reasoning", "intent": "primary"},
            ]
            return base

        # basic/default
        base["core"] = [
            {"topic": "DBMS", "intent": "primary"},
            {"topic": "OS", "intent": "primary"},
            {"topic": "OOP", "intent": "primary"},
            {"topic": "Computer_Networks", "intent": "primary"},
            {"topic": "Software_Engineering", "intent": "primary"},
        ]
        base["problem_solving"] = [
            {"topic": "Arrays_and_Strings", "intent": "primary"},
            {"topic": "Linked_Lists_and_Stacks", "intent": "primary"},
            {"topic": "Trees_and_Graphs", "intent": "primary"},
            {"topic": "Sorting_and_Searching", "intent": "primary"},
            {"topic": "Dynamic_Programming_Basics", "intent": "primary"},
        ]
        base["mixed"] = [
            {"topic": "System_Design_Basics", "intent": "primary"},
            {"topic": "Advanced_DSA", "intent": "primary"},
            {"topic": "Core_Subject_Scenarios", "intent": "primary"},
            {"topic": "Debugging_and_Testing", "intent": "primary"},
            {"topic": "Optimization_Strategies", "intent": "primary"},
            {"topic": "General_Technical_Logic", "intent": "primary"},
        ]
        return base

    def _filter_resume_project_summary(self, project_summary: str) -> str:
        """Filter resume project lines to the ones most relevant to the selected mode."""
        summary = (project_summary or "").strip()
        if not summary:
            return summary

        mode = self._mode
        needles = {
            "frontend": ["react", "next", "vue", "angular", "frontend", "ui", "css", "html", "javascript", "redux", "tailwind"],
            "backend": ["api", "backend", "server", "database", "db", "postgres", "mysql", "mongodb", "redis", "auth", "jwt", "microservice"],
            "fullstack": ["mern", "fullstack", "react", "node", "express", "mongo", "api", "frontend", "backend"],
            "java": ["java", "spring", "spring boot", "jpa", "hibernate"],
            "python": ["python", "django", "flask", "fastapi"],
            "cybersecurity": ["security", "cyber", "oauth", "jwt", "encryption", "vulnerability", "pentest", "xss", "csrf", "sql injection"],
        }.get(mode, [])

        if not needles:
            return summary

        lines = [ln.strip() for ln in summary.splitlines() if ln.strip()]
        kept = [ln for ln in lines if any(n in ln.lower() for n in needles)]
        return "\n".join(kept) if kept else summary

    def _has_any_relevant_project(self, project_summary: str) -> bool:
        """Return True if any resume project line matches the selected mode."""
        summary = (project_summary or "").strip()
        if not summary:
            return False

        mode = self._mode
        needles = {
            "frontend": ["react", "next", "vue", "angular", "frontend", "ui", "css", "html", "javascript", "redux", "tailwind"],
            "backend": ["api", "backend", "server", "database", "db", "postgres", "mysql", "mongodb", "redis", "auth", "jwt", "microservice"],
            "fullstack": ["mern", "fullstack", "react", "node", "express", "mongo", "api", "frontend", "backend"],
            "java": ["java", "spring", "spring boot", "jpa", "hibernate"],
            "python": ["python", "django", "flask", "fastapi"],
            "cybersecurity": ["security", "cyber", "oauth", "jwt", "encryption", "vulnerability", "pentest", "xss", "csrf", "sql injection"],
        }.get(mode, [])

        # If we have no mode-specific needles (e.g., basic), treat projects as relevant.
        if not needles:
            return True

        lines = [ln.strip() for ln in summary.splitlines() if ln.strip()]
        return any(any(n in ln.lower() for n in needles) for ln in lines)

    def _extract_turn_history_metadata(self, turns) -> tuple[list, list, list]:
        """Return (question_history, used_topics, used_concepts) from prior turns."""
        question_history = []
        used_topics = []
        used_concepts = []
        used_subtopics = []
        for t in turns:
            if t.question:
                question_history.append(t.question)
            ev = t.evaluation if isinstance(t.evaluation, dict) else {}
            qm = ev.get("question_meta") if isinstance(ev, dict) else None
            if isinstance(qm, dict):
                topic = (qm.get("topic") or "").strip()
                st = (qm.get("subtopic") or topic or "").strip()
                c = (qm.get("concept") or "").strip()
                sc = (qm.get("secondary_concept") or "").strip()
                if topic and topic not in used_topics:
                    used_topics.append(topic)
                if st and st not in used_subtopics:
                    used_subtopics.append(st)
                if c and c not in used_concepts:
                    used_concepts.append(c)
                if sc and sc not in used_concepts:
                    used_concepts.append(sc)
        return question_history, used_topics, used_concepts, used_subtopics

    def _rag_query_for_question(self, question_number: int, project_summary: str, plan: dict | None = None) -> str:
        """Build a focused RAG query from deterministic topic/concept when applicable."""
        if plan and plan.get("concept"):
            return get_rag_query_for_selection(plan.get("topic", ""), plan.get("concept", ""), project_summary)
        return f"{project_summary} project architecture tech stack"
        
    def _get_next_topic(self) -> tuple[str, str]:
        """Strict topic fetch mechanism based on current phase and un-used topics."""
        phase_list = self._phase_topics.get(self._current_phase, [])
        for item in phase_list:
            if item["topic"] not in self._previous_topics:
                return item["topic"], item["intent"]
        return "general", "concept"

    def set_state(self, state: InterviewState) -> None:
        """Manually set the orchestrator state."""
        self.state = state

    def set_max_questions(self, max_q: int) -> None:
        """Override the maximum question count."""
        self._max_questions = max_q

    def set_question_count(self, count: int) -> None:
        """Restore question count (for session resumption)."""
        self._question_count = count
        # Also sync self._questions_in_phase if we're resuming
        # This is a simplification; for full resumption we'd need turn history
        # but for now we assume we start fresh or at a known count.

    async def step(
        self,
        last_answer: str = "",
    ) -> Dict[str, Any]:
        """
        Execute one step of the state machine.

        Parameters
        ----------
        last_answer : str
            The candidate's last answer text (empty on first call).

        Returns
        -------
        dict   {"next_agent": str, "difficulty": str, "action": str, "data": dict}
        """
        logger.info(
            "Orchestrator step: state=%s session=%s",
            self.state.value, self.session_id,
        )

        print("\n===== STEP CALLED =====")
        print("CURRENT STATE:", self.state)
        print("LAST ANSWER:", last_answer)

        # ── INIT → PROFILING → GREETING + FIRST QUESTION ─────────────────
        if self.state == InterviewState.INIT:
            try:
                self.state = InterviewState.PROFILING
                profile_data = await analyze_profile(
                    self.student_id, self.db, self.llm
                )

                # Restore/derive profile fields for question generation
                self._has_projects = bool(profile_data.get("has_projects", False)) if isinstance(profile_data, dict) else False
                self._skill_summary = ", ".join(profile_data.get("skills", [])) if isinstance(profile_data, dict) else ""
                self._project_summary = profile_data.get("project_summary", "") if isinstance(profile_data, dict) else ""
                filtered_project_summary = self._filter_resume_project_summary(self._project_summary)
                self._has_relevant_projects = self._has_projects and self._has_any_relevant_project(self._project_summary)
                self._project_list = extract_projects(filtered_project_summary or self._project_summary)
                self._profile_context = (
                    f"Candidate skills: {self._skill_summary}. "
                    f"Has Projects: {self._has_projects}. "
                    f"Project Summary: {self._project_summary}."
                )

                # Greeting used by the API handshake response payload
                greeting = GREETING_TEMPLATE.format(student_name=self.student_name)

                # Resume/project questions only if relevant to the selected mode.
                if self._current_phase == "resume" and not self._has_relevant_projects:
                    logger.info("No relevant projects for mode=%s, skipping to core phase. Q1 will be scenario-based.", self._mode)
                    self._current_phase = "core"

                # Safety check: never exceed max_questions
                print("QUESTION COUNT (INIT):", self._question_count)
                if self._question_count >= self._max_questions:
                    print("MAX QUESTIONS REACHED IN INIT, ENDING INTERVIEW")
                    return await self._end_interview()

                # Strict topic extraction
                next_topic, next_intent = self._get_next_topic()
                self._current_topic = next_topic
                self._current_intent = next_intent
                
                # Fetch RAG context will be done after we compute the plan and concept

                # Generate first question
                self.state = InterviewState.QUESTIONING
                gen_fn = generate_question_strict
                
                # Fetch history turns (empty on first question, but good for consistency)
                turns_for_history = (
                    await self.db.execute(
                        select(InterviewTurn)
                        .where(InterviewTurn.session_id == self.session_id)
                        .order_by(InterviewTurn.timestamp.asc())
                    )
                ).scalars().all()
                
                history_metadata = []
                question_history = []
                for t in turns_for_history:
                    if t.question:
                        question_history.append(t.question)
                    ev = t.evaluation if isinstance(t.evaluation, dict) else {}
                    qm = ev.get("question_meta") if isinstance(ev, dict) else None
                    if isinstance(qm, dict):
                        history_metadata.append({
                            "phase": qm.get("phase") or t.phase or "",
                            "topic": qm.get("topic") or "",
                            "concept": qm.get("concept") or "",
                            "project": qm.get("project") or "",
                            "technology": qm.get("technology") or "",
                            "role": qm.get("role") or "",
                            "difficulty": qm.get("difficulty") or t.difficulty or "",
                            "intent": qm.get("intent") or qm.get("type") or "",
                            "question_number": qm.get("question_number") or 1
                        })

                # Compute next plan
                plan = InterviewPlanner.get_next_plan(
                    question_number=self._question_count + 1,
                    mode=self._mode,
                    history_metadata=history_metadata,
                    resume_project_summary=self._project_summary,
                    resume_has_projects=self._has_relevant_projects,
                    answer_quality=self._last_evaluation.get("answer_classification", "") if self._last_evaluation else "",
                    topic_depth=self._topic_depth,
                    skills=self._skill_summary,
                    phase=self._current_phase,
                    job_description=self._job_role
                )
                
                # Select concept dynamically
                used_concepts = [m["concept"] for m in history_metadata if m.get("concept")]
                plan["concept"] = select_concept(
                    phase=plan.get("phase", ""),
                    topic=plan.get("topic", ""),
                    role=plan.get("role", ""),
                    difficulty=plan.get("difficulty", ""),
                    used_concepts=used_concepts
                )
                
                # Fetch RAG context if in resume phase
                rag_context = ""
                if plan.get("phase") == "resume" or plan.get("project"):
                    rag_query = self._rag_query_for_question(
                        self._question_count + 1,
                        filtered_project_summary or self._project_summary,
                        plan
                    )
                    rag_context = await get_interview_context(
                        self.student_id, rag_query, self.db
                    )
                
                # Ensure the orchestrator's phase matches the planner's plan
                self._current_phase = plan.get("phase", self._current_phase)
                self._current_topic = plan.get("topic", "")
                self._current_intent = plan.get("intent", "concept")

                question_data = await gen_fn(
                    plan=plan,
                    context=self._profile_context,
                    difficulty=plan.get("difficulty", self._current_difficulty),
                    llm=self.llm,
                    last_answer=last_answer,
                    skill_summary=self._skill_summary,
                    resume_has_projects=self._has_relevant_projects,
                    resume_project_summary=self._project_summary,
                    phase=self._current_phase,
                    mode=self._mode,
                    previous_topics=self._previous_topics,
                    topic_depth=self._topic_depth,
                    current_topic=self._current_topic,
                    last_evaluation=self._last_evaluation,
                    rag_context=rag_context,
                    question_history=question_history,
                )
                self._last_question = question_data.get("question", "")
                self._question_count += 1
                self._questions_in_phase += 1
                print("QUESTION COUNT (INIT after increment):", self._question_count)
                
                # Additional safety check after increment
                if self._question_count > self._max_questions:
                    print("SAFETY: EXCEEDED MAX QUESTIONS AFTER INCREMENT, ENDING INTERVIEW")
                    return await self._end_interview()

                # Store question in turn (answer not yet received)
                self._current_turn = InterviewTurn(
                    session_id=self.session_id,
                    question=self._last_question,
                    answer=None,  # Will be filled when answer arrives
                    timestamp=datetime.utcnow(),
                    evaluation={
                        "question_meta": {
                            "question_number": self._question_count,
                            "phase": plan.get("phase", self._current_phase),
                            "topic": plan.get("topic", ""),
                            "concept": plan.get("concept", ""),
                            "project": plan.get("project", ""),
                            "technology": plan.get("technology", ""),
                            "role": plan.get("role", self._mode),
                            "difficulty": plan.get("difficulty", self._current_difficulty),
                            "intent": plan.get("intent", ""),
                        }
                    },
                    phase=self._current_phase,
                    difficulty=question_data.get("difficulty", self._current_difficulty),
                )
                self.db.add(self._current_turn)
                
                # Track topic to prevent repetition
                topic = question_data.get("topic", "general")
                self._current_topic = topic
                if topic and topic not in self._previous_topics:
                    self._previous_topics.append(topic)
                    
                await self.db.flush()  # Get turn_id without committing

                # Persist current turn id to session for reliable mapping
                try:
                    from app.models.interview import InterviewSession

                    sess = await self.db.get(InterviewSession, self.session_id)
                    if sess is not None:
                        sess.current_turn_id = self._current_turn.turn_id
                        await self.db.flush()
                except Exception:
                    pass

                question_data = {
                    **(question_data or {}),
                    "question": self._last_question,
                    "question_id": str(self._current_turn.turn_id),
                }

                # Print PLAN diagnostics for transparency
                print(f"\n[PLAN] phase={self._current_phase}")
                print(f"[PLAN] topic={question_data.get('topic') or self._current_topic}")
                project_name = plan.get("project", "")
                print(f"[PLAN] project={project_name or 'None'}")
                print(f"[PLAN] Reason For Transition=Deterministic plan progression\n")

                return {
                    "next_agent": "question_generator",
                    "difficulty": question_data.get("difficulty", self._current_difficulty),
                    "action": "ask_question",
                    "data": {
                        "profile": profile_data,
                        "question": question_data,
                        "greeting": greeting,
                    },
                }
            except Exception as e:
                logger.error("Orchestrator: INIT failed: %s", e)
                self.state = InterviewState.INIT
                return {"action": "error", "message": str(e)}

        # ── QUESTIONING (generate next question) ─────────────────────────
        if self.state == InterviewState.QUESTIONING:
            print(f"MODE: {self._mode}")
            print(f"QUESTION COUNT: {self._question_count}")
            print(f"MAX QUESTIONS: {self._max_questions}")
            
            # Safety check: never exceed max_questions
            if self._question_count >= self._max_questions:
                print("MAX QUESTIONS REACHED IN QUESTIONING, ENDING INTERVIEW")
                return await self._end_interview()

            try:
                # Fetch history turns
                turns_for_history = (
                    await self.db.execute(
                        select(InterviewTurn)
                        .where(InterviewTurn.session_id == self.session_id)
                        .order_by(InterviewTurn.timestamp.asc())
                    )
                ).scalars().all()
                
                history_metadata = []
                question_history = []
                for t in turns_for_history:
                    if t.question:
                        question_history.append(t.question)
                    ev = t.evaluation if isinstance(t.evaluation, dict) else {}
                    qm = ev.get("question_meta") if isinstance(ev, dict) else None
                    if isinstance(qm, dict):
                        history_metadata.append({
                            "phase": qm.get("phase") or t.phase or "",
                            "topic": qm.get("topic") or "",
                            "concept": qm.get("concept") or "",
                            "project": qm.get("project") or "",
                            "technology": qm.get("technology") or "",
                            "role": qm.get("role") or "",
                            "difficulty": qm.get("difficulty") or t.difficulty or "",
                            "intent": qm.get("intent") or qm.get("type") or "",
                            "question_number": qm.get("question_number") or 1
                        })

                # Compute next plan
                plan = InterviewPlanner.get_next_plan(
                    question_number=self._question_count + 1,
                    mode=self._mode,
                    history_metadata=history_metadata,
                    resume_project_summary=self._project_summary,
                    resume_has_projects=self._has_relevant_projects,
                    answer_quality=self._last_evaluation.get("answer_classification", "") if self._last_evaluation else "",
                    topic_depth=self._topic_depth,
                    skills=self._skill_summary,
                    phase=self._current_phase,
                    job_description=self._job_role
                )
                
                if self._current_intent == "follow-up" and history_metadata:
                    # Override planner with follow-up context
                    last_meta = history_metadata[-1]
                    plan["intent"] = "follow-up"
                    plan["topic"] = last_meta.get("topic", plan["topic"])
                    plan["concept"] = last_meta.get("concept", plan["concept"])
                    plan["project"] = last_meta.get("project", plan["project"])
                    plan["technology"] = last_meta.get("technology", plan["technology"])
                    plan["phase"] = last_meta.get("phase", plan["phase"])
                else:
                    # Select concept dynamically
                    used_concepts = [m["concept"] for m in history_metadata if m.get("concept")]
                    plan["concept"] = select_concept(
                        phase=plan.get("phase", ""),
                        topic=plan.get("topic", ""),
                        role=plan.get("role", ""),
                        difficulty=plan.get("difficulty", ""),
                        used_concepts=used_concepts
                    )
                
                # Ensure current state properties match the planner
                self._current_phase = plan.get("phase", self._current_phase)
                self._current_topic = plan.get("topic", "")
                self._current_intent = plan.get("intent", "concept")

                # Fetch RAG context using clean planner-derived metadata
                rag_context = ""
                followup_context = ""
                if plan.get("phase") == "resume" or plan.get("project"):
                    rag_query = self._rag_query_for_question(
                        self._question_count + 1,
                        self._project_summary,
                        plan
                    )
                    rag_context = await get_interview_context(
                        self.student_id, rag_query, self.db
                    )
                elif plan.get("intent") == "follow-up":
                    followup_context = await get_followup_context(
                        self.student_id, last_answer, self.db
                    )

                # Always use strict generator
                gen_fn = generate_question_strict

                question_data = await gen_fn(
                    plan=plan,
                    context=self._profile_context,
                    difficulty=plan.get("difficulty", self._current_difficulty),
                    llm=self.llm,
                    last_question=self._last_question,
                    last_answer=last_answer,
                    last_answer_summary=self._last_answer_summary,
                    behavior=self._last_behavior,
                    skill_summary=self._skill_summary,
                    resume_has_projects=self._has_relevant_projects,
                    resume_project_summary=self._project_summary,
                    phase=self._current_phase,
                    mode=self._mode,
                    previous_topics=self._previous_topics,
                    topic_depth=self._topic_depth,
                    current_topic=self._current_topic,
                    last_evaluation=self._last_evaluation,
                    rag_context=rag_context,
                    followup_context=followup_context,
                    question_history=question_history,
                    technologies_discussed=", ".join(list(set(m.get("technology") for m in history_metadata if m.get("technology")))),
                    projects_discussed=", ".join(list(set(m.get("project") for m in history_metadata if m.get("project")))),
                    previous_concepts=", ".join(list(set(m.get("concept") for m in history_metadata if m.get("concept")))),
                    current_difficulty=plan.get("difficulty", self._current_difficulty),
                    interview_phase=self._current_phase,
                )

                new_question = (question_data.get("question") or "").strip()
                self._last_question = new_question
                self._question_count += 1
                self._questions_in_phase += 1
                print("QUESTION COUNT (QUESTIONING after increment):", self._question_count)
                
                # Additional safety check after increment
                if self._question_count > self._max_questions:
                    print("SAFETY: EXCEEDED MAX QUESTIONS AFTER INCREMENT, ENDING INTERVIEW")
                    return await self._end_interview()

                # Store question in turn (answer not yet received)
                self._current_turn = InterviewTurn(
                    session_id=self.session_id,
                    question=self._last_question,
                    answer=None,  # Will be filled when answer arrives
                    timestamp=datetime.utcnow(),
                    evaluation={
                        "question_meta": {
                            "question_number": self._question_count,
                            "phase": plan.get("phase", self._current_phase),
                            "topic": plan.get("topic", ""),
                            "concept": plan.get("concept", ""),
                            "project": plan.get("project", ""),
                            "technology": plan.get("technology", ""),
                            "role": plan.get("role", self._mode),
                            "difficulty": plan.get("difficulty", self._current_difficulty),
                            "intent": plan.get("intent", ""),
                        }
                    },
                    phase=self._current_phase,
                    difficulty=question_data.get("difficulty", self._current_difficulty),
                )
                self.db.add(self._current_turn)
                
                # Track topic to prevent repetition
                topic = question_data.get("topic", "general")
                self._current_topic = topic
                if topic and topic not in self._previous_topics:
                    self._previous_topics.append(topic)
                    
                await self.db.flush()  # Get turn_id without committing

                # Persist current turn id to session for reliable mapping
                try:
                    from app.models.interview import InterviewSession

                    sess = await self.db.get(InterviewSession, self.session_id)
                    if sess is not None:
                        sess.current_turn_id = self._current_turn.turn_id
                        await self.db.flush()
                except Exception:
                    pass

                question_data = {
                    **(question_data or {}),
                    "question": self._last_question,
                    "question_id": str(self._current_turn.turn_id),
                }

                # Print PLAN diagnostics for transparency
                print(f"\n[PLAN] phase={self._current_phase}")
                print(f"[PLAN] topic={question_data.get('topic') or self._current_topic}")
                print(f"[PLAN] project={plan.get('project') or 'None'}")
                print(f"[PLAN] Reason For Transition=Deterministic plan progression\n")

                return {
                    "next_agent": "question_generator",
                    "difficulty": question_data.get("difficulty", self._current_difficulty),
                    "action": "ask_question",
                    "data": {"question": question_data},
                }
            except Exception as e:
                logger.error("Orchestrator: Question generation failed: %s", e)
                return {"action": "error", "message": str(e)}

        # ── EVALUATING (answer received → evaluate → memory → response) ──
        if self.state == InterviewState.EVALUATING:
            try:
                processed_answer = (last_answer or "").strip()

                # Query the turn first to get metadata
                try:
                    result = await self.db.execute(
                        select(InterviewTurn)
                        .where(
                            InterviewTurn.session_id == self.session_id,
                            or_(
                                InterviewTurn.answer.is_(None),
                                func.trim(InterviewTurn.answer) == "",
                            ),
                        )
                        .order_by(InterviewTurn.timestamp.desc())
                        .limit(1)
                    )
                    turn_obj = result.scalar_one_or_none()
                except Exception as db_err:
                    logger.error("Orchestrator: DB query for turn failed: %s", db_err)
                    turn_obj = None

                # Fallback: get the most recent turn if no unanswered turn found
                if turn_obj is None:
                    try:
                        result = await self.db.execute(
                            select(InterviewTurn)
                            .where(InterviewTurn.session_id == self.session_id)
                            .order_by(InterviewTurn.timestamp.asc())
                            .limit(1)
                        )
                        turn_obj = result.scalar_one_or_none()
                    except Exception as fb_err:
                        logger.error("Orchestrator: Fallback turn query failed: %s", fb_err)
                        turn_obj = None

                # Retrieve metadata from the turn's evaluation question_meta
                phase_val = "core_technical"
                topic_val = ""
                concept_val = ""
                role_val = ""
                difficulty_val = self._current_difficulty

                if turn_obj and isinstance(turn_obj.evaluation, dict):
                    qm = turn_obj.evaluation.get("question_meta", {})
                    if isinstance(qm, dict):
                        phase_val = qm.get("phase") or turn_obj.phase or "core_technical"
                        topic_val = qm.get("topic") or ""
                        concept_val = qm.get("concept") or ""
                        role_val = qm.get("role") or ""
                        difficulty_val = qm.get("difficulty") or turn_obj.difficulty or self._current_difficulty

                eval_data = None
                try:
                    eval_data = await evaluate_answer(
                        question=self._last_question,
                        answer=processed_answer,
                        llm=self.llm,
                        difficulty=difficulty_val,
                        phase=phase_val,
                        topic=topic_val,
                        concept=concept_val,
                        role=role_val,
                    )
                except Exception as eval_exc:
                    logger.error("Orchestrator: evaluate_answer exception: %s", eval_exc)
                    eval_data = None

                if not isinstance(eval_data, dict) or not eval_data:
                    # Rule 2: evaluation MUST always produce a result
                    logger.warning("Orchestrator: Evaluation returned empty — using fallback evaluation")
                    eval_data = {
                        **_default_turn_evaluation(),
                        "overall_score": 0,
                        "error": "evaluation_failed",
                        "answer_classification": "weak",
                        "technical_score": 0.0,
                        "communication_score": 0.0,
                        "behavior_score": 0.0,
                        "weighted_score": 0.0,
                        "behavior_flag": "neutral",
                        "next_difficulty": "easy",
                    }
                else:
                    # Enforce minimum schema while keeping extra keys
                    base = _default_turn_evaluation()
                    base.update(eval_data)
                    base["mistakes"] = base.get("mistakes") or []
                    base["missing_points"] = base.get("missing_points") or []
                    base["misconceptions"] = base.get("misconceptions") or []
                    eval_data = base

                behavior = eval_data.get("behavior_flag", "neutral")
                self._last_behavior = behavior

                # ── RULE 1 + 6: SAVE EVERY TURN (fail-safe, never skip) ──────
                # Determine clean answer — Rule 6: no "None" answers
                clean_answer = (last_answer or "").strip()
                stored_answer = clean_answer if clean_answer else "Skipped"
                logger.info("[DEBUG] DB Save Answer Length: %d", len(stored_answer))

                if turn_obj is not None:
                    existing_answer = (turn_obj.answer or "").strip() if isinstance(turn_obj.answer, str) else ""
                    # Duplicate write protection — Rule 1: never overwrite
                    if turn_obj.answer is None or existing_answer == "":
                        turn_obj.answer = stored_answer
                        turn_obj.answer_timestamp = datetime.utcnow()
                        existing_eval = turn_obj.evaluation if isinstance(turn_obj.evaluation, dict) else {}
                        qm = existing_eval.get("question_meta") if isinstance(existing_eval, dict) else None
                        merged = dict(eval_data) if isinstance(eval_data, dict) else {}
                        if isinstance(qm, dict) and "question_meta" not in merged:
                            merged["question_meta"] = qm
                        turn_obj.evaluation = merged
                        try:
                            await self.db.flush()  # Persist immediately — Rule 9
                        except Exception as flush_err:
                            logger.error("Orchestrator: Turn flush failed (non-fatal): %s", flush_err)
                    else:
                        logger.warning("Orchestrator: Duplicate answer write blocked for turn %s", turn_obj.turn_id)
                else:
                    logger.error("Orchestrator: CRITICAL — No turn found to store answer for session %s", self.session_id)

                # Generate behavior-reactive response
                agent_response = self._get_behavior_response(
                    behavior=behavior,
                    is_correct=eval_data.get("technical_score", 5) >= 5,
                    has_answer=bool(last_answer.strip()),
                )

                # Update memory with behavior
                self.state = InterviewState.MEMORY_UPDATE
                memory_data = await update_memory(
                    session_id=self.session_id,
                    answer=processed_answer,
                    db=self.db,
                    llm=self.llm,
                    behavior=behavior,
                )

                # Store summarized answer for next question context
                self._last_answer_summary = memory_data.get("summary", "")

                # Decide next difficulty
                self._current_difficulty = eval_data.get("next_difficulty", "medium")

                # Transition to next question or end
                if self._question_count >= self._max_questions:
                    return await self._end_interview()

                # ✅ Answer classification mapping (CRITICAL): use evaluator output.
                # If evaluator didn't provide it, derive a reasonable fallback.
                classification = eval_data.get("answer_classification")
                if classification not in ("strong", "partial", "weak"):
                    score = eval_data.get("technical_score", eval_data.get("correctness", 0))
                    try:
                        score = float(score)
                    except Exception:
                        score = 0.0
                    if score >= 7:
                        classification = "strong"
                    elif score >= 4:
                        classification = "partial"
                    else:
                        classification = "weak"

                eval_data["answer_classification"] = classification
                InterviewTracer.log_pipeline_step(1, "classify_answer", classification)

                if classification == "strong":
                    answer_state = "strong"
                elif classification == "partial":
                    answer_state = "partial"
                else:
                    answer_state = "weak"
                self._last_evaluation = eval_data
                
                # Advanced follow-up logic based on Evaluation + Answer Length + Concept Depth + Confidence
                self._weak_streak = 0
                self._last_evaluation = eval_data
                
                is_last_followup = False
                if turn_obj and isinstance(turn_obj.evaluation, dict):
                    qm = turn_obj.evaluation.get("question_meta", {})
                    if qm.get("intent") == "follow-up":
                        is_last_followup = True
                        
                correctness = float(eval_data.get("correctness", 0))
                concept_depth = float(eval_data.get("concept_depth", 0))
                communication = float(eval_data.get("communication", 0))
                confidence = float(eval_data.get("confidence", 0))
                
                total_score = correctness + concept_depth + communication + confidence
                
                # Assume each is out of 10. Max = 40. Trigger on > 32 and decent length.
                if not is_last_followup and total_score >= 32.0 and len(processed_answer) > 50:
                    self._current_intent = "follow-up"
                    self._topic_depth += 1
                else:
                    self._current_intent = "concept"
                    self._topic_depth = 0

                # Phase transitions are owned strictly by the deterministic planner progression.
                pass
                    
                InterviewTracer.log_pipeline_step(2, "phase", self._current_phase)
                InterviewTracer.log_pipeline_step(3, "topic", self._current_topic)

                self.state = InterviewState.QUESTIONING
                return {
                    "next_agent": "answer_evaluator",
                    "difficulty": self._current_difficulty,
                    "action": "ask_question",
                    "data": {
                        "evaluation": eval_data,
                        "memory": memory_data,
                        "agent_response": agent_response,
                        "phase": self._current_phase,
                    },
                }
            except Exception as e:
                logger.error("Orchestrator: Evaluation or Memory update failed: %s", e)
                return {"action": "error", "message": str(e)}

        # ── ENDED ────────────────────────────────────────────────────────
        if self.state == InterviewState.ENDED:
            return await self._end_interview(reason="normal")

        # Fallback
        return {
            "next_agent": "none",
            "difficulty": self._current_difficulty,
            "action": "end",
            "data": {},
        }

    async def _end_interview(self, reason: str = "normal") -> Dict[str, Any]:
        """Transition to ENDED and generate the final report.
        
        Implements Rules 4, 7, 9 from the orchestrator spec:
        - Rule 4: Early termination still produces complete report
        - Rule 7: Finalization step validates turns before report
        - Rule 9: Commit all turns THEN generate report
        """
        self.state = InterviewState.ENDED
        try:
            # ── Rule 9: Mark session status & end_time BEFORE report ───────────
            try:
                from app.models.interview import InterviewSession
                sess = await self.db.get(InterviewSession, self.session_id)
                if sess is not None:
                    # Use existing SessionStatus enum values to avoid invalid DB writes.
                    from app.models.interview import SessionStatus
                    sess.status = SessionStatus.CANCELLED if reason != "normal" else SessionStatus.COMPLETED
                    sess.end_time = datetime.utcnow()
                    await self.db.flush()
            except Exception as sess_err:
                logger.error("Orchestrator: Could not update session status: %s", sess_err)

            # ── Rule 7: Finalization validation ─────────────────────────────
            try:
                turns_result = await self.db.execute(
                    select(InterviewTurn)
                    .where(InterviewTurn.session_id == self.session_id)
                    .order_by(InterviewTurn.timestamp.asc())
                )
                all_turns = list(turns_result.scalars().all())
                turn_count = len(all_turns)

                if turn_count == 0:
                    logger.error("Orchestrator: Finalization — zero turns found for session %s", self.session_id)
                else:
                    # Validate each turn has required fields; fill defaults for missing
                    for t in all_turns:
                        if not t.question:
                            logger.error("Orchestrator: Turn %s missing question", t.turn_id)
                        if not t.answer:
                            t.answer = "Skipped"  # Rule 6: never store None
                        if not isinstance(t.evaluation, dict) or not t.evaluation:
                            t.evaluation = {
                                "overall_score": 0,
                                "error": "evaluation_failed",
                            }  # Rule 2: fallback evaluation
                    await self.db.flush()  # Rule 9: commit all before report
            except Exception as fin_err:
                logger.error("Orchestrator: Finalization validation failed (non-fatal): %s", fin_err)

            # ── Rule 5: Generate report from ALL stored turns ────────────────
            report = await generate_report(
                session_id=self.session_id,
                db=self.db,
                llm=self.llm,
                ended_reason=reason,
            )
            return {
                "next_agent": "feedback_agent",
                "difficulty": self._current_difficulty,
                "action": "end",
                "message": "Interview complete",
                "data": {"report": report},
            }
        except Exception as exc:
            logger.error("Orchestrator: _end_interview failed (non-fatal): %s", exc)
            # Rule 10: fail-safe — always return something
            return {
                "next_agent": "feedback_agent",
                "difficulty": self._current_difficulty,
                "action": "end",
                "message": "Interview complete",
                "data": {"report": {}},
            }

    @staticmethod
    def _get_behavior_response(
        behavior: str,
        is_correct: bool,
        has_answer: bool,
    ) -> str:
        """Return a neutral, formal transition sentence (no LLM call).

        Strict rule: no praise, no evaluation, no hints.
        """
        if not has_answer:
            return "Alright, let us proceed to the next question."
        return "Alright, let's proceed to the next question."

    def _move_to_next_phase(self) -> None:
        """Transition to the next phase in the predefined order."""
        try:
            current_idx = self._phase_order.index(self._current_phase)
            if current_idx < len(self._phase_order) - 1:
                self._current_phase = self._phase_order[current_idx + 1]
                self._questions_in_phase = 0
                self._weak_answers_in_phase = 0
                self._strong_answers_in_phase = 0
                self._topic_depth = 0
                logger.info("Orchestrator: Transitioning to phase '%s'", self._current_phase)
            else:
                # Last phase complete - we'll stop soon based on max_questions
                logger.info("Orchestrator: All phases complete.")
        except ValueError:
            self._current_phase = "core"
            self._questions_in_phase = 0
            self._weak_answers_in_phase = 0
            self._strong_answers_in_phase = 0
            self._topic_depth = 0
