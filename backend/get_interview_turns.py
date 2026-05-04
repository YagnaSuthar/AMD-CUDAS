#!/usr/bin/env python3
"""Utility: fetch interview turns for a session.

Demonstrates that session.turns is accessible and populated.
"""

import asyncio
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine
from app.models.interview import InterviewSession, InterviewTurn


async def main(session_id: str) -> None:
    sid = UUID(session_id)
    async with engine.begin() as conn:
        # Load session with turns
        result = await conn.execute(
            select(InterviewSession)
            .where(InterviewSession.session_id == sid)
        )
        session = result.scalar_one_or_none()
        if not session:
            print(f"Session {session_id} not found")
            return

        # Load turns
        turns_result = await conn.execute(
            select(InterviewTurn)
            .where(InterviewTurn.session_id == sid)
            .order_by(InterviewTurn.timestamp)
        )
        turns = list(turns_result.scalars().all())

        print(f"Session {session_id} has {len(turns)} turns:")
        for i, t in enumerate(turns, 1):
            print(f"\n--- Turn {i} ---")
            print(f"Question: {t.question}")
            print(f"Answer: {t.answer}")
            print(f"Timestamp: {t.timestamp}")
            print(f"Phase: {t.phase}")
            print(f"Difficulty: {t.difficulty}")
            print(f"Evaluation keys: {list((t.evaluation or {}).keys())}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python get_interview_turns.py <session_id>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
