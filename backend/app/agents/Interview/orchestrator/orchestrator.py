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

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.Interview.prompts import (
    BEHAVIOR_RESPONSES,
    GREETING_TEMPLATE,
)
from app.agents.Interview.sub_agents.profile_intelligence.agent import analyze_profile
from app.agents.Interview.sub_agents.question_generator.agent import generate_question
from app.agents.Interview.sub_agents.answer_evaluator.agent import evaluate_answer
from app.agents.Interview.sub_agents.memory_agent.agent import update_memory
from app.agents.Interview.sub_agents.feedback_agent.agent import generate_report
from app.core.config import settings

logger = logging.getLogger(__name__)


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
    ) -> None:
        self.student_id = student_id
        self.session_id = session_id
        self.db = db
        self.llm = llm
        self.student_name = student_name
        self.state: InterviewState = InterviewState.INIT
        self._profile_context: str = ""
        self._skill_summary: str = ""
        self._current_difficulty: str = "medium"
        self._question_count: int = 0
        self._max_questions: int = settings.MAX_QUESTIONS_PER_SESSION
        self._last_question: str = ""
        self._last_answer_summary: str = ""
        self._last_behavior: str = "neutral"

    def set_state(self, state: InterviewState) -> None:
        """Manually set the orchestrator state."""
        self.state = state

    def set_max_questions(self, max_q: int) -> None:
        """Override the maximum question count."""
        self._max_questions = max_q

    def set_question_count(self, count: int) -> None:
        """Restore question count (for session resumption)."""
        self._question_count = count

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

        # ── INIT → PROFILING → GREETING + FIRST QUESTION ─────────────────
        if self.state == InterviewState.INIT:
            try:
                self.state = InterviewState.PROFILING
                profile_data = await analyze_profile(
                    self.student_id, self.db, self.llm
                )
                skills_list = profile_data.get("skills", [])
                self._skill_summary = ", ".join(skills_list) if skills_list else "general topics"
                domains_str = ", ".join(profile_data.get("domains", []))
                exp = profile_data.get("experience_level", "junior")
                self._profile_context = (
                    f"Candidate skills: {self._skill_summary}. "
                    f"Domains: {domains_str}. "
                    f"Experience level: {exp}."
                )

                # Generate human greeting
                greeting = GREETING_TEMPLATE.format(
                    student_name=self.student_name,
                    skills=self._skill_summary,
                )

                # Generate first question
                self.state = InterviewState.QUESTIONING
                question_data = await generate_question(
                    context=self._profile_context,
                    difficulty=self._current_difficulty,
                    llm=self.llm,
                    skill_summary=self._skill_summary,
                )
                self._last_question = question_data.get("question", "")
                self._question_count += 1

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
            if self._question_count >= self._max_questions:
                return await self._end_interview()

            try:
                question_data = await generate_question(
                    context=self._profile_context,
                    difficulty=self._current_difficulty,
                    llm=self.llm,
                    last_question=self._last_question,
                    last_answer_summary=self._last_answer_summary,
                    behavior=self._last_behavior,
                    skill_summary=self._skill_summary,
                )
                self._last_question = question_data.get("question", "")
                self._question_count += 1
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
                eval_data = await evaluate_answer(
                    question=self._last_question,
                    answer=last_answer,
                    llm=self.llm,
                )

                behavior = eval_data.get("behavior_flag", "neutral")
                self._last_behavior = behavior

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
                    answer=last_answer,
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

                self.state = InterviewState.QUESTIONING
                return {
                    "next_agent": "answer_evaluator",
                    "difficulty": self._current_difficulty,
                    "action": "ask_question",
                    "data": {
                        "evaluation": eval_data,
                        "memory": memory_data,
                        "agent_response": agent_response,
                    },
                }
            except Exception as e:
                logger.error("Orchestrator: Evaluation or Memory update failed: %s", e)
                return {"action": "error", "message": str(e)}

        # ── ENDED ────────────────────────────────────────────────────────
        if self.state == InterviewState.ENDED:
            report = await generate_report(
                session_id=self.session_id,
                db=self.db,
                llm=self.llm,
            )
            return {
                "next_agent": "feedback_agent",
                "difficulty": self._current_difficulty,
                "action": "end",
                "data": {"report": report},
            }

        # Fallback
        return {
            "next_agent": "none",
            "difficulty": self._current_difficulty,
            "action": "end",
            "data": {},
        }

    async def _end_interview(self) -> Dict[str, Any]:
        """Transition to ENDED and generate the final report."""
        self.state = InterviewState.ENDED
        report = await generate_report(
            session_id=self.session_id,
            db=self.db,
            llm=self.llm,
        )
        return {
            "next_agent": "feedback_agent",
            "difficulty": self._current_difficulty,
            "action": "end",
            "data": {"report": report},
        }

    @staticmethod
    def _get_behavior_response(
        behavior: str,
        is_correct: bool,
        has_answer: bool,
    ) -> str:
        """Return a behavior-reactive response (no LLM call — template-based)."""
        if not has_answer:
            return BEHAVIOR_RESPONSES["no_answer"]

        key = f"{behavior}_{'correct' if is_correct else 'incorrect'}"
        return BEHAVIOR_RESPONSES.get(key, BEHAVIOR_RESPONSES["neutral_correct"])
