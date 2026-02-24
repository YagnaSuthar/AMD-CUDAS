"""
Interview Orchestrator — runtime module.
Implements the interview state machine and dispatches to sub-agents.

States: INIT → PROFILING → QUESTIONING → EVALUATING → MEMORY_UPDATE → ENDED
"""

import enum
import logging
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.Interview.sub_agents.profile_intelligence.agent import analyze_profile
from app.agents.Interview.sub_agents.question_generator.agent import generate_question
from app.agents.Interview.sub_agents.answer_evaluator.agent import evaluate_answer
from app.agents.Interview.sub_agents.memory_agent.agent import update_memory
from app.agents.Interview.sub_agents.feedback_agent.agent import generate_report

logger = logging.getLogger(__name__)


class InterviewState(str, enum.Enum):
    """States in the interview state machine."""
    INIT = "init"
    PROFILING = "profiling"
    QUESTIONING = "questioning"
    EVALUATING = "evaluating"
    MEMORY_UPDATE = "memory_update"
    ENDED = "ended"


class InterviewOrchestrator:
    """
    Stateful orchestrator that manages the flow of an interview session.

    Each call to ``step()`` determines the next agent to invoke and
    returns an action indicating what the caller should do next.
    """

    def __init__(
        self,
        student_id: UUID,
        session_id: UUID,
        db: AsyncSession,
        llm: Any,
    ) -> None:
        self.student_id = student_id
        self.session_id = session_id
        self.db = db
        self.llm = llm
        self.state: InterviewState = InterviewState.INIT
        self._profile_context: str = ""
        self._current_difficulty: str = "medium"
        self._question_count: int = 0
        self._max_questions: int = 15
        self._last_question: str = ""

    def set_state(self, state: InterviewState) -> None:
        """Manually set the orchestrator state (used by terminal test runner)."""
        self.state = state

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

        # ── INIT → PROFILING ─────────────────────────────────────────────
        if self.state == InterviewState.INIT:
            try:
                self.state = InterviewState.PROFILING
                profile_data = await analyze_profile(
                    self.student_id, self.db, self.llm
                )
                skills_str = ", ".join(profile_data.get("skills", []))
                domains_str = ", ".join(profile_data.get("domains", []))
                exp = profile_data.get("experience_level", "junior")
                self._profile_context = (
                    f"Candidate skills: {skills_str}. "
                    f"Domains: {domains_str}. "
                    f"Experience level: {exp}."
                )

                # Immediately proceed to question generation
                self.state = InterviewState.QUESTIONING
                question_data = await generate_question(
                    context=self._profile_context,
                    difficulty=self._current_difficulty,
                    llm=self.llm,
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
                    },
                }
            except Exception as e:
                logger.error("Orchestrator: INIT failed: %s", e)
                self.state = InterviewState.INIT  # Reset so user can retry
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

        # ── EVALUATING (answer received → evaluate → update memory) ──────
        if self.state == InterviewState.EVALUATING:
            # This state is entered from the service layer after an answer
            try:
                eval_data = await evaluate_answer(
                    question=self._last_question,
                    answer=last_answer,
                    llm=self.llm,
                )

                # Update memory
                self.state = InterviewState.MEMORY_UPDATE
                memory_data = await update_memory(
                    session_id=self.session_id,
                    answer=last_answer,
                    db=self.db,
                    llm=self.llm,
                )

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

    def set_state(self, state: InterviewState) -> None:
        """Explicitly set the orchestrator state (used by service layer)."""
        self.state = state

    def set_max_questions(self, max_q: int) -> None:
        """Override the maximum question count."""
        self._max_questions = max_q

    def set_question_count(self, count: int) -> None:
        """Restore question count (for session resumption)."""
        self._question_count = count
