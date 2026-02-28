"""
Interview Service Layer.
Orchestrates the full interview flow behind each route, calling
the orchestrator and sub-agents, and persisting results to the DB.

Updated with:
- Controlled Yes/No greeting handshake
- Resume-aware question generation
- Interview history endpoints
- JWT auth (student_id from token)
- Behavior-reactive agent responses
- Context-aware follow-up questions
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import get_llm
from app.agents.Interview.prompts import (
    BEHAVIOR_RESPONSES,
    GREETING_TEMPLATE,
    GREETING_COMFORTABLE_YES,
    GREETING_COMFORTABLE_NO,
    GREETING_START_NO,
)
from app.agents.Interview.sub_agents.answer_evaluator.agent import evaluate_answer
from app.agents.Interview.sub_agents.memory_agent.agent import update_memory
from app.agents.Interview.sub_agents.question_generator.agent import generate_question
from app.agents.Interview.sub_agents.profile_intelligence.agent import analyze_profile
from app.agents.Interview.sub_agents.feedback_agent.agent import generate_report
from app.api.ai.agents.interview.schema import (
    EndInterviewResponse,
    EvaluationOutput,
    FeedbackOutput,
    GreetingResponse,
    InterviewConfigResponse,
    InterviewHistoryItem,
    InterviewHistoryResponse,
    InterviewReportResponse,
    MemoryOutput,
    NextQuestionResponse,
    ProfileOutput,
    QuestionOutput,
    SessionDetailResponse,
    SessionQuestionAnswer,
    StartInterviewResponse,
    SubmitAnswerResponse,
)
from app.core.config import settings
from app.core.llm import get_llm
from app.models.interview import (
    Answer,
    AnswerScore,
    BehaviorFlag,
    Difficulty,
    InterviewMemory,
    InterviewReport,
    InterviewSession,
    Question,
    QuestionType,
    SessionStatus,
)
from app.services.pipeline_service import attach_session_to_pipeline, mark_pipeline_ai_completed

logger = logging.getLogger(__name__)


class InterviewService:
    """Business logic for the interview endpoints."""

    # ── POST /interview/start ─────────────────────────────────────────────
    # Step 1: Create session, return greeting only (NO LLM call)

    @staticmethod
    async def start_interview(
        student_id: UUID,
        student_name: str,
        job_role: str,
        db: AsyncSession,
    ) -> StartInterviewResponse:
        """Create a session and return the greeting. No LLM call yet."""

        # 1. Create the session record
        session = InterviewSession(
            student_id=student_id,
            job_role=job_role,
            status=SessionStatus.ACTIVE,
            current_difficulty=Difficulty.MEDIUM,
        )
        db.add(session)
        await db.flush()

        await attach_session_to_pipeline(db=db, student_id=student_id, session_id=session.session_id)

        logger.info(
            "InterviewService: created session %s for student %s",
            session.session_id, student_id,
        )

        # 2. Return the greeting (no LLM, no question yet)
        greeting = GREETING_TEMPLATE.format(student_name=student_name)

        return StartInterviewResponse(
            session_id=session.session_id,
            status="greeting",
            student_name=student_name,
            greeting=greeting,
        )

    # ── POST /interview/greet ─────────────────────────────────────────────
    # Steps 2-5: Handle the Yes/No greeting handshake

    @staticmethod
    async def respond_greeting(
        student_id: UUID,
        student_name: str,
        session_id: UUID,
        answer: str,
        db: AsyncSession,
    ) -> GreetingResponse:
        """Handle Yes/No responses during the greeting handshake."""

        # Fetch session
        sess_result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
                InterviewSession.student_id == student_id,
            )
        )
        session = sess_result.scalar_one_or_none()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Count existing questions to determine greeting step
        q_count_result = await db.execute(
            select(func.count()).select_from(Question).where(
                Question.session_id == session_id
            )
        )
        q_count = q_count_result.scalar() or 0

        normalized = answer.strip().lower()
        is_yes = normalized in ("yes", "y", "yeah", "yep", "sure", "ok", "okay")

        # ── Determine which step we are in ─────────────────────────────
        # If q_count == 0 and session total_questions == 0, we're still in greeting.
        # We use session.total_questions as a state marker:
        #   total_questions == 0 → "are you comfortable?" step
        #   total_questions == -1 → "can we start?" step (marker)

        if session.total_questions == 0:
            # Step 1 response: "Are you comfortable?"
            if is_yes:
                # Mark that we've moved to "confirm start" step
                session.total_questions = -1  # marker for confirm step
                await db.flush()
                return GreetingResponse(
                    agent_message=GREETING_COMFORTABLE_YES,
                    next_step="confirm_start",
                    session_id=session_id,
                )
            else:
                # Close the session
                session.status = SessionStatus.CANCELLED
                session.end_time = datetime.utcnow()
                await db.flush()
                return GreetingResponse(
                    agent_message=GREETING_COMFORTABLE_NO,
                    next_step="session_closed",
                    session_id=session_id,
                )

        elif session.total_questions == -1:
            # Step 3 response: "Can we start the interview?"
            if is_yes:
                # Reset total_questions to 0 for real usage
                session.total_questions = 0
                await db.flush()

                # NOW run profile analysis + generate first question
                llm = get_llm()
                profile_data = await analyze_profile(student_id, db, llm)

                # Generate the first question (resume-aware)
                has_projects = profile_data.get("has_projects", False)
                project_summary = profile_data.get("project_summary", "")
                skills_list = profile_data.get("skills", [])
                skill_summary = ", ".join(skills_list) if skills_list else "general topics"

                q_data = await generate_question(
                    context="",
                    difficulty="medium",
                    llm=llm,
                    skill_summary=skill_summary,
                    resume_has_projects=has_projects,
                    resume_project_summary=project_summary,
                    is_first_question=True,
                )

                # Persist the question
                q = Question(
                    session_id=session_id,
                    question_text=q_data.get("question", ""),
                    question_order=1,
                    topic=q_data.get("topic", "general"),
                    difficulty=Difficulty(q_data.get("difficulty", "medium")),
                    question_type=QuestionType.TECHNICAL,
                )
                db.add(q)
                await db.flush()

                return GreetingResponse(
                    agent_message=f"Let's begin! Here's your first question.",
                    next_step="first_question",
                    session_id=session_id,
                    profile=ProfileOutput(**profile_data),
                    first_question=QuestionOutput(
                        question_id=q.question_id,
                        question=q.question_text,
                        topic=q.topic,
                        difficulty=q.difficulty.value if isinstance(q.difficulty, Difficulty) else q.difficulty,
                    ),
                )
            else:
                # Close the session
                session.status = SessionStatus.CANCELLED
                session.end_time = datetime.utcnow()
                session.total_questions = 0
                await db.flush()
                return GreetingResponse(
                    agent_message=GREETING_START_NO,
                    next_step="session_closed",
                    session_id=session_id,
                )

        # Fallback (shouldn't reach here normally)
        return GreetingResponse(
            agent_message="Something went wrong. Please start a new session.",
            next_step="session_closed",
            session_id=session_id,
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
        """Evaluate the answer, classify behavior, update memory, and decide next step."""
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

        # Evaluate (now includes behavior classification)
        eval_data = await evaluate_answer(
            question=question.question_text,
            answer=answer_text,
            llm=llm,
        )

        behavior_flag = eval_data.get("behavior_flag", "neutral")
        technical_score = eval_data.get("technical_score", 5)

        # Compute overall score and persist with behavior
        overall = round(
            (eval_data["clarity"] + eval_data["depth"] + eval_data["confidence"]) / 3,
            2,
        )

        # Map behavior string to enum
        try:
            behavior_enum = BehaviorFlag(behavior_flag)
        except ValueError:
            behavior_enum = BehaviorFlag.NEUTRAL

        score = AnswerScore(
            answer_id=answer.answer_id,
            clarity=eval_data["clarity"],
            depth=eval_data["depth"],
            confidence=eval_data["confidence"],
            technical_score=technical_score,
            overall_score=overall,
            behavior_flag=behavior_enum,
        )
        db.add(score)

        # Update memory with behavior
        memory_data = await update_memory(
            session_id=session_id,
            answer=answer_text,
            db=db,
            llm=llm,
            behavior=behavior_flag,
        )

        # Generate behavior-reactive agent response
        is_correct = technical_score >= 5
        has_answer = bool(answer_text.strip())
        if not has_answer:
            agent_response = BEHAVIOR_RESPONSES["no_answer"]
        else:
            key = f"{behavior_flag}_{'correct' if is_correct else 'incorrect'}"
            agent_response = BEHAVIOR_RESPONSES.get(key, BEHAVIOR_RESPONSES["neutral_correct"])

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
            select(func.count()).select_from(Question).where(
                Question.session_id == session_id
            )
        )
        q_count = q_count_result.scalar() or 0

        if q_count >= settings.MAX_QUESTIONS_PER_SESSION:
            next_action = "end"
            next_question = None
        else:
            next_action = "ask_question"
            # Generate next question with context-aware follow-up
            q_data = await generate_question(
                context=memory_data.get("summary", ""),
                difficulty=next_diff,
                llm=llm,
                last_question=question.question_text,
                last_answer_summary=memory_data.get("summary", ""),
                behavior=behavior_flag,
                skill_summary=memory_data.get("summary", ""),
            )
            q_obj = Question(
                session_id=session_id,
                question_text=q_data.get("question", ""),
                question_order=q_count + 1,
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
            agent_response=agent_response,
            behavior_flag=behavior_flag,
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

        # Count total questions
        q_count_result = await db.execute(
            select(func.count()).select_from(Question).where(
                Question.session_id == session_id
            )
        )
        session.total_questions = q_count_result.scalar() or 0

        # Generate report
        report_data = await generate_report(
            session_id=session_id,
            db=db,
            llm=llm,
        )

        await db.flush()

        await mark_pipeline_ai_completed(db=db, session_id=session_id)

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

        # Get session for communication score
        sess_result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
            )
        )
        session = sess_result.scalar_one_or_none()

        return InterviewReportResponse(
            session_id=session_id,
            final_score=report.final_score,
            communication_score=session.communication_score if session else 0.0,
            strengths=list(report.strengths) if report.strengths else [],
            weaknesses=list(report.weaknesses) if report.weaknesses else [],
            recommendation=report.recommendation,
        )

    # ── GET /interview/config ─────────────────────────────────────────────

    @staticmethod
    async def get_config() -> InterviewConfigResponse:
        """Return client-side interview configuration."""
        return InterviewConfigResponse(
            max_questions=settings.MAX_QUESTIONS_PER_SESSION,
            answer_timeout=settings.ANSWER_TIMEOUT,
            silence_timeout=settings.VOICE_SILENCE_TIMEOUT,
        )

    # ── GET /interview/history ────────────────────────────────────────────

    @staticmethod
    async def get_history(
        student_id: UUID,
        db: AsyncSession,
    ) -> InterviewHistoryResponse:
        """Fetch all interview sessions for the logged-in student."""
        result = await db.execute(
            select(InterviewSession)
            .where(InterviewSession.student_id == student_id)
            .order_by(InterviewSession.start_time.desc())
        )
        sessions = result.scalars().all()

        items = []
        for s in sessions:
            # Try to get recommendation from report
            rec = None
            if s.status == SessionStatus.COMPLETED:
                rpt_result = await db.execute(
                    select(InterviewReport.recommendation).where(
                        InterviewReport.session_id == s.session_id
                    )
                )
                rec = rpt_result.scalar_one_or_none()

            items.append(InterviewHistoryItem(
                session_id=s.session_id,
                job_role=s.job_role,
                status=s.status.value if isinstance(s.status, SessionStatus) else str(s.status),
                started_at=s.start_time,
                ended_at=s.end_time,
                total_questions=max(s.total_questions, 0) if s.total_questions else 0,
                overall_score=s.overall_score,
                recommendation=rec,
            ))

        return InterviewHistoryResponse(sessions=items)

    # ── GET /interview/session/{session_id} ───────────────────────────────

    @staticmethod
    async def get_session_detail(
        student_id: UUID,
        session_id: UUID,
        db: AsyncSession,
    ) -> SessionDetailResponse:
        """Fetch questions and answers for a specific session (own sessions only)."""
        # Verify ownership
        sess_result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
                InterviewSession.student_id == student_id,
            )
        )
        session = sess_result.scalar_one_or_none()
        if not session:
            raise ValueError("Session not found or access denied")

        # Get recommendation
        rec = None
        if session.status == SessionStatus.COMPLETED:
            rpt_result = await db.execute(
                select(InterviewReport.recommendation).where(
                    InterviewReport.session_id == session_id
                )
            )
            rec = rpt_result.scalar_one_or_none()

        # Fetch questions with answers
        q_result = await db.execute(
            select(Question)
            .where(Question.session_id == session_id)
            .order_by(Question.question_order)
        )
        questions = q_result.scalars().all()

        qa_list = []
        for q in questions:
            # Get the answer for this question
            ans_result = await db.execute(
                select(Answer).where(Answer.question_id == q.question_id)
            )
            ans = ans_result.scalar_one_or_none()

            # Get the score
            score_val = None
            if ans:
                sc_result = await db.execute(
                    select(AnswerScore.overall_score).where(
                        AnswerScore.answer_id == ans.answer_id
                    )
                )
                score_val = sc_result.scalar_one_or_none()

            qa_list.append(SessionQuestionAnswer(
                question_order=q.question_order,
                question_text=q.question_text,
                topic=q.topic,
                difficulty=q.difficulty.value if isinstance(q.difficulty, Difficulty) else str(q.difficulty),
                answer_text=ans.answer_text if ans else None,
                score=score_val,
            ))

        return SessionDetailResponse(
            session_id=session.session_id,
            job_role=session.job_role,
            status=session.status.value if isinstance(session.status, SessionStatus) else str(session.status),
            started_at=session.start_time,
            ended_at=session.end_time,
            total_questions=max(session.total_questions, 0) if session.total_questions else 0,
            overall_score=session.overall_score,
            recommendation=rec,
            questions=qa_list,
        )

    # ── DELETE /interview/session/{session_id} ────────────────────────────

    @staticmethod
    async def delete_session(
        student_id: UUID,
        session_id: UUID,
        db: AsyncSession,
    ) -> None:
        """Delete an interview session and all its related data (answers, scores, etc)."""
        # Verify ownership
        sess_result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
                InterviewSession.student_id == student_id,
            )
        )
        session = sess_result.scalar_one_or_none()
        if not session:
            raise ValueError("Session not found or access denied")

        await db.delete(session)
        await db.commit()
