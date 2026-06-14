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

from sqlalchemy import select, func, cast, Integer
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
from app.agents.Interview.orchestrator.orchestrator import InterviewOrchestrator, InterviewState
from app.api.ai.agents.interview.schema import (
    EndInterviewResponse,
    EvaluationOutput,
    FeedbackOutput,
    GreetingResponse,
    InterviewConfigResponse,
    InterviewHistoryItem,
    InterviewHistoryResponse,
    InterviewReportResponse,
    InterviewSessionReportResponse,
    InterviewScoreBreakdown,
    InterviewReportQuestionItem,
    MemoryOutput,
    NextQuestionResponse,
    ProfileOutput,
    ProctoringViolationRequest,
    ProctoringViolationResponse,
    QuestionOutput,
    SessionDetailResponse,
    SessionQuestionAnswer,
    StartInterviewResponse,
    SubmitAnswerResponse,
)
from app.core.config import settings
from app.models.interview import (
    Answer,
    AnswerScore,
    BehaviorFlag,
    Difficulty,
    InterviewMemory,
    InterviewReport,
    InterviewSession,
    InterviewTurn,
    ProctoringViolation,
    Question,
    SessionStatus,
    Skill,
    StudentProfile,
)
from app.agents.Interview.report.report_builder import build_report
from app.services.pipeline_service import attach_session_to_pipeline, mark_pipeline_ai_completed
from app.core.modes import normalize_interview_mode

logger = logging.getLogger(__name__)


def _clamp_0_10(val: float) -> float:
    try:
        v = float(val)
    except Exception:
        v = 0.0
    return max(0.0, min(10.0, v))


def _safe_mean(values: list[float]) -> float:
    vals = [v for v in values if v is not None]
    if not vals:
        return 0.0
    return float(sum(vals) / len(vals))


def _is_dsa_like_turn(question: str, phase: str | None) -> bool:
    if (phase or "").strip().lower() in ("problem_solving", "dsa"):
        return True
    q = (question or "").lower()
    keywords = [
        "array",
        "linked list",
        "stack",
        "queue",
        "binary search",
        "two pointers",
        "sliding window",
        "hashmap",
        "heap",
        "priority queue",
        "tree",
        "graph",
        "bfs",
        "dfs",
        "dynamic programming",
        "dp",
        "recursion",
        "time complexity",
        "space complexity",
        "big o",
    ]
    return any(k in q for k in keywords)


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
        mode: str = "basic",
    ) -> StartInterviewResponse:
        """Create a session and return the greeting. No LLM call yet."""

        normalized_mode = normalize_interview_mode(mode)

        # 1. Create the session record
        session = InterviewSession(
            student_id=student_id,
            job_role=job_role,
            mode=normalized_mode,
            status=SessionStatus.ACTIVE,
            current_difficulty=Difficulty.MEDIUM,
        )
        db.add(session)
        await db.flush()
        await db.commit()

        logger.info(
            "start_interview: created session_id=%s for student_id=%s mode=%s",
            session.session_id,
            student_id,
            normalized_mode,
        )

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
        """Handle Yes/No responses during the greeting handshake.

        Uses InterviewOrchestrator.step(INIT) to generate the first question
        so phase tracking, RAG retrieval, and topic ordering all begin correctly.
        """

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

        normalized = answer.strip().lower()
        is_yes = normalized in ("yes", "y", "yeah", "yep", "sure", "ok", "okay")

        # ── Determine which step we are in ─────────────────────────────
        # We use session.total_questions as a state marker:
        #   total_questions == 0 → "are you comfortable?" step
        #   total_questions == -1 → "can we start?" step (marker)

        if session.total_questions == 0:
            # Step 1 response: "Are you comfortable?"
            if is_yes:
                session.total_questions = -1  # marker for confirm step
                await db.flush()
                return GreetingResponse(
                    agent_message=GREETING_COMFORTABLE_YES,
                    next_step="confirm_start",
                    session_id=session_id,
                )
            else:
                session.status = SessionStatus.CANCELLED
                session.end_time = datetime.utcnow()
                await db.flush()
                return GreetingResponse(
                    agent_message=GREETING_COMFORTABLE_NO,
                    next_step="session_closed",
                    session_id=session_id,
                )

        elif session.total_questions == -1:
            # Step 2 response: "Can we start the interview?"
            if is_yes:
                # Reset total_questions to 0 so the orchestrator owns the count
                session.total_questions = 0
                await db.flush()

                # ── Use InterviewOrchestrator (INIT) ─────────────────────
                # This ensures:
                #   • Phase starts at "resume"
                #   • RAG context is fetched for project-based Q1
                #   • _question_count & _questions_in_phase begin properly
                llm = get_llm()
                orchestrator = InterviewOrchestrator(
                    student_id=student_id,
                    session_id=session_id,
                    db=db,
                    llm=llm,
                    job_role=getattr(session, "job_role", "") or "",
                    mode=getattr(session, "mode", "basic") or "basic",
                )

                # If no resume/projects found, skip resume phase to core
                # (orchestrator INIT handles this internally)
                result = await orchestrator.step(last_answer="")

                if result.get("action") == "error":
                    raise RuntimeError(result.get("message", "Orchestrator INIT failed"))

                data = result.get("data", {})
                question_data = data.get("question", {})
                profile_data = data.get("profile", {})

                if not question_data or not question_data.get("question"):
                    raise RuntimeError("Orchestrator did not return a first question")

                # The orchestrator already persisted the InterviewTurn; fetch it
                turn_result = await db.execute(
                    select(InterviewTurn)
                    .where(InterviewTurn.session_id == session_id)
                    .order_by(InterviewTurn.timestamp.desc())
                    .limit(1)
                )
                turn = turn_result.scalar_one_or_none()

                if not turn:
                    raise RuntimeError("InterviewTurn not found after orchestrator INIT")

                # Commit: guarantee the first question turn is durable before returning to UI.
                await db.commit()

                logger.info(
                    "respond_greeting: first question generated via orchestrator "
                    "phase=%s topic=%s question='%s'",
                    getattr(orchestrator, "_current_phase", "n/a"),
                    getattr(orchestrator, "_current_topic", "n/a"),
                    turn.question,
                )

                profile_out = ProfileOutput(**profile_data) if profile_data else None

                return GreetingResponse(
                    agent_message="Let's begin! Here's your first question.",
                    next_step="first_question",
                    session_id=session_id,
                    profile=profile_out,
                    first_question=QuestionOutput(
                        question_id=str(turn.turn_id),
                        question=turn.question,
                        topic=question_data.get("topic", "resume"),
                        difficulty=(
                            turn.difficulty.value
                            if isinstance(turn.difficulty, Difficulty)
                            else str(turn.difficulty)
                        ),
                    ),
                )
            else:
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
        """Submit an answer via InterviewOrchestrator (state-driven)."""

        logger.info("[DEBUG] Received answer length: %d", len(answer_text))
        print("ANSWER API CALLED")
        print("SETTING STATE TO EVALUATING")
        print("CALLING ORCHESTRATOR STEP")

        llm = get_llm()

        sess_result = await db.execute(
            select(InterviewSession).where(InterviewSession.session_id == session_id)
        )
        session = sess_result.scalar_one_or_none()
        if session is None:
            raise RuntimeError("Session not found")

        mem_result = await db.execute(
            select(InterviewMemory).where(InterviewMemory.session_id == session_id)
        )
        memory = mem_result.scalar_one_or_none()

        orchestrator = InterviewOrchestrator(
            student_id=student_id,
            session_id=session_id,
            db=db,
            llm=llm,
            job_role=getattr(session, "job_role", "") or "",
            mode=getattr(session, "mode", "basic") or "basic",
        )


        # Restore continuity fields from DB so the orchestrator knows its phase
        turn_count_result = await db.execute(
            select(func.count()).select_from(InterviewTurn).where(
                InterviewTurn.session_id == session_id
            )
        )
        orchestrator._question_count = int(turn_count_result.scalar() or 0)

        if session is not None:
            cd = getattr(session, "current_difficulty", "medium")
            orchestrator._current_difficulty = cd.value if hasattr(cd, "value") else str(cd)

        if memory is not None:
            orchestrator._profile_context = memory.summary or ""
            orchestrator._skill_summary = ", ".join(memory.strong_areas) if getattr(memory, "strong_areas", None) else ""

        # ── Restore profile data (projects/skills) for personalization ─────
        try:
            profile_res = await db.execute(
                select(StudentProfile).where(StudentProfile.student_id == student_id)
            )
            profile = profile_res.scalar_one_or_none()
            if profile:
                orchestrator._project_summary = profile.project_summary or ""
                orchestrator._has_projects = profile.has_projects
                if not orchestrator._skill_summary:
                    # Fallback to profile skills if memory is new
                    skills_res = await db.execute(
                        select(Skill).where(Skill.student_id == student_id)
                    )
                    s_list = skills_res.scalars().all()
                    orchestrator._skill_summary = ", ".join([s.skill_name for s in s_list])
        except Exception as e:
            logger.warning("submit_answer: could not restore profile data: %s", e)

        # ── Restore current phase and per-phase question count from turns ──────
        # Phase is stored per-turn. We derive the current phase and how many
        # questions have been asked in that phase from persisted turns.
        try:
            all_turns_result = await db.execute(
                select(InterviewTurn.phase)
                .where(InterviewTurn.session_id == session_id)
                .order_by(InterviewTurn.timestamp.asc())
            )
            phase_list = [row[0] for row in all_turns_result.fetchall() if row[0]]
            if phase_list:
                # Current phase = phase of the latest turn
                orchestrator._current_phase = phase_list[-1]
                # Per-phase count = how many turns share the current phase at the tail
                current_ph = phase_list[-1]
                count_in_phase = sum(1 for p in reversed(phase_list) if p == current_ph)
                orchestrator._questions_in_phase = count_in_phase

            # Enforce resume phase for first 2 questions when the candidate has projects.
            # This is derived from persisted turns, not runtime state.
            resume_count_result = await db.execute(
                select(func.count()).select_from(InterviewTurn).where(
                    InterviewTurn.session_id == session_id,
                    InterviewTurn.phase == "resume",
                )
            )
            resume_turns = int(resume_count_result.scalar() or 0)
            if getattr(orchestrator, "_has_projects", False) and resume_turns < 2:
                orchestrator._current_phase = "resume"
                orchestrator._questions_in_phase = resume_turns

            # Topic persistence (without a DB column): deterministically reconstruct
            # which topics were already used in the current phase based on how many
            # questions have been asked in that phase.
            phase_topics = getattr(orchestrator, "_phase_topics", {}).get(orchestrator._current_phase, [])
            used = []
            for item in phase_topics[: max(orchestrator._questions_in_phase, 0)]:
                t = item.get("topic")
                if t:
                    used.append(t)
            orchestrator._previous_topics = used
            if used:
                orchestrator._current_topic = used[-1]

            logger.info(
                "submit_answer: restored orchestrator phase=%s, q_in_phase=%d, q_count=%d",
                orchestrator._current_phase,
                orchestrator._questions_in_phase,
                orchestrator._question_count,
            )
        except Exception as exc:
            logger.warning("submit_answer: could not restore phase state: %s", exc)

        orchestrator.set_state(InterviewState.EVALUATING)
        result = await orchestrator.step(last_answer=answer_text)

        # If the next step is to ask a question, keep it orchestrator-driven.
        # The EVALUATING step returns eval+memory+agent_response; QUESTIONING generates the next question.
        if result.get("action") == "ask_question":
            orchestrator.set_state(InterviewState.QUESTIONING)
            q_result2 = await orchestrator.step(last_answer="")
            if isinstance(q_result2, dict) and (q_result2.get("data") is not None):
                result_data = result.get("data") or {}
                q_data = q_result2.get("data") or {}
                # preserve evaluation/memory/agent_response + attach question
                if "question" in q_data:
                    result_data["question"] = q_data["question"]
                result["data"] = result_data

        # Commit: guarantee answer + evaluation + (optional) next question are durable.
        await db.commit()


        # Map orchestrator output back into the existing SubmitAnswerResponse contract
        data = result.get("data") or {}
        eval_data = data.get("evaluation") or {}
        memory_data = data.get("memory") or {}
        agent_response = data.get("agent_response") or ""

        next_action = result.get("action") or "ask_question"
        next_difficulty = result.get("difficulty") or eval_data.get("next_difficulty") or "medium"

        next_question = None
        if next_action == "ask_question":
            qd = data.get("question") or {}
            if isinstance(qd, dict) and qd.get("question"):
                next_question = QuestionOutput(
                    question_id=qd.get("question_id"),
                    question=qd.get("question", ""),
                    topic=qd.get("topic", "general"),
                    difficulty=qd.get("difficulty", next_difficulty),
                )

        # Normalize evaluation payload to match EvaluationOutput schema requirements.
        # Evaluator/orchestrator may return {communication, concept_depth, confidence} instead.
        def _num(val, default: float = 0.0) -> float:
            try:
                if val is None:
                    return float(default)
                return float(val)
            except Exception:
                return float(default)

        normalized_eval = dict(eval_data) if isinstance(eval_data, dict) else {}
        normalized_eval.setdefault("clarity", _num(normalized_eval.get("clarity", normalized_eval.get("communication")), 0.0))
        normalized_eval.setdefault("depth", _num(normalized_eval.get("depth", normalized_eval.get("concept_depth")), 0.0))
        normalized_eval.setdefault("confidence", _num(normalized_eval.get("confidence"), 0.0))

        # Running average: computed from stored turn evaluation.overall_score (0–10 scale).
        running_avg_score = 0.0
        try:
            turn_evals_result = await db.execute(
                select(InterviewTurn.evaluation).where(InterviewTurn.session_id == session_id)
            )
            scores: list[float] = []
            for (ev,) in turn_evals_result.all():
                if not isinstance(ev, dict):
                    continue
                try:
                    scores.append(float(ev.get("overall_score", 0.0)))
                except Exception:
                    scores.append(0.0)
            if scores:
                running_avg_score = float(round(sum(scores) / len(scores), 2))
        except Exception:
            pass

        return SubmitAnswerResponse(
            evaluation=EvaluationOutput(**normalized_eval),
            memory=MemoryOutput(**memory_data),
            agent_response=agent_response,
            behavior_flag=eval_data.get("behavior_flag", "neutral"),
            next_action=next_action,
            next_difficulty=next_difficulty,
            next_question=next_question,
            running_avg_score=running_avg_score,
        )

    # ── POST /interview/end ───────────────────────────────────────────────

    @staticmethod
    async def end_interview(
        student_id: UUID,
        session_id: UUID,
        db: AsyncSession,
        ended_reason: str = "normal",
    ) -> EndInterviewResponse:
        """End the interview session and generate the final report."""
        llm = get_llm()

        # Update session status
        sess_result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
                InterviewSession.student_id == student_id,
            )
        )
        session = sess_result.scalar_one_or_none()
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        # Mark completion vs early termination using the existing enum.
        # We map early termination to CANCELLED to avoid invalid enum writes.
        if ended_reason != "normal":
            session.status = SessionStatus.CANCELLED
        else:
            session.status = SessionStatus.COMPLETED
        session.end_time = datetime.utcnow()

        # Count total questions via InterviewTurn
        q_count_result = await db.execute(
            select(func.count()).select_from(InterviewTurn).where(
                InterviewTurn.session_id == session_id
            )
        )
        session.total_questions = q_count_result.scalar() or 0

        # Finalization: ensure every stored turn has answer + evaluation before report.
        # This guarantees early termination still produces a complete partial report.
        try:
            turns_result = await db.execute(
                select(InterviewTurn)
                .where(InterviewTurn.session_id == session_id)
                .order_by(InterviewTurn.timestamp.asc())
            )
            turns = list(turns_result.scalars().all())
            if not turns:
                logger.error("end_interview: no turns found for session_id=%s", session_id)
            else:
                for t in turns:
                    if not t.question:
                        logger.error("end_interview: turn %s missing question", getattr(t, "turn_id", "n/a"))
                    if not t.answer or not str(t.answer).strip():
                        t.answer = "Skipped"
                    if not isinstance(t.evaluation, dict) or not t.evaluation:
                        t.evaluation = {
                            "overall_score": 0,
                            "error": "evaluation_failed",
                        }
                await db.flush()
        except Exception as exc:
            logger.exception("end_interview: finalization validation failed (non-fatal)")

        # Commit: ensure session + any turn fixes are durable BEFORE generating report.
        await db.commit()

        # Generate report
        logger.info("end_interview: generating report for session_id=%s", session_id)
        report_data = await generate_report(
            session_id=session_id,
            db=db,
            llm=llm,
            ended_reason=ended_reason,
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

        # Commit all changes — ensure report + session status persist
        await db.commit()
        logger.info(
            "end_interview: committed session_id=%s as %s",
            session_id,
            "CANCELLED" if ended_reason != "normal" else "COMPLETED",
        )

        return EndInterviewResponse(
            session_id=session_id,
            status="terminated" if ended_reason != "normal" else "completed",
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

            # Fallback: compute average from InterviewTurn evaluations
            avg_score_result = await db.execute(
                select(func.avg((cast(func.json_extract(InterviewTurn.evaluation, "$.overall_score"), Integer) / 10.0)))
                .select_from(InterviewTurn)
                .where(
                    InterviewTurn.session_id == session_id,
                    InterviewTurn.evaluation.isnot(None)
                )
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

        qa_list = []
        # Prefer InterviewTurn as source of truth; fall back to legacy Question for order/topic if needed
        turns_result = await db.execute(
            select(InterviewTurn).where(InterviewTurn.session_id == session_id)
        )
        turns = list(turns_result.scalars().all())
        for idx, turn in enumerate(sorted(turns, key=lambda t: t.timestamp)):
            # Extract score from evaluation JSON if present
            score_val = None
            try:
                if turn.evaluation:
                    score_val = int(turn.evaluation.get("overall_score"))
            except Exception:
                pass

            qa_list.append(SessionQuestionAnswer(
                question_order=idx + 1,
                question_text=turn.question or "",
                topic="general",  # Topic can be enriched later from evaluation if needed
                difficulty=turn.difficulty.value if isinstance(turn.difficulty, Difficulty) else str(turn.difficulty),
                answer_text=turn.answer,
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

    # ── GET /interview/{session_id}/report ─────────────────────────────

    @staticmethod
    async def get_session_report(
        student_id: UUID,
        session_id: UUID,
        db: AsyncSession,
    ) -> InterviewSessionReportResponse:
        """Build a full report view for history (works for partial/failed sessions)."""

        sess_result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
                InterviewSession.student_id == student_id,
            )
        )
        session = sess_result.scalar_one_or_none()
        if not session:
            raise ValueError("Session not found or access denied")

        turns_result = await db.execute(
            select(InterviewTurn)
            .where(InterviewTurn.session_id == session_id)
            .order_by(InterviewTurn.timestamp.asc())
        )
        turns = list(turns_result.scalars().all())

        # Determine status for history view
        status_raw = session.status.value if isinstance(session.status, SessionStatus) else str(session.status)
        status = status_raw
        if status_raw != SessionStatus.COMPLETED.value:
            viol_res = await db.execute(
                select(func.count()).select_from(ProctoringViolation).where(
                    ProctoringViolation.session_id == session_id
                )
            )
            viol_count = int(viol_res.scalar() or 0)
            status = "failed" if viol_count > 0 else "partial"

        turn_dicts = []
        for t in turns:
            turn_dicts.append({
                "question": t.question or "",
                "answer": t.answer or "",
                "evaluation": t.evaluation if t.evaluation else {},
            })

        report_dict = build_report(turn_dicts)
        summary_obj = report_dict.get("summary") if isinstance(report_dict, dict) else {}
        if not isinstance(summary_obj, dict):
            summary_obj = {}

        avg_corr = float(summary_obj.get("average_correctness") or 0.0)
        avg_comm = float(summary_obj.get("average_communication") or 0.0)
        avg_conf = float(summary_obj.get("average_confidence") or 0.0)

        # Scores: keep 0-10 scale in response breakdown, but final_score in 0-100
        final_0_10 = float(summary_obj.get("overall_score") or report_dict.get("final_score") or 0.0)
        final_score = max(0.0, min(100.0, (final_0_10 / 10.0) * 100.0))

        # Behavior: best-effort from evaluation payload if present, otherwise use confidence average.
        beh_scores = []
        for t in turns:
            try:
                ev = t.evaluation or {}
                if isinstance(ev, dict) and "behavior_score" in ev:
                    beh_scores.append(float(ev.get("behavior_score") or 0.0) * 10.0)
            except Exception:
                pass
        behavior = (sum(beh_scores) / len(beh_scores)) if beh_scores else avg_conf

        questions = [
            InterviewReportQuestionItem(
                question=td.get("question", ""),
                answer=td.get("answer", ""),
                evaluation=td.get("evaluation", {}) if isinstance(td.get("evaluation"), dict) else {},
            )
            for td in turn_dicts
        ]

        summary_text = ""
        if isinstance(summary_obj.get("communication_summary"), str):
            summary_text = summary_obj.get("communication_summary") or ""
        elif not turn_dicts:
            summary_text = "No answers provided."

        return InterviewSessionReportResponse(
            session_id=session_id,
            status=status,
            final_score=round(final_score, 2),
            scores=InterviewScoreBreakdown(
                technical=round(avg_corr, 2),
                communication=round(avg_comm, 2),
                behavior=round(float(behavior or 0.0), 2),
            ),
            strengths=list(report_dict.get("strengths") or []),
            weaknesses=list(report_dict.get("weaknesses") or []),
            summary=summary_text,
            questions=questions,
            pdf_url=f"/ai/interview/{session_id}/download",
        )

    @staticmethod
    async def get_visualization_report(
        student_id: UUID,
        session_id: UUID,
        db: AsyncSession,
    ) -> dict:
        """Aggregate multi-question performance metrics for visualization.

        Deterministic: relies on stored per-turn evaluation payloads.
        STT robustness is handled upstream by the per-turn evaluator.
        """

        sess_result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.session_id == session_id,
                InterviewSession.student_id == student_id,
            )
        )
        session = sess_result.scalar_one_or_none()
        if not session:
            raise ValueError("Session not found or access denied")

        turns_result = await db.execute(
            select(InterviewTurn)
            .where(InterviewTurn.session_id == session_id)
            .order_by(InterviewTurn.timestamp.asc())
        )
        turns = list(turns_result.scalars().all())

        per_correctness: list[float] = []
        per_communication: list[float] = []
        per_depth: list[float] = []
        per_confidence: list[float] = []
        per_overall: list[float] = []
        dsa_scores: list[float] = []

        strengths: list[str] = []
        weaknesses: list[str] = []
        improvements: list[str] = []

        for t in turns:
            ev = t.evaluation if isinstance(t.evaluation, dict) else {}
            if not ev:
                continue

            corr = ev.get("correctness")
            comm = ev.get("communication")
            depth = ev.get("concept_depth")
            conf = ev.get("confidence")

            if corr is not None:
                per_correctness.append(_clamp_0_10(corr))
            if comm is not None:
                per_communication.append(_clamp_0_10(comm))
            if depth is not None:
                per_depth.append(_clamp_0_10(depth))
            if conf is not None:
                per_confidence.append(_clamp_0_10(conf))

            # Use stored overall_score if present; otherwise compute per-turn approximation.
            o = ev.get("overall_score")
            if o is None:
                o = (
                    _clamp_0_10(corr) * 0.40
                    + _clamp_0_10(comm) * 0.20
                    + _clamp_0_10(depth) * 0.20
                    + _clamp_0_10(conf) * 0.20
                )
            per_overall.append(_clamp_0_10(o))

            if _is_dsa_like_turn(t.question or "", getattr(t, "phase", None)):
                # If evaluator doesn't provide a DSA score explicitly, approximate with correctness+depth.
                dsa_scores.append((_clamp_0_10(corr) * 0.6) + (_clamp_0_10(depth) * 0.4))

            gp = ev.get("good_points")
            if isinstance(gp, list):
                for item in gp:
                    s = str(item).strip()
                    if s and s not in strengths and len(strengths) < 6:
                        strengths.append(s)

            ms = ev.get("mistakes")
            if isinstance(ms, list):
                for item in ms:
                    s = str(item).strip()
                    if s and s not in weaknesses and len(weaknesses) < 6:
                        weaknesses.append(s)

            mp = ev.get("missing_points")
            if isinstance(mp, list):
                for item in mp:
                    s = str(item).strip()
                    if s and s not in improvements and len(improvements) < 6:
                        improvements.append(s)

        avg_correctness = _safe_mean(per_correctness)
        avg_communication = _safe_mean(per_communication)
        avg_depth = _safe_mean(per_depth)
        avg_confidence = _safe_mean(per_confidence)
        avg_dsa = _safe_mean(dsa_scores) if dsa_scores else 0.0

        # Consistency: based on std-dev of per-question overall scores.
        import math

        if per_overall:
            mean_overall = _safe_mean(per_overall)
            variance = _safe_mean([(x - mean_overall) ** 2 for x in per_overall])
            std = math.sqrt(max(0.0, variance))
            # Map higher std => lower consistency. std≈0 => 10. std>=5 => ~0.
            consistency = _clamp_0_10(10.0 - (std * 2.0))
        else:
            consistency = 0.0

        overall_score = (
            (avg_correctness * 0.4)
            + (avg_communication * 0.2)
            + (avg_depth * 0.2)
            + (avg_dsa * 0.1)
            + (avg_confidence * 0.1)
        )
        overall_score = _clamp_0_10(overall_score)

        if overall_score < 4.0:
            rating = "Needs Improvement"
        elif overall_score < 7.0:
            rating = "Average"
        else:
            rating = "Good"

        return {
            "overall_score": round(overall_score, 2),
            "rating": rating,
            "radar": {
                "correctness": round(_clamp_0_10(avg_correctness), 2),
                "communication": round(_clamp_0_10(avg_communication), 2),
                "depth": round(_clamp_0_10(avg_depth), 2),
                "dsa": round(_clamp_0_10(avg_dsa), 2),
                "consistency": round(_clamp_0_10(consistency), 2),
            },
            "summary": {
                "strengths": strengths[:2] if strengths else [],
                "weaknesses": weaknesses[:2] if weaknesses else [],
                "improvements": improvements[:2] if improvements else [],
            },
        }

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

    # ── GET /interview/report/{session_id}/recruiter ──────────────────

    @staticmethod
    async def get_recruiter_report(
        session_id: UUID,
        db: AsyncSession,
    ) -> dict:
        """Fetch the recruiter-facing report for a completed interview."""
        import json as _json

        result = await db.execute(
            select(InterviewReport).where(InterviewReport.session_id == session_id)
        )
        report = result.scalar_one_or_none()
        if report is None:
            raise ValueError(f"No report found for session {session_id}")

        # Try to parse stored recruiter_report JSON
        recruiter_data = {}
        if hasattr(report, "recruiter_report") and report.recruiter_report:
            try:
                recruiter_data = _json.loads(report.recruiter_report) if isinstance(report.recruiter_report, str) else report.recruiter_report
            except Exception:
                recruiter_data = {}

        # Build response with fallbacks
        base = {
            "session_id": str(session_id),
            "final_score": report.final_score,
            "technical_score": recruiter_data.get("technical_score", report.final_score / 10.0 if report.final_score else 0),
            "communication_score": recruiter_data.get("communication_score", 0),
            "behavior_score": recruiter_data.get("behavior_score", 0),
            "recommendation": recruiter_data.get("recommendation", report.recommendation or ""),
            "justification": recruiter_data.get("justification", ""),
            "strengths": recruiter_data.get("strengths", list(report.strengths) if report.strengths else []),
            "weaknesses": recruiter_data.get("weaknesses", list(report.weaknesses) if report.weaknesses else []),
            "technical_assessment": recruiter_data.get("technical_assessment", ""),
            "communication_assessment": recruiter_data.get("communication_assessment", ""),
            "behavior_analysis": recruiter_data.get("behavior_analysis", ""),
        }

        # Include new structured fields if present
        if "critical_issues" in recruiter_data:
            base["critical_issues"] = recruiter_data["critical_issues"]
        if "evaluations" in recruiter_data:
            base["evaluations"] = recruiter_data["evaluations"]

        return base

    # ── GET /interview/report/{session_id}/student ────────────────────

    @staticmethod
    async def get_student_report(
        session_id: UUID,
        db: AsyncSession,
    ) -> dict:
        """Fetch the student-facing report for a completed interview."""
        import json as _json

        result = await db.execute(
            select(InterviewReport).where(InterviewReport.session_id == session_id)
        )
        report = result.scalar_one_or_none()
        if report is None:
            raise ValueError(f"No report found for session {session_id}")

        # Try to parse stored student_report JSON
        student_data = {}
        if hasattr(report, "student_report") and report.student_report:
            try:
                student_data = _json.loads(report.student_report) if isinstance(report.student_report, str) else report.student_report
            except Exception:
                student_data = {}

        base = {
            "session_id": str(session_id),
            "final_score": report.final_score,
            "strengths": student_data.get("strengths", list(report.strengths) if report.strengths else []),
            "weaknesses": student_data.get("areas_to_improve", list(report.weaknesses) if report.weaknesses else []),
            "encouragement": student_data.get("encouragement", ""),
            "learning_resources": student_data.get("learning_resources", []),
            "recommendation": report.recommendation or "",
        }

        # Include new structured fields if present
        if "critical_issues" in student_data:
            base["critical_issues"] = student_data["critical_issues"]
        if "evaluations" in student_data:
            base["evaluations"] = student_data["evaluations"]

        return base
