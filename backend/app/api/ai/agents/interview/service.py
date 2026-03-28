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
    get_feedback_for_answer,
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


async def _get_job_description_from_session(
    db: AsyncSession,
    session_id: UUID,
) -> str:
    """Fetch job description from the job associated with this interview session via pipeline."""
    from app.models.pipeline import InterviewPipeline
    from app.models.job import Job
    
    # Find pipeline entry with this session
    result = await db.execute(
        select(InterviewPipeline).where(
            InterviewPipeline.ai_session_id == session_id
        )
    )
    pipeline = result.scalar_one_or_none()
    
    if not pipeline:
        return ""
    
    # Fetch job description
    job_result = await db.execute(
        select(Job).where(Job.id == pipeline.job_id)
    )
    job = job_result.scalar_one_or_none()
    
    if job:
        return job.description or ""
    return ""


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
        await db.commit()

        logger.info("start_interview: created session_id=%s for student_id=%s", session.session_id, student_id)

        try:
            logger.info("start_interview: calling attach_session_to_pipeline for session_id=%s", session.session_id)
            await attach_session_to_pipeline(db=db, student_id=student_id, session_id=session.session_id)
            logger.info("start_interview: attach_session_to_pipeline returned for session_id=%s", session.session_id)
        except Exception:
            logger.exception(
                "InterviewService: failed to attach session %s to pipeline for student %s",
                session.session_id,
                student_id,
            )

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

                # Fetch job description for question generation
                job_description = await _get_job_description_from_session(db, session_id)

                q_data = await generate_question(
                    context="",
                    difficulty="medium",
                    llm=llm,
                    skill_summary=skill_summary,
                    resume_has_projects=has_projects,
                    resume_project_summary=project_summary,
                    is_first_question=True,
                    job_description=job_description,
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
        # Pass current session difficulty so evaluator can recommend decrease
        sess_result_pre = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
            )
        )
        session_pre = sess_result_pre.scalar_one()
        current_diff = session_pre.current_difficulty
        if isinstance(current_diff, Difficulty):
            current_diff = current_diff.value

        eval_data = await evaluate_answer(
            question=question.question_text,
            answer=answer_text,
            llm=llm,
            difficulty=current_diff,
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

        # Generate behavior-reactive agent response using weighted scores
        weighted = eval_data.get("weighted_score", 0.5)
        has_answer = bool(answer_text.strip())
        answer_type = eval_data.get("answer_type", "VALID")
        agent_response = get_feedback_for_answer(weighted, has_answer, answer_type)

        # Determine next difficulty using code logic (NOT trusting the LLM)
        # This ensures difficulty always adjusts based on actual performance
        weighted = eval_data.get("weighted_score", 0.5)
        if weighted < 0.4:
            next_diff = "easy"
        elif weighted > 0.7:
            next_diff = "hard"
        else:
            next_diff = "medium"
        
        # Override in eval_data too so frontend gets consistent info
        eval_data["next_difficulty"] = next_diff
        
        logger.info(
            "submit_answer: weighted_score=%.2f → next_difficulty=%s",
            weighted, next_diff,
        )
        
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
            # Fetch job description for follow-up questions
            job_description = await _get_job_description_from_session(db, session_id)
            # Generate next question with context-aware follow-up
            q_data = await generate_question(
                context=memory_data.get("summary", ""),
                difficulty=next_diff,
                llm=llm,
                last_question=question.question_text,
                last_answer_summary=memory_data.get("summary", ""),
                behavior=behavior_flag,
                skill_summary=memory_data.get("summary", ""),
                job_description=job_description,
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
        logger.info("end_interview: generating report for session_id=%s", session_id)
        report_data = await generate_report(
            session_id=session_id,
            db=db,
            llm=llm,
        )
        logger.info("end_interview: report generated for session_id=%s, data=%s", session_id, report_data)

        # Get proctoring summary from DetectorAgent
        try:
            from app.agents.Interview.sub_agents.detector_agent.agent import DetectorAgent
            detector = DetectorAgent(db)
            proctor_summary = await detector.get_proctoring_summary(session_id)
            report_data["proctoring_summary"] = proctor_summary
            logger.info("end_interview: proctoring summary for session_id=%s — integrity=%.2f, violations=%d",
                       session_id, proctor_summary.get("integrity_score", 1.0), proctor_summary.get("total_violations", 0))
        except Exception as exc:
            logger.warning("Proctoring summary failed (non-fatal): %s", exc)

        await db.flush()
        logger.info("end_interview: flushed DB for session_id=%s", session_id)

        logger.info("end_interview: calling mark_pipeline_ai_completed for session_id=%s", session_id)

        try:
            await mark_pipeline_ai_completed(db=db, session_id=session_id)
            logger.info("end_interview: mark_pipeline_ai_completed returned for session_id=%s", session_id)
        except Exception as exc:
            logger.warning("mark_pipeline_ai_completed failed (non-fatal): %s", exc)

        # Commit all changes — ensure COMPLETED status persists
        await db.commit()
        logger.info("end_interview: committed session_id=%s as COMPLETED", session_id)

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
        logger.info("get_report called for session_id=%s", session_id)

        result = await db.execute(
            select(InterviewReport).where(
                InterviewReport.session_id == session_id,
            )
        )
        report = result.scalar_one_or_none()
        logger.info("report query result: %s", report)
        if report is None:
            logger.warning("No report found for session %s; creating fallback report", session_id)

            avg_score_result = await db.execute(
                select(func.avg(AnswerScore.overall_score))
                .select_from(Answer)
                .join(AnswerScore, AnswerScore.answer_id == Answer.answer_id, isouter=True)
                .where(Answer.session_id == session_id)
            )
            avg_score = avg_score_result.scalar()

            sess_result = await db.execute(
                select(InterviewSession).where(InterviewSession.session_id == session_id)
            )
            session = sess_result.scalar_one_or_none()

            computed_final_score = None
            if avg_score is not None:
                computed_final_score = float(avg_score)
            elif session and session.overall_score is not None:
                computed_final_score = float(session.overall_score)
            else:
                computed_final_score = 0.0

            if session and session.overall_score is None:
                session.overall_score = computed_final_score

            report = InterviewReport(
                session_id=session_id,
                final_score=computed_final_score,
                strengths=[],
                weaknesses=[],
                recommendation="Report not available. Showing computed score.",
            )
            db.add(report)
            await db.flush()

        # Get session for communication score
        sess_result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
            )
        )
        session = sess_result.scalar_one_or_none()
        logger.info("session query result: %s", session)

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

    # ── DELETE /interview/history/all ──────────────────────────────────

    @staticmethod
    async def delete_all_sessions(
        student_id: UUID,
        db: AsyncSession,
    ) -> int:
        """Delete ALL interview sessions for this student. Returns count deleted."""
        result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.student_id == student_id,
            )
        )
        sessions = list(result.scalars().all())
        count = len(sessions)

        for session in sessions:
            await db.delete(session)

        await db.commit()
        logger.info("Deleted %d interview sessions for student %s", count, student_id)
        return count
