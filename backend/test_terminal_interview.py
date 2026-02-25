"""
test_terminal_interview.py - Interactive terminal interview using the Agent system.

Usage:
  1. First run: python seed_db.py       (populate DB with test data)
  2. Then run:  python test_terminal_interview.py

The script connects to the database, loads the seeded student/session,
and runs the full interview loop:
  INIT → PROFILING → QUESTIONING ↔ EVALUATING → ENDED (report)
"""

import asyncio
import uuid
import logging
import time

from app.core.database import async_session_factory
from app.models.interview import InterviewSession, SessionStatus, Difficulty
from app.agents.Interview.orchestrator.orchestrator import InterviewOrchestrator, InterviewState
from app.agents.Interview.llm_provider import get_llm
from sqlalchemy import select, update

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Same IDs used in seed_db.py
STUDENT_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
SESSION_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")

# Limit questions for testing (override the orchestrator's default of 15)
MAX_QUESTIONS_FOR_TEST = 3


async def reset_session(session):
    """Reset the interview session to ACTIVE state for a fresh run."""
    await session.execute(
        update(InterviewSession)
        .where(InterviewSession.session_id == SESSION_ID)
        .values(status=SessionStatus.ACTIVE, current_difficulty=Difficulty.MEDIUM, end_time=None)
    )
    await session.flush()


async def run_terminal_interview():
    print("=" * 60)
    print("  🎤 AI INTERVIEW AGENT — Terminal Mode")
    print("=" * 60)
    print()

    # ── Initialize LLM ──────────────────────────────────────────────
    print("Initializing LLM...")
    try:
        llm = get_llm()
        model_name = getattr(llm, "model_name", getattr(llm, "model", "unknown"))
        print(f"  ✓ LLM ready (model: {model_name})")
    except Exception as e:
        print(f"  ✗ Failed to initialize LLM: {e}")
        return
    print()

    # ── Open DB session & verify data exists ────────────────────────
    async with async_session_factory() as db:
        # Verify session exists
        result = await db.execute(
            select(InterviewSession).where(InterviewSession.session_id == SESSION_ID)
        )
        interview = result.scalars().first()
        if interview is None:
            print("  ✗ No interview session found! Run `python seed_db.py` first.")
            return

        print(f"  Student ID  : {STUDENT_ID}")
        print(f"  Session ID  : {SESSION_ID}")
        print(f"  Job Role    : {interview.job_role}")
        print(f"  Difficulty  : {interview.current_difficulty}")
        print()

        # Reset session for fresh run
        await reset_session(db)
        await db.commit()

        # ── Create Orchestrator ─────────────────────────────────
        orchestrator = InterviewOrchestrator(
            student_id=STUDENT_ID,
            session_id=SESSION_ID,
            db=db,
            llm=llm,
        )
        # Override max questions for quick testing
        orchestrator._max_questions = MAX_QUESTIONS_FOR_TEST

        print("=" * 60)
        print(f"  INTERVIEW START (max {MAX_QUESTIONS_FOR_TEST} questions)")
        print("  Type 'quit' to exit early")
        print("=" * 60)
        print()

        # ── Main Interview Loop ─────────────────────────────────
        last_answer = ""
        question_num = 0

        while True:
            state_str = orchestrator.state.value.upper()
            print(f"[State: {state_str}] Processing...", flush=True)

            # Call the orchestrator
            try:
                action_data = await orchestrator.step(last_answer=last_answer)
                await db.commit() # ensure step updates are written
            except Exception as e:
                print(f"\n  ✗ Unexpected error: {e}")
                break

            action = action_data.get("action")
            data = action_data.get("data", {})

            # ── Handle 429 quota errors with auto-retry ─────────
            if action == "error":
                msg = action_data.get("message", "")
                if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                    print(f"\n  ⏳ API Quota Limit Hit. Waiting 60s for reset...")
                    for i in range(60, 0, -1):
                        print(f"\r     Retrying in {i}s...  ", end="", flush=True)
                        await asyncio.sleep(1)
                    print("\r     Retrying now!            ")
                    continue
                else:
                    print(f"\n  ✗ Error: {msg}")
                    break

            # ── Ask question ────────────────────────────────────
            if action == "ask_question":
                question_obj = data.get("question", {})
                q_text = question_obj.get("question", "No question text.")
                q_diff = question_obj.get("difficulty", "medium")
                q_topic = question_obj.get("topic", "general")
                question_num += 1

                print()
                print(f"  ┌─ Question {question_num}/{MAX_QUESTIONS_FOR_TEST} ─────────────────────")
                print(f"  │ Difficulty: {q_diff.upper()}")
                print(f"  │ Topic:      {q_topic}")
                print(f"  │")
                print(f"  │ {q_text}")
                print(f"  └────────────────────────────────────────")
                print()

                # Get user answer
                print("  Your Answer > ", end="", flush=True)
                a = input()
                if a.strip().lower() in ["quit", "exit"]:
                    print("\n  [!] Exiting early.")
                    await db.commit()
                    break
                last_answer = a.strip()

            # ── Evaluation ──────────────────────────────────────
            elif action == "evaluation":
                metrics = data.get("evaluation", {})
                print()
                print(f"  ✓ Evaluation from previous answer:")
                print(f"     Clarity:    {metrics.get('clarity')}/10")
                print(f"     Depth:      {metrics.get('depth')}/10")
                print(f"     Confidence: {metrics.get('confidence')}/10")
                print(f"     Next Diff:  {metrics.get('next_difficulty')}")
                print("-" * 60)
            
            # ── End of Interview ────────────────────────────────
            elif action == "ended":
                metadata = data.get("metadata", {})
                final_status = metadata.get("final_status")
                perf = metadata.get("performance_metrics", {})
                print("=" * 60)
                print("  🏁 INTERVIEW COMPLETE")
                print(f"  Status: {final_status}")
                print(f"  Avg Clarity:    {perf.get('avg_clarity', 0)}")
                print(f"  Avg Depth:      {perf.get('avg_depth', 0)}")
                print(f"  Avg Confidence: {perf.get('avg_confidence', 0)}")
                print("=" * 60)
                await db.commit()
                break

            # Small delay for reading
            time.sleep(1)


if __name__ == "__main__":
    asyncio.run(run_terminal_interview())
