#!/usr/bin/env python3
"""Migration script: create interview_turns table.

Adds InterviewTurn model for structured storage of question+answer+evaluation.
"""

import asyncio
from sqlalchemy import text

from app.core.database import engine


async def main() -> None:
    async with engine.begin() as conn:
        # Create interview_turns table
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS interview_turns (
                    turn_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id UUID NOT NULL REFERENCES interview_sessions(session_id) ON DELETE CASCADE,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    evaluation JSONB,
                    phase VARCHAR(50),
                    difficulty VARCHAR(20)
                );
                """
            )
        )
        # Create index for session_id for fast lookups
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_interview_turns_session_id ON interview_turns(session_id);
                """
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
