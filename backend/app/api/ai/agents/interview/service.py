"""
Interview Service Layer.
Orchestrates the full interview flow behind each route, calling
the orchestrator and sub-agents, and persisting results to the DB.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.Interview.llm_provider import get_llm
from app.agents.Interview.orchestrator.orchestrator import (
    InterviewOrchestrator,
    InterviewState,
)
from app.agents.Interview.sub_agents.answer_evaluator.agent import evaluate_answer
from app.agents.Interview.sub_agents.memory_agent.agent import update_memory
from app.agents.Interview.sub_agents.question_generator.agent import generate_question
from app.agents.Interview.sub_agents.speech_to_text.agent import transcribe
from app.agents.Interview.sub_agents.text_to_speech.agent import synthesize
from app.agents.Interview.sub_agents.feedback_agent.agent import generate_report
from app.api.ai.agents.interview.schema import (
    EndInterviewResponse,
    EvaluationOutput,
    FeedbackOutput,
    InterviewReportResponse,
    MemoryOutput,
    NextQuestionResponse,
    ProfileOutput,
    QuestionOutput,
    StartInterviewResponse,
    SubmitAnswerResponse,
)
from app.models.interview import (
    Answer,
    AnswerScore,
    Difficulty,
    InterviewReport,
    InterviewSession,
    Question,
    QuestionType,
    SessionStatus,
)

logger = logging.getLogger(__name__)


class InterviewService:
    """Business logic for the five interview endpoints."""

    # ── POST /interview/start ─────────────────────────────────────────────

    @staticmethod
    async def start_interview(
        student_id: UUID,
        job_role: str,
        db: AsyncSession,
    ) -> StartInterviewResponse:
        """Create a session, profile the student, and return the first question."""
        llm = get_llm()

        # 1. Create the session record
        session = InterviewSession(
            student_id=student_id,
            job_role=job_role,
            status=SessionStatus.ACTIVE,
            current_difficulty=Difficulty.MEDIUM,
        )
        db.add(session)
        await db.flush()  # populate session_id

        logger.info("InterviewService: created session %s for student %s",
                     session.session_id, student_id)

        # 2. Run orchestrator from INIT (profiles + first question)
        orchestrator = InterviewOrchestrator(
            student_id=student_id,
            session_id=session.session_id,
            db=db,
            llm=llm,
        )
        result = await orchestrator.step()

        profile_data = result["data"].get("profile", {})
        question_data = result["data"].get("question", {})

        # 3. Persist the first question
        q = Question(
            session_id=session.session_id,
            question_text=question_data.get("question", ""),
            topic=question_data.get("topic", "general"),
            difficulty=Difficulty(question_data.get("difficulty", "medium")),
            question_type=QuestionType.TECHNICAL,
        )
        db.add(q)
        await db.flush()

        return StartInterviewResponse(
            session_id=session.session_id,
            status="active",
            profile=ProfileOutput(**profile_data),
            first_question=QuestionOutput(
                question_id=q.question_id,
                question=q.question_text,
                topic=q.topic,
                difficulty=q.difficulty.value if isinstance(q.difficulty, Difficulty) else q.difficulty,
            ),
        )

    # ── POST /interview/next ──────────────────────────────────────────────

    @staticmethod
    async def next_question(
        student_id: UUID,
        session_id: UUID,
        db: AsyncSession,
    ) -> NextQuestionResponse:
        """Generate and return the next question for the active session."""
        llm = get_llm()

        # Look up the session
        sess_result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
            )
        )
        session = sess_result.scalar_one()

        # Count existing questions
        q_count_result = await db.execute(
            select(Question).where(Question.session_id == session_id)
        )
        existing_questions = list(q_count_result.scalars().all())
        q_count = len(existing_questions)

        orchestrator = InterviewOrchestrator(
            student_id=student_id,
            session_id=session_id,
            db=db,
            llm=llm,
        )
        orchestrator.set_state(InterviewState.QUESTIONING)
        orchestrator.set_question_count(q_count)
        current_diff = session.current_difficulty
        if isinstance(current_diff, Difficulty):
            orchestrator._current_difficulty = current_diff.value
        else:
            orchestrator._current_difficulty = str(current_diff)

        result = await orchestrator.step()
        question_data = result["data"].get("question", {})

        # Persist
        q = Question(
            session_id=session_id,
            question_text=question_data.get("question", ""),
            topic=question_data.get("topic", "general"),
            difficulty=Difficulty(question_data.get("difficulty", "medium")),
            question_type=QuestionType.TECHNICAL,
        )
        db.add(q)
        await db.flush()

        return NextQuestionResponse(
            question=QuestionOutput(
                question_id=q.question_id,
                question=q.question_text,
                topic=q.topic,
                difficulty=q.difficulty.value if isinstance(q.difficulty, Difficulty) else q.difficulty,
            ),
            difficulty=result.get("difficulty", "medium"),
            question_number=q_count + 1,
        )

    # ── POST /interview/answer ────────────────────────────────────────────

    @staticmethod
    async def submit_answer(
        student_id: UUID,
        session_id: UUID,
        question_id: UUID,
        answer_text: str,
        audio_path: Optional[str],
        db: AsyncSession,
    ) -> SubmitAnswerResponse:
        """Evaluate the answer, update memory, and decide the next step."""
        llm = get_llm()

        # Fetch the question
        q_result = await db.execute(
            select(Question).where(Question.question_id == question_id)
        )
        question = q_result.scalar_one()

        # Persist the answer
        answer = Answer(
            session_id=session_id,
            question_id=question_id,
            answer_text=answer_text,
            audio_path=audio_path,
        )
        db.add(answer)
        await db.flush()

        # Evaluate
        eval_data = await evaluate_answer(
            question=question.question_text,
            answer=answer_text,
            llm=llm,
        )

        # Compute overall score and persist
        overall = round(
            (eval_data["clarity"] + eval_data["depth"] + eval_data["confidence"]) / 3,
            2,
        )
        score = AnswerScore(
            answer_id=answer.answer_id,
            clarity=eval_data["clarity"],
            depth=eval_data["depth"],
            confidence=eval_data["confidence"],
            overall_score=overall,
        )
        db.add(score)

        # Update memory
        memory_data = await update_memory(
            session_id=session_id,
            answer=answer_text,
            db=db,
            llm=llm,
        )

        # Update session difficulty
        next_diff = eval_data.get("next_difficulty", "medium")
        session_result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
            )
        )
        session = session_result.scalar_one()
        session.current_difficulty = Difficulty(next_diff)
        await db.flush()

        # Count questions to decide next action
        q_count_result = await db.execute(
            select(Question).where(Question.session_id == session_id)
        )
        q_count = len(list(q_count_result.scalars().all()))

        from app.core.config import settings

        if q_count >= settings.MAX_QUESTIONS_PER_SESSION:
            next_action = "end"
            next_question = None
        else:
            next_action = "ask_question"
            # Auto-generate the next question
            q_data = await generate_question(
                context=memory_data.get("summary", ""),
                difficulty=next_diff,
                llm=llm,
            )
            q_obj = Question(
                session_id=session_id,
                question_text=q_data.get("question", ""),
                topic=q_data.get("topic", "general"),
                difficulty=Difficulty(q_data.get("difficulty", "medium")),
                question_type=QuestionType.TECHNICAL,
            )
            db.add(q_obj)
            await db.flush()
            next_question = QuestionOutput(
                question_id=q_obj.question_id,
                question=q_obj.question_text,
                topic=q_obj.topic,
                difficulty=q_obj.difficulty.value if isinstance(q_obj.difficulty, Difficulty) else q_obj.difficulty,
            )

        return SubmitAnswerResponse(
            evaluation=EvaluationOutput(**eval_data),
            memory=MemoryOutput(**memory_data),
            next_action=next_action,
            next_difficulty=next_diff,
            next_question=next_question,
        )

    # ── POST /interview/end ───────────────────────────────────────────────

    @staticmethod
    async def end_interview(
        student_id: UUID,
        session_id: UUID,
        db: AsyncSession,
    ) -> EndInterviewResponse:
        """End the interview session and generate the final report."""
        llm = get_llm()

        # Update session status
        sess_result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
            )
        )
        session = sess_result.scalar_one()
        session.status = SessionStatus.COMPLETED
        session.end_time = datetime.utcnow()

        # Generate report
        report_data = await generate_report(
            session_id=session_id,
            db=db,
            llm=llm,
        )

        await db.flush()

        return EndInterviewResponse(
            session_id=session_id,
            status="completed",
            report=FeedbackOutput(**report_data),
        )

    # ── GET /interview/report/{session_id} ────────────────────────────────

    @staticmethod
    async def get_report(
        session_id: UUID,
        db: AsyncSession,
    ) -> InterviewReportResponse:
        """Fetch the saved report for a completed interview session."""
        result = await db.execute(
            select(InterviewReport).where(
                InterviewReport.session_id == session_id,
            )
        )
        report = result.scalar_one_or_none()
        if report is None:
            raise ValueError(f"No report found for session {session_id}")

        return InterviewReportResponse(
            session_id=session_id,
            final_score=report.final_score,
            strengths=list(report.strengths) if report.strengths else [],
            weaknesses=list(report.weaknesses) if report.weaknesses else [],
            recommendation=report.recommendation,
        )
